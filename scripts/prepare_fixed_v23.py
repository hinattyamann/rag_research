"""Deploy original v23 sources plus a sealed collection-only overlay; no inference."""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.fixed_v23 import BASE, CANDIDATE, VERSION  # noqa: E402
from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402

OVERLAY = ("src/rag_research/experiments/bilingual_runner.py",
           "src/rag_research/experiments/fixed_v23.py",
           "src/rag_research/experiments/fixed_v23_control.py", "scripts/fixed_v23.py",
           "scripts/preflight_fixed_v23.py")
STUDY = "configs/fixed_v23_study_v1.json"
RUN = "data/runs/bilingual_development/fixed-v23-main-v1"


def binding(root, name):
    return {"path": name, "sha256": file_hash(root / name)}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def install(source, destination, *, large=False):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        require(file_hash(source) == file_hash(destination), "Existing deployment asset differs: " + str(destination))
        return
    if large:
        os.link(source.resolve(), destination)
    else:
        shutil.copy2(source, destination)


def prepare(checkout, *, refresh=False):
    checkout = checkout.resolve()
    require(checkout.is_relative_to(ROOT / ".tools/worktrees") and checkout != ROOT,
            "Use a dedicated checkout in .tools/worktrees")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()
    require(head == BASE and (refresh or not (checkout / "fixed-v23-release.json").exists()),
            "Use a new original-v23 checkout; never replace a sealed release")
    status = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=checkout, text=True)
    require(not status or refresh, "Original checkout has tracked modifications")
    if refresh:
        require(not (checkout / RUN).exists(), "Never refresh controls after initializing the real collection")
        previous = json.loads((checkout / "fixed-v23-release.json").read_text())
        originals = previous["original_source_sha256"]
        for name, sha in previous["files"].items():
            require(file_hash(checkout / name) == sha, "Previously sealed deployment changed: " + name)
        history = checkout / "data/runs/model_screening" / ("control-revision-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f"))
        for name in ("fixed-v23-release.json", STUDY, *OVERLAY, *[b["path"] for b in previous["configs"].values()]):
            install(checkout / name, history / name)
    else:
        originals = {p.relative_to(checkout).as_posix(): file_hash(p)
                     for p in (checkout / "src/rag_research").rglob("*.py")}
    # All old inference code is retained. Only this previously identical collector is overlaid.
    original_runner = subprocess.check_output(["git", "show", BASE + ":" + OVERLAY[0]], cwd=ROOT)
    require(refresh or (checkout / OVERLAY[0]).read_bytes() == original_runner, "Original collector differs")
    copied = []
    for folder in ("data/processed", "data/indexes", "data/models/multilingual-e5-small",
                   "data/models/Qwen2.5-3B-Instruct-GGUF",
                   "data/runtimes/llama.cpp/b11433-cuda12.9-graph-off-v1"):
        for source in sorted((ROOT / folder).rglob("*")):
            if source.is_file() and ".cache" not in source.parts:
                name = source.relative_to(ROOT).as_posix()
                install(source, checkout / name, large=source.stat().st_size > 1024 * 1024)
                copied.append(name)
    model = json.loads((ROOT / "data/manifests/phase11_auxiliary_qwen35_9b_q6_manifest_v1.json").read_text())
    for entry in model["files"]:
        install(ROOT / entry["path"], checkout / entry["path"], large=True)
        require((checkout / entry["path"]).stat().st_size == entry["bytes"] and
                file_hash(checkout / entry["path"]) == entry["sha256"], "Original Q6 model changed")
        copied.append(entry["path"])
    spec = json.loads((ROOT / "configs/lab_cuda_graph_off_runtime_v1.json").read_text())
    for entry in spec["build"].values():
        install(ROOT / entry["path"], checkout / entry["path"])
    known_name = "data/manifests/phase11_known_trace_direct_result_v12_v2.json"
    install(ROOT / known_name, checkout / known_name)
    selection_name = "data/manifests/phase11_main_development_selection_v1.json"
    selection = json.loads((checkout / selection_name).read_text())
    for name in selection["used_baseline_input_sha256"]:
        install(ROOT / name, checkout / name)
    for run_name in ("phase11-connection-en-v2", "phase11-connection-ja-v1"):
        for source in (ROOT / "data/runs/bilingual_development" / run_name / "baseline").glob("*/record.json"):
            name = source.relative_to(ROOT)
            install(source, checkout / name)
    candidate_name = "configs/phase11_semantic_candidate_v23.yaml"
    prior = yaml.safe_load((checkout / candidate_name).read_text())
    require(prior["candidate_identity_sha256"] == CANDIDATE, "Original v23 candidate differs")
    study = {"version": VERSION, "registered_at_utc": datetime.now(UTC).isoformat(),
        "base_commit": BASE, "candidate_identity_sha256": CANDIDATE, "mode": "main",
        "known_limit_acknowledged": True, "old_gate11_passed": False, "phase12_allowed": False,
        "known_result": binding(checkout, known_name), "candidate": binding(checkout, candidate_name),
        "selection": binding(checkout, selection_name),
        "assets": binding(checkout, "configs/phase11_bilingual_assets_v2.json"),
        "baseline": binding(checkout, "configs/phase11_bilingual_baseline_graph_off_v3.yaml"),
        "initial_prompts": {lang: binding(checkout, f"configs/phase11_bilingual_initial_{lang}_v1.yaml")
                            for lang in ("en", "ja")},
        "count_per_language": 20, "minimum_comparable_per_language": 10,
        "quality_and_expected_seal": "all_both_languages_before_internal_unblinding",
        "automatic_retries": 0, "output_dir": RUN,
        "limits_per_language": {"maximum_completion_attempts": 1660,
            "maximum_new_qa_per_stage_session": 5, "stop_on_any_task_error": True, "automatic_refill": False},
        "pilot_wall_seconds": 14400, "session_wall_seconds": 43200, "total_wall_seconds": 259200,
        "budget_reason": "Keep the original 1660-call ceiling per language; reserve complete QA before execution. "
            "First-QA segment <=4h, each five-QA stage <=12h, whole Main collection <=72h including resumptions. "
            "These are stop limits, not measured duration guarantees. No automatic extension/refill.",
        "time_estimate_basis": "Original 84-call known result; update estimates after the user's first QA. "
            "Quality annotation and writing are additional. Cal is separately registered only after Main scoring.",
        "fixed_inputs": []}
    names = [candidate_name, known_name, selection_name, study["assets"]["path"], study["baseline"]["path"],
             *[v["path"] for v in study["initial_prompts"].values()], *prior["prompts"].values(),
             prior["auxiliary_model_manifest"], prior["execution"]["runtime_spec"], prior["diagnostics"],
             *selection["used_baseline_input_sha256"]]
    study["fixed_inputs"] = [binding(checkout, name) for name in sorted(set(names))]
    save(ROOT / STUDY, study)
    save(checkout / STUDY, study)
    configs = {}
    for lang in ("en", "ja"):
        template_name = f"configs/phase11_bilingual_main_template_{lang}_graph_off_v3.yaml"
        install(ROOT / template_name, checkout / template_name)
        template = yaml.safe_load((checkout / template_name).read_text())
        for key, value in prior.items():
            if key not in {"study_version", "purpose", "diagnostics", "prompts", "candidate_identity_sha256",
                           "autonomy_protocol", "autonomy_protocol_version", "semantic_evidence_reuse"}:
                template[key] = deepcopy(value)
        template.update(study_version=f"{VERSION}-{lang}", execution_scope="fixed_v23_main_v1",
            assets=study["assets"]["path"], baseline_config=study["baseline"]["path"],
            baseline_prompts=study["initial_prompts"][lang]["path"],
            prompts=prior["prompts"][lang], fixed_v23_protocol=binding(checkout, STUDY),
            data={"split": "development", "answerable_only": True,
                  "record_ids": [r["record_id"] for r in selection["languages"][lang]["selected"]]},
            main_limits=study["limits_per_language"])
        template["decision"]["bare_refusal_policy"] = "rewrite_once"
        name = f"configs/fixed_v23_main_{lang}_v1.yaml"
        (ROOT / name).write_text(yaml.safe_dump(template, allow_unicode=True, sort_keys=False), encoding="utf-8")
        shutil.copy2(ROOT / name, checkout / name)
        configs[lang] = binding(checkout, name)
    for name in OVERLAY:
        (checkout / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, checkout / name)
    wrapper = '#!/bin/bash\nset -euo pipefail\ncd -- ' + shlex.quote(str(checkout)) + '\n'
    wrapper += 'export UV_CACHE_DIR=' + shlex.quote(str(ROOT / ".tools/uv-cache")) + '\n'
    wrapper += 'exec ' + shlex.quote(str(ROOT / ".tools/bin/uv")) + ' run --offline --frozen --project environments/embedding_gpu python scripts/fixed_v23.py "$@"\n'
    (checkout / "fixed-v23.sh").write_text(wrapper, encoding="utf-8")
    (checkout / "fixed-v23.sh").chmod(0o755)
    sources = {p.relative_to(checkout).as_posix(): file_hash(p)
               for p in (checkout / "src/rag_research").rglob("*.py")}
    changed = [name for name, sha in originals.items() if sources[name] != sha]
    require(changed == [OVERLAY[0]], "Only collection control may change old source")
    for name in (*OVERLAY, STUDY, *[v["path"] for v in configs.values()], "fixed-v23.sh",
                 "environments/embedding_gpu/pyproject.toml", "environments/embedding_gpu/uv.lock"):
        sources[name] = file_hash(checkout / name)
    release = {"version": VERSION, "base_commit": BASE,
        "control_commit_at_preparation": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "study": binding(checkout, STUDY), "configs": configs, "files": sources,
        "original_source_sha256": originals, "changed_original_sources": changed,
        "new_native_calls": 0, "old_gate11_passed": False, "phase12_allowed": False,
        "large_assets": {name: binding(checkout, name)["sha256"] for name in copied}}
    save(checkout / "fixed-v23-release.json", release)
    save(ROOT / "data/manifests/fixed_v23_preparation_v1.json", {
        "checkout": str(checkout), "release_sha256": file_hash(checkout / "fixed-v23-release.json"),
        "release": release, "actual_qa_inference_tested": False, "gpu_preflight_tested": False,
        "main_started": False, "cal_protocol_issued": False})
    print(json.dumps({"checkout": str(checkout), "base_commit": BASE, "original_source_changed": changed,
                      "asset_files": len(copied), "new_native_calls": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--refresh-before-init", action="store_true")
    args = parser.parse_args()
    prepare(args.checkout, refresh=args.refresh_before_init)
