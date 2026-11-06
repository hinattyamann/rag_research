"""Reconcile saved order effects against candidate annotations and trial plans."""

import copy
import csv
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("order_effects", HERE / "derive_order_effects.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
MATERIALS = HERE.parent / "materials/fixed_v23_v1"


def read_csv(name):
    with (MATERIALS / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


@pytest.fixture(scope="module")
def result():
    return MODULE.derive()


def test_frozen_sources_and_saved_result(result):
    saved = json.loads((HERE.parent / "notes/order_effects_v1.json").read_text(encoding="utf-8"))
    assert result == saved
    assert result["source_rows"] == {"qa_summary": 80, "trials": 706, "policy_slots": 880}
    for name, expected in result["source_sha256"].items():
        assert hashlib.sha256((MATERIALS / name).read_bytes()).hexdigest() == expected
    assert len([n for n in result["source_sha256"] if n.startswith("inputs/")]) == 80


def test_independent_candidate_selection_reconciliation(result):
    """Use trial decisions and A/B annotations, not exported selected-Y values."""
    qa_rows = read_csv("qa_summary.csv")
    trials = [
        json.loads(line)
        for line in (MATERIALS / "trials.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    trial_lookup = {(t["qa_key"], t["trial_id"]): t for t in trials}
    derived = {q["qa_key"]: q for q in result["questions"]}
    oracle_counts = Counter()
    for row in qa_rows:
        actual = derived[row["qa_key"]]
        if row["comparable"] != "True":
            assert actual["classification"] == "excluded_primary"
            continue
        source = json.loads((MATERIALS / row["input_path"]).read_text(encoding="utf-8"))
        order_ids = source["trial_plan"]["order_group"]
        decisions, labels = [], []
        for trial_id in order_ids:
            trial = trial_lookup[row["qa_key"], trial_id]
            assert trial["status"] == "ok"
            decisions.append(trial["decision"])
            candidate = (
                source["B"]
                if trial["decision"] == "rewrite" and source["B"]["status"] == "ok"
                else source["A"]
            )
            labels.append((candidate.get("quality") or {}).get("y"))
        if len(set(decisions)) < 2:
            expected = "no_decision_change"
        elif any(label is None for label in labels):
            expected = "decision_change_quality_unknown"
        elif min(labels) != max(labels):
            expected = "decision_change_quality_changes"
        else:
            expected = "decision_change_same_binary_quality"
        assert actual["classification"] == expected
        assert actual["valid_unique_order_trial_ids"] == order_ids
        assert actual["decision_varies_in_valid_orders"] == (row["order_varies"] == "True")
        assert len(actual["order_routes"]) == len(order_ids)
        assert not set(actual["omitted_duplicate_order_aliases"]) & set(order_ids)
        assert all(not name.startswith("repeat_") for name in order_ids)
        oracle_counts[row["cohort"], row["language"], expected] += 1
    for summary in result["strata"]:
        for category, count in summary["classification_counts"].items():
            assert count == oracle_counts[summary["cohort"], summary["language"], category]
        assert sum(summary["classification_counts"].values()) == summary["comparable_qa"]
        assert summary["selected_qa"] == summary["comparable_qa"] + summary["excluded_qa"]
        assert sum(summary["exclusion_reasons"].values()) == summary["excluded_qa"]
    assert [s["comparable_qa"] for s in result["strata"]] == [16, 13, 16, 12]
    assert [s["decision_change_qa"] for s in result["strata"]] == [3, 1, 5, 2]


@pytest.mark.parametrize(
    ("decisions", "labels", "expected"),
    [
        (["accept", "rewrite"], [0, 1], "decision_change_quality_changes"),
        (["accept", "rewrite"], [1, 1], "decision_change_same_binary_quality"),
        (["accept", "rewrite"], [0, None], "decision_change_quality_unknown"),
        (["accept", "rewrite", "rewrite"], [0, 1, None], "decision_change_quality_unknown"),
        (["accept", "accept"], [None, None], "no_decision_change"),
    ],
)
def test_exclusive_unknown_priority(decisions, labels, expected):
    assert MODULE.quality_class(decisions, labels) == expected


def fixture_question():
    row = next(
        r for r in read_csv("qa_summary.csv") if r["qa_key"] == "main_en_077f873a5422561eb7efb581"
    )
    source = json.loads((MATERIALS / row["input_path"]).read_text(encoding="utf-8"))
    trials = [
        json.loads(line)
        for line in (MATERIALS / "trials.jsonl").read_text(encoding="utf-8").splitlines()
        if json.loads(line)["qa_key"] == row["qa_key"]
    ]
    policies = [r for r in read_csv("policy_outcomes.csv") if r["qa_key"] == row["qa_key"]]
    return row, source, trials, policies


def test_failed_rewrite_retains_actual_a_not_unknown_or_harm():
    row, source, trials, policies = fixture_question()
    row["order_varies"], row["rewrite_status"], row["B_y"] = "True", "error", ""
    source["B"]["status"] = "error"
    source["B"]["quality"] = None
    first = source["trial_plan"]["order_group"][0]
    trial = next(t for t in trials if t["trial_id"] == first)
    trial["decision"], trial["score"] = "rewrite", 0.0
    policy = next(p for p in policies if p["route"] == first)
    policy["rewrite_requested"], policy["fallback"] = "True", "rewrite_failed"
    # A was already the selected candidate; its known Y=1 is kept.
    actual = MODULE.summarize_question(row, source, trials, policies)
    assert actual["classification"] == "decision_change_same_binary_quality"
    assert actual["selected_binary_y_values"] == [1]
    assert actual["selected_answer_varies_in_valid_orders"] is False
    assert actual["has_unknown_selected_y_in_valid_orders"] is False


def test_unknown_costs_remain_unknown_not_zero():
    row, source, trials, policies = fixture_question()
    policy = next(p for p in policies if p["route"] == "original")
    policy["recorded_completion_attempts"] = ""
    policy["input_tokens"] = ""
    policy["output_tokens"] = ""
    policy["unknown_outcome_steps"] = "1"
    policy["incomplete"] = "True"
    actual = MODULE.summarize_question(row, source, trials, policies)
    route = next(r for r in actual["order_routes"] if r["trial_id"] == "original")
    assert route["recorded_calls"] is None
    assert route["known_input_plus_output_tokens"] is None
    costs = actual["known_route_cost_range"]
    assert costs["recorded_calls"]["unknown_routes"] == 1
    assert costs["recorded_input_plus_output_tokens"]["unknown_routes"] == 1
    assert costs["recorded_calls"]["min"] > 0
    assert costs["incomplete_routes"] == costs["routes_with_unknown_outcome_steps"] == 1


def test_inconsistent_selected_quality_is_an_integrity_error():
    row, source, trials, policies = fixture_question()
    policy = next(p for p in policies if p["route"] == "original")
    policy["quality_y"] = "0"
    with pytest.raises(ValueError, match="Selected quality differs"):
        MODULE.summarize_question(row, source, trials, policies)


def test_group_flags_do_not_select_orders_and_missing_policy_is_rejected():
    row, source, trials, policies = fixture_question()
    baseline = MODULE.summarize_question(row, source, trials, policies)
    altered = copy.deepcopy(trials)
    for trial in altered:
        trial["in_order_group"] = True
        trial["in_repeat_group"] = True
    actual = MODULE.summarize_question(row, source, altered, policies)
    assert actual["classification"] == baseline["classification"]
    assert actual["valid_unique_order_trial_ids"] == baseline["valid_unique_order_trial_ids"]
    # An absent observed route is an integrity error, never a zero-quality result.
    incomplete = [p for p in policies if p["route"] != "original"]
    with pytest.raises(ValueError, match="lacks an observed route"):
        MODULE.summarize_question(row, source, trials, incomplete)


def test_duplicate_rows_cannot_inflate_denominator():
    row, source, trials, policies = fixture_question()
    with pytest.raises(ValueError, match="Duplicate trial_id"):
        MODULE.summarize_question(row, source, trials + [copy.deepcopy(trials[0])], policies)
