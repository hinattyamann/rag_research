"""Finite orchestration, ChatGPT-only billing, real annotation seals and aggregate figures."""

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_bilingual_semantics import public_packet
from test_calibration_analysis import evidence  # noqa: F401
from test_fixed_v23_recovery_v2 import recovery as recovery_v2

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts/fixed_v23_automation"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import figures  # noqa: E402
import pipeline  # noqa: E402
import review  # noqa: E402
import service  # noqa: E402

from rag_research.experiments.bilingual_semantics import (  # noqa: E402
    blank_unit_annotations,
    make_unit_packet,
)
from rag_research.experiments.quality import blank_annotations  # noqa: E402


@pytest.fixture
def config(tmp_path):
    return {"version": "fixed-v23-automation-v1", "repo": str(tmp_path), "checkout": str(tmp_path),
        "state_dir": str(tmp_path / "state"), "main_run": str(tmp_path / "main"),
        "cal_run": str(tmp_path / "cal"), "public_dir": str(tmp_path / "reports/results"),
        "public_status_json": "status.json", "public_status_markdown": "status.md", "sealed_files": {},
        "phase12_allowed": False, "api_billing_allowed": False, "maximum_cli_invocations": 5,
        "maximum_cli_job_seconds": 10, "maximum_format_repairs": 1, "annotation_cases_per_job": 4,
        "configured_codex_model": "synthetic-test-model", "configured_codex_reasoning_effort": "high",
        "codex": "synthetic-codex", "git_publish_interval_seconds": 3600, "poll_seconds": .001,
        "cal_launch_authorized": True,
        "deadline_utc": "2099-01-01T00:00:00+00:00", "branch": "main", "remote": "origin"}


def test_clean_environment_removes_both_api_keys_without_printing_them(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-secret-1")
    monkeypatch.setenv("CODEX_API_KEY", "synthetic-secret-2")
    env = common.clean_env()
    assert "OPENAI_API_KEY" not in env and "CODEX_API_KEY" not in env
    assert env["LANGSMITH_TRACING"] == "false"


def test_auth_rejects_api_login_without_exposing_credentials(config, monkeypatch):
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout="Logged in using an API key", stderr="")

    monkeypatch.setattr(review.subprocess, "run", run)
    with pytest.raises(ValueError, match="ChatGPT authentication"):
        review.cli_auth(config)
    assert len(calls) == 1 and 'forced_login_method="chatgpt"' in calls[0]


def test_cli_budget_is_durable_finite_and_same_job_is_not_charged_twice(config, tmp_path):
    assert review.reserve_cli(config, tmp_path / "job1") == 1
    assert review.reserve_cli(config, tmp_path / "job1") == 1
    config["maximum_cli_invocations"] = 1
    with pytest.raises(ValueError, match="budget exhausted"):
        review.reserve_cli(config, tmp_path / "job2")


def test_owned_receipt_never_resubmits_a_failed_or_interrupted_process(tmp_path):
    receipt = tmp_path / "receipt.json"
    common.write(receipt, {"exit_code": None})
    with pytest.raises(ValueError, match="unknown outcome"):
        common.run_owned([sys.executable, "-c", "raise Exception('must not run')"], cwd=tmp_path,
                         receipt=receipt, timeout=1)
    receipt.unlink()
    result = common.run_owned([sys.executable, "-c", "print('synthetic')"], cwd=tmp_path, receipt=receipt, timeout=2)
    assert result["exit_code"] == 0 and common.run_owned(["invalid-command"], cwd=tmp_path,
        receipt=receipt, timeout=2) == result


def packets(run):
    for lang in ("en", "ja"):
        packet, _ = public_packet(lang)
        bundle = run / lang / "quality"
        common.write(bundle / "packet.json", packet)
        common.write(bundle / "annotations.blank.json", blank_annotations(packet))
        units = make_unit_packet(packet, lang)
        common.write(bundle / "units/packet.json", units)
        common.write(bundle / "units/annotations.blank.json", blank_unit_annotations(units))


