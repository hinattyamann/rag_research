"""Validate calibration evidence and freeze conditions only when all Phase 11 gates pass."""

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.frozen_trace import digest, require  # noqa: E402
from rag_research.experiments.quality import (  # noqa: E402
    reconstruct,
    validate_annotations,
    verify_packet,
)
from rag_research.experiments.storage import (  # noqa: E402
    checkpoint,
    read_json,
    run_lock,
    verify_checkpoint,
)
from rag_research.retrieval.common import file_hash  # noqa: E402

SECTIONS = ("semantic_validity", "refusal_fallback", "external_quality", "runtime", "analysis")


def local_path(root, value):
    require(isinstance(value, str) and value.strip(), "Missing artifact path")
    path = (root / value).resolve()
    require(path.is_relative_to(root), "Artifact path escapes repository")
    return path


def evidence(root, reference):
    require(isinstance(reference, dict) and set(reference) == {"path", "sha256"},
            "Evidence needs a path and SHA256")
    path = local_path(root, reference["path"])
    require(file_hash(path) == reference["sha256"], "Evidence artifact changed")
    value = read_json(path)
    verify_checkpoint(value)
    return value


def verify_calibration(root, run, selection, archive=None):
    """Never read private scores until the complete external quality file is sealed."""
    require(run.is_relative_to(root / "data/runs/calibration"), "Not a Calibration run")
    candidate = read_json(run / "candidate_manifest.json")
    verify_checkpoint(candidate)
    require(candidate["purpose"] == "phase11-provisional-conditions-not-final-freeze" and
            candidate["phase12_allowed"] is False, "Unexpected candidate manifest")
    for name, expected_hash in candidate["source_sha256"].items():
        path = local_path(root, name)
        if path.exists() and file_hash(path) == expected_hash:
            continue
        require(archive is not None and archive.is_relative_to(root), "Calibration source changed")
        archived = (archive / name).resolve()
        require(archived.is_relative_to(archive) and archived.is_file() and
                file_hash(archived) == expected_hash, "Archived Calibration source changed/missing")
    chosen = read_json(selection)
    verify_checkpoint(chosen)
    require(chosen["split"] == "calibration" and digest(chosen) == candidate["selection_sha256"],
            "Calibration selection differs")
    require(file_hash(local_path(root, candidate["config"]["qa_path"])) == chosen["qa_sha256"],
            "Calibration data changed")
    packet = read_json(run / "quality/final/packet.json")
    annotations_path = run / "quality/quality-annotations.ai.json"
    annotations = read_json(annotations_path)
    by_id = validate_annotations(packet, annotations)
    require(all(a["label"] != "pending" for a in by_id.values()), "Quality is not complete")
    provenance = read_json(run / "quality/assessment_manifest.json")
    verify_checkpoint(provenance)
    require(provenance["annotations_sha256"] == file_hash(annotations_path) and
            provenance["packet_sha256"] == packet["packet_sha256"] and
            provenance["human_reviewed"] is False, "Quality provenance differs")
    # Only after the quality gate above may private stage mappings/outcomes be read.
    mapping = read_json(run / "quality/final/mapping.private.json")
    verify_packet(packet, mapping)
    manifest = read_json(run / "internal/manifest.json")
    require(manifest["purpose"] == "phase11-calibration-not-final-evaluation" and
            manifest["selection_sha256"] == digest(chosen) and
            mapping["run_manifest_sha256"] == digest(manifest), "Calibration/quality run differs")
    private = read_json(run / "internal/report.private.json")
    require(private["manifest_sha256"] == digest(manifest), "Private report binding differs")
    records = private["records"]
    expected, tasks = {}, []
    for row in records:
        verify_checkpoint(row)
        require(row["pilot_manifest_sha256"] == digest(manifest), "Question binding differs")
        identifier = row["trace"]["record_id"]
        folder = run / "internal" / digest(identifier)[:24]
        require(read_json(folder / "completed.json") == row, "Question artifact changed")
        entries = [("claims.json", row["tasks"]["extraction"]), ("rewrite.json", row["rewrite"]),
                   *[(f"{key}.json", value) for key, value in row["tasks"]["judges"].items()]]
        for name, task in entries:
            verify_checkpoint(task)
            require(read_json(folder / name) == task, "Raw calibration task changed")
            tasks.append(task)
        expected[(identifier, "initial")] = (row, row["trace"]["answer"])
        if row["rewrite"]["status"] == "ok":
            expected[(identifier, "rewritten")] = (row, row["rewrite"]["answer"])
    labels, seen = {}, set()
    cases = {case["annotation_id"]: case for case in packet["cases"]}
    for anonymous, assignments in mapping["assignments"].items():
        for assignment in assignments:
            key = assignment["record_id"], assignment["stage"]
            require(key in expected and key not in seen, "Unknown/duplicate quality assignment")
            seen.add(key)
            row, answer = expected[key]
            case = cases[anonymous]
            require(case["answer"] == answer and case["question"] == row["trace"]["question"] and
                    case["documents"] == row["trace"]["documents"], "Quality assignment content differs")
            labels[key] = by_id[anonymous]["label"]
    require(seen == set(expected), "Missing quality assignment")
    report_path = run / "calibration_report.json"
    report = read_json(report_path)
    verify_checkpoint(report)
    require(report["manifest_sha256"] == digest(manifest) and report["analysis"] == reconstruct(records, labels),
            "Calibration analysis differs from sealed quality/raw outputs")
    baseline_path = run / "baseline/run_manifest.json"
    baseline = read_json(baseline_path)
    require(baseline["status"] == "completed" and baseline["split"] == "calibration" and
            baseline["selection_sha256"] == digest(chosen) and
            file_hash(baseline_path) == manifest["baseline_provenance_sha256"] and
            file_hash(run / "baseline/answers.jsonl") == manifest["baseline_answers_sha256"],
            "Baseline provenance changed")
    require({r["record_id"] for r in baseline["questions"]} ==
            {r["record_id"] for r in chosen["records"]}, "Baseline question set differs")
    return candidate, chosen, report, records, tasks, provenance


