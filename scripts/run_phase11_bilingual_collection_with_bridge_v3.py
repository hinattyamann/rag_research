"""Require the portable baseline bridge and a live v3 run before collection."""

import argparse
import json
import os
import runpy
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import psutil
import yaml
from validate_phase11_baseline_bridge_v2 import (
    BRIDGE_PATH,
    ClosedFiles,
    digest,
    file_sha,
    require,
    validate_bridge,
)

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = "scripts/run_phase11_bilingual_collection_v3.py"


def repository_head(root):
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def repository_common_root(root):
    common = subprocess.check_output(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=root, text=True).strip()
    return Path(common).resolve().parent


def live_run(root, argv, checked, args):
    require(os.environ.get("RAG_PHASE11_AUTONOMY_CONTEXT"), "Collection requires its live v3 supervisor")
    context = json.loads(os.environ["RAG_PHASE11_AUTONOMY_CONTEXT"])
    ledger_dir = Path(context["ledger_dir"]).resolve()
    canonical_ledger = repository_common_root(root) / "data/runs/development_screening/phase11-autonomy-v3"
    require(ledger_dir == canonical_ledger.resolve(), "Use the shared canonical v3 ledger outside dedicated checkouts")
    ledger = json.loads((ledger_dir / "ledger.json").read_text("utf-8"))
    require(ledger["version"] == "phase11-autonomy-v3", "Wrong live ledger version")
    rows = [row for row in ledger["runs"] if row["run_id"] == context["run_id"]]
    require(len(rows) == 1 and rows[0]["state"] == "running", "No unique running registered collection")
    row, bridge = rows[0], checked["bridge"]
    plan = row["plan"]
    monitor = json.loads((ledger_dir / row["run_id"] / "manifest.json").read_text("utf-8"))
    require(plan["version"] == "phase11-autonomy-v3" and plan["stage"] == args.mode and
            plan["candidate_identity_sha256"] == bridge["current_adoption_identity_sha256"] and
            plan["identity_files"] == bridge["current_identity_files"], "Run/bridge current identity or stage differs")
    require(digest(plan) == row["plan_content_sha256"] and monitor["plan"] == plan and
            monitor["plan_sha256"] == row["plan_sha256"] and monitor["protocol_sha256"] == ledger["protocol_sha256"],
            "Registered plan SHA/content changed")
    require(plan["command"] == [Path(__file__).relative_to(root).as_posix(), *argv], "Registered wrapper command differs")
    require(repository_head(root) == plan["fixed_commit"], "Run fixed Commit differs from checkout HEAD")
    for kind in ("supervisor", "child"):
        process = psutil.Process(row[kind + "_pid"])
        require(process.is_running() and process.status() != psutil.STATUS_ZOMBIE and
                process.create_time() == row[kind + "_create_time"], "Stale supervisor/child handle")
    require(row["child_pid"] == os.getpid() and os.getpgrp() == row["child_pid"], "Wrapper is not the owned v3 child group")
    elapsed = (datetime.now(UTC) - datetime.fromisoformat(row["started_at_utc"])).total_seconds()
    require(0 <= elapsed < plan["budget"]["maximum_wall_seconds"] and plan["automatic_retries"] == 0,
            "Registered finite deadline/retry contract differs")
    files = ClosedFiles(root)
    resource_name = args.resource_spec.resolve().relative_to(root).as_posix()
    resource_binding = {"path": resource_name, "sha256": file_sha(args.resource_spec)}
    resource = files.read(resource_binding)
    require(resource["baseline_current_core_bridge"] == checked["bridge_binding"] and
            resource["baseline_current_core_bridge_inline"] == bridge and resource["baseline_config"] == bridge["baseline_config"],
            "Finite resources must bind the complete verified bridge and baseline")
    require(resource["candidate_identity_sha256"] == plan["candidate_identity_sha256"] and
            resource["stage"] == args.mode, "Resource/current Run identity or stage differs")
    identity = files.read(bridge["old_generation_identity"])
    candidate = checked["candidate"]
    autonomy = files.read(candidate["autonomy_protocol"])
    require(ledger["protocol_sha256"] == plan["protocol_sha256"] == candidate["autonomy_protocol"]["sha256"],
            "Live ledger/plan/actual candidate protocol SHA differs")
    for language, path in (("en", args.config), ("ja", args.config_ja)):
        name = path.resolve().relative_to(root).as_posix()
        config = yaml.safe_load(files.bound({"path": name, "sha256": file_sha(path)}).read_text("utf-8"))
        require(config["language"] == language and config["candidate_identity_sha256"] == plan["candidate_identity_sha256"] and
                config["baseline_config"] == bridge["baseline_config"]["path"] and
                config["baseline_prompts"] == identity["initial_prompts"][language]["path"] and
                config["prompts"] == candidate["prompts"][language], "Config/current identity/baseline/prompt differs")
        for key in ("auxiliary_model_manifest", "auxiliary_runtime", "sampling", "tasks", "trials", "errors", "output_constraints",
                    "execution", "verification_mode"):
            require(config[key] == candidate[key], "Collection native candidate contract differs: " + key)
        decision = deepcopy(candidate["decision"])
        decision["bare_refusal_policy"] = "rewrite_once"
        require(config["decision"] == decision, "Collection decision must preserve candidate and mandatory one-rewrite policy")
        require(config["semantic_adoption_version"] == autonomy["semantic_adoption_version"],
                "Collection semantic adoption version differs")
        if args.mode == "main":
            policy = files.read(config["main_execution_policy"])
        else:
            calibration = files.read(config["calibration_protocol"])
            policy = files.read(calibration["rules"])
        require(policy["resource_budget_registration"] == resource_binding, "Config policy does not bind these finite resources")
    needed = {binding["path"]: binding["sha256"] for binding in checked["required_bindings"]}
    needed.update(files.required)
    for name in (ORIGINAL, "scripts/validate_phase11_baseline_bridge_v2.py", Path(__file__).relative_to(root).as_posix()):
        needed[name] = file_sha(files.path(name))
    registered = {item["path"]: item["sha256"] for item in plan["bindings"]}
    require(all(registered.get(name) == wanted for name, wanted in needed.items()),
            "Registered Run must directly bind wrapper/original/resource/bridge and its whole portable closure")
    output = files.path(args.output_dir.resolve().relative_to(root).as_posix())
    require(output == files.path(plan["output_dir"]) and not output.exists(), "Preserve registered collection output")
    return needed


