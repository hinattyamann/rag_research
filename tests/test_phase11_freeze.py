import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("phase11_freeze", ROOT / "scripts/finalize_phase11.py")
freeze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(freeze)


def test_gpu_inventory_is_insufficient_and_cpu_cannot_be_frozen_as_gpu():
    assert not freeze.runtime_check({"purpose": "execution-environment-inventory-not-inference-proof",
                                     "gpu_inference_verified": False}, "p")
    runtime = {"purpose": "phase11-target-runtime-calibration", "backend": "CUDA",
               "actual_gpu_offload": True, "offloaded_layers": 20, "gpu_devices": ["synthetic fixture"],
               "completion_attempts": 1, "protocol_sha256": "p", "native_audits_valid": True,
               "semantic_check_completed": True, "summed_step_seconds": 1,
               "runtime_files_sha256": {"runtime": "hash"}, "model_files_sha256": {"model": "hash"}}
    assert freeze.runtime_check(runtime, "p")
    for key, value in [("backend", "CPU"), ("actual_gpu_offload", False), ("offloaded_layers", 0),
                       ("completion_attempts", 0), ("protocol_sha256", "other"),
                       ("native_audits_valid", False), ("semantic_check_completed", False),
                       ("summed_step_seconds", float("nan"))]:
        assert not freeze.runtime_check({**runtime, key: value}, "p")


def test_parser_gate_uses_actual_native_audit_schema_and_preserves_health_failure():
    task = {"task": "verify_claims", "status": "ok", "completion_attempted": True,
            "settings": {"final_json_grammar": True, "reasoning_budget_tokens": 512},
            "reasoning_budget_audit": {"budget": 512, "tokens_before_end_marker": 512,
                                       "budget_message_tokens": 10},
            "final_grammar_audit": {"runtime_settings_verified": True, "trigger_text_verified": True}}
    report = {"health_gate": {"status": "passed"}}
    assert freeze.parser_check(report, [task])
    assert not freeze.parser_check({"health_gate": {"status": "stopped"}}, [task])
    for key, value in [("status", "error"), ("cost_incomplete", True),
                       ("reasoning_budget_audit", None), ("final_grammar_audit", None)]:
        assert not freeze.parser_check(report, [{**task, key: value}])
    changed = deepcopy(task)
    changed["reasoning_budget_audit"]["tokens_before_end_marker"] = 9999
    assert not freeze.parser_check(report, [changed])


def test_gpu_requires_saved_native_outputs_and_matching_offload_log(tmp_path):
    from rag_research.experiments.storage import checkpoint
    from rag_research.retrieval.common import file_hash

    task = {"completion_attempted": True, "status": "ok",
            "settings": {"reasoning_budget_tokens": 512},
            "reasoning_budget_audit": {"budget": 512, "tokens_before_end_marker": 200,
                                       "budget_message_tokens": 10},
            "final_grammar_audit": {"runtime_settings_verified": True, "trigger_text_verified": True}}
    checkpoint(tmp_path / "task.json", task)
    log = tmp_path / "server.log"
    log.write_text("offloaded 20/20 layers to GPU", encoding="utf-8")
    (tmp_path / "runtime.bin").write_text("synthetic runtime", encoding="utf-8")
    (tmp_path / "model.gguf").write_text("synthetic model", encoding="utf-8")
    runtime = {"completion_attempts": 1, "offloaded_layers": 20,
               "probe_tasks": [{"path": "task.json", "sha256": file_hash(tmp_path / "task.json")}],
               "server_log": {"path": "server.log", "sha256": file_hash(log)},
               "runtime_files_sha256": {"runtime.bin": file_hash(tmp_path / "runtime.bin")},
               "model_files_sha256": {"model.gguf": file_hash(tmp_path / "model.gguf")}}
    assert freeze.runtime_output_check(tmp_path, runtime)
    with pytest.raises(ValueError, match="saved native"):
        freeze.runtime_output_check(tmp_path, {**runtime, "probe_tasks": []})
    log.write_text("offloaded 0/20 layers to GPU", encoding="utf-8")
    runtime["server_log"]["sha256"] = file_hash(log)
    with pytest.raises(ValueError, match="offload"):
        freeze.runtime_output_check(tmp_path, runtime)


def test_semantic_review_requires_all_fixed_claims_and_real_context_quotes():
    records = [{"trace": {"record_id": "q1", "documents": [
        {"passage_id": "p1", "text": "The event happened in 2017."}]},
        "evaluation": {"claims": [{"claim_id": "c1", "text": "In 2017."}]}}]
    audit = {"purpose": "phase11-semantic-audit", "calibration_report_sha256": "r",
             "human_reviewed": False, "limitations": ["Single AI diagnostic review"],
             "claims": [{"record_id": "q1", "claim_id": "c1", "expected_label": "supported",
                         "reason": "Explicit date", "evidence": [
                             {"passage_id": "p1", "quote": "happened in 2017"}]}]}
    assert freeze.semantic_check(audit, "r", records)
    assert not freeze.semantic_check({**audit, "claims": []}, "r", records)
    changed = deepcopy(audit)
    changed["claims"][0]["evidence"][0]["quote"] = "happened in 2018"
    with pytest.raises(ValueError, match="Context"):
        freeze.semantic_check(changed, "r", records)
    with pytest.raises(ValueError, match="binding"):
        freeze.semantic_check(audit, "another report", records)


