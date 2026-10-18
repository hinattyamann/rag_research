"""Whitelist baseline inference fields; never pass QA annotations downstream."""

import hashlib
import json


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_documents(documents):
    require(isinstance(documents, list) and documents, "Evidence must be a nonempty list")
    for doc in documents:
        require(isinstance(doc, dict) and set(doc) == {"passage_id", "title", "text"},
                "Unexpected evidence fields")
        require(all(isinstance(v, str) for v in doc.values()), "Evidence values must be text")
        require(bool(doc["passage_id"]) and bool(doc["text"].strip()), "Empty evidence ID/text")
    require(len({d["passage_id"] for d in documents}) == len(documents), "Duplicate evidence IDs")


def freeze_record(record):
    require(record["status"] == "ok", "Only successful baseline records may be frozen")
    for key in ("record_id", "question", "answer"):
        require(isinstance(record[key], str) and record[key].strip(), f"Invalid {key}")
    documents = record["used_context"]
    validate_documents(documents)
    trace = {
        "schema_version": 1,
        "record_id": record["record_id"],
        "question": record["question"],
        "answer": record["answer"],
        "documents": json.loads(json.dumps(documents, ensure_ascii=False)),
    }
    trace["answer_sha256"] = digest(trace["answer"])
    trace["ordered_documents_sha256"] = digest(documents)
    trace["document_set_sha256"] = digest(sorted(documents, key=lambda d: d["passage_id"]))
    trace["trace_sha256"] = digest(trace)
    return trace


def assert_same_evidence(original, reordered):
    validate_documents(reordered)
    require(sorted(original, key=lambda d: d["passage_id"])
            == sorted(reordered, key=lambda d: d["passage_id"]),
            "Order manipulation changed evidence content")
