"""Certify completed, sealed main Development evidence without running any model."""

import math
import re
import shutil
import tempfile
import time
from contextlib import ExitStack
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import yaml

from rag_research.data.study_assets import load_assets, load_rows
from rag_research.evaluation.claimwise import atomic_steps, verify_once
from rag_research.experiments import (
    bilingual_quality,
    bilingual_semantics,
    bilingual_statistics,
    semantic_diagnostics,
)
from rag_research.experiments.bilingual_budget import budget_snapshot
from rag_research.experiments.bilingual_main import validate_main
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.protocol import task_config
from rag_research.experiments.quality import cost
from rag_research.experiments.storage import read_json, run_lock, verify_checkpoint
from rag_research.generation.auxiliary import auxiliary_identity
from rag_research.generation.cuda_runtime import execution_identity
from rag_research.retrieval.common import file_hash

SOURCE_ROOT = Path(__file__).resolve().parents[3]
ROOT = SOURCE_ROOT
FIELDS = {"run", "quality_bundle", "quality_annotations", "unit_bundle", "unit_annotations"}


def input_paths(path):
    path = (ROOT / path).resolve()
    require(path.is_file() and any(path.is_relative_to(ROOT / folder) for folder in
            ("configs", "data/manifests", "data/runs/bilingual_development")),
            "Certificate inputs must be a local configuration, not Evaluation QA")
    inputs = read_json(path)
    require(isinstance(inputs, list) and len(inputs) == 2, "Exactly two main Development inputs required")
    paths = []
    for spec in inputs:
        require(isinstance(spec, dict) and set(spec) == FIELDS and all(isinstance(v, str) and v and
                not Path(v).is_absolute() for v in spec.values()), "Use portable repository-relative main input paths")
        row = {k: (ROOT / v).resolve() for k, v in spec.items()}
        run, bundle, unit = row["run"], row["quality_bundle"], row["unit_bundle"]
        require(run.is_relative_to(ROOT / "data/runs/bilingual_development") and run != ROOT / "data/runs/bilingual_development" and
                bundle.is_relative_to(run) and bundle != run and unit.is_relative_to(bundle) and unit != bundle and
                row["quality_annotations"].is_relative_to(bundle) and row["unit_annotations"].is_relative_to(unit),
                "Certificate review paths must remain inside their Development run")
        require((run / ".run.lock").is_file() and (run / ".run.lock").stat().st_size > 0,
                "An existing completed run with its original lock is required")
        paths.append(row)
    require(len({r["run"] for r in paths}) == 2, "Duplicate main Development run")
    return path, paths


def snapshot(paths, extra_roots=()):
    files = {}
    for run in sorted({r["run"] for r in paths} | set(extra_roots)):
        for path in sorted(run.rglob("*")):
            if path.is_file():
                require(path.resolve().is_relative_to(run), "Certificate run file escapes its source")
                files[path.relative_to(ROOT).as_posix()] = file_hash(path)
    return files


