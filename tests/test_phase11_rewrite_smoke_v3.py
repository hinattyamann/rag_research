"""Independent synthetic live-ledger fixtures; no process, server or QA access."""

import copy
import hashlib
import importlib.util
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
SOURCE = ROOT / "data/manifests/phase11_rewrite_smoke_inputs_v25.json"
spec = importlib.util.spec_from_file_location("portable_rewrite_smoke_entry", ROOT / "scripts/run_phase11_rewrite_smoke_v3.py")
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(autouse=True)
def forbid_server(monkeypatch):
    def fail(*_args, **_kwargs):
        pytest.fail("Contract unit tests must never start a model server")
    monkeypatch.setattr(entry, "LocalServer", fail)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


@pytest.fixture
def live(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git/HEAD").write_text("a" * 40)
    script = tmp_path / entry.ENTRY
    script.parent.mkdir()
    script.write_bytes((ROOT / "scripts/run_phase11_rewrite_smoke_v3.py").read_bytes())
    config = tmp_path / "config.yaml"
    config.write_text("generation: {timeout_seconds: 1200}\n")
    protocol = tmp_path / "configs/phase11_autonomy_v3.json"
    protocol.parent.mkdir()
    protocol.write_text("{}\n")
    protocol_sha = sha(protocol)
    identity = {}
    for component in ("model", "runtime", "prompt", "sampler", "schema", "core"):
        path = tmp_path / (component + ".synthetic")
        path.write_text("registered " + component + "\n")
        identity[component] = [{"path": path.name, "sha256": sha(path)}]
    rewrite_plan = tmp_path / "rewrite-plan.json"
    rewrite_plan.write_text("{}\n")
    argv = ["--config", "config.yaml", "--rewrite-plan", "rewrite-plan.json", "--output-dir", "data/runs/runtime_screening/synthetic-review"]
    args = SimpleNamespace(config=config, rewrite_plan=rewrite_plan, output_dir=tmp_path / argv[-1])
    bindings = [{"path": p.relative_to(tmp_path).as_posix(), "sha256": sha(p)} for p in (script, config, rewrite_plan)]
    plan = {"version": "phase11-autonomy-v3", "stage": "smoke", "automatic_retries": 0,
        "phase12_allowed": False, "protocol_sha256": protocol_sha, "command": [entry.ENTRY, *argv],
        "semantic_adoption_version": "support-binary-v2", "run_id": "synthetic-review",
        "hypothesis": "synthetic hypothesis", "change": "synthetic change", "validation_scope": "synthetic only",
        "stop_method": "stop owned group", "resume_method": "no resend",
        "targets": ["rewrite/en", "rewrite/ja"], "target_counts": {"qa": 2, "fixed_units": 2, "conditions": 2},
        "identity_files": identity, "candidate_identity_sha256": entry.digest(identity),
        "fixed_commit": "a" * 40, "budget": {"maximum_wall_seconds": 1800, "planned_calls": 2,
            "maximum_calls": 2, "request_timeout_seconds": 1200, "maximum_tokens_per_call": 6144,
            "estimated_tokens": 24576, "estimated_native_seconds": 160},
        "monitor": {"method": "process_journal_resources", "interval_seconds": 5}, "bindings": bindings,
        "output_dir": argv[-1]}
    ledger_dir = tmp_path / "data/runs/development_screening/phase11-autonomy-v3"
    row = {"run_id": "synthetic-review", "state": "running", "plan": plan,
        "plan_content_sha256": entry.digest(plan), "plan_sha256": "c" * 64,
        "supervisor_pid": 12345, "supervisor_create_time": 100.0,
        "child_pid": os.getpid(), "child_create_time": 200.0,
        "started_at_utc": (datetime.now(UTC) - timedelta(seconds=30)).isoformat()}
    ledger = {"version": "phase11-autonomy-v3", "protocol_sha256": protocol_sha, "runs": [row]}
    monitor = {"plan": copy.deepcopy(plan), "plan_sha256": "c" * 64, "protocol_sha256": protocol_sha}

    def sync():
        row["plan_content_sha256"] = entry.digest(plan)
        monitor["plan"] = copy.deepcopy(plan)
        save(ledger_dir / "ledger.json", ledger)
        save(ledger_dir / row["run_id"] / "manifest.json", monitor)

    class Process:
        def __init__(self, pid):
            self.pid = pid

        def is_running(self):
            return True

        def status(self):
            return "running"

        def create_time(self):
            return 100.0 if self.pid == 12345 else 200.0

    # Only this synthetic fixture substitutes protocol-history loading; the real
    # validate_plan body and every synthetic identity/binding hash execute.
    monkeypatch.setattr(entry.validate_plan.__globals__["sys"].modules[entry.validate_plan.__module__], "load_protocol", lambda *_: {})
    monkeypatch.setenv("RAG_PHASE11_AUTONOMY_CONTEXT", json.dumps({"ledger_dir": str(ledger_dir), "run_id": row["run_id"]}))
    monkeypatch.setattr(entry, "__file__", str(script))
    monkeypatch.setattr(entry.psutil, "Process", Process)
    monkeypatch.setattr(entry.os, "getpgrp", os.getpid)
    sync()
    return SimpleNamespace(root=tmp_path, args=args, argv=argv, plan=plan, row=row, ledger=ledger,
        monitor=monitor, ledger_dir=ledger_dir, sync=sync, Process=Process)


def test_complete_synthetic_live_owner_contract_accepts(live):
    plan, bindings = entry.live_plan(live.root, live.argv, live.args)
    assert plan == live.plan and len(bindings) == 3


@pytest.mark.parametrize("change", ["canonical", "terminal", "duplicate", "plan_digest", "manifest",
    "protocol", "command", "head", "pid_time", "zombie", "child_pid", "group", "expired", "future",
    "calls", "wall", "timeout", "tokens", "monitor", "changed_binding", "missing_config_binding",
    "missing_entry_binding", "old_output", "root_output", "outside_output"])
def test_live_contract_mutations_reject(live, monkeypatch, change):
    if change == "canonical":
        monkeypatch.setenv("RAG_PHASE11_AUTONOMY_CONTEXT", json.dumps({"ledger_dir": str(live.root / "other"), "run_id": "synthetic-review"}))
    elif change == "terminal":
        live.row["state"] = "process_completed"
    elif change == "duplicate":
        live.ledger["runs"].append(copy.deepcopy(live.row))
    elif change == "plan_digest":
        live.row["plan_content_sha256"] = "d" * 64
    elif change == "manifest":
        live.monitor["plan_sha256"] = "d" * 64
    elif change == "protocol":
        live.ledger["protocol_sha256"] = "d" * 64
    elif change == "command":
        live.plan["command"].append("extra")
    elif change == "head":
        (live.root / ".git/HEAD").write_text("d" * 40)
    elif change == "pid_time":
        live.row["supervisor_create_time"] = 99.0
    elif change == "zombie":
        monkeypatch.setattr(live.Process, "status", lambda _: entry.psutil.STATUS_ZOMBIE)
    elif change == "child_pid":
        live.row["child_pid"] = os.getpid() + 1
    elif change == "group":
        monkeypatch.setattr(entry.os, "getpgrp", lambda: os.getpid() + 1)
    elif change in {"expired", "future"}:
        seconds = 1900 if change == "expired" else -30
        live.row["started_at_utc"] = (datetime.now(UTC) - timedelta(seconds=seconds)).isoformat()
    elif change == "calls":
        live.plan["budget"]["maximum_calls"] = 3
    elif change == "wall":
        live.plan["budget"]["maximum_wall_seconds"] = 1801
    elif change == "timeout":
        live.plan["budget"]["request_timeout_seconds"] = 300
    elif change == "tokens":
        live.plan["budget"]["maximum_tokens_per_call"] = 6145
    elif change == "monitor":
        live.plan["monitor"]["interval_seconds"] = 60
    elif change == "changed_binding":
        live.args.config.write_text("changed: true\n")
    elif change in {"missing_config_binding", "missing_entry_binding"}:
        name = "config.yaml" if change == "missing_config_binding" else entry.ENTRY
        live.plan["bindings"] = [b for b in live.plan["bindings"] if b["path"] != name]
    elif change == "old_output":
        live.args.output_dir.mkdir(parents=True)
    elif change == "root_output":
        live.args.output_dir = live.root / "data/runs/runtime_screening"
        live.plan["output_dir"] = "data/runs/runtime_screening"
    elif change == "outside_output":
        live.args.output_dir = live.root / "data/runs/elsewhere/new"
        live.plan["output_dir"] = "data/runs/elsewhere/new"
    if change not in {"plan_digest", "manifest"}:
        live.sync()
    else:
        save(live.ledger_dir / "ledger.json", live.ledger)
        save(live.ledger_dir / live.row["run_id"] / "manifest.json", live.monitor)
    with pytest.raises((ValueError, FileNotFoundError)):
        entry.live_plan(live.root, live.argv, live.args)


def test_identity_file_not_directly_bound_is_rehashed_and_change_rejects(live):
    """Full candidate revalidation rejects the initial-entry counterexample."""
    core = live.root / "core.py"
    core.write_text("registered = True\n")
    live.plan["identity_files"]["core"] = [{"path": "core.py", "sha256": sha(core)}]
    live.plan["candidate_identity_sha256"] = entry.digest(live.plan["identity_files"])
    live.sync()
    core.write_text("registered = False\n")
    with pytest.raises(ValueError, match="Missing or changed bound file: core.py"):
        entry.live_plan(live.root, live.argv, live.args)


def test_duplicate_binding_rejects_at_entry(live):
    """Existing full validator now rejects duplicate input bindings at entry."""
    live.plan["bindings"].append(copy.deepcopy(live.plan["bindings"][0]))
    live.sync()
    with pytest.raises(ValueError, match="Duplicate input binding"):
        entry.live_plan(live.root, live.argv, live.args)


def fixture(tmp_path, monkeypatch):
    config = yaml.safe_load((ROOT / "configs/phase11_semantic_candidate_v25.yaml").read_text())
    prompts = {lang: yaml.safe_load((ROOT / path).read_text()) for lang, path in config["prompts"].items()}
    monkeypatch.setattr(entry, "load_config", lambda _: (config, {}, prompts, None))
    source = tmp_path / "source.json"
    source.write_bytes(SOURCE.read_bytes())
    source_binding = {"path": "source.json", "sha256": sha(source)}
    cases = json.loads(source.read_text())["cases"]
    target = {"purpose": "phase11-synthetic-rewrite-smoke-v3", "maximum_calls": 2,
        "automatic_retries": 0, "phase12_allowed": False, "source": source_binding,
        "targets": [c["id"] for c in cases]}
    target_path = tmp_path / "target.json"
    target_path.write_text(json.dumps(target))
    args = SimpleNamespace(config=tmp_path / "config.yaml", rewrite_plan=target_path,
        output_dir=tmp_path / "out")
    plan = {"candidate_identity_sha256": config["candidate_identity_sha256"],
        "targets": ["rewrite/" + c["id"] for c in cases],
        "target_counts": {"qa": 2, "fixed_units": 2, "conditions": 2}}
    return config, args, plan, {"source.json": source_binding}


def test_missing_live_context_rejects_before_source_reads(tmp_path, monkeypatch):
    monkeypatch.delenv("RAG_PHASE11_AUTONOMY_CONTEXT", raising=False)
    monkeypatch.setattr(entry, "read_json", lambda _: pytest.fail("Read before live supervisor check"))
    with pytest.raises(ValueError, match="live v3 supervisor"):
        entry.live_plan(tmp_path, [], None)


def test_two_full_inputs_and_effective_rewrite1024(tmp_path, monkeypatch):
    _, args, plan, bindings = fixture(tmp_path, monkeypatch)
    _, prompts, generation, _, cases = entry.load_rewrite_inputs(tmp_path, plan, bindings, args)
    assert generation.reasoning_budget_tokens == 1024
    assert len(cases) == 2 and {c["language"] for c in cases} == {"en", "ja"}
    for case in cases:
        trace = {key: case[key] for key in entry.FIELDS}
        messages = entry.rewrite_once.__globals__["build_messages"](prompts[case["language"]], "rewrite_answer", trace)
        payload = json.loads(messages[1]["content"].removeprefix("Input JSON:\n"))
        assert set(payload) == {"question", "answer", "documents"}
        assert payload["documents"] == case["documents"] and payload["answer"] == case["answer"]
        assert "offline_expected" not in payload


@pytest.mark.parametrize("change", ["budget4096", "candidate", "targets", "denominator", "sourcebytes"])
def test_changed_contract_rejected(tmp_path, monkeypatch, change):
    config, args, plan, bindings = fixture(tmp_path, monkeypatch)
    if change == "budget4096":
        config["sampling"]["reasoning_budget_tokens"] = 4096
    elif change == "candidate":
        plan["candidate_identity_sha256"] = "0" * 64
    elif change == "targets":
        plan["targets"].pop()
    elif change == "denominator":
        plan["target_counts"]["fixed_units"] = 0
    else:
        source = tmp_path / "source.json"
        source.write_bytes(source.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        entry.load_rewrite_inputs(tmp_path, plan, bindings, args)
