"""Real guard boundaries; these software checks do not constitute Gate11 evidence."""

import copy
import io
import json
from unittest.mock import Mock

import pytest

from rag_research.experiments import phase11_autonomy as autonomy
from rag_research.experiments.frozen_trace import digest
from rag_research.experiments.storage import checkpoint, read_json, write_json
from rag_research.generation.local import GenerationError, LlamaClient
from rag_research.retrieval.common import file_hash


def bind(root, name):
    return {"path": name, "sha256": file_hash(root / name)}


@pytest.fixture
def setup_run(tmp_path):
    root = tmp_path
    for name in ("configs", "scripts", "data/runs", "docs"):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / "docs/authorization.md").write_text("Finite plans; scientific criteria stay unchanged")
    (root / "configs/legacy.json").write_text(json.dumps({
        "cumulative_recorded_all9b_development_attempts": 909, "cumulative_unknown_responses": 3,
        "known_regression_adopted": False}))
    (root / "configs/candidate.yaml").write_text(
        "auxiliary_runtime:\n  timeout_seconds: 10\nerrors:\n  automatic_retries: 0\n")
    (root / "scripts/probe.py").write_text(
        "import pathlib,sys\n"
        "p=pathlib.Path(sys.argv[sys.argv.index('--output-dir')+1]); p.mkdir(parents=True)\n"
        "(p/'report.json').write_text('{}')\n")
    protocol = {"version": autonomy.VERSION, "semantic_adoption_version": autonomy.ADOPTION,
                "scientific_rules": autonomy.SCIENTIFIC_RULES,
                "authorization": bind(root, "docs/authorization.md"),
                "legacy_result": bind(root, "configs/legacy.json"), "legacy_attempts": 909,
                "legacy_unknown": 3, "global_call_ceiling": None, "global_seconds_ceiling": None,
                "global_candidate_ceiling": None}
    protocol_path = root / "configs/autonomy.json"
    write_json(protocol_path, protocol)
    identity = {key: [bind(root, "configs/candidate.yaml")] for key in autonomy.COMPONENTS}
    plan = {"version": autonomy.VERSION, "semantic_adoption_version": autonomy.ADOPTION,
            "protocol_sha256": file_hash(protocol_path), "run_id": "probe-first", "stage": "smoke",
            "phase12_allowed": False, "fixed_commit": "a" * 40,
            "hypothesis": "Isolate a changed runtime", "change": "Graph setting changed",
            "validation_scope": "One complete fixed target", "stop_method": "TERM owned session",
            "resume_method": "Preserve unknowns, register a changed condition; no resend",
            "targets": ["development-case-1"], "target_counts": {"qa": 1, "fixed_units": 1, "conditions": 1},
            "identity_files": identity, "candidate_identity_sha256": digest(identity),
            "bindings": [bind(root, "scripts/probe.py"), bind(root, "configs/candidate.yaml")],
            "budget": {"planned_calls": 1, "maximum_calls": 1, "estimated_tokens": 30,
                       "estimated_native_seconds": 1, "maximum_wall_seconds": 20,
                       "request_timeout_seconds": 10, "maximum_tokens_per_call": 32},
            "monitor": {"method": "process_journal_resources", "interval_seconds": 1},
            "automatic_retries": 0, "output_dir": "data/runs/probe-first",
            "command": ["scripts/probe.py", "--config", "configs/candidate.yaml",
                        "--output-dir", "data/runs/probe-first"]}
    plan_path = root / "configs/plan.json"
    write_json(plan_path, plan)
    return root, protocol_path, plan_path, plan, root / "data/runs/ledger"


def test_legacy_guard_and_result_bindings_preserved(setup_run):
    root, protocol_path, _, plan, _ = setup_run
    autonomy.validate_plan(root, plan, protocol_path)
    protocol = read_json(protocol_path)
    protocol["legacy_attempts"] = 908
    write_json(protocol_path, protocol)
    with pytest.raises(ValueError, match="Legacy counters"):
        autonomy.load_protocol(root, protocol_path)


@pytest.mark.parametrize("field,value", [
    ("hypothesis", ""), ("resume_method", ""), ("automatic_retries", 1),
    ("candidate_identity_sha256", "0" * 64), ("phase12_allowed", True)])
def test_missing_registration_or_changed_identity_rejected(setup_run, field, value):
    root, protocol_path, _, plan, _ = setup_run
    plan[field] = value
    with pytest.raises(ValueError):
        autonomy.validate_plan(root, plan, protocol_path)


