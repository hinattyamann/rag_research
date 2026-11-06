"""Seal controller bytes before the first research request; refuse live changes."""

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def deploy(config_path):
    cfg = read(config_path)
    batches = [read(Path(path)) for path in cfg["batches"]]
    for batch in batches:
        run = Path(batch["cal_run"])
        if any(list((run / lang / "baseline").glob("*/record.json")) or
               list((run / lang / "internal").glob("*/*.json")) for lang in ["en", "ja"]):
            raise ValueError("Do not redeploy a controller after any research record exists")
        if (Path(batch["state_dir"]) / "cli_ledger.json").exists():
            raise ValueError("Do not redeploy after research grading starts")
    state, helper, author = Path(cfg["state_dir"]), Path(cfg["helper_dir"]), Path(cfg["repo"])
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    backup = state / "deployment-drafts" / stamp
    backup.mkdir(parents=True)
    shutil.copy2(config_path, backup / "config.json")
    shutil.copy2(cfg["plan"], backup / "plan.json")
    for path in (author / "scripts/cal_extension").glob("*.py"):
        shutil.copy2(path, helper / path.name)
    plan_path = Path(cfg["plan"])
    plan = read(plan_path)
    plan["partial_deadline_policy"] = "Finish active QA, stop new QA at cutoff; preserve partial batch and publish completed sealed batches with all uncollected selections explicit"
    plan["artificial_cli_smoke_limit"] = 2
    save(plan_path, plan)
    fixed = {str(path): sha(path) for path in helper.rglob("*.py")}
    fixed.update({str(plan_path): sha(plan_path), str(Path(cfg["checkout"]) / "fixed-v23-release.json"):
                  sha(Path(cfg["checkout"]) / "fixed-v23-release.json")})
    for path, batch in zip(map(Path, cfg["batches"]), batches, strict=True):
        run = Path(batch["cal_run"])
        protocol_path = run / "protocol.json"
        shutil.copy2(path, backup / (batch["batch_id"] + "-config.json"))
        shutil.copy2(protocol_path, backup / (batch["batch_id"] + "-protocol.json"))
        protocol = read(protocol_path)
        protocol["plan_sha256"] = sha(plan_path)
        protocol["inputs"][str(plan_path)] = sha(plan_path)
        save(protocol_path, protocol)
        for lang in ["en", "ja"]:
            path_config = run / "configs" / (lang + ".json")
            value = read(path_config)
            value["fixed_v23_calibration_protocol"]["sha256"] = sha(protocol_path)
            save(path_config, value)
            manifest_path = run / lang / "manifest.json"
            manifest = read(manifest_path)
            manifest["config"] = value
            manifest["source_sha256"][str(protocol_path.relative_to(cfg["checkout"]))] = sha(protocol_path)
            manifest["source_sha256"][str(path_config.relative_to(cfg["checkout"]))] = sha(path_config)
            save(manifest_path, manifest)
        batch.update(source_repo=cfg["source_repo"], helper_dir=str(helper), cpu_python=cfg["cpu_python"],
            recorded_at_utc=datetime.now(UTC).isoformat(), controller_revision=1, inherited_controller_revision=7,
            sealed_files={**fixed, str(protocol_path): sha(protocol_path)})
        save(path, batch)
        path.with_suffix(".sha256").write_text(sha(path) + "\n")
    cfg.update(sealed_files=fixed, plan_sha256=sha(plan_path),
               batch_config_hashes={path: sha(Path(path)) for path in cfg["batches"]})
    save(config_path, cfg)
    config_path.with_suffix(".sha256").write_text(sha(config_path) + "\n")
    save(state / "controller_deployment.json", {"at_utc": datetime.now(UTC).isoformat(),
        "research_native_calls_at_deployment": 0, "research_cli_calls_at_deployment": 0,
        "sealed_controller_files": len(fixed), "config_sha256": sha(config_path), "previous_draft": str(backup),
        "scientific_conditions_changed": False})
    print(json.dumps(read(state / "controller_deployment.json"), ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    deploy(parser.parse_args().config)