def adopted_sources(paths):
    """Keep the complete known regression and its prerequisite in the same seal."""
    bound, roots, prerequisites = {}, set(), {}

    def bind(name, sha):
        require(isinstance(name, str) and not Path(name).is_absolute(), "Evidence paths must be portable")
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT) and path.is_file() and file_hash(path) == sha,
                "Declared main/adoption source changed")
        bound[path.relative_to(ROOT).as_posix()] = sha
        return path

    for row in paths:
        manifest = read_json(row["run"] / "manifest.json")
        for name, sha in manifest["source_sha256"].items():
            bind(name, sha)
        bind(manifest["qa_path"], manifest["qa_sha256"])
        adoption = manifest["config"]["adopted_known_regression"]
        report = bind(adoption["path"], adoption["sha256"])
        require(report.is_relative_to(ROOT / "data/runs/semantic_diagnostics"), "Adoption must use known diagnostic evidence")
        roots.add(report.parent)
        config_path = bind(adoption["config"]["path"], adoption["config"]["sha256"])
        require(config_path.is_relative_to(ROOT / "configs"), "Known adoption config must stay in configs")
        config = yaml.safe_load(config_path.read_text("utf-8"))
        plan_path = (ROOT / config["diagnostics"]).resolve()
        require(plan_path.is_relative_to(ROOT / "configs"), "Known adoption plan must stay in configs")
        plan = read_json(plan_path)
        known_manifest = read_json(report.parent / "manifest.json")
        require(known_manifest["plan_sha256"] == file_hash(plan_path), "Adopted known plan differs from its run")
        bound[plan_path.relative_to(ROOT).as_posix()] = file_hash(plan_path)
        for name, sha in plan["source_sha256"].items():
            bind(name, sha)
        prerequisite = plan["prerequisite"]
        prior = bind(prerequisite["report_path"], prerequisite["sha256"])
        require(prior.is_relative_to(ROOT / "data/runs/semantic_diagnostics"), "Prerequisite must stay in diagnostics")
        roots.add(prior.parent)
        policy_binding = manifest["config"]["main_execution_policy"]
        policy = read_json(bind(policy_binding["path"], policy_binding["sha256"]))
        candidate = policy["candidate_config"]
        candidate_path = bind(candidate["path"], candidate["sha256"])
        require(candidate_path.is_relative_to(ROOT / "configs"), "Adopted candidate must stay in configs")
        require(prior not in prerequisites or prerequisites[prior] == candidate_path, "Prerequisite candidate differs across languages")
        prerequisites[prior] = candidate_path
    return bound, roots, prerequisites


def verify_prerequisite(report_path, candidate_path):
    """Recompute the entire bilingual diagnostic, rather than trusting a pass flag."""
    config, plan, prompts, plan_path = semantic_diagnostics.load_config(candidate_path)
    report, manifest = read_json(report_path), read_json(report_path.parent / "manifest.json")
    selected = semantic_diagnostics.specs(plan)
    require(plan["purpose"] == "phase11-known-bilingual-semantic-diagnostics" and manifest["config"] == config and
            manifest["plan_sha256"] == file_hash(plan_path) and report["manifest_sha256"] == digest(manifest) and
            report["planned_conditions"] == report["completed_conditions"] == len(selected) and
            set(report["task_result_sha256"]) == {key for _, _, key in selected} and
            report["completion_attempts_recorded"] == plan["max_completion_attempts"] and not report["cost_incomplete"],
            "Prerequisite must contain every planned bilingual condition and call")
    require(manifest["model"] == auxiliary_identity(config) and
            all(manifest.get(k) == v for k, v in execution_identity(config).items()), "Prerequisite model/runtime changed")
    for name, sha in manifest["source_sha256"].items():
        if name.startswith(("src/rag_research/evaluation/", "src/rag_research/generation/")) or name in {
                "src/rag_research/experiments/protocol.py", "src/rag_research/experiments/frozen_trace.py",
                "src/rag_research/experiments/storage.py"}:
            require(file_hash(ROOT / name) == sha, "Prerequisite native core changed")
    results = {}
    mode = config.get("verification_mode", "joint")
    for case, order, key in selected:
        path = report_path.parent / "tasks" / (key + ".json")
        saved = read_json(path)
        verify_checkpoint(saved)
        require(saved["status"] == "ok" and saved["result_sha256"] == report["task_result_sha256"][key],
                "Prerequisite raw condition changed")
        documents = case["documents"] if order == "original" else list(reversed(case["documents"]))
        result = verify_once(None, task_config(config, "verify_claims"), prompts[case["language"]],
            {"question": case["question"], "answer": case["answer"], "claims": case["claims"], "documents": documents},
            path, {"manifest_sha256": digest(manifest), "case_id": case["id"], "order": order},
            constraints=config["output_constraints"], mode=mode,
            reader_generation=task_config(config, "read_sources") if mode == "source-reading-v1" else None)
        require(result == saved, "Prerequisite inputs/raw costs changed")
        results[key] = result
    assessed = semantic_diagnostics.assess(plan, results)
    require(assessed["diagnostic_gate_passed"] is True and all(report.get(k) == v for k, v in assessed.items()) and
            sum(bool(t["completion_attempted"]) for t in atomic_steps(results.values())) == plan["max_completion_attempts"],
            "Prerequisite pass flag differs from all actual diagnostic results")