def parser_check(report, tasks):
    judges = [task for task in tasks if task["task"] == "verify_claims"]
    generated = [task for task in tasks if task.get("completion_attempted")]
    native = [task for task in generated if task.get("settings", {}).get("final_json_grammar")]
    return (report["health_gate"]["status"] == "passed" and bool(judges) and
            all(task["status"] == "ok" for task in judges) and
            all(task.get("error_code") != "input_overflow" and not task.get("cost_incomplete")
                for task in tasks) and
            all(native_check(task) for task in native))


def native_check(task):
    reasoning = task.get("reasoning_budget_audit") or {}
    grammar = task.get("final_grammar_audit") or {}
    size = reasoning.get("tokens_before_end_marker")
    return (type(size) is int and size >= 0 and
            reasoning.get("budget") == task["settings"]["reasoning_budget_tokens"] and
            size <= reasoning["budget"] + reasoning.get("budget_message_tokens", -100) + 2 and
            grammar.get("runtime_settings_verified") is True and grammar.get("trigger_text_verified") is True)


def semantic_check(audit, report_hash, records):
    require(audit["purpose"] == "phase11-semantic-audit" and
            audit["calibration_report_sha256"] == report_hash and audit["human_reviewed"] is False,
            "Semantic audit binding differs")
    required = {(row["trace"]["record_id"], claim["claim_id"]): row
                for row in records for claim in row["evaluation"]["claims"]}
    reviewed = set()
    for item in audit["claims"]:
        key = item["record_id"], item["claim_id"]
        require(key in required and key not in reviewed, "Unknown/duplicate semantic audit claim")
        require(item["expected_label"] in {"supported", "contradicted", "not_supported"} and
                isinstance(item["reason"], str) and item["reason"].strip(), "Invalid semantic review")
        for quote in item["evidence"]:
            require(any(quote["passage_id"] == doc["passage_id"] and quote["quote"] and
                        quote["quote"] in doc["text"] for doc in required[key]["trace"]["documents"]),
                    "Semantic evidence is not in used Context")
        require(item["expected_label"] == "not_supported" or bool(item["evidence"]),
                "Support/conflict review needs actual evidence")
        reviewed.add(key)
    return bool(required) and reviewed == set(required) and bool(audit["limitations"])


def runtime_check(runtime, protocol_hash, expected_model_hashes=None):
    # An nvidia-smi inventory or a CPU run cannot stand in for GPU inference/calibration.
    return (runtime.get("purpose") == "phase11-target-runtime-calibration" and
            runtime.get("backend") == "CUDA" and runtime.get("actual_gpu_offload") is True and
            type(runtime.get("offloaded_layers")) is int and runtime["offloaded_layers"] > 0 and
            bool(runtime.get("gpu_devices")) and
            type(runtime.get("completion_attempts")) is int and runtime["completion_attempts"] > 0 and
            runtime.get("protocol_sha256") == protocol_hash and
            runtime.get("native_audits_valid") is True and
            runtime.get("semantic_check_completed") is True and
            type(runtime.get("summed_step_seconds")) in {int, float} and
            math.isfinite(runtime["summed_step_seconds"]) and runtime["summed_step_seconds"] > 0 and
            bool(runtime.get("runtime_files_sha256")) and bool(runtime.get("model_files_sha256")) and
            (expected_model_hashes is None or set(runtime["model_files_sha256"].values()) == expected_model_hashes))