@pytest.mark.parametrize("value", [float("inf"), float("nan"), -1, True])
def test_nonfinite_run_budget_rejected(setup_run, value):
    root, protocol_path, _, plan, _ = setup_run
    plan["budget"]["maximum_wall_seconds"] = value
    with pytest.raises(ValueError):
        autonomy.validate_plan(root, plan, protocol_path)


def test_bound_config_request_timeout_enforced(setup_run):
    root, protocol_path, _, plan, _ = setup_run
    plan["budget"]["request_timeout_seconds"] = 9
    with pytest.raises(ValueError, match="timeout"):
        autonomy.validate_plan(root, plan, protocol_path)


def test_known_cannot_shrink_denominators(setup_run):
    root, protocol_path, _, plan, _ = setup_run
    plan["stage"] = "known"
    with pytest.raises(ValueError, match="15/42/30/84"):
        autonomy.validate_plan(root, plan, protocol_path)


def test_same_condition_cannot_be_resampled_under_new_run_name(setup_run):
    root, protocol_path, plan_path, plan, ledger_dir = setup_run
    autonomy.register(root, protocol_path, plan_path, ledger_dir)
    plan.update(run_id="renamed-run", output_dir="data/runs/renamed-run")
    plan["command"][-1] = plan["output_dir"]
    write_json(plan_path, plan)
    with pytest.raises(ValueError, match="resampling"):
        autonomy.register(root, protocol_path, plan_path, ledger_dir)
    assert autonomy.inspect_handle(ledger_dir)["totals"]["cumulative_attempts"] == 909


def activate(setup_run, monkeypatch):
    root, protocol_path, plan_path, plan, ledger_dir = setup_run
    autonomy.register(root, protocol_path, plan_path, ledger_dir)
    ledger_path = ledger_dir / "ledger.json"
    ledger = read_json(ledger_path)
    ledger["runs"][0].update(state="running", started_at_utc=autonomy.now())
    write_json(ledger_path, ledger)
    monkeypatch.setenv(autonomy.CONTEXT_ENV, json.dumps({"ledger_dir": str(ledger_dir),
                                                       "run_id": plan["run_id"]}))
    return ledger_dir, plan


def test_budget_reserves_before_http_and_second_call_never_sent(setup_run, monkeypatch):
    ledger_dir, plan = activate(setup_run, monkeypatch)
    client = LlamaClient(8000, timeout=10)
    response = {"content": "ok", "tokens": [1, 2], "stop_type": "eos"}

    def open_request(*args, **kwargs):
        snapshot = autonomy.native_snapshot(ledger_dir, plan["run_id"])
        assert snapshot["attempts"] == snapshot["unknown"] == 1
        return io.StringIO(json.dumps(response))

    client.opener.open = Mock(side_effect=open_request)
    assert client.request("/completion", {"n_predict": 3}) == response
    with pytest.raises(ValueError, match="budget exhausted"):
        client.request("/completion", {"n_predict": 3})
    assert client.opener.open.call_count == 1
    snapshot = autonomy.native_snapshot(ledger_dir, plan["run_id"])
    assert snapshot["returned"] == 1 and snapshot["observed_output_tokens"] == 2


def test_transport_unknown_preserved_and_no_second_submission(setup_run, monkeypatch):
    ledger_dir, plan = activate(setup_run, monkeypatch)
    client = LlamaClient(8000, timeout=10)
    client.opener.open = Mock(side_effect=TimeoutError("uncertain server outcome"))
    with pytest.raises(GenerationError):
        client.request("/completion", {"n_predict": 3})
    with pytest.raises(ValueError, match="unknown"):
        client.request("/completion", {"n_predict": 3})
    assert client.opener.open.call_count == 1
    snapshot = autonomy.native_snapshot(ledger_dir, plan["run_id"])
    assert snapshot["attempts"] == snapshot["unknown"] == 1
    assert snapshot["total_output_tokens"] is None and snapshot["cost_incomplete"]


def test_inflight_reservation_is_not_resent_after_crash(setup_run, monkeypatch):
    ledger_dir, plan = activate(setup_run, monkeypatch)
    autonomy.begin_native_call("/completion", {"n_predict": 3}, 10)
    with pytest.raises(ValueError, match="in-flight"):
        autonomy.begin_native_call("/completion", {"n_predict": 3}, 10)
    assert autonomy.native_snapshot(ledger_dir, plan["run_id"])["unknown"] == 1


