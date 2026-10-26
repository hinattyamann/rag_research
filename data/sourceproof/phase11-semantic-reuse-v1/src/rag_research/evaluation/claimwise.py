"""Durable one-request-per-fixed-sentence verification with full untrusted answer context."""

from dataclasses import asdict
from pathlib import Path

from rag_research.evaluation.tasks import execute_task
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.storage import checkpoint, read_json, verify_checkpoint

MODE = "claimwise-v1"
COST_FIELDS = ("completion_attempted", "input_tokens", "output_tokens", "elapsed_seconds", "error_code", "cost_incomplete")


def atomic_steps(tasks):
    """Collection and operational routes pay for every actual child request."""
    for task in tasks:
        if task.get("execution_mode") in {MODE, "source-reading-v1"}:
            yield from task["subtask_costs"]
        else:
            yield task


def payloads(payload, mode):
    if mode == "joint":
        return [(None, payload)]
    require(mode == MODE, "Unknown verification mode")
    return [(claim["claim_id"], {**payload, "claims": [{"claim_id": "c1", "text": claim["text"]}]})
            for claim in payload["claims"]]


def pending(path, mode="joint"):
    if mode == "source-reading-v1":
        from rag_research.evaluation.source_reading import pending as reading_pending

        return reading_pending(path)
    path = Path(path)
    if not path.exists():
        return True
    root = read_json(path)
    if mode == "joint":
        return False
    verify_checkpoint(root)
    require(root["execution_mode"] == MODE, "Saved verification mode differs")
    if root["status"] != "partial":
        return False
    children = [path.parent / (path.stem + ".claims") / (i + ".json") for i in root["expected_claim_ids"]]
    present = [read_json(p) for p in children if p.exists()]
    if any(t["status"] in {"started", "error"} for t in present):
        return False
    return any(not p.exists() for p in children)


def derived(path, base, children):
    ids = base["expected_claim_ids"]
    first_error = next((task for _, task in children if task["status"] != "ok"), None)
    status = "error" if first_error else "ok" if len(children) == len(ids) else "partial"
    verdicts = [{**task["parsed"]["verdicts"][0], "claim_id": original} for original, task in children if task["status"] == "ok"]
    score = sum(v["label"] == "supported" for v in verdicts) / len(ids) if status == "ok" and ids else None
    return {**base, "status": status if ids else "not_applicable", "parsed": {"verdicts": verdicts, "score": score}
            if status == "ok" else None,
            "not_attempted_claim_ids": ids[len(children):],
            "subtasks": [{"original_claim_id": original, "local_claim_id": "c1",
                          "task_file": (Path(path.stem + ".claims") / (original + ".json")).as_posix(),
                          "result_sha256": task["result_sha256"]} for original, task in children],
            "subtask_costs": [{k: task.get(k, 0 if k == "elapsed_seconds" else None) for k in COST_FIELDS}
                              for _, task in children],
            "completion_attempted": any(t["completion_attempted"] for _, t in children),
            "completion_attempts_recorded": sum(t["completion_attempted"] for _, t in children),
            "input_tokens": sum(t["input_tokens"] or 0 for _, t in children),
            "output_tokens": sum(t["output_tokens"] or 0 for _, t in children),
            "elapsed_seconds": sum(t.get("elapsed_seconds", 0) for _, t in children),
            "generation_seconds": sum(t.get("generation_seconds", 0) for _, t in children),
            "json_schema_sha256": digest([t["json_schema_sha256"] for _, t in children]),
            "error_code": first_error["error_code"] if first_error else None,
            "error": first_error["error"] if first_error else None,
            "cost_incomplete": any(t["cost_incomplete"] for _, t in children), "audit_warnings": []}


def verify_aggregate(path, value):
    """Recompute global IDs, score, costs and root fields from the durable child tasks."""
    path = Path(path)
    verify_checkpoint(value)
    require(value["execution_mode"] == MODE, "Not a claimwise aggregate")
    children = []
    for entry in value["subtasks"]:
        child = (path.parent / entry["task_file"]).resolve()
        require(child.is_relative_to((path.parent / (path.stem + ".claims")).resolve()), "Child task escapes aggregate")
        task = read_json(child)
        verify_checkpoint(task)
        require(task["result_sha256"] == entry["result_sha256"] and entry["local_claim_id"] == "c1" and
                task["binding"] == {**value["binding"], "aggregate_request_sha256": value["request_sha256"],
                                    "original_claim_id": entry["original_claim_id"]}, "Child task binding changed")
        children.append((entry["original_claim_id"], task))
    require([i for i, _ in children] == value["expected_claim_ids"][:len(children)], "Missing/reordered child claims")
    base = {k: value[k] for k in ("schema_version", "task", "execution_mode", "request_sha256", "binding", "expected_claim_ids")}
    expected = derived(path, base, children)
    require({k: v for k, v in value.items() if k != "result_sha256"} == expected, "Aggregate differs from raw child tasks")
    return value


def verify_once(client, generation, prompts, payload, path, binding, *, constraints="none", mode="joint",
                reader_generation=None):
    if mode == "source-reading-v1":
        from rag_research.evaluation.source_reading import verify_once as reading_verify

        return reading_verify(client, generation, reader_generation, prompts, payload, path, binding, constraints=constraints)
    if mode == "joint":
        return execute_task(client, generation, prompts, "verify_claims", payload, path, binding, constraints=constraints)
    from rag_research.experiments.protocol import build_messages

    require(mode == MODE and prompts.get("judge_payload") is None, "Claimwise requires fixed answer context")
    build_messages(prompts, "verify_claims", payload)  # Validate the original complete field/claim/document whitelist.
    request_key = digest({"binding": binding, "mode": MODE, "settings": asdict(generation),
                          "prompts": prompts, "constraints": constraints, "payload": payload})
    path = Path(path)
    base = {"schema_version": 1, "task": "verify_claims", "execution_mode": MODE,
            "request_sha256": request_key, "binding": binding,
            "expected_claim_ids": [c["claim_id"] for c in payload["claims"]]}
    if path.exists():
        saved = read_json(path)
        require(saved["request_sha256"] == request_key, "Claimwise resume inputs changed")
        verify_aggregate(path, saved)
        if saved["status"] != "partial":
            for original, local_payload in payloads(payload, mode):
                child = path.parent / (path.stem + ".claims") / (original + ".json")
                if not child.exists():
                    break
                execute_task(None, generation, prompts, "verify_claims", local_payload, child,
                             {**binding, "aggregate_request_sha256": request_key, "original_claim_id": original},
                             constraints=constraints)
            return saved
    else:
        checkpoint(path, derived(path, base, []))
    folder = path.parent / (path.stem + ".claims")
    folder.mkdir(exist_ok=True)
    children = []
    for original, local_payload in payloads(payload, mode):
        task = execute_task(client, generation, prompts, "verify_claims", local_payload, folder / (original + ".json"),
                            {**binding, "aggregate_request_sha256": request_key, "original_claim_id": original},
                            constraints=constraints)
        children.append((original, task))
        result = checkpoint(path, derived(path, base, children))
        if task["status"] != "ok":
            return result
    return checkpoint(path, derived(path, base, children))