def fake_annotations(payload):
    rows = deepcopy(payload["annotations"])
    for row in rows:
        row.update(reason="Synthetic source support", evidence=[{"passage_id": "p1", "quote": "42"}])
        if payload["kind"] == "quality":
            row.update(label="reliable", criteria=dict.fromkeys(row["criteria"], "pass"), essential_points="Height")
        else:
            # The second anonymous candidate has 24, contradicting the actual source's 42.
            case = next(c for c in payload["cases"] if c["annotation_id"] == row["annotation_id"])
            claim = next(c for c in case["unit_audit"]["claims"] if c["claim_id"] == row["claim_id"])
            row["label"] = "contradicted" if "24" in claim["text"] else "supported"
    return {"annotations": rows}


def test_real_annotation_validators_and_both_language_seal_reuse_validated_jobs(config, monkeypatch):
    run = Path(config["main_run"])
    packets(run)
    calls = []

    def job(config, path, payload, blank, kind, **kwargs):
        calls.append((payload["language"], kind))
        assert "record_id" not in json.dumps(payload)
        if kind == "units":
            assert "GOLD-SECRET" not in json.dumps(payload) and "REFERENCE-SECRET" not in json.dumps(payload)
        path.mkdir(parents=True)
        common.write(path / "provenance.json", {"synthetic": True})
        return fake_annotations(payload), {"elapsed_seconds": 1., "finished_at_utc": "2026-10-30T00:00:00+00:00"}

    monkeypatch.setattr(review, "run_job", job)
    review.complete_annotations(config, run, "main")
    assert calls == [("en", "quality"), ("en", "units"), ("ja", "quality"), ("ja", "units")]
    seal = pipeline.verify_seal(run)
    assert len(seal["files"]) == 8 and not seal["human_reviewed"]
    before = len(calls)
    review.complete_annotations(config, run, "main")
    assert len(calls) == before
    annotation = common.read(run / "ja/quality/units/annotations.json")["annotations"][0]
    assert annotation["history_isolated"] is False and annotation["exact_model_identifier"] is None
    (run / "ja/quality/annotations.json").write_text("{}")
    with pytest.raises(ValueError, match="changed"):
        pipeline.verify_seal(run)


def test_pending_labels_in_last_language_prevent_every_private_analysis(config, monkeypatch):
    run = Path(config["main_run"])
    packets(run)
    files = {str(p.relative_to(run)): common.sha(p) for p in run.rglob("packet.json")}
    for language in ("en", "ja"):
        for folder in (run / language / "quality", run / language / "quality/units"):
            common.write(folder / "annotations.json", common.read(folder / "annotations.blank.json"))
            files[str((folder / "annotations.json").relative_to(run))] = common.sha(folder / "annotations.json")
    common.write(run / "all_annotations.seal.json", {"all_both_languages_sealed": True,
        "human_reviewed": False, "files": files})
    monkeypatch.setattr(pipeline, "runtime", lambda cfg: None)
    from rag_research.experiments import bilingual_quality

    def private(*args):
        pytest.fail("No private source may be opened before all labels are sealed")

    monkeypatch.setattr(bilingual_quality, "validated_annotations", private)
    with pytest.raises(ValueError, match="pending|Seal"):
        pipeline.analyze_cohort(config, "main")


def test_cal_gate_failure_stops_before_reserved_qa_or_collection_is_opened(config, monkeypatch):
    monkeypatch.setattr(pipeline, "runtime", lambda cfg: None)
    monkeypatch.setattr(pipeline, "verify_seal", lambda run: {})
    common.write(Path(config["state_dir"]) / "main/analysis.private.json", {
        "progression_gate_passed": False, "source_files_sha256": {}})
    with pytest.raises(ValueError, match="progression"):
        pipeline.prepare_cal(config)
    assert not Path(config["cal_run"]).exists()


