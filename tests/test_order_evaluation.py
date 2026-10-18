"""Research validity boundaries: fixed inputs, real repeats, failure preservation and resume."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from rag_research.evaluation.claims import parse_claims
from rag_research.evaluation.judge import parse_verdicts
from rag_research.evaluation.order import trial_plan
from rag_research.evaluation.schema import output_schema, quote_candidates
from rag_research.evaluation.tasks import execute_task
from rag_research.experiments.decisions import decide
from rag_research.experiments.frozen_trace import assert_same_evidence, digest, freeze_record
from rag_research.experiments.order_runner import evaluate_traces, group_summary, load_traces
from rag_research.experiments.protocol import build_messages, load_protocol, task_config
from rag_research.experiments.storage import read_json, run_lock, write_json
from rag_research.generation.config import GenerationConfig
from rag_research.generation.local import GenerationError, LlamaClient

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def protocol():
    return load_protocol(ROOT / "configs/order_phase8_v5.yaml")[:2]


@pytest.fixture
def trace():
    return freeze_record({"record_id": "development-q", "question": "Q?", "answer": "A. B.",
                          "status": "ok", "reference_answer": "DO NOT LEAK",
                          "used_context": [{"passage_id": str(i), "title": f"T{i}",
                                            "text": f"Evidence {i}."} for i in range(10)]})


class Client:
    def __init__(self, *, malformed=False, transport_error=False, token_count=20):
        self.calls = []
        self.messages = None
        self.malformed = malformed
        self.transport_error = transport_error
        self.token_count = token_count
        self.schemas = []

    def render(self, messages):
        self.messages = deepcopy(messages)
        return json.dumps(messages)

    def tokenize(self, text, *, special=False):
        assert special
        return [1] * self.token_count

    def complete(self, tokens, config, **kwargs):
        self.calls.append(deepcopy(self.messages))
        self.schemas.append(kwargs.get("json_schema"))
        if self.transport_error:
            raise GenerationError("test transport failure")
        payload = json.loads(self.messages[1]["content"].removeprefix("Input JSON:\n"))
        if set(payload) == {"answer"}:
            value = {"claims": [{"claim_id": "c1", "text": "A."}]}
        else:
            document = payload["documents"][0]
            value = {"verdicts": [{"claim_id": "c1", "label": "supported", "reason": "Test",
                                    "evidence": [{"passage_id": document["passage_id"],
                                                  "quote": document["text"]}]}]}
        return {"content": "invalid" if self.malformed else json.dumps(value),
                "stop_type": "eos", "tokens": [1, 2], "truncated": False}


def test_freeze_drops_annotations_and_copies_evidence(trace):
    assert "reference_answer" not in trace
    changed = deepcopy(trace["documents"])
    changed[0]["text"] += " changed"
    with pytest.raises(ValueError, match="changed evidence"):
        assert_same_evidence(trace["documents"], changed)
    assert_same_evidence(trace["documents"], trace["documents"][::-1])


def test_gold_field_inside_evidence_is_rejected(trace):
    documents = deepcopy(trace["documents"])
    documents[0]["is_gold"] = True
    with pytest.raises(ValueError, match="Unexpected evidence"):
        assert_same_evidence(trace["documents"], documents)


def test_plan_reproducible_nine_calls_and_one_shared_trial(protocol, trace):
    config, _ = protocol
    plan = trial_plan(trace, config)
    assert trial_plan(trace, config) == plan
    assert len(plan["trials"]) == 9
    assert set(plan["order_group"]) & set(plan["repeat_group"]) == {"original"}
    assert len({tuple(t["document_ids"]) for t in plan["trials"]}) == 5
    for trial in plan["trials"]:
        assert set(trial["document_ids"]) == {d["passage_id"] for d in trace["documents"]}


def test_single_document_deduplicates_orders_but_keeps_real_repeats(protocol, trace):
    config, _ = protocol
    trace["documents"] = trace["documents"][:1]
    plan = trial_plan(trace, config)
    assert len(plan["trials"]) == 5
    assert plan["order_group"] == ["original"]
    assert len(plan["duplicate_order_aliases"]) == 4
    assert len(plan["repeat_group"]) == 5


@pytest.mark.parametrize("text", [
    '{"claims":[],"score":1}', '{"claims":[{"claim_id":"c2","text":"A"}]}',
    '{"claims":[{"claim_id":"c1","text":""}]}', '{"claims":[],"claims":[]}',
    '```json\n{"claims":[]}\n```', '{"claims":[{"claim_id":"c1","text":"A","gold":true}]}',
])
def test_invalid_extraction_is_not_treated_as_no_claims(text):
    with pytest.raises(ValueError):
        parse_claims(text)
    assert parse_claims('{"claims":[]}') == []


def verdict():
    return {"verdicts": [{"claim_id": "c1", "label": "supported", "reason": "Because",
                          "evidence": [{"passage_id": "p", "quote": "Exact evidence."}]}]}


@pytest.mark.parametrize("alter", [
    lambda v: v["verdicts"][0].update(claim_id="c2"),
    lambda v: v["verdicts"].append(deepcopy(v["verdicts"][0])),
    lambda v: v["verdicts"][0].update(label="partially_supported"),
    lambda v: v["verdicts"][0].update(evidence=[]),
    lambda v: v["verdicts"][0]["evidence"][0].update(passage_id="unknown"),
    lambda v: v["verdicts"][0]["evidence"][0].update(quote="Paraphrased evidence."),
    lambda v: v["verdicts"][0]["evidence"][0].update(quote=""),
    lambda v: v.update(score=1),
])
def test_verdict_boundaries_prevent_fake_valid_scores(alter):
    value = verdict()
    alter(value)
    with pytest.raises(ValueError):
        parse_verdicts(json.dumps(value), [{"claim_id": "c1", "text": "A"}],
                       [{"passage_id": "p", "title": "T", "text": "Exact evidence."}])


def test_score_is_computed_from_all_fixed_claims():
    value = verdict()
    value["verdicts"].append({"claim_id": "c2", "label": "not_supported", "evidence": [],
                              "reason": "No support"})
    result = parse_verdicts(json.dumps(value),
                            [{"claim_id": "c1", "text": "A"}, {"claim_id": "c2", "text": "B"}],
                            [{"passage_id": "p", "title": "T", "text": "Exact evidence."}])
    assert result["score"] == 0.5
    assert decide(0.7, 0.7)["decision"] == "accept"
    assert decide(0.699, 0.7)["decision"] == "rewrite"
    assert decide(None, 0.7)["action"] == "keep_initial_fallback"


def test_no_leakage_in_all_three_task_whitelists(protocol, trace):
    _, prompts = protocol
    with pytest.raises(ValueError, match="forbidden"):
        build_messages(prompts, "extract_claims", {"answer": "A", "question": "Q"})
    with pytest.raises(ValueError, match="Unexpected evidence"):
        build_messages(prompts, "verify_claims", {"answer": "A", "question": "Q", "claims": [],
                                                 "documents": [{**trace["documents"][0],
                                                                "reference": "LEAK"}]})


def test_phase8_rejects_rewrite_before_any_runtime_call(protocol, trace, tmp_path):
    config, prompts = protocol
    client = Client()
    with pytest.raises(ValueError, match="does not generate rewrite"):
        execute_task(client, task_config(config, "rewrite_answer"), prompts, "rewrite_answer",
                     {"answer": trace["answer"], "question": trace["question"],
                      "documents": trace["documents"]}, tmp_path / "rewrite.json", {})
    assert client.calls == []
    assert not (tmp_path / "rewrite.json").exists()


def test_empty_claims_on_prose_warns_without_inventing_claims(protocol, tmp_path):
    config, prompts = protocol
    client = Client()
    client.complete = lambda *args: {"content": '{"claims":[]}', "tokens": [1],
                                     "stop_type": "eos"}
    result = execute_task(client, task_config(config, "extract_claims"), prompts, "extract_claims",
                          {"answer": "[p1] The library opens on Monday."}, tmp_path / "task.json", {})
    assert result["audit_warnings"] == ["empty_claims_on_prose_requires_review"]
    assert result["status"] == "not_applicable"
    assert result["parsed"]["claims"] == []


def test_full_execution_fixed_claims_real_repeats_and_resume(protocol, trace, tmp_path):
    config, prompts = protocol
    manifest = {"traces": [{"directory": "q", "plan": trial_plan(trace, config)}]}
    client = Client()
    records, results = evaluate_traces(client, config, prompts, [trace], manifest, tmp_path)
    assert len(client.calls) == 10  # one extraction and nine real verifier completions
    assert all(client.schemas)
    assert len({digest(s) for s in client.schemas[1:]}) == 1
    assert len(results) == 10
    inputs = [json.loads(m[1]["content"].removeprefix("Input JSON:\n")) for m in client.calls]
    assert inputs[0] == {"answer": trace["answer"]}
    for payload in inputs[1:]:
        assert payload["answer"] == trace["answer"]
        assert payload["claims"] == [{"claim_id": "c1", "text": "A."}]
        assert_same_evidence(trace["documents"], payload["documents"])
    original_inputs = [p for p in inputs[1:] if p["documents"] == trace["documents"]]
    assert len(original_inputs) == 5
    records_again, _ = evaluate_traces(client, config, prompts, [trace], manifest, tmp_path)
    assert len(client.calls) == 10
    assert records_again == records
    # A changed protocol cannot reuse existing extraction, even for the same answer.
    with pytest.raises(ValueError, match="input hash mismatch"):
        evaluate_traces(client, config, prompts, [trace], {**manifest, "version": "changed"}, tmp_path)


@pytest.mark.parametrize("mode", ["malformed", "transport_error", "overflow", "no_claims"])
def test_failures_do_not_become_scores_or_trigger_hidden_retries(protocol, tmp_path, mode):
    config, prompts = protocol
    client = Client(malformed=mode == "malformed", transport_error=mode == "transport_error",
                    token_count=9000 if mode == "overflow" else 20)
    if mode == "no_claims":
        client.complete = lambda *args: {"content": '{"claims":[]}', "tokens": [1],
                                         "stop_type": "eos"}
    path = tmp_path / "task.json"
    result = execute_task(client, task_config(config, "extract_claims"), prompts, "extract_claims",
                          {"answer": "A"}, path, {"trace": "frozen"})
    assert result["status"] == ("not_applicable" if mode == "no_claims" else "error")
    before = len(client.calls)
    assert execute_task(client, task_config(config, "extract_claims"), prompts, "extract_claims",
                        {"answer": "A"}, path, {"trace": "frozen"}) == result
    assert len(client.calls) == before
    assert not client.calls if mode == "overflow" else True


def test_interrupted_unknown_result_is_preserved_without_rerun(protocol, tmp_path):
    config, prompts = protocol
    path = tmp_path / "task.json"
    client = Client()
    result = execute_task(client, task_config(config, "extract_claims"), prompts, "extract_claims",
                          {"answer": "A"}, path, {})
    result.pop("result_sha256")
    result.update(status="started", parsed=None)
    write_json(path, result)
    resumed = execute_task(client, task_config(config, "extract_claims"), prompts, "extract_claims",
                           {"answer": "A"}, path, {})
    assert resumed["error_code"] == "interrupted_unknown_outcome"
    assert resumed["cost_incomplete"]
    assert len(client.calls) == 1


def test_modified_saved_result_is_rejected(protocol, tmp_path):
    config, prompts = protocol
    path = tmp_path / "task.json"
    client = Client()
    execute_task(client, task_config(config, "extract_claims"), prompts, "extract_claims",
                 {"answer": "A"}, path, {})
    modified = read_json(path)
    modified["parsed"]["claims"] = []
    write_json(path, modified)
    with pytest.raises(ValueError, match="Checkpoint hash"):
        execute_task(client, task_config(config, "extract_claims"), prompts, "extract_claims",
                     {"answer": "A"}, path, {})


def test_input_overflow_preserves_exact_prompt_without_completion(protocol, tmp_path):
    _, prompts = protocol
    client = Client(token_count=90)
    path = tmp_path / "task.json"
    result = execute_task(client, GenerationConfig(context_tokens=100, max_output_tokens=11),
                          prompts, "extract_claims", {"answer": "A"}, path, {})
    assert result["error_code"] == "input_overflow"
    assert result["input_tokens"] == 90 and result["prompt_tokens"] == [1] * 90
    assert client.calls == []


def test_group_summary_excludes_failures_instead_of_counting_as_agreement():
    rows = [{"trial_id": str(i), "status": status, "decision": decision}
            for i, (status, decision) in enumerate(
                [("ok", "accept"), ("ok", "rewrite"), ("ok", "accept"), ("error", "unscorable")])]
    result = group_summary(rows, ["0", "1", "2", "3"])
    assert result["planned_trials"] == 4 and result["valid_trials"] == 3
    assert result["valid_pairs"] == 3 and result["disagreeing_pairs"] == 2


def test_lock_blocks_concurrent_run_and_releases(tmp_path):
    with run_lock(tmp_path):
        with pytest.raises((ValueError, OSError)):
            with run_lock(tmp_path):
                pytest.fail("Concurrent run was allowed")
    with run_lock(tmp_path):
        assert digest("released")


@pytest.mark.parametrize("change", ["split", "question", "config", "model"])
def test_baseline_provenance_mismatch_is_rejected_before_inference(
    protocol, trace, tmp_path, monkeypatch, change
):
    import yaml

    from rag_research.experiments import order_runner
    from rag_research.generation.artifacts import model_identity
    from rag_research.retrieval.common import file_hash

    config, _ = protocol
    config = deepcopy(config)
    config["data"]["qa_path"] = "development.jsonl"
    config["data"]["preflight_baseline_answers"] = "unrelated/answers.jsonl"
    config["baseline_config"] = "baseline.yaml"
    qa = {"record_id": trace["record_id"], "question": trace["question"],
          "is_answerable": True, "research_split": "development"}
    if change == "split":
        qa["research_split"] = "evaluation"
    if change == "question":
        qa["question"] = "A different question"
    (tmp_path / "development.jsonl").write_text(json.dumps(qa) + "\n", encoding="utf-8")
    (tmp_path / "baseline.yaml").write_text(yaml.safe_dump({"condition": "fixed"}), encoding="utf-8")
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/prompts.yaml").write_text("fixed prompt", encoding="utf-8")
    row = {"record_id": trace["record_id"], "question": trace["question"], "answer": trace["answer"],
           "status": "ok", "used_context": trace["documents"]}
    answers = tmp_path / "answers.jsonl"
    answers.write_text(json.dumps(row) + "\n", encoding="utf-8")
    provenance = {"status": "completed", "split": "development", "config": {"condition": "fixed"},
                  "config_sha256": file_hash(tmp_path / "baseline.yaml"),
                  "development_sha256": file_hash(tmp_path / "development.jsonl"),
                  "prompts_sha256": file_hash(tmp_path / "configs/prompts.yaml"),
                  "generator": model_identity(), "questions": [{"record_id": trace["record_id"]}]}
    if change == "config":
        provenance["config"]["condition"] = "changed"
    if change == "model":
        provenance["generator"] = {"model_id": "another-model"}
    write_json(tmp_path / "run_manifest.json", provenance)
    monkeypatch.setattr(order_runner, "ROOT", tmp_path)
    with pytest.raises(ValueError):
        load_traces(config, answers)


def test_quote_choices_are_exact_and_decoder_schema_does_not_change_with_order(trace):
    text = "First fact .  Second `` quoted '' fact ; third fact."
    candidates = quote_candidates(text)
    assert text in candidates
    assert all(c in text and c for c in candidates)
    assert any("Second `` quoted '' fact" in c for c in candidates)
    claims = [{"claim_id": "c1", "text": "A"}]
    payload = {"claims": claims, "documents": trace["documents"]}
    original = output_schema("verify_claims", payload)
    reversed_schema = output_schema("verify_claims", {**payload,
                                                      "documents": trace["documents"][::-1]})
    assert original == reversed_schema
    assert "DO NOT LEAK" not in json.dumps(original)
    bounded = output_schema("verify_claims", payload, bounded=True)
    assert bounded == output_schema("verify_claims", {**payload,
                                    "documents": trace["documents"][::-1]}, bounded=True)
    fixed_verdict = bounded["properties"]["verdicts"]["items"][0]["properties"]
    assert fixed_verdict["claim_id"] == {"const": "c1"}
    assert fixed_verdict["evidence"]["maxItems"] == 2
    assert fixed_verdict["reason"]["maxLength"] == 200


def test_local_completion_baseline_payload_unchanged_without_schema():
    client = LlamaClient(12345)
    requests = []
    client.request = lambda route, payload: requests.append((route, payload)) or {}
    config = GenerationConfig()
    client.complete([1, 2], config)
    assert "json_schema" not in requests[0][1]
    schema = {"type": "object"}
    client.complete([1, 2], config, json_schema=schema)
    assert requests[1][1]["json_schema"] == schema
    assert {k: v for k, v in requests[1][1].items() if k != "json_schema"} == requests[0][1]
    assert client.completion_attempts == 2


@pytest.mark.parametrize("flags", [{"stop_type": "limit"}, {"truncated": True}])
def test_incomplete_or_truncated_valid_json_is_still_a_failure(protocol, tmp_path, flags):
    config, prompts = protocol
    client = Client()
    client.complete = lambda *args: {"content": '{"claims":[]}', "tokens": [1],
                                     "stop_type": "eos", **flags}
    result = execute_task(client, task_config(config, "extract_claims"), prompts, "extract_claims",
                          {"answer": "A"}, tmp_path / "task.json", {})
    assert result["status"] == "error" and result["parsed"] is None
