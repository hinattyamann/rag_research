"""Real child processes exercise finite supervision; inference remains synthetic."""

import json
import os
import subprocess
import sys
import time
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from rag_research.experiments import fixed_v23 as fixed
from rag_research.experiments import fixed_v23_control as control
from rag_research.experiments.storage import checkpoint, read_json
from rag_research.retrieval.common import file_hash

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def contract(tmp_path, monkeypatch):
    monkeypatch.setattr(fixed, "verify_release", lambda root: {})
    candidate = yaml.safe_load((REPO / "configs/phase11_semantic_candidate_v23.yaml").read_text())
    (tmp_path / "candidate.yaml").write_text(yaml.safe_dump(candidate))
    rejection = json.loads((REPO / "data/manifests/phase11_known_trace_direct_result_v12_v2.json").read_text())
    (tmp_path / "known.json").write_text(json.dumps(rejection))
    (tmp_path / "assets.json").write_text("{}")
    (tmp_path / "qa.jsonl").write_text("synthetic metadata only")
    rows = [{"record_id": str(i), "document_group_id": "g" + str(i)} for i in range(20)]
    selection = {"languages": {lang: {"selected": rows} for lang in ("en", "ja")},
                 "assets_sha256": file_hash(tmp_path / "assets.json"),
                 "development_qa_sha256": {"qa.jsonl": file_hash(tmp_path / "qa.jsonl")}}
    checkpoint(tmp_path / "selection.json", selection)
    def bind(name):
        return {"path": name, "sha256": file_hash(tmp_path / name)}
    study = {"version": fixed.VERSION, "base_commit": fixed.BASE, "candidate_identity_sha256": fixed.CANDIDATE,
             "mode": "main", "phase12_allowed": False, "old_gate11_passed": False,
             "known_limit_acknowledged": True, "automatic_retries": 0, "count_per_language": 20,
             "minimum_comparable_per_language": 10,
             "quality_and_expected_seal": "all_both_languages_before_internal_unblinding",
             "pilot_wall_seconds": 14400, "session_wall_seconds": 43200, "total_wall_seconds": 259200,
             "candidate": bind("candidate.yaml"), "known_result": bind("known.json"),
             "selection": bind("selection.json"), "assets": bind("assets.json"), "fixed_inputs": [],
             "baseline": {"path": "baseline.yaml"},
             "initial_prompts": {lang: {"path": "initial.yaml"} for lang in ("en", "ja")},
             "limits_per_language": {"maximum_completion_attempts": 1660, "maximum_new_qa_per_stage_session": 5,
                                     "stop_on_any_task_error": True, "automatic_refill": False}}
    (tmp_path / "study.json").write_text(json.dumps(study))
    config = {key: deepcopy(candidate[key]) for key in fixed.INFERENCE_KEYS}
    config.update(fixed_v23_protocol=bind("study.json"), execution_scope="fixed_v23_main_v1",
                  purpose="phase11-bilingual-development-candidate", data={"split": "development"},
                  phase12_allowed=False, decision={**candidate["decision"], "bare_refusal_policy": "rewrite_once"},
                  main_limits=study["limits_per_language"], language="ja", prompts=candidate["prompts"]["ja"],
                  assets="assets.json", baseline_config="baseline.yaml", baseline_prompts="initial.yaml")
    return tmp_path, config, rows


def test_fixed_protocol_accepts_known_rejection_without_changing_old_result(contract):
    root, config, rows = contract
    before = (root / "known.json").read_bytes()
    fixed.validate_fixed(config, rows, root / "qa.jsonl", root=root)
    assert (root / "known.json").read_bytes() == before


@pytest.mark.parametrize("change", ["seed", "prompt", "gpu", "threshold", "ids", "budget", "legacy", "tamper"])
def test_fixed_protocol_rejects_condition_selection_and_binding_changes(contract, change):
    root, config, rows = contract
    if change == "seed":
        config["auxiliary_runtime"]["seed"] = 43
    elif change == "prompt":
        config["prompts"] = "latest.yaml"
    elif change == "gpu":
        config["execution"]["gpu_layers"] = 16
    elif change == "threshold":
        config["decision"]["threshold"] = .6
    elif change == "ids":
        rows.reverse()
    elif change == "budget":
        config["main_limits"] = {**config["main_limits"], "maximum_completion_attempts": 1661}
    elif change == "legacy":
        config["adopted_known_regression"] = {}
    else:
        (root / "known.json").write_text("{}")
    with pytest.raises(ValueError):
        fixed.validate_fixed(config, rows, root / "qa.jsonl", root=root)


def test_supervisor_saves_real_child_exit_and_survives_without_calling_codex(tmp_path, monkeypatch):
    monkeypatch.setattr(control, "ROOT", tmp_path)
    monkeypatch.setattr(control, "public_state", lambda *args: None)
    state = {"sessions": [], "spent_wall_seconds": 0.}
    code, reason = control.supervise([sys.executable, "-c", "print('synthetic child')"], tmp_path, state, 3, interval=.02)
    assert code == 0 and reason is None
    assert "synthetic child" in (tmp_path / "session-000.log").read_text()
    assert state["sessions"][0]["exit_code"] == 0 and state["spent_wall_seconds"] > 0
    assert "child" not in read_json(tmp_path / "control.json")


