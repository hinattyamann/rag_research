"""QA pair denominators, missingness and independently sampled whole-document groups."""

from copy import deepcopy

import numpy as np
import pytest

from rag_research.experiments.statistics import analyze, grouped_means, qa_increment


def evaluation(kind="positive", single=False):
    orders = ["original"] if single else ["original", "reversed", "shuffle_1", "shuffle_2", "shuffle_3"]
    repeats = ["original", "repeat_2", "repeat_3", "repeat_4", "repeat_5"]
    documents = [["a", "b", "c"], ["c", "b", "a"], ["b", "a", "c"], ["a", "c", "b"], ["b", "c", "a"]]
    definitions = {key: documents[n] for n, key in enumerate(orders)}
    definitions.update({key: documents[0] for key in repeats})
    if single:
        definitions = {key: ["a"] for key in definitions}
    negative = {"repeat_2", "repeat_3"} if kind == "negative" else {"reversed", "shuffle_1"} if kind == "positive" else set()
    trials = [{"trial_id": key, "score": 0. if key in negative else 1., "decision": "rewrite" if key in negative else "accept",
               "status": "ok"} for key in definitions]
    return {"threshold": .7, "trials": trials, "plan": {"trials": [{"trial_id": k, "document_ids": v} for k, v in definitions.items()],
            "order_group": orders, "repeat_group": repeats}}


def row(language, identifier, group, kind="positive"):
    return {"language": language, "record_id": identifier, "document_group_id": group, "evaluation": evaluation(kind)}


def test_qa_increments_share_original_and_pairs_are_not_observations():
    positive = qa_increment(evaluation())
    negative = qa_increment(evaluation("negative"))
    assert positive["increment"] == .6 and negative["increment"] == -.6
    assert positive["order"]["valid_pairs"] == positive["repeat"]["valid_pairs"] == 10
    assert positive["order"]["disagreeing_pairs"] == 6 and positive["repeat"]["disagreeing_pairs"] == 0
    assert positive["comparable"] and negative["comparable"]


def test_partial_and_structural_missing_are_not_primary_values():
    partial = evaluation()
    partial["trials"][1].update(status="error", score=None, decision="unscorable")
    result = qa_increment(partial)
    assert result["increment"] is None and result["partial_pair_increment_exploratory"] is not None
    assert result["order"]["valid_pairs"] == 6
    structural = qa_increment(evaluation(single=True))
    assert structural["increment"] is None and structural["reason"] == "insufficient_distinct_order_conditions"
    assert qa_increment(None)["reason"] == "baseline_unavailable"


def test_invalid_grouping_scores_or_source_orders_fail_closed():
    for change in ("duplicate", "score", "order", "repeat"):
        value = evaluation()
        if change == "duplicate":
            value["trials"][1]["trial_id"] = "original"
        elif change == "score":
            value["trials"][1]["score"] = 1.
        elif change == "order":
            value["plan"]["trials"][1]["document_ids"] = ["unknown"]
        else:
            value["plan"]["repeat_group"].append("reversed")
        with pytest.raises(ValueError):
            qa_increment(value)


def test_bootstrap_keeps_groups_together_and_qa_weighting():
    values = {"large": [.6, .6], "small": [-.6]}
    samples = grouped_means(values, rng=np.random.default_rng(42), repetitions=1000)
    assert all(any(np.isclose(v, target) for target in (-.6, .2, .6)) for v in samples)
    rows = [row(lang, identifier, group, kind) for lang in ("en", "ja")
            for identifier, group, kind in (("a", "large", "positive"), ("b", "large", "positive"), ("c", "small", "negative"))]
    result = analyze(rows, repetitions=1000)
    assert result["languages"]["en"]["mean_increment"] == pytest.approx(.2)
    assert result["languages"]["en"]["mean_increment"] != pytest.approx(0.)
    assert result["languages"]["en"]["comparable_document_groups"] == 2


def test_languages_unpaired_even_with_same_qa_and_group_names_reproducible():
    rows = [row(lang, "a", "g1", "positive") for lang in ("en", "ja")]
    rows += [row(lang, "b", "g2", "negative") for lang in ("en", "ja")]
    result = analyze(rows, repetitions=2000)
    assert result == analyze(list(reversed(rows)), repetitions=2000)
    assert result["ja_minus_en"]["mean"] == 0.
    assert result["ja_minus_en"]["ci95"] == [-1.2, 1.2]
    changed = deepcopy(rows)
    changed[0]["evaluation"] = evaluation("zero")
    assert analyze(changed, repetitions=2000) != result


def test_fewer_than_two_comparable_groups_keeps_counts_and_null_ci():
    rows = [row("en", "a", "g1"), row("en", "b", "g1"), row("ja", "a", "g1")]
    rows[-1]["evaluation"] = None
    result = analyze(rows, repetitions=100)
    assert result["languages"]["en"]["mean_increment"] == .6
    assert result["languages"]["en"]["ci95"] is None
    assert result["languages"]["ja"]["selected_qa_count"] == result["languages"]["ja"]["missing_qa_count"] == 1
    assert result["ja_minus_en"] == {"mean": None, "ci95": None}
    with pytest.raises(ValueError, match="duplicate QA"):
        analyze(rows + [rows[0]])
