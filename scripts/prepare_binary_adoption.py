"""Register binary-v2 and its single final validation, without new QA or inference."""

import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import yaml  # noqa: E402

from rag_research.experiments.bilingual_main import validate_main_policy  # noqa: E402
from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.protocol import ROOT  # noqa: E402
from rag_research.experiments.semantic_adoption import (  # noqa: E402
    BINARY,
    BINARY_RULES,
    KNOWN_GATE_V2,
)
from rag_research.experiments.storage import read_json, write_json  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def bind(name):
    return {"path": name, "sha256": file_hash(ROOT / name)}


def prepare():
    outputs = ["configs/phase11_known_trace_regression_v10.json", "configs/phase11_known_trace_candidate_v10.yaml",
        "configs/phase11_main_development_execution_policy_v2.json",
        "configs/phase11_bilingual_calibration_execution_rules_v2.json",
        "configs/phase11_bilingual_freeze_decisions_v2.json",
        "data/manifests/phase11_review_development_preregistration_v1.json"]
    require(all(not (ROOT / name).exists() for name in outputs), "Preserve existing binary-v2 preregistration")
    handover = read_json(ROOT / "data/manifests/phase11_chat_handover_v1.json")
    changed_sources = []
    for name, info in handover["files"].items():
        path = ROOT / name
        if path.is_file() and path.stat().st_size == info["size_bytes"] and file_hash(path) == info["sha256"]:
            continue
        require(name.startswith(("src/", "scripts/")), "Preserved handover evidence missing or changed: " + name)
        previous = subprocess.check_output(["git", "show", handover["base_commit"] + ":" + name], cwd=ROOT)
        require(len(previous) == info["size_bytes"] and hashlib.sha256(previous).hexdigest() == info["sha256"],
                "Historical source must remain recoverable at its original commit: " + name)
        changed_sources.append(name)
    old = read_json(ROOT / "configs/phase11_known_trace_regression_v9.json")
    plan = deepcopy(old)
    plan["gate"] = deepcopy(KNOWN_GATE_V2)
    require(len(plan["cases"]) == 15 and sum(len(c["claims"]) for c in plan["cases"]) == 42 and
            plan["max_completion_attempts"] == 84, "Preserve full known15/42/84 and original Expected")
    write_json(ROOT / outputs[0], plan)
    config = yaml.safe_load((ROOT / "configs/phase11_known_trace_candidate_v9.yaml").read_text())
    config.update(study_version="known15-q6-temperature-binary-v10", diagnostics=outputs[0])
    (ROOT / outputs[1]).write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))
    for source, target in zip(("configs/phase11_main_development_execution_policy_v1.json",
            "configs/phase11_bilingual_calibration_execution_rules_v1.json"), outputs[2:4], strict=True):
        policy = read_json(ROOT / source)
        policy["semantic_adoption_version"] = BINARY
        policy["created_at_utc"] = datetime.now(UTC).isoformat()
        rules = policy["semantic_adoption_after_blind_seal"]
        for key in ("minimum_exact_label_accuracy_per_language", "minimum_supported_label_accuracy_per_language",
                    "maximum_definite_negative_false_support"):
            rules.pop(key)
        rules.update(BINARY_RULES)
        if "candidate_config" in policy:
            policy["status"] = "preregistered"
            policy["candidate_config"] = bind("configs/phase11_semantic_candidate_v20.yaml")
            policy["known_regression_required"] = "New complete known15/42unit/30condition/84call binary-v2; no result claimed"
            policy["time_policy"]["prior_rough_generation_estimate_hours_for_both_languages"] = [25.6, 33.8]
            policy["time_policy"]["estimate_scope"] = "Judge only, five units per QA; not wall-time bound/CI; other stages and review additional"
        validate_main_policy(policy)
        write_json(ROOT / target, policy)
    freeze = read_json(ROOT / "configs/phase11_bilingual_freeze_decisions_v1.json")
    freeze["semantic_adoption_version"] = BINARY
    write_json(ROOT / outputs[4], freeze)
    registration = {"schema_version": 1, "purpose": "phase11-review-single-final-candidate-development-preregistration",
        "created_at_utc": datetime.now(UTC).isoformat(), "semantic_adoption_version": BINARY,
        "candidate": bind("configs/phase11_semantic_candidate_v20.yaml"),
        "known_config": bind(outputs[1]), "known_plan": bind(outputs[0]),
        "preserved_handover": bind("data/manifests/phase11_chat_handover_v1.json"),
        "preserved_handover_files_verified": len(handover["files"]),
        "current_adoption_sources_changed_with_old_git_blobs_preserved": changed_sources,
        "previous_recorded_all9b_attempts": 851, "previous_unknown_responses": 2,
        "old_limits_and_unused_not_reallocated": {"ceiling": 920, "unused": [69, 42, 42, 81, 42]},
        "maximum_additional_candidates": 1, "maximum_additional_completion_attempts": 188,
        "maximum_cumulative_all9b_attempts": 1039, "maximum_native_task_seconds": 14400,
        "maximum_runtime_diagnostic_attempts_within_total": 24,
        "allocated_calls": {"runtime_smoke": 2, "fresh_complete_known": 84},
        "unallocated_calls_not_automatically_usable": 102,
        "runtime_smoke_targets": [{"case_id": "known-gpu-31e646aa9601", "order": "original", "claim_id": "c1"},
                                  {"case_id": "known-warm-front", "order": "original", "claim_id": "c2"}],
        "runtime_smoke_selection_reason": "First is the old unknown CUDA-failed request; second checks an independent known table input. Full answer/evidence/prompt/schema unchanged, not a semantic gate.",
        "time_enforcement": "Sequential supervised Native wall seconds (including startup/preflight/overhead) <=14400, a conservative upper bound on summed Task seconds; reserve 15s termination grace, timeout TERM then KILL. Before each launch subtract prior wall seconds. Per-call adopted timeout1200 unchanged. No request retry after timeout; preserve unknown raw/cost and audit without generation.",
        "continuation": "Generation0 full input fit/full CUDA -> 2-call runtime smoke health -> one fresh complete 84-call known run. Any health error stops. Complete all known conditions for binary class coverage; adoption only after whole-run audit. No new model/sampler/prompt; reuse unchanged prior bilingual70 and format evidence.",
        "prerequisite_reused": deepcopy(plan["prerequisite"]),
        "inference_core_change": False, "runtime_driver_OS_change": False,
        "no_new_or_evaluation_qa_read": True, "new_model_calls": 0,
        "main_calibration_and_evaluation_calls": 0, "gate11_passed": False, "phase12_allowed": False,
        "new_protocol_files": {name: file_hash(ROOT / name) for name in outputs[:-1]}}
    write_json(ROOT / outputs[-1], registration)
    return {"preserved_files": len(handover["files"]), "new_protocol_files": len(outputs), "new_model_calls": 0}


if __name__ == "__main__":
    print(json.dumps(prepare()))
