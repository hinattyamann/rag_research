"""Source-label integrity, stop-before-expansion, leakage and durable diagnostic resume."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from rag_research.experiments import semantic_diagnostics as module
from rag_research.experiments.frozen_trace import digest, freeze_record
from rag_research.experiments.storage import read_json, write_json
from rag_research.generation.local import GenerationError
from rag_research.retrieval.common import file_hash

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def diagnostic(tmp_path, monkeypatch):
    original = read_json(REPO / "configs/phase11_semantic_diagnostics_v1.json")
    config = yaml.safe_load((REPO / "configs/phase11_semantic_candidate_v1.yaml").read_text())
    config.pop("sampling")
    config["output_constraints"] = "none"
    config["auxiliary_runtime"].update(temperature=0., context_tokens=65536)
    config["diagnostics"] = "plan.json"
    config["prompts"] = {lang: lang + ".yaml" for lang in ("en", "ja")}
    for lang, name in config["prompts"].items():
        value = yaml.safe_load((REPO / f"configs/phase11_bilingual_order_prompts_{lang}_v1.yaml").read_text())
        (tmp_path / name).write_text(yaml.safe_dump(value))
    documents = [{"passage_id": "d1", "title": "Fixture", "text": "A is true."}]
    trace = freeze_record({"record_id": "used-calibration-fixture", "question": "Known question", "answer": "A is false.",
                           "status": "ok", "used_context": documents})
    write_json(tmp_path / "trace.json", trace)
    write_json(tmp_path / "old_audit.json", {"claims": [{"record_id": trace["record_id"], "claim_id": "c1",
               "ambiguous_scope": False, "expected_label": "contradicted"}]})
    known = {"id": "known", "language": "en", "scope": "known_used_calibration",
             **{k: trace[k] for k in ("answer", "question", "documents")},
             "claims": [{"claim_id": "c1", "text": "A is false."}], "expected": {"c1": "contradicted"},
             "expected_reasons": {"c1": "EXPECTED-SECRET"}, "critical_claim_ids": ["c1"],
             "original_record_id": trace["record_id"], "source_trace_sha256": file_hash(tmp_path / "trace.json")}
    cases = [known]
    for lang in ("en", "ja"):
        cases.append({"id": "synthetic-" + lang, "language": lang, "scope": "synthetic_development",
                      "question": "Synthetic question", "answer": "A is true.", "documents": documents,
                      "claims": [{"claim_id": "c1", "text": "A is true."}], "expected": {"c1": "supported"},
                      "expected_reasons": {"c1": "EXPECTED-SECRET"}, "critical_claim_ids": []})
    original.update(cases=cases, max_completion_attempts=6, source_sha256={"trace.json": file_hash(tmp_path / "trace.json")})
    original["expected_annotations"].update(known_trace_expected_source="old_audit.json",
        known_trace_expected_sha256=file_hash(tmp_path / "old_audit.json"))
    write_json(tmp_path / "plan.json", original)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    script = tmp_path / "scripts/run_semantic_diagnostics.py"
    script.parent.mkdir()
    script.write_text("fixed source fixture")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "auxiliary_identity", lambda c: {"test": "identity"})
    monkeypatch.setattr(module, "auxiliary_server_kwargs", lambda c: {})
    monkeypatch.setattr(module, "execution_identity", lambda c: {})
    state = {"calls": [], "servers": 0, "critical_failure": False, "runtime_error": False,
             "allow_answer_context": False}

    class Client:
        def render(self, messages):
            self.messages = deepcopy(messages)
            return json.dumps(messages)

        def tokenize(self, text, *, special=False):
            return list(map(ord, text))

        def complete(self, tokens, config, **kwargs):
            state["calls"].append(deepcopy(self.messages))
            payload = json.loads(self.messages[1]["content"].removeprefix("Input JSON:\n"))
            if state.get("source_reading") and set(payload) == {"question", "documents"}:
                assert "EXPECTED-SECRET" not in json.dumps(self.messages)
                return {"content": json.dumps({"readings": [{"passage_id": d["passage_id"], "actor": "A",
                    "action": "is true", "quote": d["text"]} for d in payload["documents"]]}),
                    "tokens": [1], "stop_type": "eos", "truncated": False}
            assert set(payload) == ({"question", "answer", "claims", "documents"} if state["allow_answer_context"] else
                                    {"question", "claims", "documents"}) | ({"source_reading"} if state.get("source_reading") else set())
            if state["allow_answer_context"]:
                assert payload["answer"] in {"A is false.", "A is true."}
            if state["runtime_error"]:
                raise GenerationError("Synthetic runtime failure")
            label = ("contradicted" if payload["claims"][0]["text"] == "A is false." and
                     not state["critical_failure"] else "supported")
            return {"content": json.dumps({"verdicts": [{"claim_id": "c1", "label": label, "reason": "Fixture",
                "evidence": [{"passage_id": "d1", "quote": "A is true."}]}]}),
                "tokens": [1], "stop_type": "eos", "truncated": False}

    class Server:
        def __init__(self, *args, **kwargs):
            args[1].touch(exist_ok=False)
            state["servers"] += 1
            self.client = Client()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def report(self):
            return {"fixture": True}

    monkeypatch.setattr(module, "LocalServer", Server)
    return path, tmp_path / "data/runs/semantic_diagnostics/fixture", state


@pytest.mark.parametrize("failure", [False, True])
def test_critical_stop_or_expansion_and_resume_without_calls(diagnostic, failure):
    path, output, state = diagnostic
    state["critical_failure"] = failure
    report = module.run(path, output)
    calls, servers = len(state["calls"]), state["servers"]
    assert calls == (2 if failure else 6)
    assert report["critical_passed"] is not failure and report["diagnostic_gate_passed"] is not failure
    assert len(report["not_attempted_ids"]) == (4 if failure else 0)
    if failure:
        assert report["synthetic"]["ja"]["accuracy_of_all_planned"] is None
    assert module.run(path, output) == report
    assert (len(state["calls"]), state["servers"]) == (calls, servers)
    assert "EXPECTED-SECRET" not in json.dumps(state["calls"])
    assert '"expected"' not in json.dumps(state["calls"])
    assert report["gate11_passed"] is False


def test_runtime_failure_retained_no_retry_or_extra_server(diagnostic):
    path, output, state = diagnostic
    state["runtime_error"] = True
    report = module.run(path, output)
    assert report["completed_conditions"] == 1 and report["cost_incomplete"]
    assert not report["diagnostic_gate_passed"]
    module.run(path, output)
    assert len(state["calls"]) == state["servers"] == 1


def test_interrupted_journal_is_unknown_without_restart_or_resampling(diagnostic):
    path, output, state = diagnostic
    module.run(path, output)
    task_path = output / "tasks/known-original.json"
    task = read_json(task_path)
    task.pop("result_sha256")
    task["status"] = "started"
    write_json(task_path, task)
    before = len(state["calls"]), state["servers"]
    report = module.run(path, output)
    assert (len(state["calls"]), state["servers"]) == before
    assert report["cost_incomplete"] and not report["diagnostic_gate_passed"]
    assert read_json(task_path)["error_code"] == "interrupted_unknown_outcome"
    assert not report["not_attempted_ids"] and report["completed_conditions"] == 6


def test_preserved_source_and_expected_labels_cannot_be_silently_changed(diagnostic):
    path, output, state = diagnostic
    plan_path = path.parent / "plan.json"
    plan = read_json(plan_path)
    plan["cases"][0]["expected"]["c1"] = "supported"
    write_json(plan_path, plan)
    with pytest.raises(ValueError, match="expected labels differ"):
        module.run(path, output)
    assert not state["calls"] and state["servers"] == 0


def test_protocol_hash_change_rejected_before_model_restart(diagnostic):
    path, output, state = diagnostic
    module.run(path, output)
    before = len(state["calls"]), state["servers"]
    config = yaml.safe_load(path.read_text())
    config["study_version"] += "-changed"
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="binding changed"):
        module.run(path, output)
    assert (len(state["calls"]), state["servers"]) == before


def test_clear_negative_false_support_fails_even_when_accuracy_above_threshold():
    plan = {"cases": [], "orders": ["original", "reversed"]}
    results = {}
    for lang in ("en", "ja"):
        for n in range(20):
            case = {"id": lang + str(n), "language": lang, "scope": "synthetic_development",
                    "critical_claim_ids": [], "expected": {"c1": "not_supported"}}
            plan["cases"].append(case)
            for order in plan["orders"]:
                results[case["id"] + "-" + order] = {"status": "ok", "parsed": {"verdicts": [
                    {"claim_id": "c1", "label": "supported" if n == 0 else "not_supported"}]}}
    gate = module.assess(plan, results)
    assert all(m["accuracy_of_all_planned"] == .95 for m in gate["synthetic"].values())
    assert not gate["diagnostic_gate_passed"]
    assert digest(plan)


@pytest.mark.parametrize("partial", [False, True])
def test_claimwise_diagnostic_uses_real_child_tasks_and_cached_resume(diagnostic, monkeypatch, partial):
    path, output, state = diagnostic
    config = yaml.safe_load(path.read_text())
    config["verification_mode"] = "claimwise-v1"
    path.write_text(yaml.safe_dump(config))
    plan_path = path.parent / "plan.json"
    plan = read_json(plan_path)
    plan["verification_mode"] = "claimwise-v1"
    write_json(plan_path, plan)
    for name in config["prompts"].values():
        p = path.parent / name
        prompt = yaml.safe_load(p.read_text())
        prompt.pop("judge_payload")
        prompt["tasks"]["verify_claims"]["input_fields"] = ["question", "answer", "claims", "documents"]
        p.write_text(yaml.safe_dump(prompt))
    state["allow_answer_context"] = True
    if partial:
        from rag_research.evaluation.claimwise import derived
        from rag_research.experiments.storage import checkpoint

        original = module.verify_once

        def interrupted(client, generation, prompts, payload, task_path, binding, **kwargs):
            if task_path.stem.startswith("synthetic-"):
                raise KeyboardInterrupt()
            return original(client, generation, prompts, payload, task_path, binding, **kwargs)

        monkeypatch.setattr(module, "verify_once", interrupted)
        with pytest.raises(KeyboardInterrupt):
            module.run(path, output)
        assert len(state["calls"]) == 2
        monkeypatch.setattr(module, "verify_once", original)
        task_path = output / "tasks/known-reversed.json"
        saved = read_json(task_path)
        base = {k: saved[k] for k in ("schema_version", "task", "execution_mode", "request_sha256", "binding", "expected_claim_ids")}
        checkpoint(task_path, derived(task_path, base, []))
        assert (output / "server-1.log").exists() and not (output / "session-1.json").exists()
    report = module.run(path, output)
    assert report["diagnostic_gate_passed"] and report["completion_attempts_recorded"] == 6
    assert len(list((output / "tasks").glob("*.claims/*.json"))) == 6
    assert module.run(path, output) == report
    assert len(state["calls"]) == 6 and state["servers"] == (2 if partial else 1)


def test_source_reading_diagnostic_counts_both_stages_and_resumes_without_calls(diagnostic):
    path, output, state = diagnostic
    config = yaml.safe_load(path.read_text())
    config["verification_mode"] = "source-reading-v1"
    config["tasks"]["read_sources"] = {"max_output_tokens": 512}
    path.write_text(yaml.safe_dump(config))
    plan_path = path.parent / "plan.json"
    plan = read_json(plan_path)
    plan.update(verification_mode="source-reading-v1", max_completion_attempts=12)
    write_json(plan_path, plan)
    for name in config["prompts"].values():
        p = path.parent / name
        prompt = yaml.safe_load(p.read_text())
        prompt.pop("judge_payload")
        prompt["source_reading_auxiliary"] = "untrusted_reading_v1"
        prompt["tasks"]["verify_claims"]["input_fields"] = ["question", "answer", "claims", "documents", "source_reading"]
        prompt["tasks"]["read_sources"] = {"input_fields": ["question", "documents"], "system": "Read fixture."}
        p.write_text(yaml.safe_dump(prompt))
    state.update(allow_answer_context=True, source_reading=True)
    report = module.run(path, output)
    assert report["diagnostic_gate_passed"] and report["completion_attempts_recorded"] == 12
    assert len(list((output / "tasks").glob("*.reading.json"))) == 6
    assert module.run(path, output) == report and len(state["calls"]) == 12 and state["servers"] == 1
