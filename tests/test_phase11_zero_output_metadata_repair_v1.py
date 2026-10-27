"""Local miniature Git worktrees and invented metadata; never real Run mutation."""

import importlib.util
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
SOURCE = next(
    p
    for p in (
        Path(__file__).with_name("phase11_zero_output_metadata_repair_v1.py"),
        PROJECT / "scripts/phase11_zero_output_metadata_repair_v1.py",
    )
    if p.is_file()
)
SPEC = importlib.util.spec_from_file_location("zero_output_metadata_repair_v1", SOURCE)
REPAIR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPAIR)


def local_git(root, *args):
    return (
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
        .stdout.decode()
        .strip()
    )


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(REPAIR.encoded(value))


@pytest.fixture
def registered(tmp_path):
    """Native0 fixture: six tiny identity files, exact real v3 policy checker."""
    from rag_research.experiments import phase11_autonomy as guard

    canonical = tmp_path / "invented-canonical"
    canonical.mkdir()
    local_git(canonical, "init", "-q")
    (canonical / ".gitignore").write_text(".tools/\ndata/runs/\n")
    identity = {}
    for component in sorted(guard.COMPONENTS):
        path = canonical / f"fixtures/{component}.txt"
        path.parent.mkdir(exist_ok=True)
        path.write_text("Invented metadata-only identity " + component)
        identity[component] = [
            {"path": path.relative_to(canonical).as_posix(), "sha256": REPAIR.sha(path)}
        ]
    for name, text in {
        "docs/test-authorization.txt": "Invented authorization fixture only.",
        "scripts/noop.py": 'raise RuntimeError("Never execute this fixture")\n',
    }.items():
        path = canonical / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(text)
    legacy = canonical / "fixtures/legacy.json"
    save(
        legacy,
        {
            "cumulative_recorded_all9b_development_attempts": 909,
            "cumulative_unknown_responses": 3,
            "known_regression_adopted": False,
        },
    )
    parent = {
        "version": guard.VERSION,
        "semantic_adoption_version": guard.ADOPTION,
        "scientific_rules": guard.SCIENTIFIC_RULES,
        "global_call_ceiling": None,
        "global_seconds_ceiling": None,
        "global_candidate_ceiling": None,
        "authorization": {
            "path": "docs/test-authorization.txt",
            "sha256": REPAIR.sha(canonical / "docs/test-authorization.txt"),
        },
        "legacy_result": {"path": "fixtures/legacy.json", "sha256": REPAIR.sha(legacy)},
        "legacy_attempts": 909,
        "legacy_unknown": 3,
    }
    parent_path = canonical / "configs/phase11_autonomy_v3.json"
    save(parent_path, parent)
    save(
        canonical / "configs/invented.yaml",
        {"auxiliary_runtime": {"timeout_seconds": 1200}, "errors": {"automatic_retries": 0}},
    )
    local_git(canonical, "add", ".")
    local_git(
        canonical,
        "-c",
        "user.name=Metadata fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "invented fixture only",
    )
    commit = local_git(canonical, "rev-parse", "HEAD")
    root = tmp_path / "invented-dedicated-WT"
    local_git(canonical, "worktree", "add", "--detach", "-q", str(root), commit)
    relocations = []
    for number, name in enumerate(REPAIR.SOURCE_JSON):
        for base in (canonical, root):
            path = base / name
            save(path, {"invented_fixture_only": True, "native_calls": 0, "number": number})
            path.with_suffix(".sha256").write_text(REPAIR.sha(path) + "  " + path.name + "\n")
        relocations.append(
            {
                "source": name,
                "destination": REPAIR.TARGET_PREFIX + Path(name).name,
                "sha256": REPAIR.sha(root / name),
                "sidecar_sha256": REPAIR.sha((root / name).with_suffix(".sha256")),
            }
        )
    bindings = [
        {"path": n, "sha256": REPAIR.sha(root / n)}
        for n in (
            "scripts/noop.py",
            "configs/invented.yaml",
            "configs/phase11_autonomy_v3.json",
            *REPAIR.SOURCE_JSON,
        )
    ]
    plan = {
        "version": guard.VERSION,
        "semantic_adoption_version": guard.ADOPTION,
        "protocol_sha256": REPAIR.sha(root / "configs/phase11_autonomy_v3.json"),
        "run_id": "phase11-v3-v26-smoke",
        "stage": "smoke",
        "phase12_allowed": False,
        "fixed_commit": commit,
        "hypothesis": "Invented local metadata fixture; no scientific adoption.",
        "change": "Two proof paths only.",
        "validation_scope": "No Native call, no QA dataset.",
        "stop_method": "Fail closed.",
        "resume_method": "No retry.",
        "targets": ["invented/en/c1", "invented/ja/c1"],
        "target_counts": {"qa": 2, "fixed_units": 2, "conditions": 2},
        "identity_files": identity,
        "candidate_identity_sha256": guard.digest(identity),
        "bindings": bindings,
        "budget": {
            "planned_calls": 2,
            "maximum_calls": 2,
            "estimated_tokens": 24576,
            "estimated_native_seconds": 155.6,
            "maximum_wall_seconds": 3000,
            "request_timeout_seconds": 1200,
            "allowed_request_timeout_seconds": [1200],
            "maximum_tokens_per_call": 6144,
        },
        "monitor": {"method": "process_journal_resources", "interval_seconds": 5},
        "automatic_retries": 0,
        "output_dir": "data/runs/runtime_screening/phase11-v3-v26-smoke",
        "command": [
            "scripts/noop.py",
            "--config",
            "configs/invented.yaml",
            "--output-dir",
            "data/runs/runtime_screening/phase11-v3-v26-smoke",
        ],
    }
    old_plan = (
        canonical / "data/runs/development_screening/phase11-autonomy-v3-plans/v26-smoke.json"
    )
    save(old_plan, plan)
    row = {
        "run_id": plan["run_id"],
        "state": "registered",
        "registered_at_utc": "2026-10-27T04:00:00+00:00",
        "plan_sha256": REPAIR.sha(old_plan),
        "plan_content_sha256": guard.digest(plan),
        "plan": plan,
        "condition_sha256": guard.condition_fingerprint(plan),
    }
    other = {
        "run_id": "invented-old-closed",
        "state": "process_completed",
        "snapshot": {"attempts": 0, "unknown": 0},
    }
    ledger_dir = canonical / "data/runs/development_screening/phase11-autonomy-v3"
    ledger = {
        "version": guard.VERSION,
        "protocol_sha256": plan["protocol_sha256"],
        "legacy_attempts": 909,
        "legacy_unknown": 3,
        "runs": [other, row],
        "totals": {"cumulative_attempts": 909, "cumulative_unknown": 3},
        "phase12_allowed": False,
    }
    save(ledger_dir / "ledger.json", ledger)
    failure = canonical / ".tools/failure.json"
    save(failure, {"fixture_only": True, "native_calls": 0, "guard_failed_before_start": True})
    protocol = {
        "version": REPAIR.VERSION,
        "maximum_wall_seconds": 1800,
        "purpose": "registered-zero-output-metadata-path-amendment",
        "new_native_calls": 0,
        "phase12_allowed": False,
        "extension_source_sha256": REPAIR.sha(SOURCE),
        "unchanged_guard_sha256": REPAIR.sha(
            PROJECT / "src/rag_research/experiments/phase11_autonomy.py"
        ),
        "run_id": plan["run_id"],
        "fixed_commit": commit,
        "candidate_identity_sha256": plan["candidate_identity_sha256"],
        "relocations": relocations,
        "ledger_before_sha256": REPAIR.sha(ledger_dir / "ledger.json"),
        "registered_row_sha256": guard.digest(row),
        "condition_sha256": row["condition_sha256"],
        "old_plan": {
            "path": old_plan.relative_to(canonical).as_posix(),
            "sha256": REPAIR.sha(old_plan),
        },
        "new_plan_path": "data/runs/development_screening/phase11-autonomy-v3-plans/v26-smoke-metadata-amendment-v1.json",
        "journal_path": "data/runs/lab/phase11-zero-output-metadata-repair-v1/v26-smoke-paths-v1",
        "parent_protocol": {
            "path": "configs/phase11_autonomy_v3.json",
            "sha256": plan["protocol_sha256"],
        },
        "failure_evidence": [
            {"path": failure.relative_to(canonical).as_posix(), "sha256": REPAIR.sha(failure)}
        ],
    }
    protocol_path = canonical / ".tools/extension.json"
    save(protocol_path, protocol)
    return SimpleNamespace(
        root=root,
        canonical=canonical,
        guard=guard,
        plan=plan,
        row=row,
        ledger=ledger,
        ledger_dir=ledger_dir,
        old_plan=old_plan,
        protocol=protocol,
        protocol_path=protocol_path,
        new_plan=canonical / protocol["new_plan_path"],
        journal=canonical / protocol["journal_path"],
    )


