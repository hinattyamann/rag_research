"""Freeze bilingual conditions only after rechecking sealed, complete real evidence."""

import math
from copy import deepcopy
from pathlib import Path

from rag_research.data.japanese_dataset import REVISION, assign_splits
from rag_research.data.study_assets import load_assets
from rag_research.experiments import calibration_analysis, calibration_protocol
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.phase11_autonomy import validate_chain_identity
from rag_research.experiments.semantic_adoption import version
from rag_research.experiments.storage import checkpoint, read_json, run_lock, verify_checkpoint
from rag_research.retrieval.common import file_hash, verify_index

ROOT = Path(__file__).resolve().parents[3]
METADATA = {
    "en": "data/manifests/clapnq_split_manifest.json",
    "ja_groups": "data/processed/wikipedia_human_retrieval_ja/02e85c8-groups-v2/groups.json",
    "ja_spec": "configs/phase11_japanese_dataset_v2.json",
}
METADATA_SHA256 = {
    "en": "148c0f95736faa8eb9a7ac6cd538988c9f31054468376d2ef9678fcdc958d330",
    "ja_groups": "2302e1f9c30da9fccf61317487873817799f79e8a17ded1d6191255e004ae800",
    "ja_spec": "73916eb2cfb9cc9e9e146966cd78d4a65a91ca1b3d1d193402e04d48f3d0b5ef",
}
SOURCE_SELECTION_SHA256 = "df2d8cfb82bfffd7b50bd401bf6d26c3becfe92e35c85f6f6b2105b363ae1d88"
STATISTICS = {
    "primary": "mean_within_qa_order_pair_disagreement_minus_repeat_pair_disagreement",
    "language_contrast": "unpaired_dataset_mean_ja_minus_en",
    "cluster": {"en": "NFC_casefold_source_title", "ja": "document_group_id"},
    "bootstrap_repetitions": 10000, "seed": 42,
    "rng": "SeedSequence(seed).spawn(2) in en,ja order",
    "quantile": "linear_percentile_2.5_97.5",
    "missing": "complete_planned_trials_only_primary_partial_exploratory_no_imputation",
    "quality_cost_denominator": "all_selected_including_failures_unknown_and_unattempted",
    "fewer_than_two_comparable_groups": "null_ci",
    "causal_language_effect_claim": False,
}
CHECKS = ("decisions", "main_development", "heldout_calibration", "datasets",
          "conditions_statistics", "evaluation_selection_resources")
VOLATILE_CALIBRATION = {"created_at_utc", "analysis_elapsed_seconds", "result_sha256"}


def path(value, *, parent=None):
    require(isinstance(value, str) and value and not Path(value).is_absolute(), "Use portable artifact paths")
    target = (ROOT / value).resolve()
    require(target.is_relative_to(ROOT) and target != ROOT, "Artifact escapes repository")
    if parent is not None:
        base = (ROOT / parent).resolve()
        require(target.is_relative_to(base) and target != base, "Unexpected artifact scope: " + value)
    return target


def bound(binding, *, parent=None, expected=None):
    require(isinstance(binding, dict) and set(binding) == {"path", "sha256"}, "Use exact path/SHA256 bindings")
    target = path(binding["path"], parent=parent)
    require(expected is None or target == ROOT / expected, "Unexpected metadata identity")
    require(target.is_file() and file_hash(target) == binding["sha256"], "Artifact missing or changed: " + binding["path"])
    return target


def finite_positive(value):
    return type(value) in {int, float} and math.isfinite(value) and value > 0


