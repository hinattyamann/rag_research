"""Length-only recovery preserves native failures, resumes batches and exports fallback QA."""

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_bilingual_pipeline import connection, registry  # noqa: F401
from test_fixed_v23_recovery import limit_record

from rag_research.experiments import bilingual_quality, bilingual_semantics
from rag_research.experiments.bilingual_budget import DevelopmentStop
from rag_research.experiments.bilingual_semantics import export_units
from rag_research.experiments.frozen_trace import digest
from rag_research.experiments.quality import reconstruct
from rag_research.experiments.storage import checkpoint, read_json, write_json
from rag_research.retrieval.common import file_hash

SPEC = importlib.util.spec_from_file_location(
    "fixed_v23_recovery_v2", Path(__file__).resolve().parents[1] / "scripts/recover_fixed_v23_v2.py")
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


def rewrite_failure():
    return {"task": "rewrite_answer", "status": "error", "completion_attempted": True,
        "cost_incomplete": False, "error_code": "invalid_output",
        "error": "Final answer exceeds 512-token candidate budget", "final_answer_tokens": 747,
        "input_tokens": 3224, "output_tokens": 4018,
        "runtime_response": {"stop_type": "eos", "truncated": False, "tokens_predicted": 4018,
            "tokens": [1] * 4018, "generation_settings": {"n_predict": 6144, "temperature": .2, "seed": 42}}}


@pytest.mark.parametrize("field,value", [
    (None, None), ("task", "verify_claims"), ("status", "started"),
    ("cost_incomplete", True), ("completion_attempted", False), ("error_code", "runtime_error"),
    ("error", "Incomplete rewrite output"), ("final_answer_tokens", 512),
    ("final_answer_tokens", True), ("input_tokens", 6145), ("output_tokens", 4017),
    ("runtime_response.stop_type", "limit"), ("runtime_response.truncated", True),
    ("runtime_response.tokens_predicted", 6145), ("runtime_response.tokens", [1]),
    ("runtime_response.generation_settings.n_predict", 8192),
    ("runtime_response.generation_settings.temperature", 0.),
    ("runtime_response.generation_settings.seed", 43),
])
def test_only_complete_final_answer_length_failure_is_skippable(field, value):
    task = rewrite_failure()
    if field:
        target = task
        parts = field.split(".")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    assert recovery.rewrite_limit(task) is (field is None)


def test_reserve_keeps_both_length_failures_and_costs_but_rejects_other_errors(tmp_path):
    baseline = tmp_path / "baseline/a/record.json"
    rewrite = tmp_path / "internal/b/rewrite.json"
    baseline.parent.mkdir(parents=True)
    rewrite.parent.mkdir(parents=True)
    checkpoint(baseline, limit_record())
    checkpoint(rewrite, rewrite_failure())
    before = {p: p.read_bytes() for p in (baseline, rewrite)}
    snapshot = recovery.reserve(tmp_path, 1660)
    assert len(snapshot["error_paths"]) == snapshot["recorded_native_attempts_upper_bound"] == 2
    assert before == {p: p.read_bytes() for p in before}
    with pytest.raises(DevelopmentStop, match="budget"):
        recovery.reserve(tmp_path, 2, 1)
    wrong = tmp_path / "internal/b/original.json"
    checkpoint(wrong, rewrite_failure())
    with pytest.raises(ValueError, match="Only confirmed"):
        recovery.reserve(tmp_path, 1660)


def test_runtime_float32_temperature_is_the_same_fixed_sampler():
    task = rewrite_failure()
    task["runtime_response"]["generation_settings"]["temperature"] = .20000000298023224
    assert recovery.rewrite_limit(task)
    task["runtime_response"]["generation_settings"]["temperature"] = .201
    assert not recovery.rewrite_limit(task)


def test_validate_binds_parent_source_and_preserved_records(tmp_path, monkeypatch):
    monkeypatch.setattr(recovery, "ROOT", tmp_path)
    output = tmp_path / recovery.RUN
    output.mkdir(parents=True)
    monkeypatch.setattr(recovery.legacy, "collection", lambda path: (output, {}))

    def bind(name, value):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, value)
        return {"path": name, "sha256": file_hash(path)}

    release = bind("fixed-v23-release.json", {"synthetic_release": True})
    parent_entry = bind("scripts/old.py", {"synthetic_source": True})
    parent = bind(recovery.PARENT_REGISTRATION, {"version": "fixed-v23-terminal-baseline-recovery-v1",
        "entrypoint": parent_entry, "wrapper": bind("old.sh", {})})
    raw = output / "retained.json"
    checkpoint(raw, rewrite_failure())
    registration = {"version": recovery.VERSION, "output_dir": recovery.RUN,
        "new_native_calls_at_preparation": 0, "original_release_sha256": release["sha256"],
        "maximum_calls_per_language": 1660, "baseline_output_limit_is_missing": True,
        "rewrite_output_limit_is_missing": True,
        "rewrite_failure_action": "keep_initial_answer_with_rewrite_failed_status",
        "automatic_retries": 0, "phase12_allowed": False,
        "entrypoint": bind("scripts/new.py", {}), "wrapper": bind("new.sh", {}),
        "parent_registration": parent, "protected_original_files": {"retained.json": file_hash(raw)}}
    write_json(tmp_path / recovery.REGISTRATION, registration)
    assert recovery.validate(output)[0] == output
    before = (tmp_path / parent_entry["path"]).read_bytes()
    (tmp_path / parent_entry["path"]).write_text("tampered")
    with pytest.raises(ValueError, match="file changed"):
        recovery.validate(output)
    (tmp_path / parent_entry["path"]).write_bytes(before)
    raw.write_text("tampered")
    with pytest.raises(ValueError, match="preserved original"):
        recovery.validate(output)


