"""Post-hoc pooled analysis of the 200 fixed-evaluator questions.

Creates new descriptive bootstrap intervals from saved decisions, never inference
or new annotation. The original packages and registered analyses are unchanged.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
OUTPUT = PAPER / "notes/pooled_results_v1.json"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


ORDER = module("pooled_order", HERE / "derive_order_effects.py")
EXT = module("pooled_extension", HERE / "derive_extension_results.py")


def disagreement(decisions):
    if len(decisions) < 2 or not set(decisions) <= {"accept", "rewrite"}:
        raise ValueError("Incomplete binary comparison")
    accept = decisions.count("accept")
    return accept * (len(decisions) - accept) / math.comb(len(decisions), 2)


def grouped_bootstrap(records, rng, repetitions=10_000):
    groups = defaultdict(list)
    for record in records:
        groups[record["document_group_id"]].append(record["increment"])
    keys = sorted(groups)
    totals = np.array([sum(groups[key]) for key in keys])
    sizes = np.array([len(groups[key]) for key in keys])
    indices = rng.integers(0, len(keys), size=(repetitions, len(keys)))
    return totals[indices].sum(axis=1) / sizes[indices].sum(axis=1)


def derive():
    old = ORDER.derive()
    extension = EXT.derive()
    questions = old["questions"] + extension["questions"]
    require = ORDER.require
    require(len(questions) == 200, "Not all 200 selected questions")
    for field in ("qa_key", "record_id", "document_group_id"):
        identities = [(q["language"], q[field]) for q in questions]
        require(len(set(identities)) == 200, f"Repeated question/group: {field}")
    packages = [PAPER / "materials/fixed_v23_v1"] + [
        PAPER / "materials/cal_extension_v1" / b for b in EXT.BATCHES
    ]
    raw, policies, hashes = {}, [], {}
    for package in packages:
        for name in ("qa_summary.csv", "trials.jsonl", "policy_outcomes.csv"):
            file = package / name
            hashes[str(file.relative_to(PAPER))] = hashlib.sha256(file.read_bytes()).hexdigest()
        trials = defaultdict(dict)
        for line in (package / "trials.jsonl").read_text(encoding="utf-8").splitlines():
            trial = json.loads(line)
            require(trial["trial_id"] not in trials[trial["qa_key"]], "Duplicate trial")
            trials[trial["qa_key"]][trial["trial_id"]] = trial
        with (package / "qa_summary.csv").open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                key = row["qa_key"]
                source = json.loads((package / row["input_path"]).read_text(encoding="utf-8"))
                require(key not in raw, "Duplicate QA key")
                raw[key] = (row, source, trials[key])
        with (package / "policy_outcomes.csv").open(encoding="utf-8", newline="") as stream:
            policies.extend(csv.DictReader(stream))
    comparable = []
    for question in questions:
        row, source, trials = raw[question["qa_key"]]
        if not question["comparable"]:
            continue
        plan = source["trial_plan"]
        rates = {}
        for group, field in (("order_group", "order_rate"), ("repeat_group", "repeat_rate")):
            chosen = [trials[key] for key in plan[group]]
            require(all(t["status"] == "ok" for t in chosen), "Invalid comparable trial")
            rates[field] = disagreement([t["decision"] for t in chosen])
            require(abs(rates[field] - float(row[field])) < 1e-12, "Saved rate differs")
        increment = rates["order_rate"] - rates["repeat_rate"]
        require(abs(increment - float(row["increment"])) < 1e-12, "Saved increment differs")
        comparable.append({**question, **rates, "increment": increment})
    require(len(comparable) == 148, "Comparable population changed")

    primary, quality, selection, semantics, thresholds = [], [], [], [], []
    bootstrap = {}
    generators = [np.random.default_rng(seed) for seed in np.random.SeedSequence(42).spawn(2)]
    for language, rng in zip(("en", "ja"), generators, strict=True):
        selected = [q for q in questions if q["language"] == language]
        observed = sorted(
            [q for q in comparable if q["language"] == language],
            key=lambda q: (q["document_group_id"], q["record_id"]),
        )
        require(len(selected) == 100, "Language allocation differs")
        bootstrap[language] = grouped_bootstrap(observed, rng)
        classifications = Counter(q["classification"] for q in observed)
        primary.append(
            {
                "language": language,
                "selected_qa": len(selected),
                "comparable_qa": len(observed),
                "excluded_qa": len(selected) - len(observed),
                "exclusion_reasons": dict(
                    Counter(q["exclusion_reason"] for q in selected if not q["comparable"])
                ),
                "mean_order_rate": float(np.mean([q["order_rate"] for q in observed])),
                "mean_repeat_rate": float(np.mean([q["repeat_rate"] for q in observed])),
                "mean_increment": float(np.mean([q["increment"] for q in observed])),
                "ci95": np.quantile(bootstrap[language], [0.025, 0.975]).tolist(),
                "decision_change_qa": sum(q["decision_varies_in_valid_orders"] for q in observed),
                "classification_counts": {key: classifications[key] for key in ORDER.CLASSES},
                "initial_failures": sum(q["initial_status"] != "ok" for q in selected),
                "rewrite_failures": sum(q["rewrite_status"] == "error" for q in selected),
                "rewrite_not_run": sum(
                    q["rewrite_status"] not in {"ok", "error"} for q in selected
                ),
            }
        )
        for route in EXT.ROUTES:
            records = [p for p in policies if p["language"] == language and p["route"] == route]
            require(len(records) == 100, "Missing operational route slots")
            delivered = [p for p in records if p["policy_state"] == "observed"]
            labels = Counter(p["quality_status"] for p in delivered)
            quality.append(
                {
                    "language": language,
                    "route": route,
                    "selected_qa": 100,
                    "delivered": len(delivered),
                    "missing": 100 - len(delivered),
                    "reliable": labels["reliable"],
                    "unreliable": labels["unreliable"],
                    "indeterminate": labels["indeterminate"],
                    "calls": sum(int(p["recorded_completion_attempts"]) for p in delivered),
                    "input_tokens": sum(int(p["input_tokens"]) for p in delivered),
                    "output_tokens": sum(int(p["output_tokens"]) for p in delivered),
                    "cost_incomplete_routes": sum(
                        ORDER.boolean(p["incomplete"]) for p in delivered
                    ),
                }
            )
            require(sum(labels.values()) == len(delivered), "Unclassified delivery")
        known = [
            q
            for q in selected
            if q["rewrite_status"] == "ok" and None not in q["candidate_y"].values()
        ]
        known_keys = {q["qa_key"] for q in known}
        transitions = Counter(f"{q['candidate_y']['A']}->{q['candidate_y']['B']}" for q in known)
        routes = [
            p
            for p in policies
            if p["language"] == language
            and p["qa_key"] in known_keys
            and p["policy_state"] == "observed"
        ]
        selection.append(
            {
                "language": language,
                "known_pairs": len(known),
                "unknown_or_failed_pairs": 100 - len(known),
                "transitions": {key: transitions[key] for key in ("0->0", "0->1", "1->0", "1->1")},
                "oe_missed_improvements": sum(
                    ORDER.boolean(p["missed_improvement"])
                    for p in routes
                    if p["route"] == "original"
                ),
                "oe_harmful_rewrites": sum(
                    ORDER.boolean(p["harmful_rewrite"]) for p in routes if p["route"] == "original"
                ),
                "ar_harmful_rewrites": sum(
                    ORDER.boolean(p["harmful_rewrite"])
                    for p in routes
                    if p["route"] == "always_rewrite"
                ),
            }
        )
        original_semantics = []
        for name in ("main", "cal"):
            file = packages[0] / "analysis" / f"{name}.private.json"
            hashes[str(file.relative_to(PAPER))] = hashlib.sha256(file.read_bytes()).hexdigest()
            original_semantics.append(
                json.loads(file.read_text(encoding="utf-8"))["semantics"][language]
            )
        extra = next(s for s in extension["semantics"] if s["language"] == language)
        negative = sum(s["planned_definite_negative_unit_conditions"] for s in original_semantics)
        false = sum(s["false_support_count"] for s in original_semantics)
        semantics.append(
            {
                "language": language,
                "negative_sentence_trial_observations": negative
                + extra["negative_unit_conditions"],
                "false_support_observations": false + extra["false_support_count"],
            }
        )
        for threshold in (0.5, 0.6, 0.7, 0.8, 0.9):
            increments = []
            for question in observed:
                _, source, trials = raw[question["qa_key"]]
                rates = [
                    disagreement(
                        [
                            "accept" if trials[key]["score"] >= threshold else "rewrite"
                            for key in source["trial_plan"][group]
                        ]
                    )
                    for group in ("order_group", "repeat_group")
                ]
                increments.append(rates[0] - rates[1])
            thresholds.append(
                {
                    "language": language,
                    "threshold": threshold,
                    "comparable_qa": len(observed),
                    "mean_increment": float(np.mean(increments)),
                }
            )
    difference = bootstrap["ja"] - bootstrap["en"]
    return {
        "version": "post-hoc-200-question-pooled-analysis-v1",
        "analysis_plan": "notes/pooled_analysis_readme.md",
        "post_hoc": True,
        "selected_qa": 200,
        "comparable_qa": 148,
        "statistics": {
            "numpy_version": np.__version__,
            "repetitions": 10_000,
            "seed": 42,
            "rng": "SeedSequence(42).spawn(2), en then ja",
            "bootstrap_unit": "document_group_id within language",
            "quantile": "linear 2.5/97.5 percentiles",
            "estimand": "QA-weighted empirical mixture conditional on comparability",
        },
        "primary": primary,
        "ja_minus_en": {
            "mean": primary[1]["mean_increment"] - primary[0]["mean_increment"],
            "ci95": np.quantile(difference, [0.025, 0.975]).tolist(),
        },
        "quality": quality,
        "selection": selection,
        "semantics": semantics,
        "thresholds": thresholds,
        "source_sha256": dict(
            sorted(
                {
                    **{
                        "materials/fixed_v23_v1/" + key: value
                        for key, value in old["source_sha256"].items()
                    },
                    **{
                        "materials/cal_extension_v1/" + key: value
                        for key, value in extension["source_sha256"].items()
                    },
                    **hashes,
                    "manuscript/derive_pooled_results.py": hashlib.sha256(
                        Path(__file__).read_bytes()
                    ).hexdigest(),
                    "notes/pooled_analysis_readme.md": hashlib.sha256(
                        (PAPER / "notes/pooled_analysis_readme.md").read_bytes()
                    ).hexdigest(),
                }.items()
            )
        ),
        "questions": comparable,
        "new_inference_calls": 0,
        "new_annotation_calls": 0,
        "unknown_interrupted_request_cost_retained": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = derive()
    if args.check:
        ORDER.require(
            json.loads(OUTPUT.read_text(encoding="utf-8")) == result, "Pooled results differ"
        )
    else:
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "primary",
                    "ja_minus_en",
                    "quality",
                    "selection",
                    "semantics",
                    "thresholds",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
