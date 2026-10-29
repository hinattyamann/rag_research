"""Recovery keeps a terminal length failure missing; every other failure still stops."""

import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest

from rag_research.experiments.bilingual_budget import DevelopmentStop
from rag_research.experiments.storage import checkpoint, read_json, write_json
from rag_research.retrieval.common import file_hash

SPEC = importlib.util.spec_from_file_location(
    "fixed_v23_recovery", Path(__file__).resolve().parents[1] / "scripts/recover_fixed_v23.py")
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


def limit_record():
    return {"status": "error", "completion_attempted": True, "cost_incomplete": False,
        "finish_reason": "limit", "error": "Output token limit reached; answer may be incomplete",
        "input_tokens": 3309, "output_tokens": 512, "answer": "SYNTHETIC_PRIVATE_PARTIAL",
        "runtime_response": {"stop_type": "limit", "truncated": False, "tokens_predicted": 512,
            "tokens": [1] * 512, "generation_settings": {"n_predict": 512, "temperature": 0., "seed": 42}}}


@pytest.mark.parametrize("change", [None, "unknown", "unreceived", "input_overflow", "bad_stop", "not_limit",
                                   "truncation", "different_budget", "incomplete_tokens", "started"])
def test_only_received_fixed_budget_terminal_baseline_is_missing(change):
    value = limit_record()
    if change == "unknown":
        value["cost_incomplete"] = True
    elif change == "unreceived":
        value.pop("runtime_response")
    elif change == "input_overflow":
        value["input_tokens"] = 3585
    elif change == "bad_stop":
        value["runtime_response"]["stop_type"] = "eos"
    elif change == "not_limit":
        value["error"] = "CUDA or transport error"
    elif change == "truncation":
        value["runtime_response"]["truncated"] = True
    elif change == "different_budget":
        value["runtime_response"]["generation_settings"]["n_predict"] = 1024
    elif change == "incomplete_tokens":
        value["runtime_response"]["tokens"].pop()
    elif change == "started":
        value["status"] = "started"
    assert recovery.terminal_limit(value) is (change is None)


def test_resume_budget_keeps_failed_call_and_raw_bytes_and_never_erases_error(tmp_path):
    folder = tmp_path / "baseline/a"
    folder.mkdir(parents=True)
    checkpoint(folder / "record.json", limit_record())
    before = (folder / "record.json").read_bytes()
    result = recovery.reserve(tmp_path, 1660, 17)
    assert result["recorded_native_attempts_upper_bound"] == 1
    assert result["error_paths"] == ["baseline/a/record.json"]
    assert (folder / "record.json").read_bytes() == before
    with pytest.raises(DevelopmentStop, match="budget"):
        recovery.reserve(tmp_path, 1, 1)


@pytest.mark.parametrize("kind", ["unknown", "other_baseline", "internal"])
def test_new_unknown_transport_or_internal_error_cannot_be_skipped(tmp_path, kind):
    path = tmp_path / ("internal/a.json" if kind == "internal" else "baseline/a/record.json")
    path.parent.mkdir(parents=True)
    value = limit_record()
    if kind == "unknown":
        value.update(status="started", cost_incomplete=True)
    elif kind == "other_baseline":
        value["error"] = "Communication lost"
    else:
        value["task"] = "verify_claims"
    checkpoint(path, value)
    with pytest.raises(ValueError):
        recovery.reserve(tmp_path, 1660, 0)


def test_modified_checkpoint_cannot_be_used_as_terminal_failure(tmp_path):
    path = tmp_path / "baseline/a/record.json"
    path.parent.mkdir(parents=True)
    checkpoint(path, limit_record())
    path.write_text(path.read_text().replace("3309", "3310"))
    with pytest.raises(ValueError, match="hash"):
        recovery.reserve(tmp_path, 1660)


def test_public_completion_retains_missing_qa_and_explicit_original_denominator(tmp_path, monkeypatch):
    path = tmp_path / "ja/baseline/a/record.json"
    path.parent.mkdir(parents=True)
    checkpoint(path, limit_record())
    totals = {"completed_qa": 39, "failed": 1, "planned_qa": 40, "unknown": 0, "baseline_qa": 39}
    monkeypatch.setattr(recovery.legacy, "totals", lambda output: deepcopy(totals))
    monkeypatch.setattr(recovery, "ORIGINAL_PUBLIC", lambda output, state, reason: {
        **totals, "state": state, "next_action": "report_to_codex.txt"})
    result = recovery.public(tmp_path, "awaiting_scoring")
    assert result["processed_qa"] == 40 and result["successful_qa"] == 39
    assert result["baseline_failed_qa"] == result["failed"] == 1
    assert result["unhandled_failure_records"] == result["baseline_remaining_qa"] == 0
    assert result["remaining_qa"] == 0 and result["collection_has_missing"] is True
    assert "SYNTHETIC_PRIVATE" not in (tmp_path / "report_to_codex.txt").read_text()
    totals["completed_qa"] = 38
    with pytest.raises(ValueError, match="incomplete"):
        recovery.public(tmp_path, "awaiting_scoring")


def test_source_and_successful_record_protection_includes_failed_response(tmp_path):
    path = tmp_path / "ja/baseline/a/record.json"
    path.parent.mkdir(parents=True)
    checkpoint(path, limit_record())
    sealed = recovery.protected_files(tmp_path)
    assert sealed["ja/baseline/a/record.json"] == file_hash(path)
    assert read_json(path)["status"] == "error"


def test_readonly_status_keeps_missing_separate_from_pending_and_does_not_write(tmp_path):
    path = tmp_path / "ja/baseline/a/record.json"
    path.parent.mkdir(parents=True)
    checkpoint(path, limit_record())
    before = path.read_bytes()
    value = recovery.enrich(tmp_path, {"state": "collecting", "completed_qa": 20, "failed": 1,
        "baseline_qa": 22, "remaining_qa": 20, "unknown": 1, "observed_task_seconds": 27812.})
    assert value["processed_qa"] == 21 and value["remaining_qa"] == 19
    assert value["baseline_remaining_qa"] == 17 and value["baseline_failed_qa"] == 1
    assert value["unhandled_failure_records"] == 0 and value["unknown"] == 1
    assert path.read_bytes() == before and not (tmp_path / "status.public.json").exists()


def test_recovery_worker_uses_only_japanese_stages_and_finite_original_budget(tmp_path, monkeypatch):
    write_json(tmp_path / "control.json", {"launch_token": "test", "spent_wall_seconds": 10., "sessions": []})
    study = {"total_wall_seconds": 1000, "session_wall_seconds": 50}
    monkeypatch.setattr(recovery, "validate", lambda output: (tmp_path, study, {}))
    monkeypatch.setattr(recovery, "public", lambda output, state, reason=None: {"state": state})
    calls = []

    def supervise(argv, output, control, deadline):
        assert deadline == 50
        language = argv[argv.index("--language") + 1]
        stage = argv[argv.index("--stage") + 1]
        calls.append((language, stage))
        write_json(output / f"recovery-result-ja-{stage}.json", {"stage_complete": calls.count((language, stage)) == 2})
        control["spent_wall_seconds"] += 1
        return 0, None

    monkeypatch.setattr(recovery.legacy, "supervise", supervise)
    monkeypatch.setattr(recovery, "export_packets", lambda output: calls.append("packets"))
    result = recovery.worker(tmp_path, "test")
    assert result["state"] == "awaiting_scoring"
    assert calls == [("ja", "baseline"), ("ja", "baseline"), ("ja", "internal"), ("ja", "internal"), "packets"]
