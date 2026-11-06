"""Derive post-outcome descriptive order/selected-quality counts from frozen records.

No inference, grading, interval estimation, or modification of the material package.
The canonical trial_plan, not the exported convenience group booleans, determines
unique order membership. Costs below are recorded route amounts, not collection
or monetary costs, confidence intervals, or measured service latency.
"""

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

PAPER = Path(__file__).resolve().parent.parent
DEFAULT_MATERIALS = PAPER / "materials/fixed_v23_v1"
DEFAULT_OUTPUT = PAPER / "notes/order_effects_v1.json"
STRATA = (("main", "en"), ("main", "ja"), ("cal", "en"), ("cal", "ja"))
CLASSES = (
    "no_decision_change",
    "decision_change_same_binary_quality",
    "decision_change_quality_changes",
    "decision_change_quality_unknown",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def boolean(value):
    if value is True or value == "True":
        return True
    if value is False or value == "False":
        return False
    raise ValueError(f"Not an explicit boolean: {value!r}")


def binary_y(value):
    if value in (None, ""):
        return None
    require(type(value) in (int, str) and str(value) in {"0", "1"}, "Nonbinary quality label")
    return int(value)


def integer(value):
    return None if value in (None, "") else int(value)


def quality_class(decisions, labels):
    require(len(decisions) == len(labels) and len(decisions) >= 2, "Incomplete order comparison")
    if len(set(decisions)) == 1:
        return "no_decision_change"
    if None in labels:
        return "decision_change_quality_unknown"
    if len(set(labels)) == 2:
        return "decision_change_quality_changes"
    return "decision_change_same_binary_quality"


def index_unique(rows, key):
    result = {}
    for row in rows:
        identity = row[key]
        require(identity not in result, f"Duplicate {key}: {identity}")
        result[identity] = row
    return result


def cost_range(routes, field):
    amounts = [row[field] for row in routes if row[field] is not None]
    return {
        "min": min(amounts) if amounts else None,
        "max": max(amounts) if amounts else None,
        "known_routes": len(amounts),
        "unknown_routes": len(routes) - len(amounts),
    }


def summarize_question(row, source, trials, policies):
    key = row["qa_key"]
    require(
        source["qa_key"] == key and source["record_id"] == row["record_id"], "QA identity differs"
    )
    comparable = boolean(row["comparable"])
    for letter in ("A", "B"):
        require(
            binary_y(row[f"{letter}_y"])
            == binary_y((source[letter].get("quality") or {}).get("y")),
            "QA summary/candidate quality differs",
        )
    trial_index = index_unique(trials, "trial_id")
    policy_index = index_unique(policies, "route")
    plan = source["trial_plan"]
    orders = plan["order_group"] if plan else []
    repeats = plan["repeat_group"] if plan else []
    require(len(orders) == len(set(orders)), "Duplicate planned order trial")
    if plan:
        require(set(orders) & set(repeats) == {"original"}, "Shared original differs")
        planned = index_unique(plan["trials"], "trial_id")
        require(set(planned) == set(trial_index), "Planned/exported trial IDs differ")
        require(
            len({tuple(planned[t]["document_ids"]) for t in orders}) == len(orders),
            "Duplicate document permutation",
        )
        require(
            all(trial_index[t]["document_ids"] == planned[t]["document_ids"] for t in planned),
            "Trial evidence order differs",
        )
        require(
            all(
                trial_index[t]["document_ids"] == planned["original"]["document_ids"]
                for t in repeats
            ),
            "Repeat evidence order differs",
        )
    else:
        require(not trials and not comparable, "Missing initial answer has experimental trials")
    flag_discrepancies = {
        field: sum(t.get(field) != (t["trial_id"] in members) for t in trials)
        for field, members in (("in_order_group", orders), ("in_repeat_group", repeats))
    }
    routes = []
    valid_ids = []
    for trial_id in orders:
        trial = trial_index[trial_id]
        policy = policy_index.get(trial_id)
        valid = trial["status"] == "ok" and trial["decision"] in {"accept", "rewrite"}
        if valid:
            require(
                policy is not None and policy["policy_state"] == "observed",
                "Valid order lacks an observed route",
            )
            valid_ids.append(trial_id)
        if policy is None or policy["policy_state"] != "observed":
            routes.append(
                {
                    "trial_id": trial_id,
                    "valid_order_trial": valid,
                    "policy_state": policy["policy_state"] if policy else "missing",
                }
            )
            continue
        stage = policy["selected_stage"]
        require(stage in {"initial", "rewritten"}, "Unknown selected stage")
        candidate = source["A" if stage == "initial" else "B"]
        y = binary_y(policy["quality_y"])
        expected_y = binary_y((candidate.get("quality") or {}).get("y"))
        require(y == expected_y, "Selected quality differs from saved candidate annotation")
        require(
            policy["selected_answer_sha256"] == candidate["answer_sha256"],
            "Selected text identity differs",
        )
        requested = boolean(policy["rewrite_requested"])
        if valid:
            require(requested == (trial["decision"] == "rewrite"), "Decision/route request differs")
            expected_stage = (
                "rewritten" if requested and source["B"]["status"] == "ok" else "initial"
            )
            require(stage == expected_stage, "Route did not select the available fixed candidate")
            if requested and source["B"]["status"] != "ok":
                require(policy["fallback"] == "rewrite_failed", "Failed rewrite fallback omitted")
        if policy["fallback"] == "rewrite_failed":
            require(
                requested and stage == "initial" and source["B"]["status"] != "ok",
                "Failed rewrite did not retain A",
            )
        if stage == "rewritten":
            require(source["B"]["status"] == "ok" and requested, "Unavailable rewrite selected")
        calls = integer(policy["recorded_completion_attempts"])
        input_tokens, output_tokens = (
            integer(policy["input_tokens"]),
            integer(policy["output_tokens"]),
        )
        routes.append(
            {
                "trial_id": trial_id,
                "valid_order_trial": valid,
                "policy_state": policy["policy_state"],
                "decision": trial["decision"],
                "selected_stage": stage,
                "selected_answer_sha256": policy["selected_answer_sha256"],
                "selected_y": y,
                "quality_status": policy["quality_status"],
                "rewrite_requested": requested,
                "fallback": policy["fallback"] or None,
                "recorded_calls": calls,
                "recorded_input_tokens": input_tokens,
                "recorded_output_tokens": output_tokens,
                "known_input_plus_output_tokens": input_tokens + output_tokens
                if input_tokens is not None and output_tokens is not None
                else None,
                "unknown_outcome_steps": integer(policy["unknown_outcome_steps"]),
                "cost_incomplete": boolean(policy["incomplete"]),
            }
        )
    valid_routes = [r for r in routes if r["valid_order_trial"] and r["policy_state"] == "observed"]
    varies = len({r["decision"] for r in valid_routes}) > 1
    if comparable:
        require(
            len(valid_routes) == len(orders) and len(orders) >= 2,
            "Comparable QA has incomplete order routes",
        )
        require(
            all(
                trial_index[t]["status"] == "ok"
                and trial_index[t]["decision"] in {"accept", "rewrite"}
                for t in repeats
            ),
            "Comparable QA has incomplete repeats",
        )
        require(
            varies == boolean(row["order_varies"]),
            "Order variation differs from original QA summary",
        )
        category = quality_class(
            [r["decision"] for r in valid_routes], [r["selected_y"] for r in valid_routes]
        )
    else:
        category = "excluded_primary"
    aliases = {
        p["route"]: p["alias_of"]
        for p in policies
        if p["policy_state"] == "omitted_duplicate_order_alias"
    }
    if plan:
        require(aliases == plan["duplicate_order_aliases"], "Duplicate alias mapping differs")
        require(not set(aliases) & set(orders), "Duplicate alias was counted as a unique order")
    return {
        "qa_key": key,
        "record_id": row["record_id"],
        "cohort": row["cohort"],
        "language": row["language"],
        "input_path": row["input_path"],
        "document_group_id": row["document_group_id"],
        "comparable": comparable,
        "exclusion_reason": row["comparison_reason"] or None,
        "initial_status": row["initial_status"],
        "rewrite_status": row["rewrite_status"],
        "candidate_y": {"A": binary_y(row["A_y"]), "B": binary_y(row["B_y"])},
        "planned_unique_order_trial_ids": orders,
        "valid_unique_order_trial_ids": valid_ids,
        "omitted_duplicate_order_aliases": aliases,
        "recorded_order_varies": boolean(row["order_varies"]),
        "decision_varies_in_valid_orders": varies,
        "selected_answer_varies_in_valid_orders": len(
            {r["selected_answer_sha256"] for r in valid_routes}
        )
        > 1,
        "has_unknown_selected_y_in_valid_orders": any(
            r["selected_y"] is None for r in valid_routes
        ),
        "selected_binary_y_values": sorted(
            {r["selected_y"] for r in valid_routes if r["selected_y"] is not None}
        ),
        "classification": category,
        "known_route_cost_range": {
            "recorded_calls": cost_range(valid_routes, "recorded_calls"),
            "recorded_input_plus_output_tokens": cost_range(
                valid_routes, "known_input_plus_output_tokens"
            ),
            "incomplete_routes": sum(r["cost_incomplete"] for r in valid_routes),
            "routes_with_unknown_outcome_steps": sum(
                r["unknown_outcome_steps"] not in (0, None) for r in valid_routes
            ),
        },
        "non_authoritative_export_flag_mismatches": flag_discrepancies,
        "order_routes": routes,
    }


def derive(materials=DEFAULT_MATERIALS):
    materials = Path(materials)
    hashes = {}

    def read_bytes(relative):
        data = (materials / relative).read_bytes()
        hashes[relative] = hashlib.sha256(data).hexdigest()
        return data

    qa_rows = list(csv.DictReader(read_bytes("qa_summary.csv").decode("utf-8").splitlines()))
    policies = list(csv.DictReader(read_bytes("policy_outcomes.csv").decode("utf-8").splitlines()))
    trials = [
        json.loads(line) for line in read_bytes("trials.jsonl").decode("utf-8").splitlines() if line
    ]
    read_bytes("artifact_manifest.json")
    index_unique(qa_rows, "qa_key")
    trial_groups, policy_groups = defaultdict(list), defaultdict(list)
    for t in trials:
        trial_groups[t["qa_key"]].append(t)
    for p in policies:
        policy_groups[p["qa_key"]].append(p)
    qa_keys = {r["qa_key"] for r in qa_rows}
    require(
        set(trial_groups) <= qa_keys and set(policy_groups) == qa_keys,
        "Unexpected/missing QA mapping",
    )
    questions = []
    for row in sorted(
        qa_rows, key=lambda r: (STRATA.index((r["cohort"], r["language"])), r["qa_key"])
    ):
        source = json.loads(read_bytes(row["input_path"]))
        questions.append(
            summarize_question(
                row, source, trial_groups[row["qa_key"]], policy_groups[row["qa_key"]]
            )
        )
    summaries = []
    for cohort, language in STRATA:
        selected = [q for q in questions if (q["cohort"], q["language"]) == (cohort, language)]
        comparable = [q for q in selected if q["comparable"]]
        counts = Counter(q["classification"] for q in comparable)
        summaries.append(
            {
                "cohort": cohort,
                "language": language,
                "selected_qa": len(selected),
                "comparable_qa": len(comparable),
                "excluded_qa": len(selected) - len(comparable),
                "exclusion_reasons": dict(
                    sorted(
                        Counter(
                            q["exclusion_reason"] for q in selected if not q["comparable"]
                        ).items()
                    )
                ),
                "classification_counts": {category: counts[category] for category in CLASSES},
                "decision_change_qa": sum(q["decision_varies_in_valid_orders"] for q in comparable),
                "comparable_qa_with_unknown_selected_y": sum(
                    q["has_unknown_selected_y_in_valid_orders"] for q in comparable
                ),
                "selected_qa_with_failed_rewrite": sum(
                    q["rewrite_status"] == "error" for q in selected
                ),
                "comparable_qa_with_failed_rewrite": sum(
                    q["rewrite_status"] == "error" for q in comparable
                ),
                "omitted_duplicate_order_slots": sum(
                    len(q["omitted_duplicate_order_aliases"]) for q in selected
                ),
                "decision_change_qa_keys": [
                    q["qa_key"] for q in comparable if q["decision_varies_in_valid_orders"]
                ],
                "quality_change_qa_keys": [
                    q["qa_key"]
                    for q in comparable
                    if q["classification"] == "decision_change_quality_changes"
                ],
            }
        )
    return {
        "version": "posthoc-order-to-quality-v1",
        "analysis_status": "post-outcome descriptive analysis of saved fixed-input results",
        "primary_population": "Existing comparable QA only; all selected QA and exclusions retained separately",
        "definitions": {
            "order_membership": "Canonical inputs/* trial_plan.order_group, after duplicate permutation omission; original is counted once and repeat_2..5 are excluded",
            "decision_change_same_binary_quality": "At least two order decisions differ, every selected Y is known binary, and all selected Y values agree",
            "decision_change_quality_changes": "At least two order decisions differ, every selected Y is known binary, and both 0 and 1 occur",
            "decision_change_quality_unknown": "At least two order decisions differ and any selected Y is unknown; this category takes priority even if known 0 and 1 also occur",
            "no_decision_change": "All valid order decisions agree; unknown selected quality is retained in a separate field",
            "failed_rewrite": "Use the actual selected A and its annotation when a failed requested rewrite falls back; do not infer B or an improvement/harm",
            "costs": "Per-QA min/max across valid unique observed order routes of recorded calls and known input+output tokens; not confidence bounds or total collection/annotation cost. Missing amounts and incomplete/unknown outcome flags are retained",
            "quality": "Saved external AI labels; not newly graded human truth. A change can be either improvement or degradation depending on which order is used",
        },
        "source_sha256": dict(sorted(hashes.items())),
        "source_rows": {
            "qa_summary": len(qa_rows),
            "trials": len(trials),
            "policy_slots": len(policies),
        },
        "non_authoritative_export_flags": {
            "note": "Exported trial group booleans disagree with canonical trial_plan membership. They are audited but never used to select orders; frozen material is unchanged",
            "mismatches": {
                name: sum(q["non_authoritative_export_flag_mismatches"][name] for q in questions)
                for name in ("in_order_group", "in_repeat_group")
            },
        },
        "strata": summaries,
        "questions": questions,
        "new_inference_calls": 0,
        "new_annotation_calls": 0,
        "new_confidence_intervals": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materials", type=Path, default=DEFAULT_MATERIALS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check", action="store_true", help="Check saved JSON without rewriting it"
    )
    args = parser.parse_args()
    result = derive(args.materials)
    if args.check:
        require(
            json.loads(args.output.read_text(encoding="utf-8")) == result,
            "Saved order effects differ from frozen sources",
        )
    else:
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result["strata"], ensure_ascii=False))


if __name__ == "__main__":
    main()