def test_cal_preparation_registers_all_reserved_ids_preserves_source_roles_and_rejects_changed_gate(config, monkeypatch):
    from rag_research.experiments import calibration_selection

    root = Path(config["repo"])
    main_run = Path(config["main_run"])
    groups = {}
    reservation = {"source_splits": {"en": "development", "ja": "calibration"}, "languages": {}}
    for language in ("en", "ja"):
        chosen = [{"record_id": language + str(i), "document_group_id": language + "g" + str(i)} for i in range(20)]
        reservation["languages"][language] = {"selected": chosen}
        groups[language] = [{**r, "question": "Synthetic question " + r["record_id"]} for r in chosen]
        common.write(main_run / language / "manifest.json", {"selection": [
            {"record_id": language + "-main", "document_group_id": language + "-main-group"}],
            "config": {"fixed_v23_protocol": {}, "data": {"split": "development", "record_ids": []},
                "language": language, "decision": {"threshold": .7},
                "sampling": {"seed": 42}, "tasks": {"rewrite_answer": {"max_output_tokens": 6144}}}})
    common.write(root / "fixed-v23-release.json", {"synthetic": True})
    common.write(root / "fixed-v23-recovery-v2.json", {"synthetic": True})
    common.write(root / "sealed-core.py", {"synthetic_original_source": True})
    common.write(root / "data/manifests/phase11_bilingual_calibration_selection_v1.json", reservation)
    common.write(main_run / "all_annotations.seal.json", {"synthetic_complete_seal": True})
    common.write(Path(config["state_dir"]) / "main/analysis.private.json", {
        "progression_gate_passed": True, "source_files_sha256": pipeline.source_hashes(main_run)})
    fake = SimpleNamespace(verify_release=lambda: {"files": {"sealed-core.py": common.sha(root / "sealed-core.py")}},
        runner=SimpleNamespace(model_identity=lambda: {"id": "same-3B"},
            auxiliary_identity=lambda cfg: {"id": "same-9B"}, execution_identity=lambda cfg: {}))
    monkeypatch.setattr(pipeline, "runtime", lambda cfg: fake)
    monkeypatch.setattr(pipeline, "verify_seal", lambda run: {})
    monkeypatch.setattr(calibration_selection, "prepare", lambda *a, **kw: reservation)

    def contract(cfg, language, recovery):
        value = common.read(Path(cfg["cal_run"]) / "configs" / (language + ".json"))
        qa = root / (language + "-synthetic-qa.json")
        common.write(qa, groups[language])
        return value, {}, groups[language], qa, {}, None, None, {}

    monkeypatch.setattr(pipeline, "cal_contract", contract)
    pipeline.prepare_cal(config)
    registered = pipeline.verify_cal(config)
    for lang in ("en", "ja"):
        manifest = common.read(Path(config["cal_run"]) / lang / "manifest.json")
        assert len(manifest["selection"]) == 20 and manifest["config"]["analysis_split"] == "calibration"
        assert manifest["config"]["execution_scope"] == "fixed_v23_calibration_v1"
        assert manifest["config"]["data"]["split"] == reservation["source_splits"][lang]
        assert manifest["config"]["decision"]["threshold"] == .7
        assert manifest["config"]["tasks"]["rewrite_answer"]["max_output_tokens"] == 6144
        assert not manifest["gate11_passed"] and not manifest["phase12_allowed"]
    assert registered["automatic_retries"] == 0 and registered["maximum_calls_per_language"] == 1660
    common.write(Path(config["state_dir"]) / "main/analysis.private.json", {"tampered": True})
    with pytest.raises(ValueError, match="prerequisite changed"):
        pipeline.verify_cal(config)