def test_failure_inventory_includes_both_stages_without_publishing_failed_rewrite(tmp_path, monkeypatch):
    reports = {}
    for language in ("en", "ja"):
        failures = []
        for i in range(19):
            record_id = f"{language}-{i}"
            path = tmp_path / language / "baseline" / digest(record_id)[:24] / "record.json"
            path.parent.mkdir(parents=True)
            checkpoint(path, limit_record())
            failures.append({"record_id": record_id})
        identifier = language + "-rewrite"
        path = tmp_path / language / "internal" / digest(identifier)[:24] / "rewrite.json"
        path.parent.mkdir(parents=True)
        task = checkpoint(path, rewrite_failure())
        reports[language] = {"selected_qa_count": 20, "failures": failures,
            "records": [{"trace": {"record_id": identifier}, "rewrite": task}]}
        bundle = tmp_path / language / "quality"
        (bundle / "units").mkdir(parents=True)
        for name in ("packet.json", "mapping.private.json", "annotations.blank.json", "export_manifest.json",
                     "units/packet.json", "units/annotations.blank.json"):
            write_json(bundle / name, {"synthetic_preexisting_export": True})
    monkeypatch.setattr(bilingual_quality, "read_run", lambda path: ({}, reports[path.name]))
    recovery.export_packets(tmp_path)
    inventory = read_json(tmp_path / "failure_inventory.json")
    assert inventory["selected_qa"] == len(inventory["failures"]) == 40
    rewrite_failures = [r for r in inventory["failures"] if r["reason"] == "rewrite_final_answer_token_limit"]
    assert len(rewrite_failures) == 2 and all(r["replacement_or_retry"] is False and
        r["initial_answer_and_evaluation_retained"] for r in rewrite_failures)


@pytest.mark.parametrize("unknown", [False, True])
def test_other_rewrite_failure_and_unknown_still_block(tmp_path, unknown):
    path = tmp_path / "internal/a/rewrite.json"
    path.parent.mkdir(parents=True)
    task = rewrite_failure()
    task["cost_incomplete"] = unknown
    if not unknown:
        task["error"] = "GPU error"
    checkpoint(path, task)
    with pytest.raises(ValueError):
        recovery.reserve(tmp_path, 1660)


def test_progress_separates_success_baseline_missing_rewrite_missing_and_pending(tmp_path, monkeypatch):
    base = tmp_path / "ja/baseline/a/record.json"
    rewrite = tmp_path / "ja/internal/b/rewrite.json"
    base.parent.mkdir(parents=True)
    rewrite.parent.mkdir(parents=True)
    checkpoint(base, limit_record())
    checkpoint(rewrite, rewrite_failure())
    write_json(rewrite.parent / "summary.json", {"trials": [{"status": "ok"}]})
    totals = {"completed_qa": 22, "failed": 2, "baseline_qa": 39, "unknown": 0}
    value = recovery.enrich(tmp_path, {**totals, "state": "failed"})
    assert value["successful_qa"] == 22 and value["processed_qa"] == 24 and value["remaining_qa"] == 16
    assert value["baseline_failed_qa"] == value["rewrite_failed_qa"] == 1
    assert value["missing_candidate_qa"] == 2 and value["unhandled_failure_records"] == 0
    assert not (tmp_path / "status.public.json").exists()
    monkeypatch.setattr(recovery.legacy, "totals", lambda p: totals)
    monkeypatch.setattr(recovery, "ORIGINAL_PUBLIC", lambda p, state, reason: {**totals, "state": state})
    with pytest.raises(ValueError, match="incomplete"):
        recovery.public(tmp_path, "awaiting_scoring")
    totals["completed_qa"] = 38
    value = recovery.public(tmp_path, "awaiting_scoring")
    assert value["processed_qa"] == 40 and value["successful_qa"] == 38
    assert value["remaining_qa"] == 0 and value["collection_completed"] is True
    assert "書換え本文上限の失敗QA：1" in (tmp_path / "report_to_codex.txt").read_text()


