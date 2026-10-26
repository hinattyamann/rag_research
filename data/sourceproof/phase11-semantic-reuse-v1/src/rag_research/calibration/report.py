"""Inspect Calibration outcomes only after every anonymous quality label is sealed."""

from collections import Counter

from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.quality import reconstruct, verify_packet
from rag_research.experiments.storage import checkpoint, read_json, verify_checkpoint
from rag_research.pilot.report import combine_annotations


def calibration_report(output):
    packet, annotations = combine_annotations(output)
    manifest = read_json(output / "internal/manifest.json")
    require(manifest["purpose"] == "phase11-calibration-not-final-evaluation",
            "Not a Calibration run")
    mapping = read_json(output / "quality/final/mapping.private.json")
    verify_packet(packet, mapping)
    require(mapping["run_manifest_sha256"] == digest(manifest), "Quality binding differs")
    private = read_json(output / "internal/report.private.json")
    require(private["manifest_sha256"] == digest(manifest), "Calibration report binding differs")
    records = private["records"]
    completion = read_json(output / "internal/completion.private.json")
    require(completion["processed_questions"] == len(records) and
            (len(records) == len(manifest["traces"]) or completion["status"] == "health_gate_stopped"),
            "Calibration incomplete without a declared stop")
    for row in records:
        verify_checkpoint(row)
        folder = output / "internal" / digest(row["trace"]["record_id"])[:24]
        require(row == read_json(folder / "completed.json"), "Calibration record changed")
        require(row["pilot_manifest_sha256"] == digest(manifest), "Question binding differs")
        for path, task in [(folder / "claims.json", row["tasks"]["extraction"]),
                           (folder / "rewrite.json", row["rewrite"]),
                           *[(folder / f"{key}.json", task)
                             for key, task in row["tasks"]["judges"].items()]]:
            verify_checkpoint(task)
            require(read_json(path) == task, "Calibration raw task changed")
    by_id = {a["annotation_id"]: a for a in annotations["annotations"]}
    labels = {(a["record_id"], a["stage"]): by_id[key]["label"]
              for key, entries in mapping["assignments"].items() for a in entries}
    analysis = reconstruct(records, labels)
    comparisons = []
    for row in records:
        evaluation = row["evaluation"]
        groups = [evaluation[key] for key in ("order_group", "repeat_group")]
        if all(g["valid_trials"] == g["planned_trials"] and g["valid_pairs"] > 0 for g in groups):
            a, b = [g["disagreeing_pairs"] / g["valid_pairs"] for g in groups]
            comparisons.append({"record_id": row["trace"]["record_id"],
                                "order_disagreement": a, "repeat_disagreement": b,
                                "paired_difference": a - b})
    judges = [task for row in records for task in row["tasks"]["judges"].values()]
    return checkpoint(output / "calibration_report.json", {
        "schema_version": 1, "purpose": "phase11-calibration-not-final-evaluation",
        "manifest_sha256": digest(manifest), "gate11_passed": False, "phase12_allowed": False,
        "human_reviewed": False, "planned_questions": private["planned_questions"],
        "processed_questions": len(records), "baseline_failures": private["baseline_failures"],
        "comparable_questions": len(comparisons), "per_question_disagreement": comparisons,
        "health_gate": completion["health_gate"], "not_attempted_ids": completion["not_attempted_ids"],
        "judge_status_counts": dict(Counter(t["status"] for t in judges)),
        "extraction_status_counts": dict(Counter(r["tasks"]["extraction"]["status"] for r in records)),
        "citation_normalization_tasks": sum(bool(t.get("citation_normalization", {}).get(
            "deduplicated_claim_ids")) for t in judges),
        "analysis": analysis,
        "limits": ["Calibration only; no final Evaluation or statistical significance claimed",
                   "AI quality labels, not human truth; current assessor model/session limitations remain",
                   "Health Gate measures execution feasibility, not semantic correctness",
                   "Semantic review, refusal policy, runtime, scale and final freeze still required"]})