@pytest.mark.parametrize("change", [None, "missing", "partial", "context"])
def test_resource_audit_checks_actual_cuda_and_retains_only_known_main_unpaired_logs(tmp_path, change):
    manifest = {"baseline": {"generation": {"context_tokens": 4096}},
                "config": {"auxiliary_runtime": {"context_tokens": 12288}}}
    for stage, context in (("baseline", 4096), ("internal", 12288)):
        folder = tmp_path / stage
        folder.mkdir()
        log = f"offloaded 37/37 layers to GPU\nusing device CUDA0\nllama_context: n_ctx = {context}\n"
        if change == "partial":
            log = log.replace("37/37", "16/37")
        if change == "context":
            log = log.replace(str(context), "2048")
        (folder / "server-1.log").write_text(log)
        if change != "missing":
            common.write(folder / "session-1.json", {"server_context_tokens": context,
                "full_gpu_offload": True, "actual_gpu_offload": True, "offloaded_layers": 37, "total_layers": 37})
    fake = SimpleNamespace(runner=SimpleNamespace(execution_identity=lambda cfg: {}),
        reserve=lambda run, cap: {"error_paths": ["baseline/a/record.json", "internal/b/rewrite.json"]})
    if change in {"partial", "context"}:
        with pytest.raises(ValueError, match="Actual CUDA"):
            pipeline.resource_audit(tmp_path, manifest, fake, cohort="main")
    else:
        checked = pipeline.resource_audit(tmp_path, manifest, fake, cohort="main")
        assert len(checked) == 2
        if change == "missing":
            assert all(not r["session_report_present"] for r in checked)
            with pytest.raises(ValueError, match="missing session"):
                pipeline.resource_audit(tmp_path, manifest, fake, cohort="cal")


def test_analysis_real_seals_semantics_bootstrap_routes_and_native_costs(evidence, config, monkeypatch):  # noqa: F811
    _, _, state, root = evidence
    from rag_research.data import study_assets
    from rag_research.experiments import bilingual_statistics

    run = root / "data/runs/bilingual_calibration"
    config.update(checkout=str(root), cal_run=str(run), state_dir=str(root / "workflow"))
    monkeypatch.setattr(pipeline, "runtime", lambda cfg: recovery_v2)
    monkeypatch.setattr(pipeline, "resource_audit", lambda *a, **kw: [{"synthetic_resource_double": True}])
    monkeypatch.setattr(study_assets, "load_assets", bilingual_statistics.load_assets)
    monkeypatch.setattr(study_assets, "load_rows", bilingual_statistics.load_rows)
    original_annotation_results = pipeline.annotation_results

    def external_labels(path, language):
        result = original_annotation_results(path, language)
        state["sealed"].add(language)
        return result

    monkeypatch.setattr(pipeline, "annotation_results", external_labels)
    for language in ("en", "ja"):
        path = run / language / "manifest.json"
        value = common.read(path)
        value["config"]["decision"]["sensitivity_thresholds"] = [.5, .6, .7, .8, .9]
        for row in value["selection"]:
            row["document_group_id"] = language + "g" + row["record_id"][2:]
        common.write(path, value)
    files = {str(p.relative_to(run)): common.sha(p) for p in run.rglob("*")
             if p.name in {"packet.json", "annotations.json"}}
    common.write(run / "all_annotations.seal.json", {"all_both_languages_sealed": True,
        "human_reviewed": False, "files": files})
    result = pipeline.analyze_cohort(config, "cal")
    assert state["private"] and state["sealed"] == state["units"] == {"en", "ja"}
    assert result["progression_gate_passed"] and not result["gate11_passed"] and not result["phase12_allowed"]
    assert all(result["statistics"]["languages"][lang]["comparable_qa_count"] == 20 and
        result["collection_costs"][lang]["native_attempts"] == 220 for lang in ("en", "ja"))
    assert result["statistics"]["ja_minus_en"] == {"mean": 0., "ci95": [0., 0.]}
    assert len(result["threshold_sensitivity"]) == 10
    assert all(r["mean_increment"] == 0. for r in result["threshold_sensitivity"])
    assert pipeline.analyze_cohort(config, "cal") == result


