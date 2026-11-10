"""Audit extension claims against sealed candidate labels and trial plans."""

import csv
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "extension_results", HERE / "derive_extension_results.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
MATERIALS = HERE.parent / "materials/cal_extension_v1"


@pytest.fixture(scope="module")
def result():
    return MODULE.derive()


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_saved_extension_reconciles_frozen_sources(result):
    saved = json.loads(
        (HERE.parent / "notes/extension_results_v1.json").read_text(encoding="utf-8")
    )
    assert result == saved
    assert result["source_rows"] == {"qa_summary": 120, "trials": 1072, "policy_slots": 1320}
    for name, digest in result["source_sha256"].items():
        assert hashlib.sha256((MATERIALS / name).read_bytes()).hexdigest() == digest
    assert len(result["questions"]) == 120
    assert len({q["qa_key"] for q in result["questions"]}) == 120
    assert len({q["record_id"] for q in result["questions"]}) == 120
    assert result["old_new_overlap_audit"]["record_overlap"] == 0
    assert result["old_new_overlap_audit"]["document_group_overlap"] == 0
    assert result["new_inference_calls"] == result["new_annotation_calls"] == 0
    assert result["new_confidence_intervals"] is False


def test_canonical_orders_independently_select_saved_candidate_labels(result):
    """Derive classification from A/B and trial decisions, without policy Y or flags."""
    by_key = {q["qa_key"]: q for q in result["questions"]}
    counts = Counter()
    for batch in MODULE.BATCHES:
        qa = read_csv(MATERIALS / batch / "qa_summary.csv")
        trials = [
            json.loads(line)
            for line in (MATERIALS / batch / "trials.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        trial_index = {(t["qa_key"], t["trial_id"]): t for t in trials}
        for row in qa:
            actual = by_key[row["qa_key"]]
            source = json.loads((MATERIALS / batch / row["input_path"]).read_text(encoding="utf-8"))
            if row["comparable"] != "True":
                assert actual["classification"] == "excluded_primary"
                assert len(source["fixed_claims"]) == 0
                continue
            decisions, labels = [], []
            for trial_id in source["trial_plan"]["order_group"]:
                trial = trial_index[row["qa_key"], trial_id]
                assert trial["status"] == "ok"
                decisions.append(trial["decision"])
                candidate = (
                    source["B"]
                    if trial["decision"] == "rewrite" and source["B"]["status"] == "ok"
                    else source["A"]
                )
                labels.append((candidate.get("quality") or {}).get("y"))
            if len(set(decisions)) == 1:
                expected = "no_decision_change"
            elif None in labels:
                expected = "decision_change_quality_unknown"
            elif len(set(labels)) == 2:
                expected = "decision_change_quality_changes"
            else:
                expected = "decision_change_same_binary_quality"
            assert actual["classification"] == expected
            counts[row["language"], expected] += 1
    for stratum in result["strata"]:
        for label, expected in stratum["classification_counts"].items():
            assert counts[stratum["language"], label] == expected
    assert [s["comparable_qa"] for s in result["strata"]] == [48, 43]
    assert [s["decision_change_qa"] for s in result["strata"]] == [6, 9]
    assert [
        s["classification_counts"]["decision_change_quality_unknown"] for s in result["strata"]
    ] == [2, 2]


def test_selection_claims_use_known_successful_pairs(result):
    """Check miss/harm from A/B truth and actual selected stages, not saved flags."""
    counts = {language: Counter() for language in MODULE.LANGUAGES}
    for batch in MODULE.BATCHES:
        qa = {q["qa_key"]: q for q in read_csv(MATERIALS / batch / "qa_summary.csv")}
        for policy in read_csv(MATERIALS / batch / "policy_outcomes.csv"):
            if policy["route"] not in {"original", "always_rewrite"}:
                continue
            row = qa[policy["qa_key"]]
            if (
                row["rewrite_status"] != "ok"
                or row["A_y"] not in {"0", "1"}
                or row["B_y"] not in {"0", "1"}
            ):
                continue
            counter = counts[row["language"]]
            if policy["route"] == "original":
                counter["known_pairs"] += 1
                counter["oe_missed_improvements"] += (
                    row["A_y"] == "0"
                    and row["B_y"] == "1"
                    and policy["selected_stage"] == "initial"
                )
                counter["oe_harmful_rewrites"] += (
                    row["A_y"] == "1"
                    and row["B_y"] == "0"
                    and policy["selected_stage"] == "rewritten"
                )
            else:
                counter["ar_harmful_rewrites"] += (
                    row["A_y"] == "1"
                    and row["B_y"] == "0"
                    and policy["selected_stage"] == "rewritten"
                )
    for summary in result["selection"]:
        for metric in (
            "known_pairs",
            "oe_missed_improvements",
            "oe_harmful_rewrites",
            "ar_harmful_rewrites",
        ):
            assert summary[metric] == counts[summary["language"]][metric]
    assert [s["known_pairs"] for s in result["selection"]] == [55, 49]
    assert [s["oe_harmful_rewrites"] for s in result["selection"]] == [1, 0]
    assert [s["ar_harmful_rewrites"] for s in result["selection"]] == [1, 2]


def test_saved_intervals_and_annotation_uncertainty_are_retained(result):
    pooled = json.loads((MATERIALS / "pooled_new_extension.json").read_text(encoding="utf-8"))
    assert result["saved_statistics"] == {
        k: v for k, v in pooled["statistics"].items() if k != "qa"
    }
    jobs = result["annotation_provenance"]
    assert len(jobs) == 120
    assert all(
        j["configured_model"] == "gpt-6.1-sol" and j["high_reasoning_requested"] for j in jobs
    )
    assert all(j["exact_model_identifier"] is None and j["human_reviewed"] is False for j in jobs)
    assert all(j["input_transport"] == "inline_citations_v3" and j["exit_code"] == 0 for j in jobs)
    assert {r["record_id"] for r in result["missing_reference_bodies"]} == {
        "whrja:02e85c8:answered:235",
        "whrja:02e85c8:answered:686",
    }
    assert [
        (s["false_support_count"], s["negative_unit_conditions"]) for s in result["semantics"]
    ] == [(218, 494), (245, 520)]
