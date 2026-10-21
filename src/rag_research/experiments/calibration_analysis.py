"""Analyze fully sealed held-out runs on isolated copies without changing originals."""

import shutil
import tempfile
import time
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

from rag_research.experiments import bilingual_semantics, bilingual_statistics
from rag_research.experiments.bilingual_budget import budget_snapshot
from rag_research.experiments.bilingual_certification import native_cost, resource_sessions
from rag_research.experiments.calibration_protocol import source_hashes
from rag_research.experiments.frozen_trace import require
from rag_research.experiments.storage import checkpoint, read_json, run_lock
from rag_research.retrieval.common import file_hash

ROOT = Path(__file__).resolve().parents[3]
FIELDS = {"run", "quality_bundle", "quality_annotations", "unit_bundle", "unit_annotations"}


def input_paths(path):
    path = (ROOT / path).resolve()
    require(path.is_file() and any(path.is_relative_to(ROOT / name) for name in
            ("configs", "data/manifests", "data/runs/bilingual_calibration")),
            "Calibration review input must be local configuration, never Evaluation QA")
    specs = read_json(path)
    require(isinstance(specs, list) and len(specs) == 2 and all(isinstance(r, dict) and set(r) == FIELDS and
            all(isinstance(v, str) and v and not Path(v).is_absolute() for v in r.values()) for r in specs),
            "Use two portable complete Calibration review inputs")
    paths = [{k: (ROOT / v).resolve() for k, v in spec.items()} for spec in specs]
    for row in paths:
        run = row["run"]
        require(run.is_relative_to(ROOT / "data/runs/bilingual_calibration") and run != ROOT / "data/runs/bilingual_calibration" and
                (run / ".run.lock").is_file() and (run / ".run.lock").stat().st_size > 0,
                "Use existing original Calibration runs with their locks")
        require(row["quality_bundle"].is_relative_to(run) and row["quality_bundle"] != run and
                row["quality_annotations"].is_relative_to(row["quality_bundle"]) and
                row["unit_bundle"].is_relative_to(row["quality_bundle"]) and row["unit_bundle"] != row["quality_bundle"] and
                row["unit_annotations"].is_relative_to(row["unit_bundle"]), "Calibration reviews must stay inside their run")
    require(len({r["run"] for r in paths}) == 2, "Duplicate Calibration run")
    return path, paths


def snapshot(paths):
    result = {}
    for row in paths:
        run = row["run"]
        for path in sorted(run.rglob("*")):
            if path.is_file():
                require(path.resolve().is_relative_to(run), "Calibration evidence file escapes run")
                result[path.relative_to(ROOT).as_posix()] = file_hash(path)
    return result


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


