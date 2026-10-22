"""Independent Draft-7 checks; provider/audit doubles do not prove native decoding."""

import hashlib
import importlib.util
import itertools
import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft7Validator

from rag_research.evaluation import tasks
from rag_research.evaluation.schema import cited_verdict_schema, object_schema
from rag_research.experiments.protocol import task_config, validate_task_contract
from rag_research.generation.json_grammar import closing_tag_grammar

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def payload():
    return {"question": "Which fact?", "answer": "Untrusted draft.",
        "claims": [{"claim_id": "c1", "text": "A fixed claim."}, {"claim_id": "c2", "text": "Another claim."}],
        "documents": [{"passage_id": "b", "title": "B", "text": "B source."},
                      {"passage_id": "a", "title": "A", "text": "A source."}]}


def output(conflict=False, complete=False, citations=()):
    return {"verdicts": [{"claim_id": key, "has_explicit_conflict": conflict, "all_details_supported": complete,
        "reason": "Synthetic comparison.", "evidence_ids": list(citations)} for key in ("c1", "c2")]}


@pytest.mark.parametrize("conflict,complete,count", list(itertools.product((False, True), (False, True), range(3))))
def test_every_state_and_citation_cardinality_with_standard_validator(payload, conflict, complete, count):
    schema = cited_verdict_schema(payload, boolean_checks=True, require_cited_decisions=True)
    Draft7Validator.check_schema(schema)
    expected = not (conflict and complete) and (count > 0 or not (conflict or complete))
    assert Draft7Validator(schema).is_valid(output(conflict, complete, ["a", "b"][:count])) is expected


def test_old_v2_schema_and_grammar_are_byte_identical_to_prechange_baseline(payload):
    schema = cited_verdict_schema(payload, boolean_checks=True)
    encoded = json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    # Captured from e4af281 before this implementation, using the same fixed IDs.
    assert hashlib.sha256(encoded).hexdigest() == "dfbc2de2f0977829e24025e1808a2d8defef0425f3b61ab7c3d9e91e68728fd6"
    grammar = closing_tag_grammar(schema, bounded_whitespace=True)
    assert hashlib.sha256(grammar.encode()).hexdigest() == "39fa8eee4c849b69aa56f2b7189bc7b81f25ad787aa84496bf65b55487133273"
    assert Draft7Validator(schema).is_valid(output(False, True, []))  # old schema; parser still rejects


def test_order_independence_no_gold_or_semantic_text_in_schema(payload):
    schema = cited_verdict_schema(payload, boolean_checks=True, require_cited_decisions=True)
    changed = deepcopy(payload)
    changed.update(question="A different question", answer="A different draft", reference_answer="SECRET")
    changed["claims"] = [{**r, "text": "Different claim content"} for r in changed["claims"]]
    changed["documents"] = [{**r, "title": "Different title", "text": "Different text"}
                            for r in reversed(changed["documents"])]
    other = cited_verdict_schema(changed, boolean_checks=True, require_cited_decisions=True)
    assert other == schema and "SECRET" not in json.dumps(schema)
    assert closing_tag_grammar(schema) == closing_tag_grammar(other)
    variants = schema["properties"]["verdicts"]["items"][0]["anyOf"]
    assert len(variants) == 3 and all(v["properties"]["evidence_ids"]["items"]["enum"] == ["a", "b"] for v in variants)


@pytest.mark.parametrize("change", ["unknown_id", "too_many", "wrong_claim_order", "missing_claim", "extra_field", "integer_boolean"])
def test_new_schema_rejects_other_structural_changes(payload, change):
    value = output(False, True, ["a"])
    if change == "unknown_id":
        value["verdicts"][0]["evidence_ids"] = ["not-given"]
    elif change == "too_many":
        value["verdicts"][0]["evidence_ids"] = ["a"] * 3
    elif change == "wrong_claim_order":
        value["verdicts"].reverse()
    elif change == "missing_claim":
        value["verdicts"].pop()
    elif change == "extra_field":
        value["verdicts"][0]["gold_label"] = "supported"
    else:
        value["verdicts"][0]["has_explicit_conflict"] = 0
    validator = Draft7Validator(cited_verdict_schema(payload, boolean_checks=True, require_cited_decisions=True))
    assert not validator.is_valid(value)


@pytest.mark.parametrize("node", [{"anyOf": []}, {"anyOf": [{"const": True}], "type": "boolean"},
    {"anyOf": [None]}, {"anyOf": [{"type": "number"}]}, {"oneOf": [{"const": True}]}])
