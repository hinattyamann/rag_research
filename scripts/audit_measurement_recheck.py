"""Freeze BOTH cohorts' external annotations before auditing the small recheck."""

import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.storage import checkpoint, read_json, verify_checkpoint  # noqa: E402
from rag_research.pilot.report import combine_annotations, pilot_report  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def main():
    runs = [ROOT / "data/runs/pilot" / name for name in
            ("phase10-five-v2", "phase10-five-extra-v2")]
    # No private outcome or candidate-stage mapping may be read above this barrier.
    frozen = []
    for run in runs:
        packet, annotations = combine_annotations(run)
        frozen.append({"run": run.relative_to(ROOT).as_posix(),
                       "packet_sha256": packet["packet_sha256"],
                       "annotations_sha256": file_hash(run / "quality/quality-annotations.ai.json"),
                       "candidate_count": len(annotations["annotations"])})
    freeze_path = ROOT / "data/manifests/phase10_recheck_quality_freeze.json"
    body = {"purpose": "both_cohorts_quality_fixed_before_first_private_analysis",
            "human_reviewed": False, "cohorts": frozen}
    if freeze_path.exists():
        saved = read_json(freeze_path)
        verify_checkpoint(saved)
        require(all(saved[k] == v for k, v in body.items()), "Frozen quality changed")
    else:
        checkpoint(freeze_path, {**body, "frozen_at_utc": datetime.now(UTC).isoformat()})
    print("Both cohorts' external quality labels frozen; opening private results now.", flush=True)

    reports = []
    records = []
    bindings = {}
    for run in runs:
        pilot_report(run)
        reports.append(read_json(run / "pilot_report.json"))
        records.extend(read_json(run / "internal/report.private.json")["records"])
        binding = read_json(run / "internal/manifest.json")
        bindings[run.name] = all(file_hash(ROOT / p) == sha
                                 for p, sha in binding["source_sha256"].items())

    diagnostic = ROOT / "data/runs/measurement/phase10-revision-v14"
    additional = ROOT / "data/runs/measurement/phase10-additional-v14"
    checks = [r for r in read_json(diagnostic / "summary.json")["judge"]
              if r["id"] != "relation-conflict"]
    checks += read_json(additional / "summary.json")["results"]
    require(len(checks) == 15, "Expected the predeclared 15 unambiguous diagnostics")
    tasks = [t for r in records for t in [r["tasks"]["extraction"],
             *r["tasks"]["judges"].values(), r["rewrite"]]]
    judges = [t for r in records for t in r["tasks"]["judges"].values()]
    comparable = [r for r in records if all(r["evaluation"][g]["valid_trials"] ==
                    r["evaluation"][g]["planned_trials"] and r["evaluation"][g]["valid_pairs"] > 0
                    for g in ("order_group", "repeat_group"))]
    per_question = []
    for row in comparable:
        evaluation = row["evaluation"]
        ranges = {}
        for group in ("order_group", "repeat_group"):
            identifiers = set(evaluation["plan"][group])
            scores = [t["score"] for t in evaluation["trials"] if t["trial_id"] in identifiers]
            ranges[group] = max(scores) - min(scores)
        per_question.append({"record_id": row["trace"]["record_id"], "score_ranges": ranges})

    historical = read_json(ROOT / "data/manifests/phase10_pilot_manifest.json")["artifacts_sha256"]
    history_paths = {p: sha for p, sha in historical.items() if p.startswith("data/runs/")}
    history_changed = [p for p, sha in history_paths.items() if file_hash(ROOT / p) != sha]
    failures = Counter(t["error_code"] for t in judges if t["status"] == "error")
    aggregate = {
        "purpose": "phase10_measurement_recheck_not_final_evaluation",
        "audited_at_utc": datetime.now(UTC).isoformat(), "phase11_started": False,
        "quality_freeze_sha256": file_hash(freeze_path), "human_reviewed": False,
        "planned_questions": sum(r["planned_questions"] for r in reports),
        "processed_questions": len(records), "comparable_questions": len(comparable),
        "extraction_status_counts": dict(Counter(r["tasks"]["extraction"]["status"] for r in records)),
        "judge_status_counts": dict(Counter(t["status"] for t in judges)),
        "judge_errors": dict(failures),
        "rewrite_status_counts": dict(Counter(r["rewrite"]["status"] for r in records)),
        "annotation_status_counts": dict(sum((Counter(r["annotation_status_counts"]) for r in reports), Counter())),
        "quality_transitions": dict(sum((Counter(r["quality_transitions"]) for r in reports), Counter())),
        "per_cohort_health_gates": [r["health_gate"] for r in reports],
        "questions_with_order_decision_flip": sum(r["questions_with_order_decision_flip"] for r in reports),
        "questions_with_repeat_decision_flip": sum(r["questions_with_repeat_decision_flip"] for r in reports),
        "per_question_score_ranges": per_question,
        "strict_diagnostic_checks": checks,
        "strict_diagnostic_passed": sum(r["pass"] for r in checks),
        "internal_source_bindings_unchanged": bindings,
        "historical_artifacts_checked": len(history_paths), "historical_artifacts_changed": history_changed,
        "completion_attempts": sum(t["completion_attempted"] for t in tasks),
        "raw_tasks": len(tasks),
        "output_tokens_max": max(t["output_tokens"] or 0 for t in tasks),
        "all_attempted_input_reservations_valid": all(t["input_tokens"] is not None and
            t["input_tokens"] + t["settings"]["max_output_tokens"] <= t["settings"]["context_tokens"]
            for t in tasks if t["completion_attempted"]),
        "raw_artifacts_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p)
            for folder in [*runs, diagnostic, additional] for p in sorted(folder.rglob("*.json"))},
        "limits": ["Development-only feasibility check, not general judge accuracy or an order-effect estimate",
                   "Sentence support fraction differs from the old extracted-claim score",
                   "Generated reasoning and attached full passages are not proof of semantic correctness",
                   "Known natural-case false rejection remains; calibration is still necessary",
                   "AI quality assessment; exact assessor model and complete session isolation not fixed"],
    }
    destination = ROOT / "data/manifests/phase10_recheck_result_manifest.json"
    checkpoint(destination, aggregate)
    print(json.dumps({k: v for k, v in aggregate.items() if k not in
                      {"raw_artifacts_sha256", "strict_diagnostic_checks"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