def analyze(inputs_path):
    started = time.perf_counter()
    inputs_path, originals = input_paths(inputs_path)
    input_sha = file_hash(inputs_path)
    sources = source_hashes(root=ROOT)
    with ExitStack() as stack:
        stack.enter_context(run_lock(ROOT / "data/runs/bilingual_calibration"))
        for row in sorted(originals, key=lambda r: str(r["run"])):
            stack.enter_context(run_lock(row["run"]))
        canonical = [{k: p.relative_to(ROOT).as_posix() for k, p in row.items()} for row in originals]
        reviews, sealed = bilingual_semantics.sealed_inputs(canonical, analysis_split="calibration")
        before = snapshot(originals)
        parent = ROOT / "data/runs/bilingual_calibration_replay"
        parent.mkdir(parents=True, exist_ok=True)
        copied_parent = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix=".analysis-", dir=parent)))
        paths, aliases = [], {}
        for number, row in enumerate(originals):
            copied = copied_parent / str(number)
            shutil.copytree(row["run"], copied)
            aliases[copied] = row["run"]
            paths.append({k: copied / p.relative_to(row["run"]) for k, p in row.items()})
        replay = [{k: p.relative_to(ROOT).as_posix() for k, p in row.items()} for row in paths]
        semantics = bilingual_semantics.analyze_semantics(replay, analysis_split="calibration", canonical_runs=aliases)
        statistics = bilingual_statistics.analyze_runs([
            {"run": r["run"], "bundle": r["quality_bundle"], "annotations": r["quality_annotations"]} for r in replay],
            analysis_split="calibration", unit_inputs=replay, canonical_runs=aliases)
        require(set(statistics["languages"]) == set(semantics["languages"]) == {"en", "ja"} and all(
            statistics["languages"][lang]["selected_qa_count"] == statistics["languages"][lang]["selected_document_groups"] == 20 and
            statistics["languages"][lang]["comparable_qa_count"] == semantics["languages"][lang]["complete_comparable_qa"]
            for lang in ("en", "ja")), "Calibration statistical/semantic cohorts or comparison counts differ")
        health, measured, budgets, resource_errors, protocols = {}, {}, {}, {}, []
        for language, row in zip(("en", "ja"), sorted(paths, key=lambda r: read_json(r["run"] / "manifest.json")["language"]), strict=True):
            manifest, report = read_json(row["run"] / "manifest.json"), read_json(row["run"] / "report.private.json")
            require(manifest["language"] == language and manifest["config"]["execution_scope"] == "heldout_calibration_v1",
                    "Calibration analysis cannot use a Development cohort")
            protocols.append(manifest["config"]["calibration_protocol"])
            budget = budget_snapshot(row["run"])
            budgets[language] = budget
            complete = report["selected_qa_count"] == len(report["records"]) == len(manifest["selection"]) == 20 and not report["failures"]
            healthy = (complete and not budget["error_paths"] and not budget["unknown_or_interrupted_paths"] and
                budget["recorded_native_attempts_upper_bound"] <= manifest["config"]["calibration_limits"]["maximum_completion_attempts"])
            try:
                measured[language] = native_cost(row["run"], budget)
            except ValueError as error:
                resource_errors[language] = "Native cost: " + str(error)
                measured[language] = None
                healthy = False
            try:
                resource_sessions(row["run"], manifest)
            except ValueError as error:
                resource_errors[language] = resource_errors.get(language, "") + " Resource: " + str(error)
                healthy = False
            health[language] = bool(healthy and all(r["rewrite"]["status"] == "ok" for r in report["records"]))
        require(protocols[0] == protocols[1], "Both Calibration languages must share the same protocol")
        for collection in statistics["all_selected_quality_costs"]:
            actual = measured[collection["language"]]
            if actual is not None:
                base, auxiliary = collection["all_selected_baseline_cost"], collection["quality_and_costs"]["auxiliary_collection_cost"]
                require(not base["incomplete"] and not auxiliary["incomplete"] and all(
                    base[k] + auxiliary[k] == actual[k] for k in
                    ("completion_attempts", "recorded_completion_attempts", "input_tokens", "output_tokens")),
                    "Calibration native cost differs from all selected analysis costs")
        burden = {}
        for paths_row, packet, _, unit_packet, labels in reviews:
            annotations = read_json(paths_row["quality_annotations"])["annotations"]
            burden[unit_packet["language"]] = {"quality_labels": len(annotations), "unit_labels": len(labels),
                "quality_annotation_seconds": sum(a["elapsed_seconds"] for a in annotations),
                "unit_annotation_seconds": sum(a["elapsed_seconds"] for a in labels.values()),
                "quality_annotators": sorted({a["annotator"] for a in annotations}),
                "unit_annotators": sorted({a["annotator"] for a in labels.values()}),
                "reported_unit_exact_model_identifiers": sorted({a["exact_model_identifier"] for a in labels.values()
                                                                 if a["exact_model_identifier"] is not None}),
                "unit_model_identifier_unknown_count": sum(a["exact_model_identifier"] is None for a in labels.values()),
                "reported_unit_history_isolated_count": sum(a["history_isolated"] for a in labels.values()),
                "quality_exact_model_identifier_not_provided_by_label_schema": True}
        require(snapshot(originals) == before and original_paths(snapshot(paths), aliases) == before and
                all(file_hash(p) == sha for p, sha in sealed.items()) and file_hash(inputs_path) == input_sha and
                all(file_hash(ROOT / name) == sha for name, sha in sources.items()), "Calibration evidence/source changed during analysis")
        result = {"schema_version": 1, "purpose": "phase11-sealed-heldout-calibration-evidence-analysis",
            "created_at_utc": datetime.now(UTC).isoformat(), "inputs": {"path": inputs_path.relative_to(ROOT).as_posix(), "sha256": input_sha},
            "canonical_inputs": canonical, "protocol": protocols[0], "semantics": semantics, "statistics": statistics,
            "health_gate_per_language": health, "native_collection_costs": measured, "native_budgets": budgets,
            "resource_validation_errors": resource_errors, "annotation_burden": burden,
            "calibration_gate_passed": all(health.values()) and semantics["calibration_semantic_gate_passed"] is True,
            "evidence_files_sha256": before, "analysis_source_sha256": sources,
            "analysis_elapsed_seconds": time.perf_counter() - started,
            "human_reviewed": False, "annotation_history_independence_not_assumed": True,
            "new_model_calls": 0, "new_model_servers": 0, "research_sample_size_frozen": False,
            "gate11_passed": False, "phase12_allowed": False}
        return original_paths(result, aliases)


def save(inputs_path, output):
    output = Path(output).resolve()
    parent = ROOT / "data/runs/bilingual_calibration_analysis"
    require(output.is_relative_to(parent) and output != parent and not output.exists(), "Preserve prior Calibration analyses")
    result = analyze(inputs_path)
    with run_lock(output):
        require({p.name for p in output.iterdir()} == {".run.lock"}, "Calibration analysis output already used")
        saved = checkpoint(output / "analysis.private.json", result)
    return {"analysis_sha256": saved["result_sha256"], "calibration_gate_passed": result["calibration_gate_passed"],
        "new_model_calls": 0, "gate11_passed": False, "phase12_allowed": False}
