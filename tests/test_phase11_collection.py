"""A session boundary is not a goal boundary; an actual health failure is retained."""

import pytest

from rag_research.experiments.phase11_collection import collect_language


def test_collects_all_eight_sessions_without_repeating_completed_qa():
    calls, receipts = [], []

    def runner(config, output, *, stage):
        calls.append(stage)
        count = 5 * calls.count(stage)
        if count < 20:
            return {"stage": stage + "_batch_complete", "processed_qa": count}
        if stage == "baseline":
            return {"stage": stage, "baseline_count": 20, "baseline_ok": 20}
        return {"trace_count": 20, "baseline_failures": 0, "judge_status_counts": {"ok": 180},
                "rewrite_statuses": ["ok"] * 20, "quality_status": "pending_external_blinded_annotation"}

    result = collect_language(runner, "same-config", "same-output",
                              lambda *args: receipts.append(args))
    assert calls == ["baseline"] * 4 + ["internal"] * 4
    assert len(receipts) == 8
    assert result["collection_completed"] is True
    assert result["scientific_adoption_claimed"] is False
    assert result["quality_and_expected_sealed"] is False


def test_stops_on_health_failure_before_next_session():
    calls = []

    def runner(*args, stage):
        calls.append(stage)
        return {"stage": "main_development_stopped", "reason": "existing_error_or_unknown_outcome"}

    result = collect_language(runner, None, None, lambda *args: None)
    assert calls == ["baseline"]
    assert result == {"collection_completed": False, "reason": "existing_error_or_unknown_outcome"}


def test_does_not_poll_or_restart_when_progress_stalls():
    calls = []

    def runner(*args, stage):
        calls.append(stage)
        return {"stage": "baseline_batch_complete", "processed_qa": 5}

    with pytest.raises(ValueError, match="advance"):
        collect_language(runner, None, None, lambda *args: None)
    assert calls == ["baseline", "baseline"]