def test_union_compiler_keeps_closed_subset(node):
    with pytest.raises(ValueError):
        closing_tag_grammar(object_schema({"field": node}))


def configuration():
    config = yaml.safe_load((ROOT / "configs/phase11_semantic_candidate_v14.yaml").read_text())
    prompts = yaml.safe_load((ROOT / config["prompts"]["en"]).read_text())
    config["output_constraints"] = "thinking_json_passage_ids_v3"
    return config, prompts


@pytest.mark.parametrize("change", [None, "joint", "reader", "no_checks", "no_grammar"])
def test_new_protocol_is_explicit_direct_boolean_candidate(change):
    config, prompts = configuration()
    if change == "joint":
        config["verification_mode"] = "joint"
    elif change == "reader":
        config["verification_mode"] = "source-reading-v1"
    elif change == "no_checks":
        prompts.pop("judge_checks")
    elif change == "no_grammar":
        config["sampling"]["final_json_grammar"] = False
    if change:
        with pytest.raises(ValueError, match="Cited-decision grammar"):
            validate_task_contract(config, prompts)
    else:
        validate_task_contract(config, prompts)


@pytest.mark.parametrize("citations,expected_status", [(["a"], "ok"), ([], "error")])
def test_pipeline_new_schema_and_cache_preserve_failed_v2_without_repair(tmp_path, monkeypatch, payload, citations, expected_status):
    config, prompts = configuration()
    # Native end-marker/settings checks have separate real probes; this test
    # exercises the real task/cache/parser with a provider that can violate grammar.
    monkeypatch.setattr(tasks, "audit_reasoning_budget", lambda *a, **k: {"test_double": True})
    monkeypatch.setattr(tasks, "audit_final_json_grammar", lambda *a, **k: {"test_double": True})

    class Client:
        calls = 0
        schema = None

        def render(self, messages):
            return json.dumps(messages)

        def tokenize(self, text, *, special):
            return [1] * 20

        def complete(self, tokens, settings, *, json_schema):
            self.calls += 1
            self.schema = json_schema
            return {"content": "<think>Synthetic.</think>" + json.dumps(output(False, True, citations)),
                    "tokens": [1] * 25, "stop_type": "eos", "truncated": False}

    client, path = Client(), tmp_path / "task.json"
    settings = task_config(config, "verify_claims")
    old = tasks.execute_task(client, settings, prompts, "verify_claims", payload, path, {},
                             constraints="thinking_json_passage_ids_v2")
    assert old["status"] == expected_status
    before, count = path.read_bytes(), client.calls
    with pytest.raises(ValueError, match="input hash mismatch"):
        tasks.execute_task(client, settings, prompts, "verify_claims", payload, path, {},
                           constraints="thinking_json_passage_ids_v3")
    assert path.read_bytes() == before and client.calls == count
    new_path = tmp_path / "new-task.json"
    result = tasks.execute_task(client, settings, prompts, "verify_claims", payload, new_path, {},
                                constraints="thinking_json_passage_ids_v3")
    assert result["status"] == expected_status
    assert client.schema == cited_verdict_schema(payload, boolean_checks=True, require_cited_decisions=True)
    cached = tasks.execute_task(client, settings, prompts, "verify_claims", payload, new_path, {},
                                constraints="thinking_json_passage_ids_v3")
    assert cached == result and client.calls == count + 1
    if expected_status == "error":
        assert result["error"] == "Supported/contradicted needs evidence" and result["parsed"] is None
    else:
        assert result["parsed"]["score"] == 1 and result["input_tokens"] == 20


def test_native_probe_keeps_six_old_cases_and_exercises_all_new_branches():
    spec = importlib.util.spec_from_file_location("cited_probe", ROOT / "scripts/probe_final_json_boundary.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    previous = probe.cases()
    encoded = json.dumps(previous, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(encoded).hexdigest() == "33d0594e05c8e9c8e4b2d5b6ee78071584f8c298956a9f9d1dd327cd6f78f91a"
    planned = probe.cases(constraints="thinking_json_passage_ids_v3")
    assert len(planned) == 10 and planned[:6] == previous
    for case in planned[6:]:
        validator = Draft7Validator(case["schema"])
        Draft7Validator.check_schema(case["schema"])
        closing_tag_grammar(case["schema"], bounded_whitespace=True)
        for conflict, complete, count in itertools.product((False, True), (False, True), range(3)):
            value = output(conflict, complete, ["a", "b"][:count])
            value["verdicts"] = value["verdicts"][:1]
            assert probe.conforms(case, value) == validator.is_valid(value)
