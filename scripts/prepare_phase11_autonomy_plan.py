"""Create content-bound identity and finite v3 plans without starting inference.

First create identity and propagate its printed chain fields to candidate configs.
Then commit, create the fixed checkout, and prepare/register its concrete run plan.
Identity deliberately excludes candidate config hashes, avoiding a hash cycle.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.frozen_trace import digest, require  # noqa: E402
from rag_research.experiments.phase11_autonomy import (  # noqa: E402
    ADOPTION,
    VERSION,
    local,
    validate_plan,
)
from rag_research.experiments.storage import read_json, write_json  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def binding(root, path):
    path = Path(path).resolve()
    require(path.is_relative_to(root) and path.is_file(), "Identity artifact must exist in checkout")
    return {"path": path.relative_to(root).as_posix(), "sha256": file_hash(path)}


def descriptor(folder, label, value):
    path = folder / f"{label}-{digest(value)}.json"
    if path.exists():
        require(read_json(path) == value, "Never overwrite a different identity descriptor")
    else:
        write_json(path, value)
    return path


def build_identity(root, config, identity_dir):
    """Actual file hashes; stable across Known/Main/Cal config and stage differences."""
    root, identity_dir = Path(root).resolve(), Path(identity_dir).resolve()
    require(identity_dir.is_relative_to(root / "data/manifests"), "Store identity under data/manifests")
    identity_dir.mkdir(parents=True, exist_ok=True)
    model_manifest = local(root, config["auxiliary_model_manifest"])
    model = read_json(model_manifest)
    model_files = [binding(root, model_manifest)]
    for artifact in model["files"]:
        item = binding(root, local(root, artifact["path"]))
        require(item["sha256"] == artifact["sha256"], "Model artifact differs from saved manifest")
        require(local(root, artifact["path"]).stat().st_size == artifact["bytes"], "Model byte count differs")
        model_files.append(item)
    runtime_spec_path = local(root, config["execution"]["runtime_spec"])
    spec = read_json(runtime_spec_path)
    runtime_dir = local(root, spec["directory"])
    runtime_manifest = runtime_dir / "runtime_manifest.json"
    runtime = read_json(runtime_manifest)
    require(runtime["specification_sha256"] == file_hash(runtime_spec_path), "Runtime specification changed")
    runtime_files = [binding(root, runtime_spec_path), binding(root, runtime_manifest)]
    for item in spec.get("build", {}).values():
        if isinstance(item, dict) and set(item) >= {"path", "sha256"}:
            bound = binding(root, local(root, item["path"]))
            require(bound["sha256"] == item["sha256"], "Runtime build provenance changed")
            runtime_files.append(bound)
    for name, expected in runtime["files"].items():
        item = binding(root, runtime_dir / name)
        require(item["sha256"] == expected, "Runtime artifact differs from saved manifest")
        runtime_files.append(item)
    sampler = {key: config[key] for key in ("auxiliary_runtime", "sampling", "tasks", "trials", "errors")}
    sampler["execution"] = {k: v for k, v in config["execution"].items() if k != "runtime_spec"}
    # Development/Main/Cal may differ only in wrapper purpose and refusal opt-in.
    # The adopted score/threshold is fixed separately by the scientific protocol.
    sampler_path = descriptor(identity_dir, "sampler", sampler)
    schema_path = descriptor(identity_dir, "schema", {
        "output_constraints": config["output_constraints"],
        "verification_mode": config.get("verification_mode", "joint")})
    files = {"model": model_files, "runtime": runtime_files,
             "prompt": [binding(root, local(root, name)) for name in sorted(set(config["prompts"].values()))],
             "sampler": [binding(root, sampler_path)],
             "schema": [binding(root, schema_path), binding(root, root / "src/rag_research/evaluation/schema.py")],
             "core": [binding(root, path) for path in sorted((root / "src/rag_research").rglob("*.py"))]}
    return {key: sorted(value, key=lambda item: item["path"]) for key, value in files.items()}


def target_scope(root, stage, config, target_plan):
    if stage == "smoke":
        require(target_plan is not None, "Smoke requires the separately registered target plan")
        plan = read_json(target_plan)
        require(plan["maximum_calls"] == len(plan["targets"]) == 2, "Two registered runtime probes")
        source = read_json(local(root, plan["source"]["path"]))
        require(file_hash(local(root, plan["source"]["path"])) == plan["source"]["sha256"],
                "Smoke source changed")
        selected = {target["case_id"] for target in plan["targets"]}
        cases = [case for case in source["cases"] if case["id"] in selected]
        require(len(cases) == len(selected), "Unknown smoke target")
        targets = ["/".join(t[k] for k in ("case_id", "order", "claim_id")) for t in plan["targets"]]
        return targets, {"qa": len(cases), "fixed_units": sum(len(c["claims"]) for c in cases),
                         "conditions": 2}, 2
    if stage == "format":
        require(config["output_constraints"] == "thinking_json_passage_ids_v3",
                "This registered format plan has exactly ten cited-state probes")
        return ["format/" + name for name in (
            "legacy-array", "strict-array", "strict-prose-fence", "strict-fixed-ids",
            "strict-unicode-escape", "strict-rewrite-bounds", "strict-cited-supported",
            "strict-cited-contradicted", "strict-cited-missing-empty", "strict-cited-union")], {
                "qa": 0, "fixed_units": 0, "conditions": 10}, 10
    plan = read_json(local(root, config["diagnostics"]))
    cases, orders = plan["cases"], plan["orders"]
    targets = [case["id"] + "/" + order for case in cases for order in orders]
    counts = {"qa": len(cases), "fixed_units": sum(len(c["claims"]) for c in cases),
              "conditions": len(targets)}
    calls = 0 if stage == "preflight" else plan["max_completion_attempts"]
    require(stage == "preflight" or stage == "known" and calls == 84 or stage == "semantic" and calls == 70,
            "Use the complete registered 70-call semantic or 84-call known plan")
    return targets, counts, calls


def prepare(root, config_path, protocol_path, identity_dir, *, stage, run_id, output_dir,
            hypothesis, change, validation_scope, maximum_wall_seconds,
            estimated_native_seconds, estimated_tokens, target_plan=None):
    root = Path(root).resolve()
    config_path, protocol_path = Path(config_path).resolve(), Path(protocol_path).resolve()
    config = yaml.safe_load(config_path.read_text("utf-8"))
    identity = build_identity(root, config, identity_dir)
    targets, counts, calls = target_scope(root, stage, config, target_plan)
    scripts = {"preflight": "preflight_semantic_model.py", "smoke": "run_phase11_runtime_smoke_v3.py",
               "format": "probe_final_json_boundary.py", "semantic": "run_semantic_diagnostics.py",
               "known": "run_semantic_diagnostics.py"}
    script = root / "scripts" / scripts[stage]
    command = [script.relative_to(root).as_posix(), "--config", config_path.relative_to(root).as_posix(),
               "--output-dir", output_dir]
    paths = [script, config_path, protocol_path, local(root, config["diagnostics"])]
    if target_plan is not None:
        target_plan = Path(target_plan).resolve()
        command.extend(["--target-plan", target_plan.relative_to(root).as_posix()])
        paths.append(target_plan)
        paths.append(local(root, read_json(target_plan)["source"]["path"]))
    if config.get("development_execution_policy"):
        paths.append(local(root, config["development_execution_policy"]))
    plan = {"version": VERSION, "semantic_adoption_version": ADOPTION,
            "protocol_sha256": file_hash(protocol_path), "run_id": run_id, "stage": stage,
            "fixed_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "hypothesis": hypothesis, "change": change, "validation_scope": validation_scope,
            "targets": targets, "target_counts": counts, "identity_files": identity,
            "candidate_identity_sha256": digest(identity),
            "bindings": [binding(root, p) for p in sorted(set(paths))],
            "budget": {"planned_calls": calls, "maximum_calls": calls,
                       "estimated_tokens": estimated_tokens, "estimated_native_seconds": estimated_native_seconds,
                       "maximum_wall_seconds": maximum_wall_seconds,
                       "request_timeout_seconds": config["auxiliary_runtime"]["timeout_seconds"],
                       "maximum_tokens_per_call": max(v["max_output_tokens"] for v in config["tasks"].values())},
            "monitor": {"method": "process_journal_resources", "interval_seconds": 5},
            "stop_method": "v3 supervisor sends TERM then KILL only to its newly owned process group; preserve journals",
            "resume_method": "Inspect v3 handle and journals; never relaunch this Run or resend unknowns. Register a cause-specific changed condition in a new Run.",
            "automatic_retries": 0, "output_dir": output_dir, "command": command, "phase12_allowed": False}
    validate_plan(root, plan, protocol_path)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["identity", "plan"])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=ROOT / "configs/phase11_autonomy_v3.json")
    parser.add_argument("--identity-dir", type=Path, required=True)
    parser.add_argument("--stage", choices=["preflight", "smoke", "format", "semantic", "known"])
    parser.add_argument("--run-id")
    parser.add_argument("--output-dir")
    parser.add_argument("--target-plan", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--hypothesis")
    parser.add_argument("--change")
    parser.add_argument("--validation-scope")
    parser.add_argument("--maximum-wall-seconds", type=float)
    parser.add_argument("--estimated-native-seconds", type=float)
    parser.add_argument("--estimated-tokens", type=int)
    args = parser.parse_args()
    if args.action == "identity":
        config = yaml.safe_load(args.config.read_text("utf-8"))
        files = build_identity(ROOT, config, args.identity_dir)
        result = {"identity_files": files, "autonomy_protocol_version": VERSION,
                  "autonomy_protocol": binding(ROOT, args.protocol),
                  "candidate_identity_sha256": digest(files), "generation_calls": 0}
    else:
        required = ["stage", "run_id", "output_dir", "destination", "hypothesis", "change", "validation_scope",
                    "maximum_wall_seconds", "estimated_native_seconds", "estimated_tokens"]
        for key in required:
            if getattr(args, key) is None:
                parser.error("--" + key.replace("_", "-") + " is required for a finite run plan")
        result = prepare(ROOT, args.config, args.protocol, args.identity_dir,
                         **{key: getattr(args, key) for key in required if key != "destination"},
                         target_plan=args.target_plan)
        require(not args.destination.exists(), "Never overwrite an existing preregistration")
        args.destination.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.destination, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
