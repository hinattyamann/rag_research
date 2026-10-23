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


def prepare_regression_fixture(diagnostic):
    path, output, state = diagnostic
    config = yaml.safe_load(path.read_text())
    config["verification_mode"] = "source-reading-v1"
    config["tasks"]["read_sources"] = {"max_output_tokens": 512}
    for name in config["prompts"].values():
        p = path.parent / name
        prompt = yaml.safe_load(p.read_text())
        prompt.pop("judge_payload")
        prompt["source_reading_auxiliary"] = "untrusted_reading_v1"
        prompt["tasks"]["verify_claims"]["input_fields"] = ["question", "answer", "claims", "documents", "source_reading"]
        prompt["tasks"]["read_sources"] = {"input_fields": ["question", "documents"], "system": "Read fixture."}
        p.write_text(yaml.safe_dump(prompt))
    path.write_text(yaml.safe_dump(config))
    plan_path = path.parent / "plan.json"
    plan = read_json(plan_path)
    old = read_json(path.parent / "old_audit.json")
    annotations = deepcopy(old["claims"])
    for case in plan["cases"][1:]:
        case["scope"] = "known_used_development"
        trace = freeze_record({"record_id": case["id"], "status": "ok", "question": case["question"],
                               "answer": case["answer"], "used_context": case["documents"]})
        p = path.parent / (case["id"] + ".json")
        write_json(p, trace)
        case.update(original_record_id=case["id"], source_trace_sha256=file_hash(p))
        plan["source_sha256"][p.name] = file_hash(p)
        annotations.append({"record_id": case["id"], "claim_id": "c1", "expected_label": "supported", "ambiguous_scope": False})
    p = path.parent / "new_expected.json"
    write_json(p, {"preserved_audit_path": "old_audit.json", "preserved_audit_sha256": file_hash(path.parent / "old_audit.json"),
                   "claims": annotations})
    plan["expected_annotations"].update(known_trace_expected_source=p.name, known_trace_expected_sha256=file_hash(p))
    plan["source_sha256"][p.name] = file_hash(p)
    core = path.parent / "src/rag_research/evaluation/fixed.py"
    core.parent.mkdir(parents=True)
    core.write_text("# Fixed fixture core, not a real Model experiment\n")
    prior = path.parent / "prior"
    prior.mkdir()
    prior_plan = deepcopy(plan)
    prior_plan.update(verification_mode="source-reading-v1", max_completion_attempts=12)
    write_json(path.parent / "prior-plan.json", prior_plan)
    prior_config = {**deepcopy(config), "diagnostics": "prior-plan.json"}
    prior_manifest = {"config": prior_config, "model": {"test": "identity"},
                      "plan_sha256": file_hash(path.parent / "prior-plan.json"),
                      "source_sha256": {str(core.relative_to(path.parent)): file_hash(core)}}
    write_json(prior / "manifest.json", prior_manifest)
    write_json(prior / "report.json", {"diagnostic_gate_passed": True, "completion_attempts_recorded": 12,
                                      "completed_conditions": 6, "planned_conditions": 6,
                                      "not_attempted_ids": [], "cost_incomplete": False,
                                      "manifest_sha256": digest(prior_manifest), "fixture_not_real_model_evidence": True})
    plan.update(purpose="phase11-known-trace-semantic-regression", verification_mode="source-reading-v1",
                max_completion_attempts=12, bare_refusal_cases_retained_separately=[],
                prerequisite={"report_path": "prior/report.json", "sha256": file_hash(prior / "report.json")},
                gate={"stop_on_task_error": True, "stop_after_critical_failure": True, "critical_all_exact": True,
                      "known_min_accuracy": .9, "known_min_supported_accuracy": .9, "known_max_false_support": 0})
    write_json(plan_path, plan)
    state.update(allow_answer_context=True, source_reading=True)
    return path, output, state


