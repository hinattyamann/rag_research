"""Record Codex assessment of public packets without reading private experimental outcomes."""

from datetime import UTC, datetime

from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.quality import blank_annotations, validate_annotations
from rag_research.experiments.storage import checkpoint, read_json, verify_checkpoint, write_json
from rag_research.retrieval.common import file_hash


def open_candidate(bundle, assessment):
    packet = read_json(bundle / "packet.json")
    require(packet["packet_sha256"] == digest({k: v for k, v in packet.items() if k != "packet_sha256"}),
            "Packet hash differs")
    assessment.mkdir(parents=True, exist_ok=True)
    path = assessment / "annotations.json"
    annotations = read_json(path) if path.exists() else blank_annotations(packet)
    validate_annotations(packet, annotations)
    pending = [i for i, a in enumerate(annotations["annotations"]) if a["label"] == "pending"]
    require(bool(pending), "This packet has been assessed; do not resample labels")
    index = pending[0]
    session_path = assessment / "active.json"
    if session_path.exists():
        session = read_json(session_path)
        verify_checkpoint(session)
        require(session["packet_sha256"] == packet["packet_sha256"] and session["index"] == index,
                "Active assessment differs")
    else:
        checkpoint(session_path, {"packet_sha256": packet["packet_sha256"], "index": index,
                                  "started_at_utc": datetime.now(UTC).isoformat()})
    # Context/ref are identical within a question; the second candidate need not reprint them.
    case = packet["cases"][index]
    if index:
        first = packet["cases"][0]
        require(all(first[k] == case[k] for k in ("question", "documents", "reference_answers",
                    "selected_sentences_by_reference", "gold_documents")), "Question packet differs")
        return {"rubric_version": packet["rubric_version"], "candidate_index": index,
                "candidate_count": len(packet["cases"]), "case": {k: case[k] for k in
                    ("annotation_id", "candidate_sha256", "question", "answer")},
                "evidence_identical_to_first_candidate": True,
                "documents_sha256": digest(case["documents"])}
    return {"rubric": packet["rubric"], "candidate_index": index,
            "candidate_count": len(packet["cases"]), "case": case}


def save_candidate(bundle, assessment, decision_path):
    packet = read_json(bundle / "packet.json")
    session = read_json(assessment / "active.json")
    verify_checkpoint(session)
    require(session["packet_sha256"] == packet["packet_sha256"], "Active packet differs")
    index = session["index"]
    path = assessment / "annotations.json"
    value = read_json(path) if path.exists() else blank_annotations(packet)
    decision = read_json(decision_path)
    candidate = packet["cases"][index]
    require(decision["annotation_id"] == candidate["annotation_id"] and
            value["annotations"][index]["label"] == "pending", "Candidate changed or already assessed")
    require("AI代行" in decision["reason"], "Record AI provenance in every annotation")
    now = datetime.now(UTC)
    annotation = value["annotations"][index]
    annotation.update({k: decision[k] for k in ("label", "criteria", "essential_points", "reason", "evidence")})
    annotation.update(annotator="リサーチャー01", confirmed_at_utc=now.isoformat(),
                      elapsed_seconds=(now - datetime.fromisoformat(session["started_at_utc"])).total_seconds())
    validate_annotations(packet, value)
    # Immutable evidence of the original assessment; overwrite of a completed label is rejected above.
    checkpoint(assessment / f"decision-{index + 1}.json", {
        "annotation": annotation, "decision": decision, "started_at_utc": session["started_at_utc"],
        "human_reviewed": False, "actual_assessor": "Codex AI",
        "exact_model_identifier": None,
        "session_scope": "same_research_session_new_internal_outcomes_withheld",
        "time_kind": "AI_review_wall_time_with_tool_overhead_not_human_effort",
        "input_packet_sha256": packet["packet_sha256"], "decision_file_sha256": file_hash(decision_path)})
    write_json(path, value)
    # Keep the closed session as evidence rather than deleting a record.
    (assessment / "active.json").replace(assessment / f"session-{index + 1}.json")
    return {"annotation_id": annotation["annotation_id"], "label": annotation["label"],
            "remaining": sum(a["label"] == "pending" for a in value["annotations"])}
