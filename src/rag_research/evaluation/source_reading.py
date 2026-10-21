"""Draft-blind source reading followed by durable full-denominator sentence checks."""

import json
from dataclasses import asdict
from pathlib import Path

from rag_research.evaluation.schema import object_schema
from rag_research.experiments.frozen_trace import digest, require, validate_documents
from rag_research.experiments.storage import checkpoint, read_json, verify_checkpoint

MODE = "source-reading-v1"
BASE_FIELDS = ("schema_version", "task", "execution_mode", "request_sha256", "binding", "expected_claim_ids")


def reading_schema(documents):
    validate_documents(documents)
    item = object_schema({"passage_id": {"enum": sorted(d["passage_id"] for d in documents)},
                          "actor": {"type": "string", "minLength": 1, "maxLength": 160},
                          "action": {"type": "string", "minLength": 1, "maxLength": 320},
                          "quote": {"type": "string", "minLength": 1, "maxLength": 1600}})
    return object_schema({"readings": {"type": "array", "items": item,
                                       "minItems": len(documents), "maxItems": len(documents)}})


def validate_reading(value, documents):
    validate_documents(documents)
    by_id = {d["passage_id"]: d for d in documents}
    require(isinstance(value, dict) and set(value) == {"readings"} and isinstance(value["readings"], list),
            "Invalid reading object")
    rows = value["readings"]
    require(all(isinstance(r, dict) and set(r) == {"passage_id", "actor", "action", "quote"} and
                isinstance(r["passage_id"], str) for r in rows), "Invalid reading fields")
    require(len(rows) == len(by_id) and {r["passage_id"] for r in rows} == set(by_id),
            "Reading must cover every document exactly once")
    for row in rows:
        for field, limit in (("actor", 160), ("action", 320), ("quote", 1600)):
            require(isinstance(row[field], str) and row[field].strip() and len(row[field]) <= limit,
                    "Empty/oversized reading text")
        require(row["quote"] in by_id[row["passage_id"]]["text"], "Reading quote is not an exact source substring")
    return value


def parse_reading(text, documents):
    return validate_reading(json.loads(text), documents)


def child_paths(path):
    path = Path(path)
    return path.with_name(path.stem + ".reading.json"), path.with_name(path.stem + ".verification.json")


def pending(path):
    from rag_research.evaluation.claimwise import pending as sentence_pending

    path = Path(path)
    if not path.exists():
        return True
    root = read_json(path)
    verify_checkpoint(root)
    require(root["execution_mode"] == MODE, "Saved reading mode differs")
    if root["status"] != "partial":
        return False
    reader_path, verifier_path = child_paths(path)
    if not reader_path.exists():
        return True
    reader = read_json(reader_path)
    if reader["status"] != "ok":
        return False
    return sentence_pending(verifier_path, "claimwise-v1")


def derived(path, base, reader=None, verifier=None):
    from rag_research.evaluation.claimwise import COST_FIELDS, atomic_steps

    tasks = [t for t in (reader, verifier) if t is not None]
    costs = [{k: t.get(k, 0 if k == "elapsed_seconds" else None) for k in COST_FIELDS} for t in atomic_steps(tasks)]
    failure = next((t for t in tasks if t["status"] == "error"), None)
    status = "error" if failure else verifier["status"] if verifier else "partial"
    if not base["expected_claim_ids"]:
        status = "not_applicable"
    reader_path, verifier_path = child_paths(path)
    return {**base, "status": status, "parsed": verifier["parsed"] if status == "ok" else None,
            "reader": {"task_file": reader_path.name, "result_sha256": reader["result_sha256"]} if reader else None,
            "verifier": {"task_file": verifier_path.name, "result_sha256": verifier["result_sha256"]} if verifier else None,
            "not_attempted_claim_ids": verifier["not_attempted_claim_ids"] if verifier else base["expected_claim_ids"],
            "subtask_costs": costs, "completion_attempted": any(t["completion_attempted"] for t in costs),
            "completion_attempts_recorded": sum(bool(t["completion_attempted"]) for t in costs),
            "input_tokens": sum(t["input_tokens"] or 0 for t in costs),
            "output_tokens": sum(t["output_tokens"] or 0 for t in costs),
            "elapsed_seconds": sum(t["elapsed_seconds"] for t in costs),
            "generation_seconds": sum(t.get("generation_seconds", 0) for t in tasks),
            "json_schema_sha256": digest([t["json_schema_sha256"] for t in tasks]),
            "error_code": failure["error_code"] if failure else None,
            "error": failure["error"] if failure else None,
            "cost_incomplete": any(t["cost_incomplete"] for t in costs), "audit_warnings": []}