def public_decisions(value):
    require(value.get("schema_version") == 1 and value.get("purpose") == "phase11-bilingual-final-freeze-decisions" and
            value.get("status") == "resolved_pending_evidence_reverification" and value.get("target_backend") == "CUDA",
            "Bilingual final decisions are pending or have the wrong schema")
    require(value.get("statistics") == STATISTICS and value.get("selection_seed") == 42 and
            value.get("automatic_refill") is False and value.get("selection_uses_evaluation_text_or_results") is False and
            value.get("selection_uses_effect_size_or_significance") is False,
            "Preserve preregistered statistics and outcome-independent selection")
    require(set(value.get("counts", {})) == {"en", "ja"} and
            all(type(n) is int and n > 0 for n in value["counts"].values()), "Both final sample sizes must be explicitly decided")
    require(set(value.get("resource_limits", {})) == {"en", "ja"} and
            all(set(row) == {"native_calls", "summed_native_step_seconds", "annotation_seconds"} and
                all(finite_positive(v) for v in row.values()) and type(row["native_calls"]) is int
                for row in value["resource_limits"].values()) and
            finite_positive(value.get("resource_safety_factor")) and value["resource_safety_factor"] >= 1,
            "Explicit finite resource planning limits and safety factor required")
    require(all(isinstance(value.get(k), str) and value[k].strip() for k in
                ("sample_size_rationale", "precision_and_group_dependence_limitations", "source_comparison_limitations",
                 "quality_assessor_limitations", "stopping_and_missing_policy")), "Final decisions need substantive reasons and limitations")
    require(value.get("stop_on_unknown_or_error") is True and value.get("no_fixed_unit_truncation") is True and
            value.get("retry_unknown_outcomes") is False, "Preserve whole units, failures and conservative stopping")


def evaluation_population(metadata):
    """Read only fixed split/group metadata; never open Evaluation QA rows."""
    require(set(metadata) == set(METADATA), "Both fixed dataset split metadata sets required")
    require(all(metadata[k].get("sha256") == sha for k, sha in METADATA_SHA256.items()),
            "Keep the immutable split/group metadata revision; updating a decision hash cannot replace it")
    files = {k: bound(metadata[k], expected=name) for k, name in METADATA.items()}
    english = read_json(files["en"])
    require(english["validation"]["passed"] is True and english["seed"] == 42 and
            english["source_revision"] == "c508d78d8c5c2eecbf172fcf5f789004206e11fb",
            "English fixed split is not verified")
    splits = english["record_ids_by_split"]
    require(set(splits) == {"development", "calibration", "evaluation"} and
            all(isinstance(ids, list) and len(ids) == len(set(ids)) for ids in splits.values()) and
            not (set(splits["evaluation"]) & (set(splits["development"]) | set(splits["calibration"]))),
            "English Evaluation ID split overlap")
    en = [i for i in splits["evaluation"] if i.endswith(":answerable")]
    groups, spec = read_json(files["ja_groups"]), read_json(files["ja_spec"])
    assignments = assign_splits(groups, spec)
    ids = [i for group in groups for i in group["source_ids"]]
    require(len(ids) == len(set(ids)) == 838, "Japanese source ID metadata changed")
    ja = [f"whrja:{REVISION[:7]}:answered:{i}" for group in groups
          if assignments[group["group_id"]] == "evaluation" for i in group["source_ids"]]
    require(len(ja) == 209 and en, "Dataset Evaluation population changed")
    return {"en": en, "ja": ja}


def choose(populations, counts, *, seed=42):
    result = {}
    for language in ("en", "ja"):
        population = populations[language]
        require(len(population) == len(set(population)) and 0 < counts[language] <= len(population),
                "Final N exceeds the unique source-answered Evaluation population")
        result[language] = sorted(population, key=lambda i: (digest([
            "phase11-bilingual-evaluation-id-selection-v1", seed, language, i]), i))[:counts[language]]
    return result