def test_no_manifest_is_written_until_all_checks_and_selection_exist(tmp_path):
    path = tmp_path / "final.json"
    with pytest.raises(ValueError, match="not ready"):
        freeze.save_freeze(path, {"gate11_passed": False, "phase12_allowed": False})
    assert not path.exists()
    with pytest.raises(ValueError, match="incomplete"):
        freeze.save_freeze(path, {"gate11_passed": True, "phase12_allowed": True,
                                 "checks": {"runtime": False}, "conditions": {}})
    assert not path.exists()
    value = {"gate11_passed": True, "phase12_allowed": True, "checks": {"synthetic": True},
             "conditions": {"evaluation_selection": {"record_ids": ["fixture"]}}}
    saved = freeze.save_freeze(path, value)
    before = path.read_bytes()
    assert freeze.save_freeze(path, value) == saved and path.read_bytes() == before
    with pytest.raises(ValueError, match="never overwrite"):
        freeze.save_freeze(path, {**value, "conditions": {"evaluation_selection": {"record_ids": ["other"]}}})
    assert path.read_bytes() == before


def test_pending_quality_blocks_before_any_private_result_is_read(tmp_path):
    from rag_research.experiments.frozen_trace import digest
    from rag_research.experiments.storage import checkpoint
    from rag_research.retrieval.common import file_hash

    run = tmp_path / "data/runs/calibration/fixture"
    run.mkdir(parents=True)
    data = tmp_path / "qa.jsonl"
    data.write_text("fixed", encoding="utf-8")
    selection_path = tmp_path / "selection.json"
    selection = checkpoint(selection_path, {"split": "calibration", "qa_sha256": file_hash(data)})
    checkpoint(run / "candidate_manifest.json", {
        "purpose": "phase11-provisional-conditions-not-final-freeze", "phase12_allowed": False,
        "source_sha256": {}, "selection_sha256": digest(selection), "config": {"qa_path": "qa.jsonl"}})
    (run / "internal").mkdir()
    (run / "internal/report.private.json").write_text("NEVER READ THIS", encoding="utf-8")
    decisions = {"schema_version": 1, "purpose": "phase11-freeze-decisions", "target_backend": "CUDA",
                 "reviews": {name: {"status": "pending"} for name in freeze.SECTIONS}}
    result = freeze.readiness(tmp_path, run, selection_path, decisions)
    assert result["gate11_passed"] is False and result["conditions"] is None
    assert all(value is False for value in result["checks"].values())
    assert "packet.json" in result["reasons"]["calibration_quality"]


def test_evaluation_selection_uses_metadata_only_and_never_upsamples_ids():
    split = {"record_ids_by_split": {"evaluation": ["q1:answerable", "q2:answerable", "q3:unanswerable"]}}
    ids = freeze.evaluation_ids(split, 2, 42)
    assert set(ids) == {"q1:answerable", "q2:answerable"}
    assert ids == freeze.evaluation_ids({"record_ids_by_split": {"evaluation": list(reversed(
        split["record_ids_by_split"]["evaluation"]))}}, 2, 42)
    with pytest.raises(ValueError, match="Insufficient"):
        freeze.evaluation_ids(split, 3, 42)
    with pytest.raises(ValueError, match="Duplicate"):
        freeze.evaluation_ids({"record_ids_by_split": {"evaluation": ["q1:answerable"] * 2}}, 1, 42)


def test_public_quality_assessment_can_run_while_inference_holds_parent_lock(tmp_path, monkeypatch):
    from rag_research.experiments.frozen_trace import digest
    from rag_research.experiments.storage import checkpoint, run_lock, write_json
    from rag_research.retrieval.common import file_hash

    spec = importlib.util.spec_from_file_location("calibration_assessor", ROOT / "scripts/assess_calibration.py")
    assessor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assessor)
    monkeypatch.setattr(assessor, "ROOT", tmp_path)
    run = tmp_path / "data/runs/calibration/fixture"
    bundle = run / "quality/ready-001"
    bundle.mkdir(parents=True)
    case = {"question": "Q?", "answer": "A", "documents": [], "gold_documents": []}
    case.update(annotation_id="anonymous", candidate_sha256=digest(case))
    packet = {"schema_version": 1, "rubric_version": "fixture", "rubric": "fixture", "cases": [case]}
    packet["packet_sha256"] = digest(packet)
    write_json(bundle / "packet.json", packet)
    write_json(bundle / "mapping.private.json", {"private": "must not be read by grading"})
    checkpoint(bundle / "export_manifest.json", {"annotation_kind": "AI", "human_reviewed": False,
               "mapping_sha256": file_hash(bundle / "mapping.private.json"),
               "packet_sha256": packet["packet_sha256"]})
    with run_lock(run):
        opened = assessor.assess(run, 1, "open")
        assert opened["case"]["annotation_id"] == "anonymous"
    (bundle / "mapping.private.json").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="provenance"):
        assessor.assess(run, 1, "open")