def verify_aggregate(path, value):
    from rag_research.evaluation.claimwise import verify_aggregate as verify_sentences

    path = Path(path)
    verify_checkpoint(value)
    require(value["execution_mode"] == MODE, "Not a reading aggregate")
    reader_path, verifier_path = child_paths(path)
    children = []
    binding = {**value["binding"], "aggregate_request_sha256": value["request_sha256"]}
    for stage, expected_path in (("reader", reader_path), ("verifier", verifier_path)):
        entry = value[stage]
        if entry is None:
            children.append(None)
            continue
        require(entry["task_file"] == expected_path.name, "Reading child path changed")
        task = read_json(expected_path)
        verify_checkpoint(task)
        expected_binding = ({**binding, "stage": "read_sources"} if stage == "reader" else
                            {**binding, "stage": "verify_after_reading", "reading_result_sha256": children[0]["result_sha256"]})
        require(task["result_sha256"] == entry["result_sha256"] and task["binding"] == expected_binding,
                "Reading child binding changed")
        if stage == "verifier":
            require(children[0]["status"] == "ok", "Cannot judge after reading failure")
            verify_sentences(expected_path, task)
        children.append(task)
    expected = derived(path, {k: value[k] for k in BASE_FIELDS}, *children)
    require({k: v for k, v in value.items() if k != "result_sha256"} == expected, "Reading aggregate differs from raw tasks")
    return value


def verify_once(client, generation, reader_generation, prompts, payload, path, binding, *, constraints):
    from rag_research.evaluation.claimwise import verify_once as verify_sentences
    from rag_research.evaluation.tasks import execute_task
    from rag_research.experiments.protocol import build_messages

    require(reader_generation is not None and prompts.get("source_reading_auxiliary") == "untrusted_reading_v1",
            "Explicit reading configuration required")
    # Validate the original four fields without allowing caller-supplied intermediate or gold information.
    build_messages({k: v for k, v in prompts.items() if k != "source_reading_auxiliary"}, "verify_claims", payload)
    request_key = digest({"mode": MODE, "binding": binding, "settings": asdict(generation),
                          "reader_settings": asdict(reader_generation), "prompts": prompts,
                          "constraints": constraints, "payload": payload})
    path = Path(path)
    base = {"schema_version": 1, "task": "verify_claims", "execution_mode": MODE, "request_sha256": request_key,
            "binding": binding, "expected_claim_ids": [c["claim_id"] for c in payload["claims"]]}
    if path.exists():
        saved = read_json(path)
        require(saved["request_sha256"] == request_key, "Source reading resume inputs changed")
        verify_aggregate(path, saved)
    else:
        checkpoint(path, derived(path, base))
    if not payload["claims"]:
        return checkpoint(path, derived(path, base))
    reader_path, verifier_path = child_paths(path)
    stage_binding = {**binding, "aggregate_request_sha256": request_key}
    reader = execute_task(client, reader_generation, prompts, "read_sources",
                          {k: payload[k] for k in ("question", "documents")}, reader_path,
                          {**stage_binding, "stage": "read_sources"}, constraints=constraints)
    if reader["status"] != "ok":
        return checkpoint(path, derived(path, base, reader))
    text = reader["raw_output"]
    if constraints == "thinking_json_passage_ids_v2":
        from rag_research.evaluation.reasoned_json import final_json

        text, _ = final_json(text)
    require(parse_reading(text, payload["documents"]) == reader["parsed"], "Saved reading differs from raw output")
    reading = validate_reading(reader["parsed"], payload["documents"])
    checkpoint(path, derived(path, base, reader))
    verifier = verify_sentences(client, generation, prompts, {**payload, "source_reading": reading}, verifier_path,
                                {**stage_binding, "stage": "verify_after_reading", "reading_result_sha256": reader["result_sha256"]},
                                constraints=constraints, mode="claimwise-v1")
    return checkpoint(path, derived(path, base, reader, verifier))