def test_cancelled_request_cost_is_not_erased_or_turned_into_candidate_missing():
    snapshot = {"error_paths": [], "unknown_or_interrupted_paths": []}
    leaves = [{"input_tokens": 3211, "output_tokens": 800, "elapsed_seconds": 30}]
    report = {"failures": [], "records": [{"rewrite": {"status": "ok"}}]}
    external = [{"input_tokens": 3211, "output_tokens": None, "cost_incomplete": True}]
    result = pipeline.collection_cost(snapshot, leaves, report, external)
    assert result["native_attempts"] == 2 and result["input_tokens"] == 6422
    assert result["output_tokens"] == 800 and result["total_output_tokens"] is None
    assert result["historical_unknown_responses"] == 1 and result["unknown"] == 0
    assert result["baseline_missing_qa"] == result["rewrite_missing_qa"] == 0
    assert not result["native_cost_complete"] and result["summed_observed_task_seconds"] == 30


def test_cancelled_session_requires_its_exact_registered_log_hash(tmp_path):
    folder = tmp_path / "internal"
    folder.mkdir()
    for stage, context in (("baseline", 4096), ("internal", 12288)):
        path = tmp_path / stage
        path.mkdir(exist_ok=True)
        (path / "server-1.log").write_text(f"offloaded 37/37 layers to GPU\nusing device CUDA0\nllama_context: n_ctx = {context}\n")
    cancelled = folder / "server-2.log"
    cancelled.write_bytes((folder / "server-1.log").read_bytes())
    attempt = {"stage": "internal", "server_log": "internal/server-2.log", "server_log_sha256": common.sha(cancelled)}
    fake = SimpleNamespace(runner=SimpleNamespace(execution_identity=lambda cfg: {}),
        reserve=lambda *a: {"error_paths": ["baseline/a/record.json", "internal/b/rewrite.json"]},
        external_attempts=lambda path: [attempt])
    manifest = {"baseline": {"generation": {"context_tokens": 4096}},
                "config": {"auxiliary_runtime": {"context_tokens": 12288}}}
    rows = pipeline.resource_audit(tmp_path, manifest, fake, cohort="main")
    assert any("external monitor cancellation" in (r["missing_report_reason"] or "") for r in rows)
    cancelled.write_text("different cancelled log")
    with pytest.raises(ValueError, match="cancelled session differs"):
        pipeline.resource_audit(tmp_path, manifest, fake, cohort="main")


def test_waiting_main_requires_all_packets_and_dead_owners(config, monkeypatch):
    run = Path(config["main_run"])
    common.write(run / "control.json", {})
    common.write(run / "status.public.json", {"state": "collecting"})
    with pytest.raises(ValueError, match="collector exited"):
        service.main_ready(config)
    monkeypatch.setattr(service, "alive", lambda owner: True)
    assert service.main_ready(config) is False
    monkeypatch.setattr(service, "alive", lambda owner: False)
    status = {"state": "awaiting_scoring", "collection_completed": True, "processed_qa": 40,
              "remaining_qa": 0, "unknown": 0, "unhandled_failure_records": 0}
    common.write(run / "status.public.json", status)
    with pytest.raises(ValueError, match="packet"):
        service.main_ready(config)
    packets(run)
    common.write(run / "failure_inventory.json", {})
    assert service.main_ready(config) is True
    monkeypatch.setattr(service, "alive", lambda owner: True)
    assert service.main_ready(config) is False


def test_waiting_service_does_not_launch_codex_or_another_collector(config, monkeypatch, tmp_path):
    path = tmp_path / "config.json"
    common.write(path, config)
    monkeypatch.setattr(service, "status_documents", lambda *a, **kw: {})
    monkeypatch.setattr(service, "publish_git", lambda cfg: {"pushed": True})
    checks = []

    def ready(cfg):
        checks.append(1)
        if len(checks) == 2:
            raise ValueError("Synthetic test stop")
        return False

    monkeypatch.setattr(service, "main_ready", ready)
    monkeypatch.setattr(service, "run_owned", lambda *a, **kw: pytest.fail("No agent/GPU calls while waiting"))
    with pytest.raises(ValueError, match="Synthetic test stop"):
        service.serve(path)
    assert len(checks) == 2 and not list(Path(config["state_dir"]).glob("jobs/*"))