def original_paths(value, aliases):
    if isinstance(value, str):
        for copied, original in aliases.items():
            source, target = copied.relative_to(ROOT).as_posix(), original.relative_to(ROOT).as_posix()
            if value == source or value.startswith(source + "/"):
                return target + value[len(source):]
        return value
    if isinstance(value, dict):
        return {original_paths(k, aliases): original_paths(v, aliases) for k, v in value.items()}
    if isinstance(value, list):
        return [original_paths(v, aliases) for v in value]
    return value


def native_cost(run, budget):
    projected = []
    for entry in budget["raw_calls"]:
        path = run / entry["path"]
        task = read_json(path)
        require(task["status"] == "ok" and not task.get("cost_incomplete") and all(
            type(task.get(k)) is int and task[k] >= 0 for k in ("input_tokens", "output_tokens")),
            "Every native call needs measured complete token costs")
        fields = ("generation_seconds", "context_seconds") if path.is_relative_to(run / "baseline") else ("elapsed_seconds",)
        require(all(type(task.get(k)) in {int, float} and math.isfinite(task[k]) and task[k] >= 0 for k in fields),
                "Every native call needs measured complete step seconds")
        projected.append({"completion_attempted": True, "input_tokens": task["input_tokens"],
            "output_tokens": task["output_tokens"], "elapsed_seconds": sum(task[k] for k in fields)})
    return cost(projected)


def resource_sessions(run, manifest):
    """Compare all saved stage sessions with actual CUDA log evidence."""
    checked = []
    for stage, config, context in (
            ("baseline", manifest["baseline"], manifest["baseline"]["generation"]["context_tokens"]),
            ("internal", manifest["config"], manifest["config"]["auxiliary_runtime"]["context_tokens"])):
        expected = execution_identity(config)
        require(expected.get("execution", {}).get("require_full_offload") is True,
                "Main certificate requires explicit CUDA execution")
        directory = run / stage
        sessions = sorted(directory.glob("session-*.json"))
        logs = {p.name for p in directory.glob("server-*.log")}
        require(sessions and logs == {p.name.replace("session-", "server-").replace(".json", ".log") for p in sessions},
                "Every main stage needs paired server logs and session reports")
        for path in sessions:
            saved = read_json(path)
            log = path.with_name(path.name.replace("session-", "server-").replace(".json", ".log")).read_text("utf-8")
            layers = re.findall(r"offloaded (\d+)/(\d+) layers to GPU", log)
            actual = tuple(map(int, layers[-1])) if layers else (0, 0)
            require(all(saved.get(k) == v for k, v in expected.items()) and saved["server_context_tokens"] == context and
                    saved["actual_gpu_offload"] is True and saved["full_gpu_offload"] is True and
                    actual == (saved["offloaded_layers"], saved["total_layers"]) and actual[0] == actual[1] > 0 and
                    re.search(r"using device CUDA\d+|CUDA\d+.*model buffer", log),
                    "Main session differs from declared context/runtime or actual full CUDA offload")
            checked.append(path.relative_to(ROOT).as_posix())
    return checked


