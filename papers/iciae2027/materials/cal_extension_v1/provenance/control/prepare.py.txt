"""Prepare a bounded extension without changing the original v23 checkout or data."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

BASE = "f0b7c71c4375a617c7142c67e3aa0610f73edb14"
VERSION = "fixed-v23-cal-extension-v1"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def link_tree(source, destination):
    """Independent directory entries; immutable large assets share their file bytes."""
    if not source.exists():
        return
    for current, _, files in os.walk(source, followlinks=False):
        relative = Path(current).relative_to(source)
        target = destination / relative
        target.mkdir(parents=True, exist_ok=True)
        for name in files:
            src, dst = Path(current) / name, target / name
            if dst.exists() or dst.is_symlink():
                continue
            if src.is_symlink():
                dst.symlink_to(os.readlink(src))
            else:
                os.link(src, dst)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--authoring", type=Path, required=True)
    p.add_argument("--runtime", type=Path, required=True)
    args = p.parse_args()
    repo, author, runtime = (x.resolve() for x in [args.repo, args.authoring, args.runtime])
    old = repo / ".tools/worktrees/fixed-v23-study-v1"
    state = repo / ".tools/cal-extension-v1"
    if (state / "config.json").exists():
        raise ValueError("Preserve an existing extension registration")
    assert subprocess.check_output(["git", "-C", str(runtime), "rev-parse", "HEAD"], text=True).strip() == BASE
    # Registered source code is copied, not shared by writable hard links.
    release = read(old / "fixed-v23-release.json")
    for name, expected in release["files"].items():
        assert sha(old / name) == expected, name
        destination = runtime / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination.unlink()
        shutil.copy2(old / name, destination)
    for path in old.glob("fixed-v23-*.json"):
        shutil.copy2(path, runtime / path.name)
    for path in old.glob("scripts/recover_fixed_v23*.py"):
        shutil.copy2(path, runtime / "scripts" / path.name)
    for name in ["processed", "indexes", "models", "runtimes", "manifests", "sourceproof"]:
        link_tree(old / "data" / name, runtime / "data" / name)
    link_tree(old / "data/runs/runtime_build", runtime / "data/runs/runtime_build")
    link_tree(old / "environments/embedding_gpu/.venv", runtime / "environments/embedding_gpu/.venv")
    for name in ["pyproject.toml", "uv.lock"]:
        shutil.copy2(old / "environments/embedding_gpu" / name, runtime / "environments/embedding_gpu" / name)
    sys.path.insert(0, str(runtime / "src"))
    from rag_research.data.study_assets import load_assets, load_rows
    from rag_research.experiments.calibration_selection import prepare, select_rows
    from rag_research.experiments.fixed_v23 import verify_release
    from rag_research.experiments.frozen_trace import digest

    verify_release(runtime)
    reservation = prepare(repo / "configs/phase11_bilingual_calibration_selection_policy_v1.json", root=repo)
    assets = load_assets(runtime / "configs/phase11_bilingual_assets_v2.json", root=runtime)
    used = set(reservation["used_or_retrieval_exposed_unique_ids"])
    old_groups = {lang: set() for lang in ["en", "ja"]}
    protected = {}
    prior_manifests = {}
    for split, name in [("bilingual_development", "fixed-v23-main-v1"),
                        ("bilingual_calibration", "fixed-v23-cal-v1")]:
        run = old / "data/runs" / split / name
        seal = read(run / "all_annotations.seal.json")
        assert seal["all_both_languages_sealed"]
        for relative, expected in seal["files"].items():
            assert sha(run / relative) == expected
        for path in run.rglob("*"):
            if path.is_file() and path.name not in ["progress.json", ".run.lock"]:
                protected[str(path)] = sha(path)
        for lang in ["en", "ja"]:
            m = read(run / lang / "manifest.json")
            used.update(x["record_id"] for x in m["selection"])
            old_groups[lang].update(x["document_group_id"] for x in m["selection"])
            if name == "fixed-v23-cal-v1":
                prior_manifests[lang] = m
    selected, qa_rows = {}, {}
    for lang, split in [("en", "development"), ("ja", "calibration")]:
        rows, _ = load_rows(assets, lang, split, root=runtime)
        prior = reservation["languages"][lang]
        excluded = set(prior["excluded_used_source_groups"]) | set(prior["excluded_reserved_groups"]) | old_groups[lang]
        selected[lang] = select_rows(rows, lang, used, excluded, count=60, seed=42)
        qa_rows[lang] = {row["record_id"]: row for row in rows}
    public_plan = {"version": VERSION, "created_at_utc": datetime.now(UTC).isoformat(),
        "purpose": "additional_confirmation_not_tuning", "source_splits": {"en": "development", "ja": "calibration"},
        "planned_qa": 120, "planned_per_language": 60, "batches": 3, "batch_per_language": 20,
        "source_selection": selected, "seed": 42, "automatic_refill": False,
        "collection_cutoff_utc": "2026-11-14T14:59:59+00:00", "finalization_deadline_utc": "2026-11-17T14:59:59+00:00",
        "maximum_native_calls": 9960, "maximum_native_calls_per_batch_language": 1660,
        "maximum_cli_invocations": 288, "maximum_cli_invocations_per_batch": 96,
        "session_wall_seconds": 43200, "batch_collection_wall_seconds": 259200,
        "workflow_wall_seconds": 950400, "outcome_dependent_stopping": False,
        "primary_analysis": "pooled new extension only after sealed complete batches; per-batch results also retained",
        "original_main_and_cal_not_pooled": True, "old_runs_preserved": True,
        "startup_oom_retries_only_before_native_request": 2, "native_request_retries": 0,
        "baseline_and_rewrite_length_failures_retained": True,
        "known_limit": "v23 specificity 87.5%, historical 90% gate not passed",
        "phase12_allowed": False, "api_billing_allowed": False, "git_publish_policy": "events_only",
        "close_vscode_authorized": True, "close_other_apps_authorized": False,
        "partial_deadline_policy": "Finish active QA, stop new QA at cutoff; preserve partial batch and publish completed sealed batches with all uncollected selections explicit",
        "unused_scope": reservation["unused_scope"], "prior_usage_source_sha256": reservation["used_baseline_input_sha256"],
        "old_main_cal_selected_ids": sorted({x["record_id"] for lang in old_groups for x in
            read(old / "data/runs/bilingual_development/fixed-v23-main-v1" / lang / "manifest.json")["selection"]} |
            {x["record_id"] for lang in old_groups for x in
            read(old / "data/runs/bilingual_calibration/fixed-v23-cal-v1" / lang / "manifest.json")["selection"]})}
    plan_path = author / "data/manifests/cal_extension_plan_v1.json"
    save(plan_path, public_plan)
    save(state / "protected_original_files.json", protected)
    helper = runtime / "scripts/cal_extension_v1"
    helper.mkdir(parents=True, exist_ok=True)
    legacy = helper / "legacy"
    shutil.copytree(old / "scripts/fixed_v23_automation_v3", legacy, ignore=shutil.ignore_patterns("__pycache__"))
    for path in (author / "scripts/cal_extension").glob("*.py"):
        shutil.copy2(path, helper / path.name)
    for name in ["build_materials.py", "verify_materials.py"]:
        shutil.copy2(author / "papers/iciae2027/materials/fixed_v23_v1" / name, helper / ("original_" + name))
    global_config = {"extension_version": VERSION, "source_repo": str(repo), "repo": str(author),
        "checkout": str(runtime), "state_dir": str(state), "helper_dir": str(helper),
        "plan": str(plan_path), "plan_sha256": sha(plan_path), "runtime_base_commit": BASE,
        "branch": "research/cal-extension-v1", "remote": "origin", "remote_url": "https://github.com/hinattyamann/rag_research.git",
        "uv": str(repo / ".tools/bin/uv"), "cpu_python": str(repo / ".venv/bin/python"),
        "gpu_python": str(runtime / "environments/embedding_gpu/.venv/bin/python"),
        "collection_cutoff_utc": public_plan["collection_cutoff_utc"],
        "deadline_utc": public_plan["finalization_deadline_utc"], "batches": []}
    fixed = {str(path): sha(path) for path in helper.rglob("*.py")}
    fixed.update({str(plan_path): sha(plan_path), str(runtime / "fixed-v23-release.json"): sha(runtime / "fixed-v23-release.json")})
    old_config = read(repo / ".tools/fixed-v23-automation-v1/config.json")
    for number in range(1, 4):
        batch_id = f"batch_{number:02}"
        run = runtime / "data/runs/bilingual_calibration" / ("fixed-v23-extension-" + batch_id)
        protocol_path = run / "protocol.json"
        configs = {}
        selections = {}
        for lang in ["en", "ja"]:
            chosen = selected[lang]["selected"][(number - 1) * 20:number * 20]
            selections[lang] = chosen
            value = deepcopy(prior_manifests[lang]["config"])
            value.pop("fixed_v23_calibration_protocol")
            value["study_version"] = "fixed-v23-extension-" + batch_id + "-" + lang
            value["data"]["record_ids"] = [x["record_id"] for x in chosen]
            configs[lang] = value
        protocol = {"version": VERSION, "batch_id": batch_id, "configs": configs,
            "source_splits": public_plan["source_splits"], "original_release_sha256": sha(runtime / "fixed-v23-release.json"),
            "plan_sha256": sha(plan_path), "selection": selections, "maximum_calls_per_language": 1660,
            "session_wall_seconds": 43200, "total_wall_seconds": 259200, "automatic_retries": 0,
            "purpose": "additional_confirmation_not_tuning", "phase12_allowed": False,
            "inputs": {str(plan_path): sha(plan_path), **{str(old / "data/runs" / split / name / "all_annotations.seal.json"):
                sha(old / "data/runs" / split / name / "all_annotations.seal.json") for split, name in
                [("bilingual_development", "fixed-v23-main-v1"), ("bilingual_calibration", "fixed-v23-cal-v1")]}}}
        save(protocol_path, protocol)
        for lang in ["en", "ja"]:
            value = {**configs[lang], "fixed_v23_calibration_protocol": {
                "path": str(protocol_path.relative_to(runtime)), "sha256": sha(protocol_path)}}
            save(run / "configs" / (lang + ".json"), value)
            prior = prior_manifests[lang]
            manifest = deepcopy(prior)
            manifest.update(config=value, status="candidate_not_frozen", selection_scope="preselected_extension_confirmation",
                selection=[{k: qa_rows[lang][x["record_id"]][k] for k in ["record_id", "question", "document_group_id"]}
                           for x in selections[lang]],
                source_sha256={**release["files"], str(protocol_path.relative_to(runtime)): sha(protocol_path),
                    str((run / "configs" / (lang + ".json")).relative_to(runtime)): sha(run / "configs" / (lang + ".json"))})
            save(run / lang / "manifest.json", manifest)
            (run / lang / "baseline").mkdir()
        cfg = {k: v for k, v in old_config.items() if k not in ["main_recovery_extension", "sealed_files", "previous_configuration_sha256"]}
        cfg.update(extension_version=VERSION, batch_id=batch_id, repo=str(author), checkout=str(runtime),
            source_repo=str(repo), helper_dir=str(helper), cpu_python=str(repo / ".venv/bin/python"),
            state_dir=str(state / batch_id), main_run=old_config["main_run"], cal_run=str(run), frozen_scripts=str(legacy),
            public_dir=str(author / "reports/cal_extension_v1" / batch_id), branch=global_config["branch"],
            sealed_files={**fixed, str(protocol_path): sha(protocol_path)}, maximum_cli_invocations=96,
            deadline_utc=global_config["deadline_utc"], config_sha256_required=True,
            recorded_at_utc=datetime.now(UTC).isoformat(), controller_revision=1, inherited_controller_revision=7,
            cal_gpu_policy={**old_config["cal_gpu_policy"], "maximum_wait_seconds": 21600},
            scope="120 preselected extension QA; separate fixed-v23 batches; no original run edits or manuscript changes")
        path = state / batch_id / "config.json"
        save(path, cfg)
        path.with_suffix(".sha256").write_text(sha(path) + "\n")
        global_config["batches"].append(str(path))
    global_config["sealed_files"] = fixed
    save(state / "config.json", global_config)
    (state / "config.sha256").write_text(sha(state / "config.json") + "\n")
    save(state / "preparation.json", {"native_calls": 0, "selected_qa": 120,
        "runtime_release_verified": True, "condition_fingerprints": {lang: digest({k: v for k, v in configs[lang].items()
            if k not in ["study_version", "data", "fixed_v23_calibration_protocol"]}) for lang in configs},
        "protected_original_files": len(protected)})
    print(json.dumps({"configuration": str(state / "config.json"), "planned_qa": 120,
                      "eligible_groups": {lang: selected[lang]["eligible_groups"] for lang in selected}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