def retrieval_artifacts(assets):
    """Verify every saved index/model payload without creating a CUDA session."""
    files = {}
    for data in assets["datasets"].values():
        corpus = bound(data["corpus"])
        for kind, binding in data["indexes"].items():
            directory = bound(binding).parent
            manifest = read_json(directory / "manifest.json")
            require(all((directory / name).resolve().is_relative_to(directory) for name in manifest["files"]),
                    "Index payload escapes its directory")
            require(verify_index(directory, corpus) == manifest, "Index manifest changed during validation")
            for name, info in manifest["files"].items():
                target = (directory / name).resolve()
                require(target.is_relative_to(directory), "Index payload escapes its directory")
                files[target.relative_to(ROOT).as_posix()] = info["sha256"]
            if kind == "embedding":
                metadata = manifest["config"]["model"]
                revision = metadata["revision"]
                require(isinstance(revision, str) and len(revision) == 40 and
                        all(c in "0123456789abcdef" for c in revision), "Pinned embedding revision required")
                model = path(assets["embedding"]["model_root"], parent="data/models") / revision
                require(read_json(model / "model_manifest.json") == metadata,
                        "Embedding installed model manifest differs from the index")
                files[(model / "model_manifest.json").relative_to(ROOT).as_posix()] = file_hash(model / "model_manifest.json")
                for name, info in metadata["files"].items():
                    target = (model / name).resolve()
                    require(target.is_relative_to(model) and file_hash(target) == info["sha256"],
                            "Embedding model payload changed or escapes its directory")
                    files[target.relative_to(ROOT).as_posix()] = info["sha256"]
    return files


def sealed_evidence(decisions):
    main_inputs = bound(decisions["main_inputs"], parent="configs")
    certificate = path(decisions["main_certificate"]["path"], parent="data/runs/development_certification")
    calibration_inputs = bound(decisions["calibration_inputs"], parent="configs")
    # Analyze first: every anonymous quality/unit label is sealed before any
    # private F, stage mappings, saved certificate or saved analysis is opened.
    current = calibration_analysis.analyze(calibration_inputs)
    bound(decisions["main_certificate"], parent="data/runs/development_certification")
    saved_path = bound(decisions["calibration_analysis"], parent="data/runs/bilingual_calibration_analysis")
    saved = read_json(saved_path)
    verify_checkpoint(saved)
    def stable(value):
        return {k: x for k, x in value.items() if k not in VOLATILE_CALIBRATION}
    require(stable(saved) == stable(current) and current["calibration_gate_passed"] is True and
            current["human_reviewed"] is False and current["new_model_calls"] == current["new_model_servers"] == 0,
            "Held-out analysis differs from complete reverified original evidence or did not pass")
    protocol_path = bound(current["protocol"], parent="data/runs/bilingual_calibration_protocol")
    protocol = read_json(protocol_path)
    verify_checkpoint(protocol)
    require(protocol["main_inputs"] == decisions["main_inputs"] and protocol["main_certificate"] == decisions["main_certificate"],
            "Final main evidence differs from the evidence authorizing Calibration")
    main = calibration_protocol.verify_main(main_inputs, certificate)
    validate_chain_identity(decisions, main, current, protocol, root=ROOT)
    require(version(main.get("semantics", {})) == version(current.get("semantics", {})) == version(decisions),
            "Final/Main/Calibration semantic adoption versions differ")
    require(main["condition_sha256"] == current["statistics"]["condition_sha256"] == protocol["condition_sha256"],
            "Main and held-out Calibration conditions differ")
    return main, current


def resource_projection(decisions, main, calibration):
    result = {}
    for lang in ("en", "ja"):
        n = decisions["counts"][lang]
        stats = calibration["statistics"]["languages"][lang]
        require(stats["selected_qa_count"] == stats["selected_document_groups"] == 20 and
                stats["comparable_qa_count"] >= 10, "Full held-out feasibility evidence required")
        native = [main["source_runs"][lang]["native_collection_cost"], calibration["native_collection_costs"][lang]]
        burdens = [main["annotation_burden"][lang], calibration["annotation_burden"][lang]]
        require(all(c and not c["incomplete"] and finite_positive(c["completion_attempts"]) and
                    finite_positive(c["summed_step_seconds"]) for c in native), "Measured native costs are incomplete")
        review_seconds = sum(b["quality_annotation_seconds"] + b["unit_annotation_seconds"] for b in burdens)
        require(finite_positive(review_seconds), "Measured full quality/unit annotation burden required")
        factor = n * decisions["resource_safety_factor"] / 40
        projected = {"native_calls": math.ceil(factor * sum(c["completion_attempts"] for c in native)),
            "summed_native_step_seconds": factor * sum(c["summed_step_seconds"] for c in native),
            "annotation_seconds": factor * review_seconds}
        require(all(v <= decisions["resource_limits"][lang][k] for k, v in projected.items()),
                "Final sample size exceeds its declared resource planning limits")
        result[lang] = {"planned_qa": n, "heldout_complete_comparable_fraction": stats["comparable_qa_count"] / 20,
            "expected_comparable_qa_planning_only": n * stats["comparable_qa_count"] / 20,
            "projected_with_safety_factor": projected, "measured_main_and_calibration_qa": 40,
            "not_a_wall_time_gpu_kernel_time_or_completion_guarantee": True,
            "full_units_may_exceed_planning_estimate_stop_without_clipping_or_refill": True}
    return result


