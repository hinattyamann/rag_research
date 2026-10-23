"""Binary adoption boundaries, class coverage and clustered uncertainty."""

from copy import deepcopy

import pytest

from rag_research.experiments import semantic_adoption as adoption
from rag_research.experiments.bilingual_main import REQUIRED_MAIN_POLICY, validate_main_policy


def observations(*, positive_errors=0, negative_errors=0, confusion=False, repeats=1):
    return [(f"g{i % 4}", str(i), truth,
             ("not_supported" if i < positive_errors else "supported") if truth == "supported" else
             ("supported" if i - 10 < negative_errors else "not_supported" if confusion else truth))
            for i in range(20) for _ in range(repeats)
            for truth in ["supported" if i < 10 else "contradicted"]]


@pytest.mark.parametrize("positive,negative,passed", [(0, 0, True), (1, 1, True), (2, 0, False), (0, 2, False)])
def test_symmetric_error_thresholds_and_full_three_label_reporting(positive, negative, passed):
    result = adoption.summarize(observations(positive_errors=positive, negative_errors=negative, confusion=True), healthy=True)
    assert result["passed"] is passed
    assert result["supported_recall"] == (10 - positive) / 10
    assert result["negative_specificity"] == (10 - negative) / 10
    assert result["C_NS_confusion_count"] == 10 - negative
    assert result["three_label_accuracy"] < result["binary_accuracy"]


@pytest.mark.parametrize("kind", ["all_positive", "all_negative", "one_group", "duplicated_units"])
def test_repeated_orders_cannot_supply_missing_classes_or_unique_coverage(kind):
    rows = observations()
    if kind == "all_positive":
        rows = [row for row in rows if row[2] == "supported"]
    elif kind == "all_negative":
        rows = [row for row in rows if row[2] != "supported"]
    elif kind == "one_group":
        rows = [("one", *r[1:]) for r in rows]
    else:
        rows = [rows[0], rows[-1]] * 100
    result = adoption.summarize(rows, healthy=True)
    assert not result["passed"] and not result["coverage_passed"]
    if kind == "all_positive":
        assert result["negative_specificity"] is None
    if kind == "all_negative":
        assert result["supported_recall"] is None


def test_unknown_health_and_ambiguity_do_not_become_non_support_or_zero_cost():
    rows = observations() + [("ambiguous", "u", None, "supported")]
    result = adoption.summarize(rows, healthy=False)
    assert not result["passed"] and result["supported_recall"] is None
    assert result["ambiguous_unit_conditions_retained_in_F"] == 1
    result = adoption.summarize(rows + [("g0", "u2", "contradicted", None)], healthy=True)
    assert not result["passed"] and result["negative_specificity"] is None and result["missing_outcomes"] == 1


def test_bootstrap_resamples_groups_without_narrowing_from_identical_repetitions():
    one = adoption.summarize(observations(positive_errors=1), healthy=True)
    repeated = adoption.summarize(observations(positive_errors=1, repeats=9), healthy=True)
    assert one["group_bootstrap"] == repeated["group_bootstrap"]
    assert one["unique_supported_units"] == repeated["unique_supported_units"] == 10
    assert repeated["supported_denominator"] == 90


def binary_policy():
    policy = deepcopy(REQUIRED_MAIN_POLICY)
    policy["semantic_adoption_version"] = adoption.BINARY
    rules = policy["semantic_adoption_after_blind_seal"]
    for key in ("minimum_exact_label_accuracy_per_language", "minimum_supported_label_accuracy_per_language",
                "maximum_definite_negative_false_support"):
        rules.pop(key)
    rules.update(adoption.BINARY_RULES, comparison_minimum_reason="Prior feasibility requirement")
    return policy


def test_policy_version_selects_explicit_binary_rules_and_retains_legacy_rejection():
    policy = binary_policy()
    validate_main_policy(policy)
    policy.pop("semantic_adoption_version")
    with pytest.raises(ValueError):
        validate_main_policy(policy)
    policy = binary_policy()
    policy["semantic_adoption_after_blind_seal"]["minimum_negative_specificity"] = .89
    with pytest.raises(ValueError):
        validate_main_policy(policy)
    policy["semantic_adoption_version"] = "unknown"
    with pytest.raises(ValueError):
        validate_main_policy(policy)
