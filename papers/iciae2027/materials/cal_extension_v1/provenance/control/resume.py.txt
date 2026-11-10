"""Prepare an explicit, export-only recovery without changing frozen inputs."""

import argparse
import importlib.util
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def audit_selected(config):
    provenance = load(Path(__file__).with_name("provenance.py"), "extension_provenance_preflight")
    fixed = Path(config["checkout"])
    assets = read(fixed / "configs/phase11_bilingual_assets_v2.json")
    wanted, counts = {"en": set(), "ja": set()}, {"en": 0, "ja": 0}
    for language in ("en", "ja"):
        ids = set()
        for path in config["batches"]:
            batch = read(path)
            manifest = read(Path(batch["cal_run"]) / language / "manifest.json")
            ids.update(row["record_id"] for row in manifest["selection"])
        split = "development" if language == "en" else "calibration"
        for line in (fixed / assets["datasets"][language]["qa"][split]["path"]).open():
            row = json.loads(line)
            if row["record_id"] in ids:
                counts[language] += 1
                wanted[language].update(row["gold_passage_ids"])
        if counts[language] != 60:
            raise ValueError("Expected every preselected QA, without reading evaluation split")
    metadata, bodies = provenance.selected_sources(fixed, assets, wanted, lambda path, role: {"path": str(path), "role": role})
    return {"selected_qa_checked": counts, "gold_ids_checked": {lang: len(ids) for lang, ids in wanted.items()},
            "reconstructed_parents": [{"language": lang, "passage_id": pid, "sha256": value["text_sha256"],
                "child_passage_ids": value["child_passage_ids"]} for (lang, pid), value in metadata.items()
                if value.get("provenance_kind") == "original_parent_reconstructed_from_fixed_children"],
            "new_inference_calls": 0, "new_annotation_calls": 0}


def prepare(config_path):
    config_path = config_path.resolve()
    config = read(config_path)
    material = load(Path(__file__).with_name("materials.py"), "extension_recovery_io")
    if config_path.with_suffix(".sha256").read_text().strip() != material.sha(config_path):
        raise ValueError("Original workflow config changed")
    for name, expected in {**config["sealed_files"], **config["batch_config_hashes"]}.items():
        if material.sha(name) != expected:
            raise ValueError("Original frozen input changed: " + name)
    for unit in ("cal-extension-v1.service", "cal-extension-v2.service"):
        if subprocess.run(["systemctl", "--user", "is-active", "--quiet", unit]).returncode == 0:
            raise ValueError("Cannot prepare recovery while a workflow is active")
    state = Path(config["state_dir"])
    helper = Path(config["helper_dir"]).with_name("cal_extension_v2")
    recovery = state / "recovery-v2"
    if recovery.exists() or helper.exists():
        raise ValueError("Recovery revision already exists; preserve it")
    receipt = state / "batch_02/steps/export.json"
    old_receipt = read(receipt)
    log = receipt.with_suffix(".log")
    if (old_receipt.get("exit_code") != 1 or old_receipt["argv"][-2:] != ["--action", "export"] or
            "Missing selected passage provenance" not in log.read_text()):
        raise ValueError("Only the proven, non-inference provenance export failure is recoverable here")
    audit = audit_selected(config)
    recovery.mkdir()
    shutil.copytree(config["helper_dir"], helper, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ["materials.py", "service.py", "provenance.py", "resume.py"]:
        shutil.copy2(Path(__file__).with_name(name), helper / name)
    snapshot = {}
    for path in config["batches"]:
        batch = read(path)
        run = Path(batch["cal_run"])
        for entry in run.rglob("*"):
            if entry.is_file() and "__pycache__" not in entry.parts:
                snapshot[str(entry)] = material.sha(entry)
        batch_state = Path(batch["state_dir"])
        for pattern in ["cal/analysis.private.json", "cli_ledger.json", "jobs/**/*", "steps/*", "cal-sessions/*"]:
            for entry in batch_state.glob(pattern):
                if entry.is_file():
                    snapshot[str(entry)] = material.sha(entry)
    material.save(recovery / "protected_existing_files.json", snapshot)
    for name in ["config.json", "config.sha256", "status.json", "error.log", "git_publication.json"]:
        shutil.copy2(state / name, recovery / name)
    new_path = state / "config-recovery-v2.json"
    config.update(helper_dir=str(helper), workflow_config_path=str(new_path), controller_revision=2,
                  vscode_close_receipt="vscode_close_v2.json")
    config["sealed_files"] = {**config["sealed_files"], **{str(path): material.sha(path) for path in helper.rglob("*.py")}}
    material.save(new_path, config)
    new_path.with_suffix(".sha256").write_text(material.sha(new_path) + "\n")
    # The old failed export is kept verbatim, including cost/time. Only this
    # offline derived-output step may run again; successful/model steps reuse receipts.
    receipt.rename(recovery / "batch_02-export-failed.json")
    log.rename(recovery / "batch_02-export-failed.log")
    value = {"at_utc": datetime.now(UTC).isoformat(), "config_path": str(new_path),
        "old_config_sha256": material.sha(config_path), "new_config_sha256": material.sha(new_path),
        "old_helper_preserved": True, "original_batch_configs_protocols_unchanged": True,
        "protected_existing_files": len(snapshot), "retry_scope": "batch_02 offline export only; no research/annotation retry",
        "preserved_failed_export_receipt": {"sha256": material.sha(recovery / "batch_02-export-failed.json"),
            "elapsed_seconds": old_receipt["elapsed_seconds"]}, "source_preflight": audit,
        "scientific_conditions_changed": False}
    material.save(recovery / "preparation.json", value)
    material.save(Path(config["repo"]) / "reports/cal_extension_v1/recovery_v2_preparation.json", value)
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    if args.audit_only:
        print(json.dumps(audit_selected(read(args.config)), ensure_ascii=False, indent=2))
    else:
        prepare(args.config)
