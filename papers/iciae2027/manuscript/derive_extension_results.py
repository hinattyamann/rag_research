"""Reconcile sealed extension batches for bilingual manuscript revision.

The extension's saved bootstrap results are reused without interval estimation.
Only the three new batches are aggregated; old Main/Cal records are inspected
solely to reject overlap. Order/quality classes reuse the canonical trial-plan
validator in derive_order_effects.py, never the convenience group flags.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
DEFAULT_MATERIALS = PAPER / "materials/cal_extension_v1"
DEFAULT_OUTPUT = PAPER / "notes/extension_results_v1.json"
SOURCE_COMMIT = "7beb396febd2842248af53a8ec39eda9fc153153"
BATCHES = ("batch_01", "batch_02", "batch_03")
LANGUAGES = ("en", "ja")
ROUTES = ("no_repair", "original", "always_rewrite")

SPEC = importlib.util.spec_from_file_location(
    "extension_order_effects", HERE / "derive_order_effects.py"
)
ORDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORDER)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def summarize(questions, language):
    selected = [q for q in questions if q["language"] == language]
    comparable = [q for q in selected if q["comparable"]]
    counts = Counter(q["classification"] for q in comparable)
    varying = [q for q in comparable if q["decision_varies_in_valid_orders"]]
    return {
        "cohort": "ext",
        "language": language,
        "selected_qa": len(selected),
        "comparable_qa": len(comparable),
        "excluded_qa": len(selected) - len(comparable),
        "exclusion_reasons": dict(
            sorted(Counter(q["exclusion_reason"] for q in selected if not q["comparable"]).items())
        ),
        "classification_counts": {category: counts[category] for category in ORDER.CLASSES},
        "decision_change_qa": len(varying),
        "comparable_qa_with_unknown_selected_y": sum(
            q["has_unknown_selected_y_in_valid_orders"] for q in comparable
        ),
        "selected_qa_with_failed_rewrite": sum(q["rewrite_status"] == "error" for q in selected),
        "comparable_qa_with_failed_rewrite": sum(
            q["rewrite_status"] == "error" for q in comparable
        ),
        "omitted_duplicate_order_slots": sum(
            len(q["omitted_duplicate_order_aliases"]) for q in selected
        ),
        "decision_change_qa_keys": [q["qa_key"] for q in varying],
        "quality_change_qa_keys": [
            q["qa_key"]
            for q in comparable
            if q["classification"] == "decision_change_quality_changes"
        ],
        "decision_change_qa_with_varying_calls": sum(
            q["known_route_cost_range"]["recorded_calls"]["min"]
            != q["known_route_cost_range"]["recorded_calls"]["max"]
            for q in varying
        ),
        "decision_change_qa_with_varying_tokens": sum(
            q["known_route_cost_range"]["recorded_input_plus_output_tokens"]["min"]
            != q["known_route_cost_range"]["recorded_input_plus_output_tokens"]["max"]
            for q in varying
        ),
    }


def derive(materials=DEFAULT_MATERIALS):
    materials = Path(materials)
    hashes = {}

    def read_bytes(relative):
        content = (materials / relative).read_bytes()
        hashes[relative] = hashlib.sha256(content).hexdigest()
        return content

    def read_json(relative):
        return json.loads(read_bytes(relative))

    def read_csv(relative):
        return list(csv.DictReader(read_bytes(relative).decode("utf-8").splitlines()))

    completion = read_json("completion.json")
    require(completion["completed_batches"] == list(BATCHES), "Extension is not complete")
    require(completion["uncollected_or_unsealed_qa"] == 0, "Unsealed extension QA remain")
    pooled = read_json("pooled_new_extension.json")
    require(pooled["completed_batches"] == list(BATCHES), "Pooled batch list differs")
    require(pooled["included_selected_qa"] == 120, "Pooled selection count differs")
    require(pooled["conditional_on_completed_batches"] is False, "Partial collection")
    method = read_json("analysis_method.json")
    questions, batch_summary, summaries, policies = [], [], [], []
    source_rows = Counter()
    missing_references = {}
    annotation_provenance = []
    for batch in BATCHES:
        result = ORDER.derive(materials / batch)
        result_definitions = result["definitions"]
        for relative, digest in result["source_sha256"].items():
            hashes[f"{batch}/{relative}"] = digest
        for name, count in result["source_rows"].items():
            source_rows[name] += count
        for question in result["questions"]:
            require(question["cohort"] == "cal", "Unexpected source cohort")
            question = dict(question)
            question.update(batch=batch, source_cohort="cal", cohort="ext")
            questions.append(question)
        summary = read_json(f"{batch}/published_results/cal_summary.json")
        summaries.append(summary)
        batch_summary.append(
            {
                "batch": batch,
                "strata": [s for s in result["strata"] if s["cohort"] == "cal"],
                "saved_statistics": summary["statistics"],
                "source_rows": result["source_rows"],
            }
        )
        policies.extend(read_csv(f"{batch}/policy_outcomes.csv"))
        missing = read_json(f"{batch}/missing_information.json")
        for item in missing["unavailable_reference_bodies"]:
            key = (item["language"], item["record_id"], item["source_reference_unit_id"])
            missing_references[key] = item
        job_root = materials / batch / "provenance/annotation_jobs"
        for path in sorted(job_root.glob("*/attempt-*/provenance.json")):
            relative = path.relative_to(materials).as_posix()
            provenance = read_json(relative)
            invocation = read_json(relative.replace("provenance.json", "invocation.json"))
            annotation_provenance.append(
                {
                    "batch": batch,
                    "path": relative,
                    "configured_model": provenance.get("configured_model"),
                    "exact_model_identifier": provenance.get("exact_model_identifier"),
                    "input_transport": provenance.get("input_transport"),
                    "human_reviewed": provenance.get("human_reviewed"),
                    "history_independence_not_assumed": provenance.get(
                        "history_independence_not_assumed"
                    ),
                    "finished_at_utc": provenance.get("finished_at_utc"),
                    "exit_code": invocation["exit_code"],
                    "high_reasoning_requested": 'model_reasoning_effort="high"'
                    in invocation["argv"],
                }
            )

    questions.sort(key=lambda q: (LANGUAGES.index(q["language"]), q["batch"], q["qa_key"]))
    for field in ("qa_key", "record_id"):
        require(
            len({q[field] for q in questions}) == len(questions), f"Duplicate extension {field}"
        )
    for language in LANGUAGES:
        groups = [q["document_group_id"] for q in questions if q["language"] == language]
        require(len(groups) == len(set(groups)), "Extension document group repeated")
    old_path = PAPER / "materials/fixed_v23_v1/qa_summary.csv"
    old_content = old_path.read_bytes()
    old_rows = list(csv.DictReader(old_content.decode("utf-8").splitlines()))
    old_records = {r["record_id"] for r in old_rows}
    old_groups = {(r["language"], r["document_group_id"]) for r in old_rows}
    require(not old_records & {q["record_id"] for q in questions}, "Old/new record overlap")
    require(
        not old_groups & {(q["language"], q["document_group_id"]) for q in questions},
        "Old/new document-group overlap",
    )

    strata = [summarize(questions, language) for language in LANGUAGES]
    saved_statistics = {key: value for key, value in pooled["statistics"].items() if key != "qa"}
    for stratum in strata:
        language = stratum["language"]
        saved = saved_statistics["languages"][language]
        require(saved["selected_qa_count"] == stratum["selected_qa"], "Selected count differs")
        require(
            saved["comparable_qa_count"] == stratum["comparable_qa"], "Comparable count differs"
        )
        saved_qa = [
            q for q in pooled["statistics"]["qa"] if q["language"] == language and q["comparable"]
        ]
        require(
            math.isclose(
                sum(q["increment"] for q in saved_qa) / len(saved_qa),
                saved["mean_increment"],
                abs_tol=1e-12,
            ),
            "Saved QA-weighted point estimate differs",
        )
        derived_by_record = {q["record_id"]: q for q in questions if q["language"] == language}
        for row in [q for q in pooled["statistics"]["qa"] if q["language"] == language]:
            question = derived_by_record[row["record_id"]]
            require(row["comparable"] == question["comparable"], "QA comparability differs")
            if row["comparable"]:
                require(
                    (row["order"]["disagreeing_pairs"] > 0)
                    == question["decision_varies_in_valid_orders"],
                    "Saved order disagreement differs from canonical trials",
                )

    quality = []
    for row in read_csv("pooled/quality_and_operational_cost.csv"):
        if row["route"] in ROUTES:
            result = dict(row)
            for key in row.keys() - {"cohort", "language", "route"}:
                result[key] = int(row[key])
            result["cohort"] = "ext"
            result["input_plus_output_tokens"] = (
                result["input_tokens_sum"] + result["output_tokens_sum"]
            )
            quality.append(result)
    selection, semantics = [], []
    for language in LANGUAGES:
        selected = [q for q in questions if q["language"] == language]
        known = [
            q
            for q in selected
            if q["rewrite_status"] == "ok" and None not in q["candidate_y"].values()
        ]
        transitions = Counter(f"{q['candidate_y']['A']}->{q['candidate_y']['B']}" for q in known)
        rows = [p for p in policies if p["language"] == language]
        oe = [p for p in rows if p["route"] == "original"]
        ar = [p for p in rows if p["route"] == "always_rewrite"]
        require(len(oe) == len(ar) == len(selected), "Operational-route mapping differs")
        known_keys = {q["qa_key"] for q in known}
        oe_known = [p for p in oe if p["qa_key"] in known_keys]
        ar_known = [p for p in ar if p["qa_key"] in known_keys]
        selection.append(
            {
                "language": language,
                "known_pairs": len(known),
                "unknown_transitions": len(selected) - len(known),
                "transitions": {key: transitions[key] for key in ("0->0", "0->1", "1->0", "1->1")},
                "oe_missed_improvements": sum(
                    ORDER.boolean(p["missed_improvement"]) for p in oe_known
                ),
                "oe_harmful_rewrites": sum(ORDER.boolean(p["harmful_rewrite"]) for p in oe_known),
                "ar_harmful_rewrites": sum(ORDER.boolean(p["harmful_rewrite"]) for p in ar_known),
            }
        )
        negative = sum(
            s["semantics"][language]["planned_definite_negative_unit_conditions"] for s in summaries
        )
        false_support = sum(s["semantics"][language]["false_support_count"] for s in summaries)
        semantics.append(
            {
                "language": language,
                "negative_unit_conditions": negative,
                "false_support_count": false_support,
                "false_support_rate": false_support / negative,
                "unique_negative_units": sum(
                    s["semantics"][language]["binary_adoption"]["unique_negative_units"]
                    for s in summaries
                ),
                "no_unit_qa": sum(s["semantics"][language]["no_unit_qa"] for s in summaries),
                "scope": "Repeated sentence-by-condition observations; saved external AI expected labels, not human ground truth",
            }
        )

    thresholds = read_csv("pooled/threshold_sensitivity.csv")
    collection_cost = read_csv("pooled/collection_cost.csv")
    annotation_cost = read_json("annotation_cost.json")
    return {
        "version": "sealed-extension-manuscript-reconciliation-v1",
        "source_materials_commit": SOURCE_COMMIT,
        "scope": "New sealed extension batches only. Old Main/Cal are excluded from every aggregate",
        "definitions": {
            **result_definitions,
            "pooling": "Three new batches only, as specified before collection in cal_extension_protocol_v1; no old/new pooling",
            "statistics": "Saved NumPy 2.5.3, SeedSequence(seed=42).spawn(2) en/ja, 10000-group-bootstrap point estimates and intervals reused without new interval estimation",
            "post_outcome_analysis": "Order-to-selected-quality counts are a descriptive extension of the earlier post-outcome analysis, not a new primary hypothesis test",
            "selection": "Known binary labels for both A and successful B are required for improvement/harm transitions; failed and indeterminate outcomes remain in operational route quality",
            "annotation": "Configured model aliases and client requests do not identify an exact serving snapshot; no human validation or complete history independence is asserted",
        },
        "old_new_overlap_audit": {
            "old_qa_summary_sha256": hashlib.sha256(old_content).hexdigest(),
            "old_rows": len(old_rows),
            "record_overlap": 0,
            "document_group_overlap": 0,
        },
        "source_sha256": dict(sorted(hashes.items())),
        "source_rows": dict(source_rows),
        "strata": strata,
        "batch_summary": batch_summary,
        "saved_statistics": saved_statistics,
        "quality": quality,
        "selection": selection,
        "semantics": semantics,
        "threshold": thresholds,
        "collection_cost": collection_cost,
        "annotation_cost": annotation_cost,
        "annotation_provenance": annotation_provenance,
        "missing_reference_bodies": [missing_references[key] for key in sorted(missing_references)],
        "analysis_method": method,
        "questions": questions,
        "new_inference_calls": 0,
        "new_annotation_calls": 0,
        "new_confidence_intervals": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materials", type=Path, default=DEFAULT_MATERIALS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = derive(args.materials)
    if args.check:
        require(
            json.loads(args.output.read_text(encoding="utf-8")) == result,
            "Saved extension results differ",
        )
    else:
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result["strata"], ensure_ascii=False))


if __name__ == "__main__":
    main()