def delegate(args):
    forwarded = [ORIGINAL, "--config", str(args.config), "--config-ja", str(args.config_ja),
                 "--mode", args.mode, "--output-dir", str(args.output_dir)]
    original_argv = sys.argv
    try:
        sys.argv = forwarded
        runpy.run_path(str(ROOT / ORIGINAL), run_name="__main__")
    finally:
        sys.argv = original_argv


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge", default=BRIDGE_PATH)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--config-ja", type=Path)
    parser.add_argument("--mode", choices=("main", "cal"))
    parser.add_argument("--resource-spec", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    require(Path.cwd().resolve() == ROOT, "Run bridge collection entry from its fixed checkout")
    checked = validate_bridge(ROOT, args.bridge)
    if args.check_only:
        print(json.dumps({"bridge_verified": True, "original_reference_count": checked["original_reference_count"],
              "resolved_old_checkout_references": checked["resolved_old_checkout_references"],
              "portable_physical_artifact_count": checked["portable_physical_artifact_count"],
              "current_adoption_identity_sha256": checked["bridge"]["current_adoption_identity_sha256"],
              "native_calls": 0, "collection_started": False, "phase12_allowed": False}))
        return 0
    require(all(getattr(args, name) is not None for name in ("config", "config_ja", "mode", "resource_spec", "output_dir")),
            "Collection requires both configs/mode/resources/output")
    live_run(ROOT, argv, checked, args)
    return delegate(args)


if __name__ == "__main__":
    sys.exit(main())
