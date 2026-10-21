"""Bound new Development calls before starting a QA; retain partial and unknown work."""

from pathlib import Path

from rag_research.experiments.frozen_trace import require
from rag_research.experiments.storage import read_json, verify_checkpoint
from rag_research.retrieval.common import file_hash


class DevelopmentStop(RuntimeError):
    def __init__(self, reason, snapshot):
        super().__init__(reason)
        self.reason, self.snapshot = reason, snapshot


def budget_snapshot(output):
    """Count raw native requests once, including durable children without aggregates."""
    output = Path(output)
    leaves, errors, unknown = [], [], []
    paths = [*sorted((output / "baseline").rglob("record.json")),
             *sorted((output / "internal").rglob("*.json"))]
    for path in paths:
        task = read_json(path)
        baseline = path.name == "record.json" and path.is_relative_to(output / "baseline")
        if not baseline and task.get("task") not in {
                "extract_claims", "read_sources", "verify_claims", "rewrite_answer"}:
            continue
        relative = path.relative_to(output).as_posix()
        if task.get("status") == "started":
            # It may have reached the server. Never repeat or treat the outcome as known.
            unknown.append(relative)
        else:
            verify_checkpoint(task)
        if task.get("status") == "error":
            errors.append(relative)
        if task.get("execution_mode") in {"source-reading-v1", "claimwise-v1"}:
            continue
        require(type(task.get("completion_attempted")) is bool, "Raw task needs a completion-attempt flag")
        if task["completion_attempted"]:
            leaves.append({"path": relative, "sha256": file_hash(path),
                           "unknown_outcome": task.get("status") == "started" or
                           task.get("error_code") == "interrupted_unknown_outcome" or bool(task.get("cost_incomplete"))})
            if leaves[-1]["unknown_outcome"] and relative not in unknown:
                unknown.append(relative)
    return {"recorded_native_attempts_upper_bound": len(leaves),
            "known_native_attempts": sum(not v["unknown_outcome"] for v in leaves),
            "possible_unknown_attempts": sum(v["unknown_outcome"] for v in leaves),
            "error_paths": errors, "unknown_or_interrupted_paths": unknown, "raw_calls": leaves,
            "model_answers_or_internal_scores_in_snapshot": False}


def pending_trace_calls(folder, trial_ids, fixed_claim_ids, *, mode="source-reading-v1"):
    """Missing raw reader/claim/rewrite leaves give the exact upper bound to reserve."""
    folder = Path(folder)
    require(mode in {"source-reading-v1", "claimwise-v1"}, "Unsupported main verification mode")
    require(len(trial_ids) == len(set(trial_ids)) and len(fixed_claim_ids) == len(set(fixed_claim_ids)),
            "Duplicate planned trials or fixed units")
    required = [folder / "rewrite.json"]
    if fixed_claim_ids:
        for trial in trial_ids:
            require(Path(trial).name == trial and trial not in {"", ".", ".."}, "Invalid trial ID")
            if mode == "source-reading-v1":
                required.append(folder / (trial + ".reading.json"))
            for claim in fixed_claim_ids:
                require(Path(claim).name == claim and claim not in {"", ".", ".."}, "Invalid fixed unit ID")
                suffix = ".verification.claims" if mode == "source-reading-v1" else ".claims"
                required.append(folder / (trial + suffix) / (claim + ".json"))
    return sum(not path.exists() for path in required)


def reserve_calls(output, maximum_attempts, maximum_new_calls):
    """Run only after taking the run lock, before any new QA/task journal is created."""
    require(type(maximum_attempts) is int and maximum_attempts > 0 and
            type(maximum_new_calls) is int and maximum_new_calls >= 0, "Invalid Development call budget")
    snapshot = budget_snapshot(output)
    if snapshot["error_paths"] or snapshot["unknown_or_interrupted_paths"]:
        raise DevelopmentStop("existing_error_or_unknown_outcome", snapshot)
    if snapshot["recorded_native_attempts_upper_bound"] + maximum_new_calls > maximum_attempts:
        raise DevelopmentStop("preregistered_call_budget_exhausted", snapshot)
    return {**snapshot, "maximum_attempts": maximum_attempts, "reserved_new_calls": maximum_new_calls}