def runtime_output_check(root, runtime):
    for category in ("runtime_files_sha256", "model_files_sha256"):
        files = runtime.get(category)
        require(isinstance(files, dict) and files, "GPU Runtime/model files are not bound")
        for name, expected in files.items():
            require(file_hash(local_path(root, name)) == expected, "GPU Runtime/model file changed")
    probes = runtime.get("probe_tasks")
    require(isinstance(probes, list) and probes, "GPU Runtime needs saved native task evidence")
    for reference in probes:
        task = evidence(root, reference)
        require(task.get("completion_attempted") is True and task.get("status") == "ok" and
                not task.get("cost_incomplete") and native_check(task), "GPU native probe is not valid")
    require(runtime["completion_attempts"] == len(probes), "GPU probe count differs")
    log_reference = runtime["server_log"]
    log_path = local_path(root, log_reference["path"])
    require(file_hash(log_path) == log_reference["sha256"], "GPU server log changed")
    offloads = re.findall(r"offloaded\s+(\d+)/(\d+)\s+layers to GPU", log_path.read_text("utf-8"))
    require(any(int(actual) == runtime["offloaded_layers"] and int(actual) > 0
                for actual, total in offloads), "GPU offload was not confirmed in the native server log")
    return True


def analysis_check(spec):
    return (spec.get("primary") == "mean_within_question_pair_disagreement_difference" and
            spec.get("cluster") == "source_title" and
            spec.get("ci_method") == "paired_title_cluster_bootstrap" and
            type(spec.get("bootstrap_repetitions")) is int and spec["bootstrap_repetitions"] >= 1000 and
            spec.get("confidence_level") == 0.95 and type(spec.get("seed")) is int and
            spec["seed"] >= 0 and type(spec.get("evaluation_count")) is int and
            1 <= spec["evaluation_count"] <= 564 and
            spec.get("missing_policy") == "common_complete_for_decisions_all_selected_for_quality_cost" and
            spec.get("unknown_quality_policy") == "report_unknown_and_best_worst_bounds" and
            isinstance(spec.get("sample_size_rationale"), str) and bool(spec["sample_size_rationale"].strip()))


def evaluation_ids(split, count, seed):
    require(type(count) is int and count > 0 and type(seed) is int and seed >= 0,
            "Invalid Evaluation selection")
    identifiers = split["record_ids_by_split"]["evaluation"]
    require(len(identifiers) == len(set(identifiers)), "Duplicate Evaluation metadata ID")
    eligible = [key for key in identifiers if key.endswith(":answerable")]
    require(len(eligible) >= count, "Insufficient Answerable Evaluation IDs")
    return sorted(eligible, key=lambda key: hashlib.sha256(
                  f"{seed}:{key}".encode()).hexdigest())[:count]