@pytest.mark.parametrize("fail_gate", [False, True])
def test_stage_order_and_failed_gate_never_start_cal(config, monkeypatch, tmp_path, fail_gate):
    config.update(uv="uv", frozen_scripts=str(SCRIPTS))
    path = tmp_path / "config.json"
    common.write(path, config)
    monkeypatch.setattr(service, "status_documents", lambda *a, **kw: {})
    monkeypatch.setattr(service, "publish_git", lambda cfg: {"pushed": True})
    monkeypatch.setattr(service, "main_ready", lambda cfg: True)
    stages = []

    def run(argv, **kwargs):
        stage = kwargs["receipt"].stem
        stages.append(stage)
        if stage == "prepare-cal" and fail_gate:
            raise ValueError("Synthetic insufficient comparable QA")
        return {"exit_code": 0}

    monkeypatch.setattr(service, "run_owned", run)
    if fail_gate:
        with pytest.raises(ValueError, match="insufficient"):
            service.serve(path)
        assert stages == service.STEPS[:4] and "collect-cal" not in stages
    else:
        service.serve(path)
        assert stages == service.STEPS


def test_cal_collection_has_bounded_stages_preserves_spent_wall_on_resume(config, monkeypatch, tmp_path):
    exports = []
    fake = SimpleNamespace(export_packets=lambda run: exports.append(run), reserve=lambda run, cap: {},
        missing_count=lambda run: 0, rewrite_missing_count=lambda run: 0,
        legacy=SimpleNamespace(totals=lambda run: {"completed_qa": 40}))
    monkeypatch.setattr(pipeline, "runtime", lambda cfg: fake)
    monkeypatch.setattr(pipeline, "verify_cal", lambda cfg: {"session_wall_seconds": 10, "total_wall_seconds": 30})
    calls = []
    new = []

    def run(argv, *, receipt, timeout, **kwargs):
        language, phase, _ = receipt.stem.split("-")
        calls.append((language, phase, timeout))
        assert timeout == 10
        if not receipt.exists():
            new.append(receipt.name)
            common.write(receipt, {"exit_code": 0, "elapsed_seconds": 2.})
        common.write(Path(config["cal_run"]) / f"result-{language}-{phase}.json", {"stage_complete": True})
        return common.read(receipt)

    monkeypatch.setattr(pipeline, "run_owned", run)
    pipeline.collect_cal(config, tmp_path / "config.json")
    pipeline.collect_cal(config, tmp_path / "config.json")
    assert len(new) == 4 and len(calls) == 8 and len(exports) == 2
    assert common.read(Path(config["cal_run"]) / "collection_completed.json")["processed_qa"] == 40


def test_cli_command_pins_chatgpt_auth_model_sandbox_and_has_durable_provenance(config, monkeypatch, tmp_path):
    monkeypatch.setattr(review, "cli_auth", lambda cfg: None)
    observed = []

    def run(argv, *, receipt, **kwargs):
        observed.append(argv)
        output = Path(argv[argv.index("--output-last-message") + 1])
        common.write(output, {"annotations": []})
        common.write(receipt, {"exit_code": 0, "elapsed_seconds": 1., "finished_at_utc": "2026-10-30T00:00:00+00:00"})
        receipt.with_suffix(".log").write_text(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10}}) + "\n")
        return common.read(receipt)

    monkeypatch.setattr(review, "run_owned", run)
    blank = {"annotation_id": "Q-test", "candidate_sha256": "test", "label": "pending",
        "criteria": {"context_support": "pending"}, "essential_points": "", "reason": "", "evidence": []}
    result, proof = review.run_job(config, tmp_path / "job", {"cohort": "synthetic", "language": "en"}, blank, "quality")
    assert result == {"annotations": []}
    assert 'forced_login_method="chatgpt"' in observed[0] and "--sandbox" in observed[0]
    assert 'model="synthetic-test-model"' in observed[0]
    assert proof["token_usage"] == [{"input_tokens": 10}] and proof["api_key_fallback"] is False


def git(cwd, *args):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()