@pytest.mark.parametrize("timeout,tokens", [(9, 3), (10, 33)])
def test_native_timeout_and_token_caps_before_submission(setup_run, monkeypatch, timeout, tokens):
    ledger_dir, plan = activate(setup_run, monkeypatch)
    with pytest.raises(ValueError):
        autonomy.begin_native_call("/completion", {"n_predict": tokens}, timeout)
    assert autonomy.native_snapshot(ledger_dir, plan["run_id"])["attempts"] == 0


def test_legacy_native_client_is_unchanged_without_v3_context(monkeypatch):
    monkeypatch.delenv(autonomy.CONTEXT_ENV, raising=False)
    client = LlamaClient(8000, timeout=10)
    client.opener.open = Mock(return_value=io.StringIO('{"tokens": []}'))
    assert client.request("/completion", {"n_predict": 3}) == {"tokens": []}


def test_chain_rejects_mixed_versions_and_changed_candidate(setup_run):
    root, protocol_path, _, plan, _ = setup_run
    identity = {"autonomy_protocol_version": autonomy.VERSION,
                "autonomy_protocol": bind(root, protocol_path.relative_to(root).as_posix()),
                "candidate_identity_sha256": plan["candidate_identity_sha256"]}
    assert autonomy.validate_chain_identity({}, {}, root=root) is None
    assert autonomy.validate_chain_identity(identity, copy.deepcopy(identity), root=root) == identity
    with pytest.raises(ValueError, match="Mixed legacy"):
        autonomy.validate_chain_identity(identity, {}, root=root)
    changed = {**identity, "candidate_identity_sha256": "0" * 64}
    with pytest.raises(ValueError, match="differs"):
        autonomy.validate_chain_identity(identity, changed, root=root)


def test_next_stage_needs_passing_bound_predecessor(setup_run):
    root, protocol_path, _, plan, _ = setup_run
    certificate = {"version": autonomy.VERSION, "semantic_adoption_version": autonomy.ADOPTION,
                   "protocol_sha256": file_hash(protocol_path),
                   "candidate_identity_sha256": plan["candidate_identity_sha256"],
                   "stage": "cal", "scientific_gate_passed": False,
                   "evidence": [bind(root, "configs/legacy.json")]}
    write_json(root / "configs/certificate.json", certificate)
    plan.update(stage="freeze", predecessor=bind(root, "configs/certificate.json"))
    plan["budget"].update(planned_calls=0, maximum_calls=0)
    with pytest.raises(ValueError, match="predecessor certificate"):
        autonomy.validate_plan(root, plan, protocol_path)


def test_journal_keeps_unknown_and_ignores_aggregate(tmp_path):
    checkpoint(tmp_path / "returned.json", {"request_sha256": "a", "completion_attempted": True,
        "status": "ok", "input_tokens": 10, "output_tokens": 20, "elapsed_seconds": 2})
    write_json(tmp_path / "started.json", {"request_sha256": "b", "completion_attempted": True,
        "status": "started", "input_tokens": 12, "output_tokens": None})
    write_json(tmp_path / "aggregate.json", {"request_sha256": "c", "completion_attempted": True,
        "status": "ok", "execution_mode": "claimwise-v1"})
    result = autonomy.journal_snapshot(tmp_path)
    assert result["attempts"] == 2 and result["successful"] == result["unknown"] == 1
    assert result["total_output_tokens"] is None and result["cost_incomplete"]


def test_execute_a_real_zero_generation_process_and_refuse_relaunch(setup_run, monkeypatch):
    root, protocol_path, plan_path, plan, ledger_dir = setup_run
    plan["stage"] = "preflight"
    plan["budget"].update(planned_calls=0, maximum_calls=0)
    write_json(plan_path, plan)
    autonomy.register(root, protocol_path, plan_path, ledger_dir)
    monkeypatch.setattr(autonomy, "_fixed_checkout", lambda *args: None)
    monkeypatch.setattr(autonomy, "_resource_sample", lambda pid: {"at_utc": autonomy.now(), "errors": []})
    result = autonomy.execute(root, protocol_path, ledger_dir, plan["run_id"])
    assert result["state"] == "process_completed" and result["snapshot"]["attempts"] == 0
    assert result["scientific_gate_passed_not_asserted"]
    assert (root / plan["output_dir"] / "report.json").exists()
    with pytest.raises(ValueError, match="Never relaunch"):
        autonomy.execute(root, protocol_path, ledger_dir, plan["run_id"])