def test_original_runner_resume_past_old_and_new_length_errors_and_blind_export(
        connection, monkeypatch):  # noqa: F811
    """Real task/checkpoint/quality functions; synthetic clients only, never GPU inference."""
    config_path, output, state = connection
    monkeypatch.setattr(recovery, "ROOT", config_path.parent)
    monkeypatch.setattr(bilingual_semantics, "ROOT", config_path.parent)
    write_json(config_path.parent / recovery.REGISTRATION, {"synthetic_test_only": True})
    runner = recovery.runner
    contract = runner.load_config(config_path)
    config, assets, rows, qa_path, _, _, _, prompts = contract
    seed = deepcopy(rows[0])
    rows[:] = [{**deepcopy(seed), "record_id": f"synthetic-{i}", "question": f"猫の色は？ {i}"}
               for i in range(9)]
    qa_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    assets["datasets"]["ja"]["qa"]["development"]["sha256"] = file_hash(qa_path)
    write_json(config_path.parent / "assets.json", assets)
    config.update(verification_mode="claimwise-v1", main_limits={
        "maximum_completion_attempts": 1660, "maximum_new_qa_per_stage_session": 5})
    config["tasks"]["rewrite_answer"]["max_output_tokens"] = 6144
    prompts["rewrite_format"] = "checked_json_v1"
    write_json(config_path.parent / "prompts.yaml", prompts)
    runner.run(config_path, output, stage="baseline")
    manifest = read_json(output / "manifest.json")
    rewrites = []
    original_rewrite = runner.rewrite_once

    class RewriteClient:
        def __init__(self, fail):
            self.fail = fail

        def render(self, messages):
            return json.dumps(messages)

        def tokenize(self, text, *, special):
            return [1] * (128 if special else 747 if self.fail else 20)

        def complete(self, tokens, generation, **kwargs):
            return {"content": json.dumps({"source_facts": "猫は赤い。", "draft_issues": "なし",
                "answer": "資料では、猫は赤い。[p1]"}), "stop_type": "eos", "truncated": False,
                "tokens": [1] * 800, "tokens_predicted": 800,
                "generation_settings": {"n_predict": 6144, "temperature": .2, "seed": 42}}

    def rewrite(client, generation, prompts, trace, path, binding):
        if not path.exists():
            rewrites.append(trace["record_id"])
        fake = None if path.exists() else RewriteClient(trace["record_id"] in {"synthetic-2", "synthetic-5"})
        return original_rewrite(fake, generation, prompts, trace, path, binding)

    monkeypatch.setattr(runner, "rewrite_once", rewrite)
    old_spec = importlib.util.spec_from_file_location(
        "old_recovery", Path(__file__).resolve().parents[1] / "scripts/recover_fixed_v23.py")
    old = importlib.util.module_from_spec(old_spec)
    old_spec.loader.exec_module(old)
    with pytest.raises(ValueError, match="Rewrite error"):
        old.internal_stage(output, contract, manifest)
    assert rewrites == ["synthetic-0", "synthetic-1", "synthetic-2"]
    protected = {p: file_hash(p) for p in output.rglob("*")
                 if p.is_file() and p.name not in {"progress.json", ".run.lock"}}
    assert protected
    assert not (output / "report.private.json").exists()
    first = recovery.internal_stage(output, contract, manifest)
    assert first["processed_qa"] == 8 and not first["stage_complete"]
    assert first["rewrite_failed_qa"] == 2
    second = recovery.internal_stage(output, contract, manifest)
    assert second["stage_complete"] and second["processed_qa"] == 9 and second["successful_qa"] == 7
    assert rewrites == [r["record_id"] for r in rows]
    assert all(file_hash(path) == sha for path, sha in protected.items())
    before = len(state["calls"]), state["servers"], len(rewrites)
    assert recovery.internal_stage(output, contract, manifest) == second
    assert (len(state["calls"]), state["servers"], len(rewrites)) == before
    _, report = bilingual_quality.read_run(output)
    assert len(report["records"]) == 9 and not report["failures"]
    failed = [r for r in report["records"] if r["rewrite"]["status"] == "error"]
    assert len(failed) == 2 and all(recovery.rewrite_limit(r["rewrite"]) for r in failed)
    bundle = output / "quality"
    bilingual_quality.export(output, bundle)
    export_units(bundle, bundle / "units", "ja")
    packet = read_json(bundle / "packet.json")
    mapping = read_json(bundle / "mapping.private.json")
    assert len(packet["cases"]) == 16
    for r in failed:
        slots = [s for group in mapping["assignments"].values() for s in group
                 if s["record_id"] == r["trace"]["record_id"]]
        assert slots == [{"record_id": r["trace"]["record_id"], "stage": "initial"}]
    routes = reconstruct(report["records"], {})
    fallback = [r for r in routes["routes"] if r["route"] == "always_rewrite" and
                r["record_id"] in {f["trace"]["record_id"] for f in failed}]
    assert len(fallback) == 2 and all(r["fallback"] == "rewrite_failed" and
        r["selected_stage"] == "initial" and r["quality_transition"] == "unknown" for r in fallback)
    for row in failed:
        path = output / "internal" / digest(row["trace"]["record_id"])[:24] / "rewrite.json"
        assert read_json(path)["status"] == "error"