def readiness(root, run, selection, decisions):
    require(decisions["schema_version"] == 1 and decisions["purpose"] == "phase11-freeze-decisions" and
            decisions["target_backend"] == "CUDA", "Unexpected freeze decision schema/target")
    require(set(decisions["reviews"]) == set(SECTIONS), "Missing/unknown Phase 11 review")
    checks = dict.fromkeys(["calibration_quality", "parser", *SECTIONS], False)
    reasons = {}
    try:
        archive = (local_path(root, decisions["calibration_source_archive"])
                   if decisions.get("calibration_source_archive") else None)
        candidate, chosen, report, records, tasks, provenance = verify_calibration(root, run, selection, archive)
    except (ValueError, KeyError, FileNotFoundError) as error:
        return {"gate11_passed": False, "phase12_allowed": False, "checks": checks,
                "reasons": {"calibration_quality": str(error)}, "conditions": None}
    checks["calibration_quality"] = True
    checks["parser"] = parser_check(report, tasks)
    report_hash = file_hash(run / "calibration_report.json")
    for name in SECTIONS:
        review = decisions["reviews"][name]
        if review.get("status") != "resolved" or not str(review.get("rationale", "")).strip():
            reasons[name] = "Review/decision is still pending"
            continue
        try:
            if name == "semantic_validity":
                audit = evidence(root, review["evidence"])
                checks[name] = semantic_check(audit, report_hash, records)
            elif name == "refusal_fallback":
                checks[name] = (review["action"] == "keep_initial_fallback" and
                                candidate["candidate_internal_protocol"]["decision"]["unscorable_action"] ==
                                "keep_initial_answer_with_separate_fallback_status")
            elif name == "external_quality":
                checks[name] = (review["human_reviewed"] is False and
                                review["exact_model_identifier"] == provenance["exact_model_identifier"] and
                                review["session_scope"] == provenance["session_scope"] and
                                bool(review["limitations"]))
            elif name == "runtime":
                runtime = evidence(root, review["evidence"])
                protocol_path = local_path(root, candidate["config"]["internal_protocol"])
                protocol = candidate["candidate_internal_protocol"]
                baseline_model = read_json(local_path(root, protocol["identity_manifest"]))["model"]
                auxiliary = read_json(local_path(root, protocol["auxiliary_model_manifest"]))
                model_hashes = {baseline_model["sha256"], *[entry["sha256"] for entry in auxiliary["files"]]}
                checks[name] = (runtime_check(runtime, file_hash(protocol_path), model_hashes) and
                                runtime_output_check(root, runtime))
            else:
                checks[name] = analysis_check(review["specification"])
            if not checks[name]:
                reasons[name] = "Evidence does not meet the declared gate"
        except (KeyError, ValueError, FileNotFoundError, TypeError) as error:
            reasons[name] = str(error)
    if not checks["parser"]:
        reasons["parser"] = "Execution/health/native parser gate has not passed"
    passed = all(checks.values())
    selected = None
    if passed:
        split_path = root / "data/manifests/clapnq_split_manifest.json"
        specification = decisions["reviews"]["analysis"]["specification"]
        selected = {"record_ids": evaluation_ids(read_json(split_path), specification["evaluation_count"],
                                                specification["seed"]),
                    "selection_rule": "sha256(seed:record_id)_ascending_before_Evaluation_outcomes",
                    "split_manifest_sha256": file_hash(split_path)}
    return {"gate11_passed": passed, "phase12_allowed": passed, "checks": checks, "reasons": reasons,
            "conditions": {"candidate_sha256": candidate["result_sha256"],
                           "selection_sha256": digest(chosen), "calibration_report_sha256": report_hash,
                           "decision_sha256": digest(decisions), "protocol": candidate["candidate_internal_protocol"],
                           "reviews": decisions["reviews"], "target_backend": "CUDA",
                           "evaluation_selection": selected,
                           "finalization_source_sha256": file_hash(Path(__file__)),
                           "research_source_sha256": {path.relative_to(root).as_posix(): file_hash(path)
                               for path in sorted((root / "src/rag_research").rglob("*.py"))}}}


def save_freeze(path, result):
    require(result["gate11_passed"] is True and result["phase12_allowed"] is True,
            "Phase 11 is not ready; no final manifest was written")
    require(result.get("checks") and all(result["checks"].values()) and
            result.get("conditions", {}).get("evaluation_selection", {}).get("record_ids"),
            "Final evidence/selection is incomplete")
    with run_lock(path.parent):
        value = {"schema_version": 1, "purpose": "phase11-final-condition-freeze", **result}
        if path.exists():
            saved = read_json(path)
            verify_checkpoint(saved)
            require({k: v for k, v in saved.items() if k != "result_sha256"} == value,
                    "Final conditions changed; never overwrite the freeze")
            return saved
        return checkpoint(path, value)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["review", "freeze"])
    parser.add_argument("--run", type=Path, default=ROOT / "data/runs/calibration/phase11-cpu-five-v1")
    parser.add_argument("--selection", type=Path,
                        default=ROOT / "data/manifests/phase11_calibration_selection_manifest.json")
    parser.add_argument("--decisions", type=Path, default=ROOT / "configs/phase11_freeze_decisions.json")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data/manifests/phase11_final_freeze.json")
    args = parser.parse_args()
    for path in (args.run, args.selection, args.decisions, args.output):
        require(path.resolve().is_relative_to(ROOT), "CLI path escapes repository")
    require(args.output.resolve().is_relative_to(ROOT / "data/manifests"), "Unexpected final manifest path")
    result = readiness(ROOT, args.run.resolve(), args.selection.resolve(), read_json(args.decisions))
    if args.stage == "freeze":
        save_freeze(args.output.resolve(), result)
    print(json.dumps({key: value for key, value in result.items() if key != "conditions"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