def certify_main(inputs_path):
    started = time.perf_counter()
    inputs_path, paths = input_paths(inputs_path)
    input_hash = file_hash(inputs_path)
    sources = [*sorted((SOURCE_ROOT / "src/rag_research").rglob("*.py")),
               SOURCE_ROOT / "scripts/certify_bilingual_main.py"]
    source_hashes = {p.relative_to(SOURCE_ROOT).as_posix(): file_hash(p) for p in sources}
    with ExitStack() as stack:
        for row in sorted(paths, key=lambda r: str(r["run"])):
            stack.enter_context(run_lock(row["run"]))
        # Only review packets/mapping integrity are read here. No raw scores,
        # run manifests or report hashes are accessed until every label is sealed.
        reviews = {}
        for row in paths:
            packet, _, quality_labels = bilingual_quality.sealed_annotations(row["quality_bundle"], row["quality_annotations"])
            unit = read_json(row["unit_bundle"] / "packet.json")
            unit_labels = bilingual_semantics.validate_unit_annotations(unit, read_json(row["unit_annotations"]), sealed=True)
            require(unit["quality_packet_sha256"] == packet["packet_sha256"] and unit["language"] not in reviews,
                    "Certificate needs distinct language reviews of the same candidates")
            reviews[unit["language"]] = row, quality_labels, unit_labels
        require(set(reviews) == {"en", "ja"}, "Both English and Japanese reviews are required")
        paths = [reviews[language][0] for language in ("en", "ja")]
        canonical = [{k: p.relative_to(ROOT).as_posix() for k, p in row.items()} for row in paths]
        bound, proof_roots, prerequisites = adopted_sources(paths)
        for run in sorted(proof_roots):
            require((run / ".run.lock").is_file() and (run / ".run.lock").stat().st_size > 0,
                    "Adopted diagnostics need their original run locks")
            stack.enter_context(run_lock(run))
        before = snapshot(paths, proof_roots)
        originals = paths
        # Existing replay helpers rebuild derived aggregate checkpoints. Use
        # byte-identical copies so interruptions cannot alter original research.
        copied_main = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix=".certificate-", dir=ROOT / "data/runs/bilingual_development")))
        copied_proof = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix=".certificate-", dir=ROOT / "data/runs/semantic_diagnostics")))
        aliases, replacement = {}, {}
        for index, row in enumerate(paths):
            run = row["run"]
            target = copied_main / str(index)
            shutil.copytree(run, target)
            aliases[target], replacement[run] = run, target
        for index, run in enumerate(sorted(proof_roots)):
            target = copied_proof / str(index)
            shutil.copytree(run, target)
            aliases[target], replacement[run] = run, target
        paths = [{k: replacement[row["run"]] / p.relative_to(row["run"]) for k, p in row.items()} for row in paths]
        replay_inputs = [{k: p.relative_to(ROOT).as_posix() for k, p in row.items()} for row in paths]
        replay_proofs = {replacement[r] for r in proof_roots}
        for report_path, candidate_path in prerequisites.items():
            verify_prerequisite(replacement[report_path.parent] / report_path.name, candidate_path)
        semantics = bilingual_semantics.analyze_semantics(replay_inputs)
        require(semantics["main_development_semantic_gate_passed"] is True and
                all(semantics["main_development_semantic_gate_per_language"].get(language) is True
                    for language in ("en", "ja")), "Both full main semantic gates must pass")
        runs, policies, conditions = {}, [], []
        for language, row in zip(("en", "ja"), paths, strict=True):
            run = row["run"]
            manifest, report = read_json(run / "manifest.json"), read_json(run / "report.private.json")
            config = manifest["config"]
            require(manifest["language"] == language and config["purpose"] == "phase11-bilingual-development-candidate" and
                    config["execution_scope"] == "main_development_v1" and
                    report["selected_qa_count"] == len(report["records"]) == len(manifest["selection"]) == 20 and
                    not report["failures"] and all(r["rewrite"]["status"] == "ok" for r in report["records"]),
                    "Certificate requires complete healthy main20, not a connection or partial run")
            assets = load_assets(ROOT / config["assets"], root=ROOT)
            qa, qa_path = load_rows(assets, language, "development", root=ROOT)
            by_id = {r["record_id"]: r for r in qa}
            selected = [by_id[r["record_id"]] for r in manifest["selection"]]
            replay_config = deepcopy(config)
            adoption = replay_config["adopted_known_regression"]
            report_path = (ROOT / adoption["path"]).resolve()
            adoption["path"] = (replacement[report_path.parent] / report_path.name).relative_to(ROOT).as_posix()
            validate_main(replay_config, selected, qa_path)
            budget = budget_snapshot(run)
            require(not budget["error_paths"] and not budget["unknown_or_interrupted_paths"] and
                    budget["recorded_native_attempts_upper_bound"] <= config["main_limits"]["maximum_completion_attempts"],
                    "Main native work must be complete, healthy and within its declared budget")
            binding = config["main_execution_policy"]
            policies.append(binding)
            conditions.append(digest(bilingual_statistics.condition(manifest)))
            runs[language] = {"run": run.relative_to(ROOT).as_posix(), "manifest_digest": digest(manifest),
                "selected": [{"record_id": r["record_id"], "document_group_id": r["document_group_id"]} for r in selected],
                "native_collection_cost": native_cost(run, budget),
                "recorded_native_attempts": budget["recorded_native_attempts_upper_bound"],
                "resource_session_files": resource_sessions(run, manifest)}
        require(policies[0] == policies[1] and conditions[0] == conditions[1], "Main policies/conditions must match across languages")
        statistics = bilingual_statistics.analyze_runs([
            {"run": r["run"], "bundle": r["quality_bundle"], "annotations": r["quality_annotations"]} for r in replay_inputs])
        require(statistics["condition_sha256"] == conditions[0] and set(statistics["languages"]) == {"en", "ja"},
                "Statistical evidence differs from the verified main conditions")
        collections = statistics["all_selected_quality_costs"]
        require(len(collections) == 2 and {c["language"] for c in collections} == {"en", "ja"}, "Main cost cohorts differ")
        burden = {}
        for collection in collections:
            language = collection["language"]
            counts = statistics["languages"][language]
            require(counts["selected_qa_count"] == counts["selected_document_groups"] == 20 and
                    counts["comparable_qa_count"] == semantics["languages"][language]["complete_comparable_qa"] >= 10,
                    "Main statistical selection/groups/comparisons differ from semantic evidence")
            measured = runs[language]["native_collection_cost"]
            base, auxiliary = collection["all_selected_baseline_cost"], collection["quality_and_costs"]["auxiliary_collection_cost"]
            require(not base["incomplete"] and not auxiliary["incomplete"] and
                    all(base[k] + auxiliary[k] == measured[k] for k in
                        ("completion_attempts", "recorded_completion_attempts", "input_tokens", "output_tokens")),
                    "Actual native calls/tokens differ from baseline plus auxiliary collection costs")
            _, quality_labels, unit_labels = reviews[language]
            burden[language] = {"quality_labels": len(quality_labels), "fixed_unit_labels": len(unit_labels),
                "quality_annotation_seconds": sum(a["elapsed_seconds"] for a in quality_labels.values()),
                "unit_annotation_seconds": sum(a["elapsed_seconds"] for a in unit_labels.values()),
                "quality_annotators": sorted({a["annotator"] for a in quality_labels.values()}),
                "unit_annotators": sorted({a["annotator"] for a in unit_labels.values()}),
                "reported_unit_exact_model_identifiers": sorted({a["exact_model_identifier"] for a in unit_labels.values()
                                                                  if a["exact_model_identifier"] is not None}),
                "unit_model_identifier_unknown_count": sum(a["exact_model_identifier"] is None for a in unit_labels.values()),
                "reported_unit_history_isolated_count": sum(a["history_isolated"] for a in unit_labels.values())}
        require(snapshot(originals, proof_roots) == before and
                original_paths(snapshot(paths, replay_proofs), aliases) == before and file_hash(inputs_path) == input_hash and
                all(file_hash(ROOT / name) == sha for name, sha in bound.items()),
                "Main/adoption evidence changed during certification")
        require(all(file_hash(SOURCE_ROOT / name) == sha for name, sha in source_hashes.items()), "Certification source changed")
        result = {"schema_version": 1, "purpose": "phase11-main-development-evidence-certificate", "status": "verified",
        "created_at_utc": datetime.now(UTC).isoformat(), "inputs": {"path": inputs_path.relative_to(ROOT).as_posix(), "sha256": input_hash},
        "canonical_inputs": canonical, "source_runs": runs, "main_execution_policy": policies[0],
        "condition_sha256": conditions[0], "semantics": semantics, "statistics": statistics, "annotation_burden": burden,
        "evidence_files_sha256": before, "bound_external_files_sha256": bound, "certification_source_sha256": source_hashes,
        "verification_elapsed_seconds": time.perf_counter() - started,
        "time_note": "Native collection seconds are measured step times, not end-to-end latency or isolated GPU kernel time; deterministic extraction/startup/retrieval and review time are separate.",
        "human_reviewed": False, "annotation_history_independence_not_assumed": True,
        "new_model_calls": 0, "new_model_servers": 0, "calibration_execution_allowed": False,
        "research_sample_size_frozen": False, "gate11_passed": False, "phase12_allowed": False}
        return original_paths(result, aliases)
