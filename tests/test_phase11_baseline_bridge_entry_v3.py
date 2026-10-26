"""Portable bytes and live registration must pass before the collection import.

These are software guard tests with metadata fixtures, never Main/Cal QA or
Native experiments. The complete issued bridge is separately checked on disk.
"""

import importlib.util
import json
import os
import sys
from argparse import Namespace
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from rag_research.experiments import calibration_protocol

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_phase11_baseline_bridge_v2", REPO / "scripts/validate_phase11_baseline_bridge_v2.py")
BRIDGE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BRIDGE
SPEC.loader.exec_module(BRIDGE)
SPEC = importlib.util.spec_from_file_location(
    "bridge_collection_entry", REPO / "scripts/run_phase11_bilingual_collection_with_bridge_v3.py")
ENTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENTRY)
SPEC = importlib.util.spec_from_file_location(
    "bridge_actual_main_producer", REPO / "scripts/prepare_bilingual_main.py")
MAIN_PRODUCER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MAIN_PRODUCER)


def save(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return {"path": name, "sha256": BRIDGE.file_sha(path)}


def test_sealed_raw_alias_is_portable_and_hash_checked(tmp_path):
    files = BRIDGE.ClosedFiles(tmp_path)
    binding = save(tmp_path, "data/runs/canonical/response.json", {"native": "saved original"})
    old = ".tools/worktrees/old/data/runs/raw/response.json"
    files.aliases[old] = binding["path"]
    assert files.read({"path": old, "sha256": binding["sha256"]}) == {"native": "saved original"}
    assert not (tmp_path / ".tools").exists()
    assert files.required == {binding["path"]: binding["sha256"]}
    (tmp_path / binding["path"]).write_text("tampered", encoding="utf-8")
    fresh = BRIDGE.ClosedFiles(tmp_path)
    fresh.aliases = files.aliases
    with pytest.raises(ValueError, match="changed"):
        fresh.bound({"path": old, "sha256": binding["sha256"]})


@pytest.mark.parametrize("path", ["../raw.json", "/tmp/raw.json", "data/../../raw.json"])
def test_bridge_path_escape_is_rejected(tmp_path, path):
    with pytest.raises(ValueError, match="relative contained"):
        BRIDGE.ClosedFiles(tmp_path).path(path)


def test_bridge_symlink_escape_is_rejected(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    (root / "raw.json").symlink_to(tmp_path / "outside.json")
    with pytest.raises(ValueError, match="escapes"):
        BRIDGE.ClosedFiles(root).path("raw.json")


def live_fixture(tmp_path, monkeypatch, mode):
    root = tmp_path / "checkout"
    canonical = tmp_path / "canonical"
    ledger_dir = canonical / "data/runs/development_screening/phase11-autonomy-v3"
    root.mkdir()
    wrapper_name = "scripts/run_phase11_bilingual_collection_with_bridge_v3.py"
    for name in (wrapper_name, ENTRY.ORIGINAL, "scripts/validate_phase11_baseline_bridge_v2.py"):
        save(root, name, "fixture implementation bytes")
    monkeypatch.setattr(ENTRY, "__file__", str(root / wrapper_name))
    monkeypatch.setattr(ENTRY, "ROOT", root)
    monkeypatch.setattr(ENTRY, "repository_head", lambda _: "fixed")
    monkeypatch.setattr(ENTRY, "repository_common_root", lambda _: canonical)
    monkeypatch.setattr(ENTRY.psutil, "Process", lambda _: SimpleNamespace(
        is_running=lambda: True, status=lambda: "running", create_time=lambda: 1.0))
    monkeypatch.setattr(ENTRY.os, "getpgrp", lambda: os.getpid())
    monkeypatch.chdir(root)
    initial = {language: save(root, f"configs/initial-{language}.yaml", {}) for language in ("en", "ja")}
    candidate = {key: {"fixed": key} for key in (
        "auxiliary_model_manifest", "auxiliary_runtime", "sampling", "tasks", "trials", "decision", "errors",
        "output_constraints", "execution", "verification_mode")}
    candidate["prompts"] = {language: f"configs/judge-{language}.yaml" for language in ("en", "ja")}
    candidate["decision"] = {"threshold": 0.7, "score": "supported_claims_divided_by_fixed_claims"}
    candidate["autonomy_protocol"] = save(root, "configs/autonomy.json", {"semantic_adoption_version": "support-binary-v2"})
    # The identity is deliberately unrelated to the currently adopted literal.
    identity = "b" * 64
    bridge = {"current_adoption_identity_sha256": identity, "old_execution_identity_sha256": "a" * 64,
              "current_identity_files": {"core": [{"path": "fixture.py", "sha256": "c" * 64}]},
              "baseline_config": save(root, "configs/baseline.yaml", {}),
              "old_generation_identity": save(root, "data/manifests/old.json", {"initial_prompts": initial})}
    bridge_binding = save(root, "data/manifests/bridge.json", bridge)
    resource = {"baseline_current_core_bridge": bridge_binding,
                "baseline_current_core_bridge_inline": bridge, "baseline_config": bridge["baseline_config"],
                "candidate_identity_sha256": identity, "stage": mode}
    resource_binding = save(root, "configs/resources.json", resource)
    configs = {}
    for language in ("en", "ja"):
        config = {**candidate, "language": language, "candidate_identity_sha256": identity,
                  "baseline_config": bridge["baseline_config"]["path"], "baseline_prompts": initial[language]["path"],
                  "prompts": candidate["prompts"][language], "semantic_adoption_version": "support-binary-v2"}
        config["decision"] = {**deepcopy(candidate["decision"]), "bare_refusal_policy": "rewrite_once"}
        policy = save(root, f"configs/policy-{language}.json", {"resource_budget_registration": resource_binding})
        if mode == "main":
            config["main_execution_policy"] = policy
        else:
            config["calibration_protocol"] = save(root, f"configs/cal-{language}.json", {"rules": policy})
        configs[language] = save(root, f"configs/{language}.yaml", config)
    args = Namespace(config=root / configs["en"]["path"], config_ja=root / configs["ja"]["path"],
                     resource_spec=root / resource_binding["path"], mode=mode, output_dir=root / "data/runs/new")
    argv = ["--config", configs["en"]["path"], "--config-ja", configs["ja"]["path"], "--mode", mode,
            "--resource-spec", resource_binding["path"], "--output-dir", "data/runs/new"]
    checked = {"bridge": bridge, "bridge_binding": bridge_binding, "candidate": candidate,
               "required_bindings": [bridge_binding]}
    bindings = [{"path": p.relative_to(root).as_posix(), "sha256": BRIDGE.file_sha(p)}
                for p in sorted(root.rglob("*")) if p.is_file()]
    plan = {"version": "phase11-autonomy-v3", "stage": mode, "candidate_identity_sha256": identity,
            "protocol_sha256": candidate["autonomy_protocol"]["sha256"],
            "identity_files": bridge["current_identity_files"], "command": [wrapper_name, *argv],
            "fixed_commit": "fixed", "budget": {"maximum_wall_seconds": 300}, "automatic_retries": 0,
            "bindings": bindings, "output_dir": "data/runs/new"}
    row = {"run_id": "registered", "state": "running", "plan": plan,
           "plan_content_sha256": BRIDGE.digest(plan), "plan_sha256": "d" * 64,
           "supervisor_pid": os.getpid(), "supervisor_create_time": 1.0,
           "child_pid": os.getpid(), "child_create_time": 1.0,
           "started_at_utc": datetime.now(UTC).isoformat()}
    ledger = {"version": "phase11-autonomy-v3", "protocol_sha256": candidate["autonomy_protocol"]["sha256"], "runs": [row]}
    monitor = {"plan": plan, "plan_sha256": row["plan_sha256"], "protocol_sha256": ledger["protocol_sha256"]}

    def persist():
        save(ledger_dir, "ledger.json", ledger)
        save(ledger_dir, "registered/manifest.json", monitor)

    persist()
    monkeypatch.setenv("RAG_PHASE11_AUTONOMY_CONTEXT", json.dumps({"ledger_dir": str(ledger_dir), "run_id": "registered"}))
    return SimpleNamespace(root=root, checked=checked, args=args, argv=argv, ledger=ledger,
                           row=row, plan=plan, monitor=monitor, persist=persist)


@pytest.mark.parametrize("mode", ["main", "cal"])
def test_registered_current_identity_and_config_bridge_pass_without_collection(tmp_path, monkeypatch, mode):
    fixture = live_fixture(tmp_path, monkeypatch, mode)
    needed = ENTRY.live_run(fixture.root, fixture.argv, fixture.checked, fixture.args)
    assert needed[ENTRY.ORIGINAL] == BRIDGE.file_sha(fixture.root / ENTRY.ORIGINAL)
    assert not fixture.args.output_dir.exists()


@pytest.mark.parametrize("mode", ["main", "cal"])
def test_actual_main_to_cal_producers_keep_exact_candidate_plus_one_rewrite_policy(tmp_path, monkeypatch, mode):
    f = live_fixture(tmp_path, monkeypatch, mode)
    prior_protocol = f.checked["candidate"]["autonomy_protocol"]
    f.checked["candidate"] = yaml.safe_load((REPO / "configs/phase11_semantic_candidate_v23.yaml").read_text("utf-8"))
    f.checked["candidate"]["autonomy_protocol"] = prior_protocol
    f.checked["candidate"]["candidate_identity_sha256"] = f.plan["candidate_identity_sha256"]
    original_candidate = deepcopy(f.checked["candidate"])
    assert "bare_refusal_policy" not in original_candidate["decision"]

    # Authentication/finite-resource metadata are covered by the live guard
    # tests. Only those dependencies are doubles; both configuration producers
    # and the final guard below are their actual production functions.
    def metadata_chain(*values, root):
        assert all(value["candidate_identity_sha256"] == f.plan["candidate_identity_sha256"] for value in values)
        return {"candidate_identity_sha256": f.plan["candidate_identity_sha256"]}

    def metadata_limits(policy, stage, *, root):
        assert stage == "cal"
        return deepcopy(calibration_protocol.LIMITS)

    monkeypatch.setattr(calibration_protocol, "validate_chain_identity", metadata_chain)
    monkeypatch.setattr(calibration_protocol, "stage_limits", metadata_limits)
    for language, path in (("en", f.args.config), ("ja", f.args.config_ja)):
        declared = yaml.safe_load(path.read_text())
        template = {"purpose": "phase11-bilingual-development-candidate", "language": language,
                    "execution_scope": "connection_smoke_only", "baseline_config": declared["baseline_config"],
                    "baseline_prompts": declared["baseline_prompts"]}
        prior = {**deepcopy(original_candidate), "candidate_identity_sha256": f.plan["candidate_identity_sha256"]}
        selected = [{"record_id": f"synthetic-main-{language}-{i}", "document_group_id": f"main-group-{language}-{i}"}
                    for i in range(20)]
        reserved = [{"record_id": f"synthetic-cal-{language}-{i}", "document_group_id": f"cal-group-{language}-{i}"}
                    for i in range(20)]
        main = MAIN_PRODUCER.configuration(template, prior, selected, language, "synthetic-assets.json",
            {"path": "synthetic-policy.json", "sha256": "a" * 64},
            {"path": "synthetic-selection.json", "sha256": "b" * 64},
            {"path": "synthetic-known-report.json", "sha256": "c" * 64}, "software-integration-only")
        # These fields are set by prepare() immediately after configuration().
        main["main_limits"] = deepcopy(calibration_protocol.LIMITS)
        main["semantic_adoption_version"] = "support-binary-v2"
        main_before = deepcopy(main)
        cal = calibration_protocol.configuration(main, reserved, language,
            {"candidate_identity_sha256": f.plan["candidate_identity_sha256"]})
        assert main == main_before and prior["decision"] == original_candidate["decision"]
        assert main["decision"] == cal["decision"] == {**original_candidate["decision"], "bare_refusal_policy": "rewrite_once"}
        assert main["data"]["record_ids"] == [r["record_id"] for r in selected]
        assert cal["data"]["record_ids"] == [r["record_id"] for r in reserved]
        produced = main if mode == "main" else cal
        policy_key = "main_execution_policy" if mode == "main" else "calibration_protocol"
        produced[policy_key] = declared[policy_key]
        path.write_text(yaml.safe_dump(produced), encoding="utf-8")
    f.plan["bindings"] = [{"path": p.relative_to(f.root).as_posix(), "sha256": BRIDGE.file_sha(p)}
                          for p in sorted(f.root.rglob("*")) if p.is_file()]
    f.row["plan_content_sha256"] = BRIDGE.digest(f.plan)
    f.persist()
    assert ENTRY.live_run(f.root, f.argv, f.checked, f.args)
    assert f.checked["candidate"] == original_candidate and not f.args.output_dir.exists()


@pytest.mark.parametrize("mode", ["main", "cal"])
@pytest.mark.parametrize("mutation", ["missing-context", "finished", "different-stage", "old-execution-id",
                                     "command", "plan-sha", "plan-content", "binding", "child-pid", "expired", "wt-local-ledger", "protocol",
                                     "resource-inline", "baseline-config", "prompt", "sampling", "policy-resource",
                                     "decision-threshold", "decision-extra", "decision-no-refusal", "decision-refusal-change",
                                     "existing-output"])
def test_collection_rejected_before_original_entry(tmp_path, monkeypatch, mode, mutation):
    f = live_fixture(tmp_path, monkeypatch, mode)
    monkeypatch.setattr(ENTRY, "validate_bridge", lambda *_: f.checked)
    delegated = []
    monkeypatch.setattr(ENTRY, "delegate", lambda *_: delegated.append(True))
    if mutation == "missing-context":
        monkeypatch.delenv("RAG_PHASE11_AUTONOMY_CONTEXT")
    elif mutation == "finished":
        f.row["state"] = "process_completed"
    elif mutation == "different-stage":
        f.plan["stage"] = "cal" if mode == "main" else "main"
    elif mutation == "old-execution-id":
        f.plan["candidate_identity_sha256"] = f.checked["bridge"]["old_execution_identity_sha256"]
    elif mutation == "command":
        f.plan["command"] = [ENTRY.ORIGINAL, *f.argv]
    elif mutation == "plan-sha":
        f.row["plan_sha256"] = "0" * 64
    elif mutation == "plan-content":
        f.row["plan_content_sha256"] = "0" * 64
    elif mutation == "binding":
        f.plan["bindings"] = [b for b in f.plan["bindings"] if b["path"] != ENTRY.ORIGINAL]
        f.row["plan_content_sha256"] = BRIDGE.digest(f.plan)
    elif mutation == "child-pid":
        f.row["child_pid"] += 1
    elif mutation == "expired":
        f.row["started_at_utc"] = "2000-01-01T00:00:00+00:00"
    elif mutation == "wt-local-ledger":
        monkeypatch.setenv("RAG_PHASE11_AUTONOMY_CONTEXT", json.dumps({"ledger_dir": str(f.root / "ledger"), "run_id": "registered"}))
    elif mutation == "protocol":
        f.plan["protocol_sha256"] = "0" * 64
        f.row["plan_content_sha256"] = BRIDGE.digest(f.plan)
    elif mutation == "resource-inline":
        resource = json.loads(f.args.resource_spec.read_text())
        resource["baseline_current_core_bridge_inline"]["old_execution_identity_sha256"] = "forged"
        save(f.root, "configs/resources.json", resource)
    elif mutation.startswith("decision-"):
        config = yaml.safe_load(f.args.config.read_text())
        if mutation == "decision-threshold":
            config["decision"]["threshold"] = 0.5
        elif mutation == "decision-extra":
            config["decision"]["unregistered"] = True
        elif mutation == "decision-no-refusal":
            config["decision"].pop("bare_refusal_policy")
        else:
            config["decision"]["bare_refusal_policy"] = "accept"
        f.args.config.write_text(yaml.safe_dump(config), encoding="utf-8")
    elif mutation in {"baseline-config", "prompt", "sampling", "policy-resource"}:
        config = yaml.safe_load(f.args.config.read_text())
        key = {"baseline-config": "baseline_config", "prompt": "prompts", "sampling": "sampling"}.get(mutation)
        if key:
            config[key] = "unregistered-change"
            f.args.config.write_text(yaml.safe_dump(config), encoding="utf-8")
        else:
            policy = "configs/policy-en.json"
            changed = save(f.root, policy, {"resource_budget_registration": {"path": "other", "sha256": "0" * 64}})
            if mode == "main":
                config["main_execution_policy"] = changed
            else:
                config["calibration_protocol"] = save(f.root, "configs/cal-en.json", {"rules": changed})
            f.args.config.write_text(yaml.safe_dump(config), encoding="utf-8")
    else:
        f.args.output_dir.mkdir(parents=True)
    f.persist()
    with pytest.raises(ValueError):
        ENTRY.main(f.argv)
    assert delegated == []


def test_check_only_never_delegates_or_requires_native_context(tmp_path, monkeypatch, capsys):
    f = live_fixture(tmp_path, monkeypatch, "main")
    f.checked.update(original_reference_count=698, resolved_old_checkout_references=20, portable_physical_artifact_count=700)
    monkeypatch.delenv("RAG_PHASE11_AUTONOMY_CONTEXT")
    monkeypatch.setattr(ENTRY, "validate_bridge", lambda *_: f.checked)
    monkeypatch.setattr(ENTRY, "delegate", lambda *_: pytest.fail("check-only reached collection"))
    assert ENTRY.main(["--check-only"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["native_calls"] == 0 and output["collection_started"] is False


def test_delegation_preserves_process_context_and_original_arguments(tmp_path, monkeypatch):
    f = live_fixture(tmp_path, monkeypatch, "cal")
    before = dict(os.environ)
    captured = []

    def observe(path, *, run_name):
        captured.append((path, run_name, list(sys.argv), dict(os.environ)))

    monkeypatch.setattr(ENTRY.runpy, "run_path", observe)
    previous_argv = sys.argv
    ENTRY.delegate(f.args)
    assert sys.argv is previous_argv
    assert captured[0][0] == str(f.root / ENTRY.ORIGINAL) and captured[0][1] == "__main__"
    assert captured[0][2] == [ENTRY.ORIGINAL, "--config", str(f.args.config), "--config-ja", str(f.args.config_ja),
                              "--mode", "cal", "--output-dir", str(f.args.output_dir)]
    assert captured[0][3] == before