@pytest.mark.parametrize("critical_failure", [False, True])
def test_known_regression_requires_negatives_and_positive_controls_and_preserves_resume(diagnostic, critical_failure):
    path, output, state = prepare_regression_fixture(diagnostic)
    state["critical_failure"] = critical_failure
    report = module.run(path, output)
    assert report["diagnostic_gate_passed"] is not critical_failure
    assert report["completion_attempts_recorded"] == (4 if critical_failure else 12)
    assert report["known_regression"]["accuracy_of_all_planned"] == (None if critical_failure else 1.)
    assert module.run(path, output) == report and state["servers"] == 1
    assert "EXPECTED-SECRET" not in json.dumps(state["calls"])


@pytest.mark.parametrize("change", ["prerequisite", "core", "old_expected", "settings", "model", "critical"])
def test_known_regression_rejects_changed_proof_criteria_and_judge_before_calls(diagnostic, monkeypatch, change):
    path, output, state = prepare_regression_fixture(diagnostic)
    plan_path = path.parent / "plan.json"
    plan = read_json(plan_path)
    if change == "prerequisite":
        p = path.parent / "prior/report.json"
        report = read_json(p)
        report["diagnostic_gate_passed"] = False
        write_json(p, report)
        plan["prerequisite"]["sha256"] = file_hash(p)
    elif change == "core":
        (path.parent / "src/rag_research/evaluation/fixed.py").write_text("# changed\n")
    elif change == "old_expected":
        p = path.parent / "new_expected.json"
        value = read_json(p)
        value["claims"][0]["expected_label"] = "supported"
        write_json(p, value)
        plan["source_sha256"][p.name] = file_hash(p)
        plan["expected_annotations"]["known_trace_expected_sha256"] = file_hash(p)
    elif change == "settings":
        config = yaml.safe_load(path.read_text())
        config["tasks"]["verify_claims"]["max_output_tokens"] += 1
        path.write_text(yaml.safe_dump(config))
    elif change == "model":
        monkeypatch.setattr(module, "auxiliary_identity", lambda c: {"test": "changed"})
    else:
        plan["cases"][0]["critical_claim_ids"] = []
        plan["cases"][1]["critical_claim_ids"] = ["c1"]
    write_json(plan_path, plan)
    with pytest.raises(ValueError):
        module.run(path, output)
    assert not state["calls"] and not state["servers"]


def test_known_regression_positive_accuracy_cannot_hide_behind_many_negative_controls():
    plan = {"purpose": "phase11-known-trace-semantic-regression", "cases": [], "orders": ["original", "reversed"]}
    results = {}
    for n in range(40):
        positive = n < 20
        label = "supported" if positive else "not_supported"
        case = {"id": str(n), "language": "en", "scope": "known_used_development",
                "critical_claim_ids": [] if positive else ["c1"], "expected": {"c1": label}}
        plan["cases"].append(case)
        for order in plan["orders"]:
            results[str(n) + "-" + order] = {"status": "ok", "parsed": {"verdicts": [
                {"claim_id": "c1", "label": "not_supported" if n < 3 else label}]}}
    assessed = module.assess(plan, results)
    assert assessed["known_regression"]["accuracy_of_all_planned"] == .925
    assert assessed["known_regression"]["supported_accuracy"] == .85
    assert assessed["critical_passed"] and not assessed["diagnostic_gate_passed"]


