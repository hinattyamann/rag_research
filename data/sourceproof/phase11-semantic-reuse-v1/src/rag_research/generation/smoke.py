"""Development-only sample selection; labels stay outside inference."""

import hashlib
import json


def select_development(path, *, limit=5):
    if type(limit) is not int or not 1 <= limit <= 10:
        raise ValueError("Phase 5 smoke limit must be between 1 and 10")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not rows or any(row.get("research_split") != "development" for row in rows):
        raise ValueError("Smoke accepts Development only; Calibration/Evaluation are not opened")
    rows.sort(key=lambda row: hashlib.sha256(f"42:{row['record_id']}".encode()).hexdigest())
    answerable = [row for row in rows if row["is_answerable"]]
    unanswerable = [row for row in rows if not row["is_answerable"]]
    selected = answerable[: (limit + 1) // 2] + unanswerable[: limit // 2]
    if len(selected) != limit:
        raise ValueError("Not enough Development records for the fixed smoke sample")
    return sorted(
        selected, key=lambda row: hashlib.sha256(f"42:{row['record_id']}".encode()).hexdigest()
    )


def inference_input(row):
    """Project an offline QA record to the only permitted inference input."""
    return row["question"]


def offline_check(row, result):
    """Retrieval diagnostics and references, not independent answer-quality labels."""
    gold = set(row["gold_passage_ids"])
    return {
        "record_id": row["record_id"],
        "is_answerable": row["is_answerable"],
        "reference_answers": row["reference_answers"],
        "gold_passage_ids": sorted(gold),
        "gold_in_retrieved": bool(gold & {hit["passage_id"] for hit in result["retrieved_context"]})
        if gold
        else None,
        "gold_in_used_context": bool(gold & {hit["passage_id"] for hit in result["used_context"]})
        if gold
        else None,
        "quality_label_y": None,
        "independent_failure_label": None,
        "note": "Offline development diagnostic only. Unanswerable corpus audit not performed.",
    }