def test_git_publisher_only_commits_allowlisted_progress_and_never_user_edits(config, tmp_path):
    repo = tmp_path / "repo"
    remote = tmp_path / "remote.git"
    repo.mkdir()
    git(tmp_path, "init", "--bare", str(remote))
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "synthetic@example.invalid")
    git(repo, "config", "user.name", "Synthetic Test")
    git(repo, "remote", "add", "origin", str(remote))
    (repo / "initial").write_text("initial")
    (repo / "user.txt").write_text("original")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "initial")
    git(repo, "push", "-u", "origin", "main")
    config.update(repo=str(repo), remote_url=str(remote), public_dir=str(repo / "reports"))
    common.write(repo / "status.json", {"stage": "waiting_main"})
    (repo / "status.md").write_text("progress")
    (repo / "user.txt").write_text("unfinished user work")
    result = service.publish_git(config)
    assert result["pushed"] and git(repo, "show", "HEAD:user.txt") == "original"
    assert git(repo, "status", "--porcelain") == "M user.txt"
    git(repo, "add", "user.txt")
    with pytest.raises(ValueError, match="staged changes"):
        service.publish_git(config)
    assert git(repo, "diff", "--cached", "--name-only") == "user.txt"


def figure_result(cohort):
    return {"cohort": cohort, "condition_sha256": "same", "progression_gate_passed": True,
        "gate11_passed": False, "phase12_allowed": False, "human_reviewed": False, "limitations": ["synthetic"],
        "statistics": {"languages": {lang: {"selected_qa_count": 20, "comparable_qa_count": 12,
            "missing_qa_count": 8, "mean_increment": 0., "ci95": [0., 0.]} for lang in ("en", "ja")},
            "qa": [], "ja_minus_en": {"mean": 0., "ci95": [0., 0.]}}, "semantics": {},
        "collection_costs": {lang: {"native_attempts": 220, "output_tokens": 4400,
            "summed_observed_task_seconds": 1000, "archived_external_attempts": 0,
            "native_cost_complete": True, "total_output_tokens": 4400} for lang in ("en", "ja")},
        "quality_routes": {lang: {"routes": [{"route": route, "quality_status": "reliable", "fallback": None,
            "operational_cost": {"recorded_completion_attempts": 1, "input_tokens": 10, "output_tokens": 2}}
            for route in ("no_repair", "always_rewrite", "original") for _ in range(20)]} for lang in ("en", "ja")},
        "threshold_sensitivity": [{"language": lang, "threshold": threshold, "comparable_qa": 12,
            "mean_increment": 0.} for lang in ("en", "ja") for threshold in (.5, .6, .7, .8, .9)]}


def test_scientific_figures_have_csv_pdf_svg_and_preserve_zero_effect_and_no_overclaim(config, monkeypatch):
    monkeypatch.setattr(figures, "verify_seal", lambda run: {})
    monkeypatch.setattr(figures, "source_hashes", lambda run: {})
    for cohort in ("main", "cal"):
        result = figure_result(cohort)
        if cohort == "main":
            result["collection_costs"]["ja"].update(native_attempts=221, archived_external_attempts=1,
                native_cost_complete=False, total_output_tokens=None)
        common.write(Path(config["state_dir"]) / cohort / "analysis.private.json", {
            **result, "source_files_sha256": {}})
    figures.create_figures(config)
    output = Path(config["public_dir"])
    manifest = common.read(output / "artifact_manifest.json")
    assert len(list(output.glob("*.pdf"))) == len(list(output.glob("*.svg"))) == 4
    assert len(list(output.glob("*.csv"))) == 4
    assert not manifest["gate11_passed"] and not manifest["phase12_allowed"]
    assert "0.0" in (output / "primary_comparison.csv").read_text()
    assert "効果なしを証明したとは書かない" in (output / "results_brief.md").read_text()
    assert "最終費用は不明" in (output / "results_brief.md").read_text()
    before = {name: common.sha(output / name) for name in manifest["files"]}
    figures.create_figures(config)
    assert before == {name: common.sha(output / name) for name in before}