def prepare_direct_regression_fixture(diagnostic):
    path, output, state = prepare_regression_fixture(diagnostic)
    config = yaml.safe_load(path.read_text())
    config["verification_mode"] = "claimwise-v1"
    config["tasks"].pop("read_sources")
    for name in config["prompts"].values():
        target = path.parent / name
        prompt = yaml.safe_load(target.read_text())
        prompt.pop("source_reading_auxiliary")
        prompt["tasks"].pop("read_sources")
        prompt["tasks"]["verify_claims"]["input_fields"].remove("source_reading")
        target.write_text(yaml.safe_dump(prompt))
    path.write_text(yaml.safe_dump(config))
    prior_plan_path = path.parent / "prior-plan.json"
    prior_plan = read_json(prior_plan_path)
    prior_plan.update(verification_mode="claimwise-v1", max_completion_attempts=6)
    write_json(prior_plan_path, prior_plan)
    prior = path.parent / "prior"
    manifest = read_json(prior / "manifest.json")
    manifest.update(config={**config, "diagnostics": "prior-plan.json"}, plan_sha256=file_hash(prior_plan_path))
    write_json(prior / "manifest.json", manifest)
    report = read_json(prior / "report.json")
    report.update(completion_attempts_recorded=6, manifest_sha256=digest(manifest))
    write_json(prior / "report.json", report)
    plan_path = path.parent / "plan.json"
    plan = read_json(plan_path)
    plan.update(verification_mode="claimwise-v1", max_completion_attempts=6)
    plan["prerequisite"]["sha256"] = file_hash(prior / "report.json")
    write_json(plan_path, plan)
    state["source_reading"] = False
    return path, output, state


def test_binary_runner_completes_positive_controls_after_a_critical_label_error(diagnostic):
    from rag_research.experiments.semantic_adoption import KNOWN_GATE_V2

    path, output, state = prepare_direct_regression_fixture(diagnostic)
    plan_path = path.parent / "plan.json"
    plan = read_json(plan_path)
    plan["gate"] = deepcopy(KNOWN_GATE_V2)
    write_json(plan_path, plan)
    state["critical_failure"] = True
    report = module.run(path, output)
    assert report["completion_attempts_recorded"] == 6 and report["not_attempted_ids"] == []
    assert not report["diagnostic_gate_passed"] and not report["binary_adoption"]["coverage_passed"]
    assert report["binary_adoption"]["negative_denominator"] == 2
    assert module.run(path, output) == report and state["servers"] == 1


@pytest.mark.parametrize("failure", [False, True])
def test_direct_regression_keeps_all_cases_and_gates_without_inventing_reader_calls(diagnostic, failure):
    path, output, state = prepare_direct_regression_fixture(diagnostic)
    state["critical_failure"] = failure
    report = module.run(path, output)
    assert report["diagnostic_gate_passed"] is not failure
    assert report["completion_attempts_recorded"] == (2 if failure else 6)
    assert not list((output / "tasks").glob("*.reading.json"))
    assert module.run(path, output) == report and state["servers"] == 1
    assert len(state["calls"]) == (2 if failure else 6) and "EXPECTED-SECRET" not in json.dumps(state["calls"])


@pytest.mark.parametrize("fault", ["plan_hash", "call_count", "incomplete", "cost", "mode"])
def test_direct_regression_requires_its_own_complete_bound_prerequisite(diagnostic, fault):
    path, output, state = prepare_direct_regression_fixture(diagnostic)
    prior = path.parent / "prior"
    manifest, report = read_json(prior / "manifest.json"), read_json(prior / "report.json")
    if fault == "plan_hash":
        manifest["plan_sha256"] = "changed"
    elif fault == "mode":
        manifest["config"]["verification_mode"] = "joint"
    else:
        report[{"call_count": "completion_attempts_recorded", "incomplete": "completed_conditions", "cost": "cost_incomplete"}[fault]] = {
            "call_count": 128, "incomplete": 5, "cost": True}[fault]
    write_json(prior / "manifest.json", manifest)
    report["manifest_sha256"] = digest(manifest)
    write_json(prior / "report.json", report)
    plan_path = path.parent / "plan.json"
    plan = read_json(plan_path)
    plan["prerequisite"]["sha256"] = file_hash(prior / "report.json")
    write_json(plan_path, plan)
    with pytest.raises(ValueError, match="Passing full bilingual"):
        module.run(path, output)
    assert state["calls"] == [] and state["servers"] == 0