def invoke(fixture, commit=False):
    return REPAIR.repair(
        fixture.root, fixture.protocol_path, REPAIR.sha(fixture.protocol_path), commit=commit
    )


def test_inspect_does_not_change_any_plan_ledger_or_WT(registered):
    f = registered
    before = (
        (f.ledger_dir / "ledger.json").read_bytes(),
        f.old_plan.read_bytes(),
        local_git(f.root, "status", "--porcelain"),
    )
    result = invoke(f)
    assert result["new_native_calls"] == 0 and result["committed"] is False
    assert before == (
        (f.ledger_dir / "ledger.json").read_bytes(),
        f.old_plan.read_bytes(),
        local_git(f.root, "status", "--porcelain"),
    )
    assert not f.new_plan.exists() and not f.journal.exists()


def test_commit_real_guard_clean_noop_native0_preserves_old_and_other_rows(registered):
    f = registered
    old_ledger = (f.ledger_dir / "ledger.json").read_bytes()
    old_plan = f.old_plan.read_bytes()
    result = invoke(f, True)
    assert (
        result["actual_v3_validate_plan_passed"] and result["actual_v3_fixed_checkout_clean_passed"]
    )
    assert result["committed"] and result["new_native_calls"] == 0
    assert f.old_plan.read_bytes() == old_plan
    assert (f.journal / "ledger-before.json").read_bytes() == old_ledger
    assert (f.journal / "original-plan.json").read_bytes() == old_plan
    after = REPAIR.read(f.ledger_dir / "ledger.json")
    assert after["runs"][0] == f.ledger["runs"][0] and after["totals"] == f.ledger["totals"]
    row = after["runs"][1]
    assert row["state"] == "registered" and row["registered_at_utc"] == f.row["registered_at_utc"]
    assert row["condition_sha256"] == f.row["condition_sha256"]
    assert f.guard.condition_fingerprint(row["plan"]) == f.row["condition_sha256"]
    assert local_git(f.root, "status", "--porcelain") == ""
    assert (
        not (f.ledger_dir / f.plan["run_id"]).exists()
        and not (f.root / f.plan["output_dir"]).exists()
    )
    for item in f.protocol["relocations"]:
        for suffix in (".json", ".sha256"):
            old = f.root / str(Path(item["source"]).with_suffix(suffix))
            new = f.root / str(Path(item["destination"]).with_suffix(suffix))
            assert not old.exists() and REPAIR.sha(new) == REPAIR.sha(
                f.canonical / str(Path(item["source"]).with_suffix(suffix))
            )
    with pytest.raises(ValueError):
        invoke(f, True)


