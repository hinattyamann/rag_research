"""Freeze AI annotations before revealing internal outcomes; report pilot feasibility."""

from collections import Counter
from datetime import UTC, datetime
from statistics import mean

from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.quality import (
    blank_annotations,
    reconstruct,
    validate_annotations,
    verify_packet,
)
from rag_research.experiments.storage import checkpoint, read_json, verify_checkpoint, write_json
from rag_research.retrieval.common import file_hash


def combine_annotations(output):
    final = output / "quality/final"
    packet = read_json(final / "packet.json")
    collected = {}
    reviews = []
    for folder in sorted((output / "quality/assessments").glob("packet-*")):
        raw = read_json(folder / "annotations.json")
        bundle = output / "quality" / ("ready-" + folder.name.removeprefix("packet-"))
        part = read_json(bundle / "packet.json")
        validate_annotations(part, raw)
        for annotation in raw["annotations"]:
            require(annotation["label"] != "pending", "Some quality candidates are pending")
            require("AI代行" in annotation["reason"], "Every annotation must identify AI delegation")
            require(annotation["annotation_id"] not in collected, "Duplicate annotation ID")
            collected[annotation["annotation_id"]] = annotation
        for path in sorted(folder.glob("decision-*.json")):
            review = read_json(path)
            verify_checkpoint(review)
            require(review["human_reviewed"] is False, "AI assessment must not claim human review")
            require(collected[review["annotation"]["annotation_id"]] == review["annotation"], "Review journal differs")
            reviews.append({"path": path.relative_to(output).as_posix(), "sha256": file_hash(path)})
    require(set(collected) == {c["annotation_id"] for c in packet["cases"]}, "Missing/unknown quality IDs")
    require(len(reviews) == len(collected), "Missing assessment provenance")
    value = blank_annotations(packet)
    value["annotations"] = [collected[c["annotation_id"]] for c in packet["cases"]]
    validate_annotations(packet, value)
    destination = output / "quality/quality-annotations.ai.json"
    if destination.exists():
        require(read_json(destination) == value, "Frozen annotations changed")
    else:
        write_json(destination, value)
    provenance = {"schema_version": 1, "annotation_kind": "Codex_AI", "human_reviewed": False,
                  "packet_sha256": packet["packet_sha256"], "annotations_sha256": file_hash(destination),
                  "rubric_version": packet["rubric_version"], "source_reviews": reviews,
                  "session_scope": "same_research_session_new_internal_outcomes_withheld",
                  "exact_model_identifier": None, "exact_model_identifier_fixed": False,
                  "note": "Pilot labels only. Complete session isolation and model identity must be settled before final evaluation."}
    provenance_path = output / "quality/assessment_manifest.json"
    if provenance_path.exists():
        require({k: v for k, v in read_json(provenance_path).items() if k != "result_sha256"} == provenance,
                "Assessment provenance changed")
    else:
        checkpoint(provenance_path, provenance)
    return packet, value


