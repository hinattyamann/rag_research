"""QA-level increments and independent language-wise document-group bootstrap."""

from collections import defaultdict
from itertools import combinations

import numpy as np

from rag_research.experiments.decisions import decide
from rag_research.experiments.frozen_trace import require

VERSION = "qa-increment-document-group-bootstrap-v1"


def pair_rate(trials, identifiers):
    selected = [trials[i] for i in identifiers if trials[i]["status"] == "ok"]
    pairs = list(combinations(selected, 2))
    disagree = sum(a["decision"] != b["decision"] for a, b in pairs)
    return {"planned_trials": len(identifiers), "valid_trials": len(selected), "valid_pairs": len(pairs),
            "disagreeing_pairs": disagree, "rate": disagree / len(pairs) if pairs else None}


def qa_increment(evaluation):
    if evaluation is None:
        return {"comparable": False, "increment": None, "reason": "baseline_unavailable"}
    plan = evaluation["plan"]
    ids = [t["trial_id"] for t in evaluation["trials"]]
    planned = [t["trial_id"] for t in plan["trials"]]
    require(len(set(ids)) == len(ids) and set(ids) == set(planned) and len(set(planned)) == len(planned),
            "Saved/expected trial set differs")
    groups = [plan["order_group"], plan["repeat_group"]]
    require(all(len(set(g)) == len(g) and set(g) <= set(ids) for g in groups) and
            set(groups[0]) & set(groups[1]) == {"original"} and set(groups[0]) | set(groups[1]) == set(ids),
            "Order/repeat groups must share only the original trial")
    require(1 <= len(groups[0]) <= 5 and len(groups[1]) == 5, "Expected up to five orders and five repeats")
    definitions = {t["trial_id"]: t["document_ids"] for t in plan["trials"]}
    original = definitions["original"]
    require(original and len(set(original)) == len(original) and
            all(len(v) == len(original) and set(v) == set(original) for v in definitions.values()) and
            all(definitions[i] == original for i in groups[1]) and
            len({tuple(definitions[i]) for i in groups[0]}) == len(groups[0]), "Document order/repeat definitions differ")
    decide(None, evaluation["threshold"])
    trials = {t["trial_id"]: t for t in evaluation["trials"]}
    for row in trials.values():
        if row["status"] == "ok":
            require(row["score"] is not None and row["decision"] == decide(row["score"], evaluation["threshold"])["decision"],
                    "Invalid scored decision")
        else:
            require(row["score"] is None and row["decision"] == "unscorable", "Failed trial cannot have a score")
    order, repeat = [pair_rate(trials, group) for group in groups]
    observed = order["rate"] - repeat["rate"] if order["rate"] is not None and repeat["rate"] is not None else None
    complete = all(row["status"] == "ok" for row in trials.values()) and observed is not None
    return {"comparable": complete, "increment": observed if complete else None,
            "partial_pair_increment_exploratory": observed, "order": order, "repeat": repeat,
            "reason": None if complete else "invalid_or_unscorable_trials" if any(t["status"] != "ok" for t in trials.values())
            else "insufficient_distinct_order_conditions"}


def grouped_means(values, *, rng, repetitions):
    """Resample whole groups; the estimator remains the mean over QA, not group means."""
    groups = sorted(values)
    require(len(groups) >= 2, "Two comparable groups are needed for bootstrap")
    require(all(values[g] and all(np.isfinite(v) and -1 <= v <= 1 for v in values[g]) for g in groups), "Invalid group increments")
    sums = np.array([sum(values[g]) for g in groups], dtype=np.float64)
    counts = np.array([len(values[g]) for g in groups], dtype=np.int64)
    draws = rng.integers(len(groups), size=(repetitions, len(groups)))
    return sums[draws].sum(axis=1) / counts[draws].sum(axis=1)


def interval(values):
    return [float(v) for v in np.quantile(values, [.025, .975], method="linear")]


def analyze(records, *, repetitions=10000, seed=42):
    require(type(repetitions) is int and repetitions >= 2 and type(seed) is int and seed >= 0, "Invalid bootstrap settings")
    require(records and len({(r["language"], r["record_id"]) for r in records}) == len(records), "Missing/duplicate QA")
    rows = []
    for row in records:
        require(row["language"] in {"en", "ja"} and isinstance(row["record_id"], str) and row["record_id"] and
                isinstance(row["document_group_id"], str) and row["document_group_id"], "Explicit language/QA/group required")
        rows.append({k: row[k] for k in ("language", "record_id", "document_group_id")} | qa_increment(row["evaluation"]))
    rows.sort(key=lambda r: (r["language"], r["record_id"]))
    require({r["language"] for r in rows} == {"en", "ja"}, "Both unpaired languages required")
    streams = np.random.SeedSequence(seed).spawn(2)
    results, samples = {}, {}
    for language, stream in zip(("en", "ja"), streams, strict=True):
        selected = [r for r in rows if r["language"] == language]
        complete = [r for r in selected if r["comparable"]]
        values = defaultdict(list)
        for row in complete:
            values[row["document_group_id"]].append(row["increment"])
        mean = float(np.mean([r["increment"] for r in complete])) if complete else None
        samples[language] = grouped_means(values, rng=np.random.default_rng(stream), repetitions=repetitions) if len(values) >= 2 else None
        results[language] = {"selected_qa_count": len(selected), "selected_document_groups": len({r["document_group_id"] for r in selected}),
                             "comparable_qa_count": len(complete), "missing_qa_count": len(selected) - len(complete),
                             "comparable_document_groups": len(values), "mean_increment": mean,
                             "ci95": interval(samples[language]) if samples[language] is not None else None,
                             "ci_status": "available" if samples[language] is not None else "fewer_than_two_comparable_groups"}
    means = [results[lang]["mean_increment"] for lang in ("ja", "en")]
    difference = means[0] - means[1] if all(m is not None for m in means) else None
    contrast = (samples["ja"] - samples["en"]) if all(samples[lang] is not None for lang in ("en", "ja")) else None
    return {"version": VERSION, "numpy_version": np.__version__, "repetitions": repetitions, "seed": seed,
            "rng": "SeedSequence(seed).spawn(2) in en,ja order", "quantile": "linear_percentile_2.5_97.5",
            "estimand": "QA-weighted complete-comparison increment, conditional on comparability",
            "languages": results, "ja_minus_en": {"mean": difference, "ci95": interval(contrast) if contrast is not None else None},
            "qa": rows, "gate11_passed": False, "phase12_allowed": False}