@pytest.mark.parametrize(
    "tamper",
    [
        "running",
        "finished",
        "supervisor_pid",
        "child_pid",
        "snapshot",
        "started_at_utc",
        "other_running",
        "output",
        "monitor",
        "native_guard",
        "dangling_output",
        "dangling_monitor",
        "WT_local_ledger",
        "old_plan_bytes",
        "registered_plan_content",
        "condition",
        "candidate",
        "budget",
        "targets",
        "argv",
        "fixed_commit",
        "source_bytes",
        "canonical_bytes",
        "sidecar_bytes",
        "failure_bytes",
        "foreign_untracked",
        "tracked_change",
        "existing_target",
        "dangling_target",
        "existing_new_plan",
        "dangling_new_plan",
        "existing_journal",
        "dangling_journal",
        "destination_parent_symlink",
        "ledger_tmp",
        "native_context",
        "wrong_protocol_sha",
        "wrong_source_sha",
        "wrong_source_allowlist",
        "extra_relocation",
        "destination_outside_allowlist",
    ],
)
def test_refuse_every_non_zero_output_or_non_path_change(registered, monkeypatch, tamper):
    f = registered
    ledger_changed = False
    protocol_changed = False
    if tamper in {"running", "finished"}:
        f.row["state"] = "running" if tamper == "running" else "process_completed"
        ledger_changed = True
    elif tamper in {"supervisor_pid", "child_pid", "snapshot", "started_at_utc"}:
        f.row[tamper] = {} if tamper == "snapshot" else 123
        ledger_changed = True
    elif tamper == "other_running":
        f.ledger["runs"][0]["state"] = "running"
        ledger_changed = True
    elif tamper in {
        "output",
        "monitor",
        "native_guard",
        "dangling_output",
        "dangling_monitor",
        "WT_local_ledger",
    }:
        if tamper == "WT_local_ledger":
            path = f.root / "data/runs/development_screening/phase11-autonomy-v3"
        elif "output" in tamper:
            path = f.root / f.plan["output_dir"]
        else:
            path = f.ledger_dir / f.plan["run_id"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if tamper.startswith("dangling"):
            path.symlink_to(path.parent / "absent-target")
        else:
            path.mkdir()
        if tamper == "native_guard":
            save(path / "native_guard/calls.json", {"calls": [{"state": "unknown"}]})
    elif tamper == "old_plan_bytes":
        f.old_plan.write_bytes(f.old_plan.read_bytes() + b"\n")
    elif tamper in {
        "registered_plan_content",
        "condition",
        "candidate",
        "budget",
        "targets",
        "argv",
        "fixed_commit",
    }:
        if tamper == "registered_plan_content":
            f.row["plan_content_sha256"] = "0" * 64
        elif tamper == "condition":
            f.row["condition_sha256"] = "0" * 64
        elif tamper == "candidate":
            f.row["plan"]["candidate_identity_sha256"] = "0" * 64
        elif tamper == "budget":
            f.row["plan"]["budget"]["maximum_calls"] = 3
        elif tamper == "targets":
            f.row["plan"]["targets"].append("extra")
        elif tamper == "argv":
            f.row["plan"]["command"].append("--other")
        elif tamper == "fixed_commit":
            f.row["plan"]["fixed_commit"] = "0" * 40
        ledger_changed = True
    elif tamper in {"source_bytes", "canonical_bytes", "sidecar_bytes"}:
        base = f.canonical if tamper == "canonical_bytes" else f.root
        path = base / f.protocol["relocations"][0]["source"]
        if tamper == "sidecar_bytes":
            path = path.with_suffix(".sha256")
        path.write_bytes(path.read_bytes() + b"changed")
    elif tamper == "failure_bytes":
        (f.canonical / f.protocol["failure_evidence"][0]["path"]).write_text("changed")
    elif tamper == "foreign_untracked":
        (f.root / "unexpected.txt").write_text("preserve")
    elif tamper == "tracked_change":
        (f.root / "scripts/noop.py").write_text("changed tracked source")
    elif tamper in {
        "existing_target",
        "dangling_target",
        "existing_new_plan",
        "dangling_new_plan",
        "existing_journal",
        "dangling_journal",
    }:
        path = (
            f.root / f.protocol["relocations"][0]["destination"]
            if "target" in tamper
            else f.new_plan
            if "plan" in tamper
            else f.journal
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        if tamper.startswith("dangling"):
            path.symlink_to(path.parent / "absent-target")
        elif "journal" in tamper:
            path.mkdir()
        else:
            path.write_text("preserve")
    elif tamper == "destination_parent_symlink":
        path = (f.root / f.protocol["relocations"][0]["destination"]).parent
        path.parent.mkdir(parents=True, exist_ok=True)
        target = f.root / "data/runs/other-existing"
        target.mkdir()
        path.symlink_to(target, target_is_directory=True)
    elif tamper == "ledger_tmp":
        (f.ledger_dir / "ledger.json.tmp").write_text("preserve")
    elif tamper == "native_context":
        monkeypatch.setenv("RAG_PHASE11_AUTONOMY_CONTEXT", "invented active context")
    elif tamper == "wrong_protocol_sha":
        with pytest.raises(ValueError):
            REPAIR.repair(f.root, f.protocol_path, "0" * 64, commit=True)
        return
    elif tamper == "wrong_source_sha":
        f.protocol["extension_source_sha256"] = "0" * 64
        protocol_changed = True
    elif tamper == "wrong_source_allowlist":
        f.protocol["relocations"][0]["source"] = "other.json"
        protocol_changed = True
    elif tamper == "extra_relocation":
        f.protocol["relocations"].append(deepcopy(f.protocol["relocations"][0]))
        protocol_changed = True
    elif tamper == "destination_outside_allowlist":
        f.protocol["relocations"][0]["destination"] = "data/runs/lab/elsewhere.json"
        protocol_changed = True
    if ledger_changed:
        save(f.ledger_dir / "ledger.json", f.ledger)
    if protocol_changed:
        save(f.protocol_path, f.protocol)
    before = (f.ledger_dir / "ledger.json").read_bytes()
    with pytest.raises((ValueError, OSError, KeyError)):
        invoke(f, True)
    assert (f.ledger_dir / "ledger.json").read_bytes() == before
    assert not (f.journal / "committed.json").exists()


def test_global_OS_lock_rejects_concurrent_amendment(registered):
    f = registered
    with f.guard.run_lock(f.ledger_dir):
        with pytest.raises((ValueError, OSError)):
            invoke(f, True)
    assert not f.journal.exists() and not f.new_plan.exists()


def test_partial_immutable_intent_refuses_rerun_and_preserves_original_registration(
    registered, monkeypatch
):
    f = registered
    original = REPAIR.os.link

    def injected(source, target):
        if str(target).endswith("phase11_v26_preflight_result_v1.json"):
            raise OSError("invented interrupted relocation after first saved metadata")
        return original(source, target)

    monkeypatch.setattr(REPAIR.os, "link", injected)
    before = (f.ledger_dir / "ledger.json").read_bytes()
    with pytest.raises(OSError, match="invented interrupted"):
        invoke(f, True)
    assert (f.journal / "intent.json").exists() and (
        f.journal / "original-plan.json"
    ).read_bytes() == f.old_plan.read_bytes()
    assert (f.ledger_dir / "ledger.json").read_bytes() == before
    assert not (f.journal / "committed.json").exists()
    assert (
        not (f.ledger_dir / f.plan["run_id"]).exists()
        and not (f.root / f.plan["output_dir"]).exists()
    )
    with pytest.raises(ValueError):
        invoke(f, True)


def test_CLI_commit_boundary_permits_only_read_only_Git_and_real_Guard(registered):
    f = registered
    command = [
        sys.executable,
        str(SOURCE),
        "commit",
        "--root",
        str(f.root),
        "--extension-protocol",
        str(f.protocol_path),
        "--extension-protocol-sha256",
        REPAIR.sha(f.protocol_path),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "ORT_DISABLE_TELEMETRY": "1"},
    )
    report = json.loads(result.stdout)
    assert (
        report["committed"]
        and report["actual_v3_validate_plan_passed"]
        and report["new_native_calls"] == 0
    )
    assert report["boundary"]["allowed_read_only_git"] >= 8
    assert all(v == 0 for k, v in report["boundary"].items() if k != "allowed_read_only_git")