def test_deadline_stops_only_owned_process_group_and_preserves_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(control, "ROOT", tmp_path)
    monkeypatch.setattr(control, "public_state", lambda *args: None)
    state = {"sessions": [], "spent_wall_seconds": 0.}
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"], start_new_session=True)
    try:
        code, reason = control.supervise([sys.executable, "-c", "import time; time.sleep(10)"],
                                          tmp_path, state, .1, interval=.02)
        assert code != 0 and reason == "finite_wall_deadline"
        assert unrelated.poll() is None
        assert state["sessions"][0]["reason"] == "finite_wall_deadline"
    finally:
        unrelated.terminate()
        unrelated.wait(timeout=3)


def test_public_progress_and_report_exclude_answers_scores_and_reference(tmp_path):
    folder = tmp_path / "en/baseline/a"
    folder.mkdir(parents=True)
    checkpoint(folder / "record.json", {"task": "baseline", "status": "ok", "completion_attempted": True,
        "input_tokens": 10, "output_tokens": 2, "generation_seconds": 1.,
        "answer": "SECRET_ANSWER", "score": .42, "decision": "SECRET_DECISION"})
    value = control.public_state(tmp_path, "failed", "synthetic_failure")
    assert value["baseline_qa"] == 1 and value["completed_qa"] == 0
    assert value["attempts"] == 1 and value["input_tokens"] == 10
    public = json.dumps(value) + (tmp_path / "report_to_codex.txt").read_text()
    assert "SECRET" not in public and "0.42" not in public
    assert value["next_owner"] == "Codex" and value["collection_completed"] is False


def test_unknown_request_refuses_resume_before_any_subprocess(tmp_path, monkeypatch):
    monkeypatch.setattr(control, "collection", lambda p: (tmp_path, {"total_wall_seconds": 100}))
    (tmp_path / "control.json").write_text(json.dumps({"spent_wall_seconds": 1}))
    (tmp_path / "status.public.json").write_text('{"state":"failed"}')
    folder = tmp_path / "en/internal/a"
    folder.mkdir(parents=True)
    (folder / "c1.json").write_text(json.dumps({"task": "verify_claims", "status": "started", "completion_attempted": True}))
    with pytest.raises(ValueError, match="error/unknown"):
        control.launch(tmp_path, "resume")


def test_detached_launch_finishes_without_parent_wait_and_rejects_second_start(tmp_path, monkeypatch):
    monkeypatch.setattr(control, "ROOT", tmp_path)
    monkeypatch.setattr(control, "collection", lambda p: (tmp_path, {"total_wall_seconds": 100}))
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/fixed_v23.py").write_text(
        "import time\nfrom pathlib import Path\ntime.sleep(.3)\n"
        f"Path({str(tmp_path / 'detached-proof')!r}).write_text('finished')\n")
    (tmp_path / "control.json").write_text(json.dumps({"spent_wall_seconds": 0., "sessions": []}))
    (tmp_path / "status.public.json").write_text('{"state":"ready"}')
    result = control.launch(tmp_path, "pilot")
    assert result["started"] is True
    with pytest.raises(ValueError, match="still running"):
        control.launch(tmp_path, "pilot")
    deadline = time.monotonic() + 5
    while not (tmp_path / "detached-proof").exists() and time.monotonic() < deadline:
        time.sleep(.02)
    assert (tmp_path / "detached-proof").read_text() == "finished"


def test_pid_reuse_does_not_count_as_live_owner():
    assert not control.alive({"pid": os.getpid(), "created": 0})
    assert control.alive(control.identity(os.getpid()))


def test_sealed_release_rejects_new_source_and_any_modified_original(tmp_path, monkeypatch):
    source = tmp_path / "src/rag_research/generation/local.py"
    source.parent.mkdir(parents=True)
    source.write_text("original inference")
    release = {"base_commit": fixed.BASE, "new_native_calls": 0,
               "files": {source.relative_to(tmp_path).as_posix(): file_hash(source)}}
    (tmp_path / "fixed-v23-release.json").write_text(json.dumps(release))
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: fixed.BASE + "\n")
    fixed.verify_release(tmp_path)
    extra = source.with_name("unexpected.py")
    extra.write_text("changed")
    with pytest.raises(ValueError, match="Unexpected"):
        fixed.verify_release(tmp_path)
    extra.unlink()
    source.write_text("modified inference")
    with pytest.raises(ValueError, match="changed"):
        fixed.verify_release(tmp_path)


def test_fixed_main_cannot_run_against_unsealed_latest_main_source(tmp_path):
    with pytest.raises(ValueError, match="sealed original-v23"):
        fixed.validate_fixed({}, [], tmp_path / "qa.jsonl", root=tmp_path)