def pilot_report(output):
    # This step succeeds only after every public candidate has a frozen annotation.
    packet, annotations = combine_annotations(output)
    final = output / "quality/final"
    mapping = read_json(final / "mapping.private.json")
    verify_packet(packet, mapping)
    manifest = read_json(output / "internal/manifest.json")
    require(mapping["run_manifest_sha256"] == digest(manifest), "Mapping belongs to another run")
    private = read_json(output / "internal/report.private.json")
    require(private["manifest_sha256"] == digest(manifest), "Private report binding differs")
    records = private["records"]
    completion = read_json(output / "internal/completion.private.json")
    require(completion["processed_questions"] == len(records) and
            (len(records) == len(manifest["traces"]) or completion["status"] == "health_gate_stopped"),
            "Internal inference incomplete without a declared health stop")
    for row in records:
        verify_checkpoint(row)
        folder = output / "internal" / digest(row["trace"]["record_id"])[:24]
        require(read_json(folder / "completed.json") == row, "Question summary changed")
        require(read_json(folder / "rewrite.json") == row["rewrite"] and
                read_json(folder / "claims.json") == row["tasks"]["extraction"], "Raw result changed")
        for trial_id, task in row["tasks"]["judges"].items():
            require(read_json(folder / f"{trial_id}.json") == task, "Raw Judge changed")
            verify_checkpoint(task)
    by_id = {a["annotation_id"]: a for a in annotations["annotations"]}
    labels = {(a["record_id"], a["stage"]): by_id[key]["label"]
              for key, assignments in mapping["assignments"].items() for a in assignments}
    analysis = reconstruct(records, labels)
    comparable = [r for r in records if all(r["evaluation"][g]["valid_trials"] ==
                    r["evaluation"][g]["planned_trials"] and r["evaluation"][g]["valid_pairs"] > 0
                    for g in ("order_group", "repeat_group"))]
    per_question = []
    for row in comparable:
        evaluation = row["evaluation"]
        order = evaluation["order_group"]
        repeat = evaluation["repeat_group"]
        require(order["valid_pairs"] > 0 and repeat["valid_pairs"] > 0, "No comparable trial pairs")
        a = order["disagreeing_pairs"] / order["valid_pairs"]
        b = repeat["disagreeing_pairs"] / repeat["valid_pairs"]
        per_question.append({"record_id": row["trace"]["record_id"], "order_disagreement": a,
                             "repeat_disagreement": b, "paired_difference": a - b})
    judges = [t for r in records for t in r["tasks"]["judges"].values()]
    attempted = [t for t in judges if t["completion_attempted"]]
    analysis.update(annotation_kind="Codex_AI", human_reviewed=False,
                    annotation_status_counts=dict(Counter(a["label"] for a in by_id.values())),
                    planned_questions=private["planned_questions"], baseline_failures=private["baseline_failures"],
                    pilot_execution_status=completion["status"], not_attempted_ids=completion["not_attempted_ids"],
                    health_gate=completion["health_gate"],
                    comparable_questions=len(comparable), per_question_disagreement=per_question,
                    mean_paired_difference=mean(r["paired_difference"] for r in per_question) if per_question else None,
                    questions_with_order_decision_flip=sum(r["evaluation"]["order_group"]["both_decisions_observed"]
                                                           for r in comparable),
                    questions_with_repeat_decision_flip=sum(r["evaluation"]["repeat_group"]["both_decisions_observed"]
                                                            for r in comparable),
                    extraction_status_counts=dict(Counter(r["tasks"]["extraction"]["status"] for r in records)),
                    judge_status_counts=dict(Counter(t["status"] for t in judges)),
                    judge_error_codes=dict(Counter(t["error_code"] for t in judges if t["status"] == "error")),
                    rewrite_status_counts=dict(Counter(r["rewrite"]["status"] for r in records)),
                    attempted_judge_seconds_mean=mean(t["elapsed_seconds"] for t in attempted) if attempted else None,
                    offline_AI_review_wall_seconds=sum(a["elapsed_seconds"] for a in by_id.values()),
                    updated_at_utc=datetime.now(UTC).isoformat(),
                    limits=["Development pilot, not final evaluation or a proof of novelty",
                            "AI-assigned quality, not independently human-confirmed truth",
                            "New outcomes hidden during grading; full session isolation/model ID not achieved",
                            "No confidence interval or hypothesis test is claimed by this pilot report",
                            "Partial/invalid trials remain separate from the common complete comparison"])
    write_json(output / "pilot_report.json", analysis)
    lines = ["# Phase 10 Development Pilot", "", f"対象 {private['planned_questions']}問、内部完了 {len(records)}問。",
             "品質採点: Codex AI。human_reviewed=false。", "",
             f"主比較の完全有効QA: {len(comparable)}問。", f"順序群−反復群の質問内不一致率の差の平均: {analysis['mean_paired_difference']}",
             f"品質四遷移: {analysis['quality_transitions']}", "", "| QA | 順序群不一致 | 同一順序反復不一致 | 差 |", "|---|---|---|---|"]
    for row in per_question:
        lines.append(f"| {row['record_id']} | {row['order_disagreement']:.3f} | {row['repeat_disagreement']:.3f} | {row['paired_difference']:.3f} |")
    lines.extend(["", "## 制約", "", *["- " + line for line in analysis["limits"]]])
    (output / "pilot_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {k: analysis[k] for k in ("planned_questions", "comparable_questions", "annotation_status_counts",
                                    "mean_paired_difference", "quality_transitions")}
