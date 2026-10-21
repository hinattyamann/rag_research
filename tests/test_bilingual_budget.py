"""Resource accounting is leaf-based, fail-closed, and never turns a stop into a call."""

import pytest

from rag_research.experiments.bilingual_budget import (
    DevelopmentStop,
    budget_snapshot,
    pending_trace_calls,
    reserve_calls,
)
from rag_research.experiments.storage import checkpoint, write_json


def save(path, task, **fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint(path, {"task": task, "status": "ok", "completion_attempted": True, **fields})


def test_counts_raw_requests_without_double_charging_partial_aggregates(tmp_path):
    save(tmp_path / "baseline/a/record.json", "baseline")
    save(tmp_path / "internal/a/original.reading.json", "read_sources")
    save(tmp_path / "internal/a/original.verification.claims/c1.json", "verify_claims")
    save(tmp_path / "internal/a/original.verification.json", "verify_claims", execution_mode="claimwise-v1", status="partial")
    save(tmp_path / "internal/a/original.json", "verify_claims", execution_mode="source-reading-v1", status="partial")
    save(tmp_path / "internal/a/claims.json", "extract_claims", completion_attempted=False)
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*.json"))
    summary = reserve_calls(tmp_path, 5, 2)
    assert summary["recorded_native_attempts_upper_bound"] == summary["known_native_attempts"] == 3
    assert not summary["error_paths"] and not summary["unknown_or_interrupted_paths"]
    with pytest.raises(DevelopmentStop, match="budget_exhausted"):
        reserve_calls(tmp_path, 5, 3)
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*.json")) == before


def test_unknown_requests_and_errors_stop_before_any_new_qa(tmp_path):
    path = tmp_path / "internal/a/original.reading.json"
    path.parent.mkdir(parents=True)
    write_json(path, {"task": "read_sources", "status": "started", "completion_attempted": True})
    summary = budget_snapshot(tmp_path)
    assert summary["possible_unknown_attempts"] == 1 and summary["known_native_attempts"] == 0
    with pytest.raises(DevelopmentStop, match="existing_error"):
        reserve_calls(tmp_path, 100, 0)
    save(path, "read_sources", status="error", error_code="invalid_output")
    with pytest.raises(DevelopmentStop, match="existing_error"):
        reserve_calls(tmp_path, 100, 0)
    save(path, "read_sources", status="error", error_code="interrupted_unknown_outcome", cost_incomplete=True)
    assert budget_snapshot(tmp_path)["possible_unknown_attempts"] == 1


def test_reserves_only_missing_reader_units_and_one_rewrite_and_handles_bare_refusal(tmp_path):
    trials = ["original", "reversed"]
    assert pending_trace_calls(tmp_path, trials, ["c1", "c2"]) == 7
    save(tmp_path / "original.reading.json", "read_sources")
    save(tmp_path / "original.verification.claims/c1.json", "verify_claims")
    assert pending_trace_calls(tmp_path, trials, ["c1", "c2"]) == 5
    assert pending_trace_calls(tmp_path, trials, []) == 1
    save(tmp_path / "rewrite.json", "rewrite_answer")
    assert pending_trace_calls(tmp_path, trials, []) == 0
    assert pending_trace_calls(tmp_path, trials, ["c1", "c2"]) == 4
    with pytest.raises(ValueError, match="Invalid trial"):
        pending_trace_calls(tmp_path, ["../outside"], ["c1"])


def test_corrupt_durable_cost_or_missing_attempt_flag_is_rejected(tmp_path):
    path = tmp_path / "baseline/a/record.json"
    save(path, "baseline")
    path.write_text(path.read_text().replace('"completion_attempted": true', '"completion_attempted": false'))
    with pytest.raises(ValueError, match="hash"):
        budget_snapshot(tmp_path)
    checkpoint(path, {"status": "ok"})
    with pytest.raises(ValueError, match="attempt flag"):
        budget_snapshot(tmp_path)
