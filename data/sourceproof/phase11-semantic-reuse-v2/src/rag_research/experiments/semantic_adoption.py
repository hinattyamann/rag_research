"""Versioned semantic adoption; preserve original three-label evidence and gates."""

from collections import defaultdict

import numpy as np

from rag_research.experiments.frozen_trace import require

LEGACY = "three-label-v1"
BINARY = "support-binary-v2"
COVERAGE = {"minimum_unique_supported_units": 10, "minimum_unique_negative_units": 5,
            "minimum_supported_groups": 3, "minimum_negative_groups": 3}
BINARY_RULES = {"minimum_supported_recall": .9, "minimum_negative_specificity": .9, **COVERAGE,
                "missing_class_or_insufficient_coverage": "fail_without_refill",
                "uncertainty": "document_group_bootstrap_10000_seed42"}
KNOWN_GATE_V2 = {"semantic_adoption_version": BINARY, "stop_on_task_error": True,
                 "stop_after_critical_failure": False, "complete_all_known_conditions_once": True,
                 **BINARY_RULES}


def version(value):
    result = value.get("semantic_adoption_version", LEGACY)
    require(result in {LEGACY, BINARY}, "Unknown semantic adoption version")
    return result


def validate_binary_rules(rules):
    require(all(k in rules and type(rules[k]) is type(v) and rules[k] == v
                for k, v in BINARY_RULES.items()), "Preserve preregistered binary adoption rules")


def summarize(observations, *, healthy):
    """Rows are (document group, unique unit ID, Expected, actual).

    Every planned order/repetition remains a row, including missing outcomes.
    Coverage counts units/groups once. CIs resample entire document groups.
    """
    units = {"supported": set(), "negative": set()}
    groups = {"supported": set(), "negative": set()}
    totals = defaultdict(int)
    clustered = defaultdict(lambda: np.zeros(4, dtype=np.int64))
    for group, unit, truth, actual in observations:
        require(truth in {"supported", "contradicted", "not_supported", "ambiguous", None},
                "Unknown Expected label")
        require(actual in {"supported", "contradicted", "not_supported", None}, "Unknown actual label")
        if truth in {"ambiguous", None}:
            totals["ambiguous_unit_conditions_retained_in_F"] += 1
            continue
        label = "supported" if truth == "supported" else "negative"
        units[label].add((group, unit))
        groups[label].add(group)
        totals[label + "_denominator"] += 1
        totals["exact_correct"] += actual == truth
        totals["missing_outcomes"] += actual is None
        correct = actual == "supported" if label == "supported" else actual in {"contradicted", "not_supported"}
        totals[label + "_correct"] += correct
        totals["false_support_count"] += label == "negative" and actual == "supported"
        totals["missed_support_count"] += label == "supported" and actual in {"contradicted", "not_supported"}
        totals["C_NS_confusion_count"] += label == "negative" and actual in {"contradicted", "not_supported"} and actual != truth
        offset = 0 if label == "supported" else 2
        clustered[group][offset] += correct
        clustered[group][offset + 1] += 1
    healthy = bool(healthy and not totals["missing_outcomes"])
    result = {"semantic_adoption_version": BINARY, "healthy": healthy, **{k: totals[k] for k in (
        "supported_denominator", "negative_denominator", "supported_correct", "negative_correct", "exact_correct",
        "missing_outcomes", "false_support_count", "missed_support_count", "C_NS_confusion_count",
        "ambiguous_unit_conditions_retained_in_F")},
        "unique_supported_units": len(units["supported"]), "unique_negative_units": len(units["negative"]),
        "supported_groups": len(groups["supported"]), "negative_groups": len(groups["negative"])}
    for label, key in (("supported", "supported_recall"), ("negative", "negative_specificity")):
        denominator = totals[label + "_denominator"]
        result[key] = totals[label + "_correct"] / denominator if healthy and denominator else None
    denominator = totals["supported_denominator"] + totals["negative_denominator"]
    result["three_label_accuracy"] = totals["exact_correct"] / denominator if healthy and denominator else None
    result["binary_accuracy"] = (totals["supported_correct"] + totals["negative_correct"]) / denominator if healthy and denominator else None
    result["coverage_passed"] = all(result[k.removeprefix("minimum_")] >= v for k, v in COVERAGE.items())
    result["passed"] = bool(healthy and result["coverage_passed"] and
                            result["supported_recall"] is not None and result["supported_recall"] >= .9 and
                            result["negative_specificity"] is not None and result["negative_specificity"] >= .9)
    intervals = {}
    if healthy and len(clustered) >= 2:
        matrix = np.array([clustered[g] for g in sorted(clustered)])
        rng = np.random.default_rng(42)
        samples = matrix[rng.integers(0, len(matrix), size=(10000, len(matrix)))].sum(axis=1)
        for key, offset in (("supported_recall", 0), ("negative_specificity", 2)):
            valid = samples[:, offset + 1] > 0
            values = samples[valid, offset] / samples[valid, offset + 1]
            intervals[key] = {"ci95": np.quantile(values, [.025, .975]).tolist() if len(values) else None,
                              "valid_replicates": int(valid.sum()), "missing_class_replicates": int((~valid).sum())}
    result["group_bootstrap"] = {"unit": "document_group", "groups": len(clustered), "repetitions": 10000,
                                 "seed": 42, "metrics": intervals,
                                 "conditional_on_observed_groups_not_population_error_guarantee": True}
    return result
