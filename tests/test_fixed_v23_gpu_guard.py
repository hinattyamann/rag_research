"""GPU resource waits and startup-only recovery must preserve native outcomes and wall costs."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/fixed_v23_automation"))
import common  # noqa: E402
import gpu_guard as guard  # noqa: E402
import pipeline  # noqa: E402

from rag_research.experiments.storage import checkpoint  # noqa: E402


@pytest.fixture
def gpu_config(tmp_path):
    return {"state_dir": str(tmp_path / "state"), "cal_run": str(tmp_path / "cal"),
        "cal_gpu_policy": {"internal_min_free_mib": 7100, "baseline_min_free_mib": 3000,
            "stable_samples": 3, "maximum_wait_seconds": 30, "poll_seconds": 1, "maximum_startup_failures": 2}}


def test_waits_for_three_stable_samples_and_retains_wait_wall(gpu_config, monkeypatch):
    values = iter([6000, 7200, 6900, 7300, 7400, 7500])
    clock = [0.]
    monkeypatch.setattr(guard, "free_mib", lambda: next(values))
    monkeypatch.setattr(guard, "time", SimpleNamespace(monotonic=lambda: clock[0], sleep=lambda s: clock.__setitem__(0, clock[0] + s)))
    guard.wait_ready(gpu_config, "en", "internal", 20)
    receipt = common.read(next((Path(gpu_config["state_dir"]) / "cal-sessions").glob("*.json")))
    assert receipt["elapsed_seconds"] == 5 and receipt["available_free_mib"] == 7500
    assert common.read(Path(gpu_config["state_dir"]) / "progress.json")["stage"] == "waiting_gpu"


def test_insufficient_headroom_stops_at_finite_wall_and_preserves_wait_cost(gpu_config, monkeypatch):
    clock = [0.]
    monkeypatch.setattr(guard, "free_mib", lambda: 1000)
    monkeypatch.setattr(guard, "time", SimpleNamespace(monotonic=lambda: clock[0], sleep=lambda s: clock.__setitem__(0, clock[0] + s)))
    with pytest.raises(ValueError, match="headroom wait exhausted"):
        guard.wait_ready(gpu_config, "ja", "internal", 3)
    receipt = common.read(next((Path(gpu_config["state_dir"]) / "cal-sessions").glob("*.json")))
    assert receipt["elapsed_seconds"] == 3 and "finished_at_utc" in receipt


def setup_failure(config, number=3):
    run = Path(config["cal_run"])
    log = run / "en/internal" / f"server-{number}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("cudaMalloc failed: out of memory\nllama_server: exiting due to model loading error\n")
    receipt = Path(config["state_dir"]) / "cal-sessions/en-internal-2.json"
    common.write(receipt, {"exit_code": 1, "finished_at_utc": "2026-10-31T07:03:44+00:00", "elapsed_seconds": 18.})
    receipt.with_suffix(".log").write_text("GenerationError: Local server exited; see " + str(log) + "\n")
    return run, receipt, log


def test_only_zero_native_startup_oom_is_archived_and_costs_are_not_reset(gpu_config):
    run, receipt, log = setup_failure(gpu_config)
    before = guard.raw_snapshot(run / "en")
    original = common.sha(receipt)
    assert guard.archive_startup_oom(gpu_config, receipt, before, "en", "internal") == 18.
    assert not receipt.exists() and log.exists()
    row = guard.registered_failures(run, "en", "internal")[0]
    assert row["new_native_calls"] == 0 and common.sha(row["archived_receipt"]) == original
    assert sum(common.read(p)["elapsed_seconds"] for p in receipt.parent.glob("*.json")) == 18.
    assert guard.raw_snapshot(run / "en") == before
    log.write_text("changed")
    with pytest.raises(ValueError, match="failure changed"):
        guard.registered_failures(run, "en", "internal")


@pytest.mark.parametrize("bad", ["new_native", "unknown", "not_oom", "unfinished"])
def test_never_retries_native_changes_unknown_or_unclassified_failures(gpu_config, bad):
    run, receipt, log = setup_failure(gpu_config)
    before = guard.raw_snapshot(run / "en")
    if bad in {"new_native", "unknown"}:
        path = run / "en/baseline/a/record.json"
        path.parent.mkdir(parents=True)
        value = {"status": "started" if bad == "unknown" else "ok", "completion_attempted": True}
        (common.write if bad == "unknown" else checkpoint)(path, value)
    elif bad == "not_oom":
        log.write_text("unrelated runtime error")
    else:
        common.write(receipt, {"exit_code": None})
    with pytest.raises(ValueError):
        guard.archive_startup_oom(gpu_config, receipt, before, "en", "internal")
    assert receipt.exists() and not (run / "startup_recovery/ledger.json").exists()


def test_startup_retries_are_bounded_and_every_failed_startup_stays_in_wall_total(gpu_config):
    for number in (3, 4):
        run, receipt, _ = setup_failure(gpu_config, number)
        guard.archive_startup_oom(gpu_config, receipt, guard.raw_snapshot(run / "en"), "en", "internal")
    run, receipt, _ = setup_failure(gpu_config, 5)
    with pytest.raises(ValueError, match="retry limit"):
        guard.archive_startup_oom(gpu_config, receipt, guard.raw_snapshot(run / "en"), "en", "internal")
    assert len(guard.registered_failures(run, "en", "internal")) == 2
    assert sum(common.read(p)["elapsed_seconds"] for p in receipt.parent.glob("*.json")) == 54.


def test_collector_resumes_after_startup_failure_without_resetting_original_stage_budget(gpu_config, monkeypatch, tmp_path):
    config = {**gpu_config, "checkout": str(tmp_path)}
    run, receipt, _ = setup_failure(config)
    renamed = receipt.with_name("en-internal-0.json")
    receipt.rename(renamed)
    receipt.with_suffix(".log").rename(renamed.with_suffix(".log"))
    guard.archive_startup_oom(config, renamed, {}, "en", "internal")
    for language, phase in (("en", "baseline"), ("ja", "baseline"), ("ja", "internal")):
        common.write(renamed.parent / f"{language}-{phase}-0.json", {"exit_code": 0, "elapsed_seconds": 2.})
        common.write(run / f"result-{language}-{phase}.json", {"stage_complete": True})
    fake = SimpleNamespace(export_packets=lambda run: None, reserve=lambda *a: {},
        missing_count=lambda run: 0, rewrite_missing_count=lambda run: 0,
        legacy=SimpleNamespace(totals=lambda run: {"completed_qa": 40}))
    monkeypatch.setattr(pipeline, "runtime", lambda cfg: fake)
    monkeypatch.setattr(pipeline, "verify_cal", lambda cfg: {"session_wall_seconds": 100, "total_wall_seconds": 300})
    waits, attempts = [], []

    def wait(cfg, language, phase, limit, *, stage_receipt):
        waits.append(limit)
        common.write(renamed.parent / f"resource-wait-test-{len(waits)}.json",
            {"elapsed_seconds": 2., "stage_receipt": stage_receipt})

    def invoke(argv, *, receipt, timeout, **kwargs):
        if receipt.exists():
            return common.read(receipt)
        assert receipt == renamed
        attempts.append(timeout)
        if len(attempts) == 1:
            log = run / "en/internal/server-4.log"
            log.write_text("cudaMalloc failed: out of memory\nexiting due to model loading error\n")
            common.write(receipt, {"exit_code": 1, "finished_at_utc": common.now(), "elapsed_seconds": 3.})
            receipt.with_suffix(".log").write_text("Local server exited; see " + str(log) + "\n")
            raise ValueError("startup OOM")
        common.write(receipt, {"exit_code": 0, "elapsed_seconds": 1.})
        common.write(run / "result-en-internal.json", {"stage_complete": True})

    monkeypatch.setattr(guard, "wait_ready", wait)
    monkeypatch.setattr(pipeline, "run_owned", invoke)
    pipeline.collect_cal(config, tmp_path / "config.json")
    assert waits == [82., 77.] and attempts == [80., 75.]
    assert sum(common.read(p).get("elapsed_seconds", 0) for p in renamed.parent.glob("*.json")) == 32.
    assert guard.raw_snapshot(run / "en") == {} and len(guard.registered_failures(run, "en", "internal")) == 2


def test_cal_resource_audit_keeps_verified_startup_failure_separate_from_successful_cuda_proof(gpu_config):
    run, receipt, _ = setup_failure(gpu_config)
    guard.archive_startup_oom(gpu_config, receipt, {}, "en", "internal")
    for stage, context, layers in (("baseline", 4096, 37), ("internal", 12288, 33)):
        folder = run / "en" / stage
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "server-1.log").write_text(
            f"offloaded {layers}/{layers} layers to GPU\nusing device CUDA0\nllama_context: n_ctx = {context}\n")
        common.write(folder / "session-1.json", {"server_context_tokens": context, "full_gpu_offload": True,
            "actual_gpu_offload": True, "offloaded_layers": layers, "total_layers": layers})
    fake = SimpleNamespace(runner=SimpleNamespace(execution_identity=lambda cfg: {}), reserve=lambda *a: {"error_paths": []})
    manifest = {"baseline": {"generation": {"context_tokens": 4096}},
                "config": {"auxiliary_runtime": {"context_tokens": 12288}}}
    rows = pipeline.resource_audit(run / "en", manifest, fake, cohort="cal")
    assert len(rows) == 3 and sum(r["session_report_present"] for r in rows) == 2
    assert rows[-1]["startup_failed_before_inference"] is True and rows[-1]["new_native_calls"] == 0