def sources():
    paths = [*sorted((ROOT / "src/rag_research").rglob("*.py")),
             ROOT / "scripts/finalize_bilingual_phase11.py", ROOT / "docs/order_quality_rubric.md",
             ROOT / "docs/phase11_statistical_plan.md"]
    return {p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths}


def validator_validation(binding):
    report_path = bound(binding, parent="data/manifests")
    report = read_json(report_path)
    verify_checkpoint(report)
    require(report["purpose"] == "phase11-bilingual-finalization-validation-not-final-freeze" and
            type(report["tests"]["pytest_passed"]) is int and report["tests"]["pytest_passed"] > 0 and
            report["tests"]["ruff"] == "passed" and report["validation_source_sha256"] == sources() and
            report["actual_pending_freeze_rejected"] is True and report["actual_evaluation_qa_rows_parsed"] == 0 and
            report["new_model_calls"] == 0 and report["gate11_passed"] is False,
            "Validator tests/actual rejection evidence are missing or refer to different source")
    require(report["artifacts"], "Validator evidence artifacts missing")
    for name, info in report["artifacts"].items():
        bound({"path": name, "sha256": info["sha256"]})
    return report


def readiness(decisions_path):
    checks, reasons = dict.fromkeys(CHECKS, False), {}
    stage = "decisions"
    try:
        decisions_path = path(str(decisions_path), parent="configs")
        before_decisions, source_before = file_hash(decisions_path), sources()
        decisions = read_json(decisions_path)
        public_decisions(decisions)
        checks[stage] = True
        stage = "main_development"
        main, calibration = sealed_evidence(decisions)
        checks[stage] = True
        stage = "heldout_calibration"
        require(calibration["calibration_gate_passed"] is True, "Both held-out semantic/health gates required")
        checks[stage] = True
        stage = "datasets"
        assets_path = bound(decisions["assets"], parent="configs")
        assets = load_assets(assets_path, root=ROOT)
        retrieval_files = retrieval_artifacts(assets)
        source_selection = bound(decisions["japanese_source_selection"], expected="data/manifests/phase11_japanese_source_selection.json")
        selected = read_json(source_selection)
        require(decisions["japanese_source_selection"]["sha256"] == SOURCE_SELECTION_SHA256 and
                selected["dataset_id"] == assets["datasets"]["ja"]["source_dataset"] and
                selected["source_revision"] == REVISION and selected["status"] == "selected_for_phase11_preparation" and
                selected["annotation_license_declared"] == "Apache-2.0" and selected["wikipedia_content_rights_retained_separately"] is True,
                "Japanese source identity, selection rationale or license boundary changed")
        comparison_document = bound(decisions["source_comparison_document"], expected="docs/japanese_dataset_selection.md")
        require(comparison_document.stat().st_size > 0, "Source comparison rationale is missing")
        populations = evaluation_population(decisions["evaluation_metadata"])
        checks[stage] = True
        stage = "conditions_statistics"
        validator = validator_validation(decisions["validator_validation"])
        configs = {}
        for language, row in main["source_runs"].items():
            manifest = read_json(path(row["run"], parent="data/runs/bilingual_development") / "manifest.json")
            require(manifest["config"]["assets"] == decisions["assets"]["path"], "Final assets differ from actual main/Calibration assets")
            configs[language] = manifest["config"]
        require(set(configs) == {"en", "ja"} and
                calibration["statistics"]["statistical_plan_sha256"] == file_hash(ROOT / "docs/phase11_statistical_plan.md"),
                "Both actual language configurations and the preregistered statistical plan required")
        checks[stage] = True
        stage = "evaluation_selection_resources"
        prior_evaluation = ROOT / "data/runs/bilingual_evaluation"
        require(not prior_evaluation.exists() or not any(p.is_file() and p.name != ".run.lock" for p in prior_evaluation.rglob("*")),
                "Evaluation execution evidence already exists; do not refreeze after observing it")
        selection = choose(populations, decisions["counts"], seed=decisions["selection_seed"])
        used = {r["record_id"] for row in main["source_runs"].values() for r in row["selected"]}
        used.update(q["record_id"] for q in calibration["statistics"]["qa"])
        require(not used & {i for ids in selection.values() for i in ids}, "Evaluation overlaps used main/Calibration IDs")
        projection = resource_projection(decisions, main, calibration)
        files = {}
        for collection in (main["evidence_files_sha256"], main["bound_external_files_sha256"],
                           calibration["evidence_files_sha256"], retrieval_files):
            require(all(name not in files or files[name] == sha for name, sha in collection.items()),
                    "Evidence bindings disagree about the same file")
            files.update(collection)
        require(all(file_hash(path(name)) == sha for name, sha in files.items()), "Verified evidence changed before final freeze")
        for key in ("main_inputs", "main_certificate", "calibration_inputs", "calibration_analysis", "assets",
                    "japanese_source_selection", "source_comparison_document"):
            bound(decisions[key])
        validator_validation(decisions["validator_validation"])
        for key, name in METADATA.items():
            bound(decisions["evaluation_metadata"][key], expected=name)
        require(file_hash(decisions_path) == before_decisions and sources() == source_before,
                "Final decisions or source changed during validation")
        checks[stage] = True
        conditions = {"decisions": {"path": decisions_path.relative_to(ROOT).as_posix(), "sha256": before_decisions},
            "complete_decisions": deepcopy(decisions), "actual_main_configurations": configs, "assets": assets,
            "shared_condition_sha256": main["condition_sha256"], "evaluation_record_ids": selection,
            "evaluation_selection_rule": "sha256_json(method,42,language,record_id)_ascending_source_answered_no_refill",
            "resource_projection": projection, "main_evidence_files_sha256": main["evidence_files_sha256"],
            "main_external_files_sha256": main["bound_external_files_sha256"],
            "calibration_evidence_files_sha256": calibration["evidence_files_sha256"],
            "retrieval_artifacts_sha256": retrieval_files,
            "validator_validation_sha256": validator["result_sha256"],
            "finalization_source_sha256": source_before, "human_reviewed": False,
            "annotation_history_independence_not_assumed": True, "new_model_calls": 0, "evaluation_qa_rows_read": 0}
        conditions.update(validate_chain_identity(decisions, main, calibration, root=ROOT) or {})
        return {"gate11_passed": True, "phase12_allowed": True, "checks": checks, "reasons": reasons, "conditions": conditions}
    except (ValueError, KeyError, TypeError, OSError) as error:
        reasons[stage] = str(error)
        return {"gate11_passed": False, "phase12_allowed": False, "checks": checks, "reasons": reasons, "conditions": None}


def save(decisions_path, output):
    """Never accept caller-provided pass flags or overwrite an older freeze."""
    output = path(str(output), parent="data/manifests")
    require(output.name.startswith("phase11_bilingual_final_freeze_") and output.suffix == ".json",
            "Use a versioned bilingual final-freeze manifest name")
    with run_lock(ROOT / "data/runs/bilingual_finalization"):
        require(not output.exists(), "Preserve the previous final freeze")
        result = readiness(decisions_path)
        require(result["gate11_passed"] is True and all(result["checks"].values()),
                "Bilingual Gate11 has unmet requirements; no final manifest written: " + str(result["reasons"]))
        return checkpoint(output, {"schema_version": 2, "purpose": "phase11-bilingual-final-condition-freeze", **result,
            **{k: result["conditions"][k] for k in
               ("autonomy_protocol_version", "autonomy_protocol", "candidate_identity_sha256") if k in result["conditions"]}})
