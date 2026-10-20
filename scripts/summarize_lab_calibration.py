"""Audit sealed GPU Calibration, without freezing conditions or reading Evaluation."""

import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.frozen_trace import digest, require  # noqa: E402
from rag_research.experiments.storage import checkpoint, read_json  # noqa: E402
from rag_research.generation.cuda_runtime import verify_cuda_runtime  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def main():
    spec = importlib.util.spec_from_file_location("freeze", ROOT / "scripts/finalize_phase11.py")
    freeze = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freeze)
    run = ROOT / "data/runs/calibration/phase11-gpu-twenty-v2"
    selection = ROOT / "data/manifests/phase11_gpu_calibration_selection_manifest.json"
    candidate, chosen, report, records, tasks, provenance = freeze.verify_calibration(
        ROOT, run, selection, run / "source_snapshot")
    audit_path = run / "semantic_audit_v2.json"
    audit = read_json(audit_path)
    require(freeze.semantic_check(audit, file_hash(run / "calibration_report.json"), records),
            "Every fixed unit needs a valid semantic review")
    generated = [t for t in tasks if t.get("completion_attempted")]
    require(len(generated) == 128 and all(t["status"] == "ok" and freeze.native_check(t)
                                         for t in generated), "Native audit failed")
    semantic = {(x["record_id"], x["claim_id"]): x for x in audit["claims"]}
    confusion, clear_confusion = Counter(), Counter()
    mismatch_by_unit = Counter()
    same_schema = True
    for row in records:
        trace = row["trace"]
        schemas = set()
        for task in row["tasks"]["judges"].values():
            payload = json.loads(task["messages"][-1]["content"].split("Input JSON:\n", 1)[1])
            require(set(payload) == {"question", "claims", "documents"}
                    and payload["question"] == trace["question"]
                    and payload["claims"] == row["evaluation"]["claims"], "Judge fixed inputs differ")
            require({d["passage_id"]: d for d in payload["documents"]} ==
                    {d["passage_id"]: d for d in trace["documents"]}, "Evidence content differs")
            schemas.add(task["json_schema_sha256"])
            require(task["input_tokens"] + task["settings"]["max_output_tokens"] <=
                    task["settings"]["context_tokens"], "Input reservation exceeded")
            for verdict in task["parsed"]["verdicts"]:
                review = semantic[trace["record_id"], verdict["claim_id"]]
                pair = review["expected_label"] + " -> " + verdict["label"]
                confusion[pair] += 1
                if not review["ambiguous_scope"]:
                    clear_confusion[pair] += 1
                if review["expected_label"] != verdict["label"]:
                    mismatch_by_unit[trace["record_id"] + "/" + verdict["claim_id"]] += 1
        same_schema &= len(schemas) <= 1
        rewrite = row["rewrite"]
        payload = json.loads(rewrite["messages"][-1]["content"].split("Input JSON:\n", 1)[1])
        require(set(payload) == {"question", "answer", "documents"}
                and payload["question"] == trace["question"] and payload["answer"] == trace["answer"]
                and payload["documents"] == trace["documents"], "Rewrite changed fixed inputs")
        require(rewrite["final_answer_tokens"] <= 512, "Rewrite final answer exceeded 512 tokens")
    require(same_schema, "Order changed the output schema")
    baseline = list(map(json.loads, (run / "baseline/answers.jsonl").read_text().splitlines()))
    require(len(baseline) == 20 and all(r["status"] == "ok" and r["finish_reason"] in {"eos", "word"}
            and r["input_tokens"] + 512 <= 4096 and r["output_tokens"] <= 512
            and not r["runtime_response"].get("truncated") for r in baseline), "Baseline health failed")
    initial = read_json(run / "baseline/session-1.json")
    auxiliary = read_json(run / "internal/session-1.json")
    require(initial["full_gpu_offload"] and auxiliary["full_gpu_offload"], "Offload not complete")
    _, runtime = verify_cuda_runtime()
    from rag_research.generation.artifacts import MODEL_DIR, MODEL_FILE, MODEL_SHA256

    model = read_json(ROOT / "data/manifests/phase10_auxiliary_qwen3_manifest.json")
    model_files = {(MODEL_DIR / MODEL_FILE).as_posix(): MODEL_SHA256,
                   **{x["path"]: x["sha256"] for x in model["files"]}}
    runtime_directory = read_json(ROOT / "configs/lab_cuda_runtime.json")["directory"]
    runtime_files = {runtime_directory + "/" + name: sha for name, sha in runtime["files"].items()}
    task_files = []
    for row in records:
        folder = run / "internal" / digest(row["trace"]["record_id"])[:24]
        task_files += [folder / "rewrite.json", *[folder / (key + ".json") for key in row["tasks"]["judges"]]]

    def reference(path):
        return {"path": path.relative_to(ROOT).as_posix(), "sha256": file_hash(path)}

    runtime_proof = checkpoint(run / "runtime_evidence.json", {
        "purpose": "phase11-target-runtime-calibration", "backend": "CUDA",
        "actual_gpu_offload": True, "offloaded_layers": auxiliary["offloaded_layers"],
        "gpu_devices": [read_json(ROOT / "data/runs/lab/ubuntu-inventory-v1.json")["nvidia_smi"]["stdout"].strip()],
        "completion_attempts": len(generated), "protocol_sha256": file_hash(ROOT / candidate["config"]["internal_protocol"]),
        "native_audits_valid": True, "semantic_check_completed": True,
        "semantic_check_is_not_approval": True,
        "summed_step_seconds": report["analysis"]["auxiliary_collection_cost"]["summed_step_seconds"],
        "runtime_files_sha256": runtime_files, "model_files_sha256": model_files,
        "probe_tasks": [reference(p) for p in task_files], "server_log": reference(run / "internal/server-1.log"),
        "baseline_completions": 20, "baseline_session": reference(run / "baseline/session-1.json"),
        "baseline_server_log": reference(run / "baseline/server-1.log"), "semantic_audit": reference(audit_path)})
    require(freeze.runtime_output_check(ROOT, runtime_proof), "Runtime evidence failed")
    routes = defaultdict(list)
    for row in report["analysis"]["routes"]:
        routes[row["route"]].append(row)
    route_summary = {key: {"quality": dict(Counter(r["quality_status"] for r in rows)),
        "missed_improvements": sum(r["missed_improvement"] is True for r in rows),
        "harmful_rewrites": sum(r["harmful_rewrite"] is True for r in rows),
        "calls": sum(r["operational_cost"]["recorded_completion_attempts"] for r in rows)}
        for key, rows in routes.items()}
    judges = [t for row in records for t in row["tasks"]["judges"].values()]
    rewrites = [row["rewrite"] for row in records]
    old = read_json(ROOT / "data/runs/lab/transfer-audit-v1.json")
    changed = [p for p, sha in old["inventory_sha256"].items() if file_hash(ROOT / p) != sha]
    require(not changed, "Transferred historical files changed")
    selected = {r["record_id"] for r in chosen["records"]}
    comparison = [row for row in records if row["trace"]["record_id"] in
                  {r["record_id"] for r in report["per_question_disagreement"]}]
    summary = {"schema_version": 1, "purpose": "phase11-gpu-calibration-complete-not-final-freeze",
        "recorded_at_utc": datetime.now(UTC).isoformat(), "implementation_commit": "d2c6550",
        "planned_questions": len(selected), "processed_questions": len(records),
        "baseline_successful": len(baseline), "standalone_refusals": sum(not r["evaluation"]["claims"] for r in records),
        "comparable_questions": report["comparable_questions"], "judge_calls": len(judges), "rewrite_calls": len(rewrites),
        "native_generated_tasks_verified": len(generated), "baseline_generated_tasks_verified": len(baseline),
        "fixed_units_audited": len(audit["claims"]), "ambiguous_audit_units": sum(x["ambiguous_scope"] for x in audit["claims"]),
        "human_reviewed": False, "quality_labels_frozen_before_private_analysis": True,
        "quality_candidates": 40, "quality_transitions": report["analysis"]["quality_transitions"],
        "health_gate": report["health_gate"], "parser_check": freeze.parser_check(report, tasks),
        "semantic_audit_completed": True, "semantic_acceptance_pending": True,
        "diagnostic_label_counts_not_general_accuracy": dict(confusion),
        "clear_scope_label_counts_not_general_accuracy": dict(clear_confusion),
        "mismatches_by_fixed_unit": dict(mismatch_by_unit),
        "order_flip_questions": sum(r["evaluation"]["order_group"]["both_decisions_observed"] for r in comparison),
        "repeat_flip_questions": sum(r["evaluation"]["repeat_group"]["both_decisions_observed"] for r in comparison),
        "mean_paired_disagreement_difference": mean(r["paired_difference"] for r in report["per_question_disagreement"]),
        "route_summary": route_summary, "auxiliary_collection_cost": report["analysis"]["auxiliary_collection_cost"],
        "mean_judge_seconds": mean(t["elapsed_seconds"] for t in judges),
        "mean_rewrite_seconds": mean(t["elapsed_seconds"] for t in rewrites),
        "baseline_generation_seconds": sum(r["generation_seconds"] for r in baseline),
        "baseline_context_seconds": sum(r["context_seconds"] for r in baseline),
        "baseline_retrieval_seconds": sum(r["retrieval_seconds"] for r in baseline),
        "maximum_judge_output_tokens": max(t["output_tokens"] for t in judges),
        "maximum_rewrite_output_tokens": max(t["output_tokens"] for t in rewrites),
        "maximum_rewrite_final_answer_tokens": max(t["final_answer_tokens"] for t in rewrites),
        "question_claim_evidence_and_schema_fixed": True, "rewrite_inputs_verified": True,
        "transferred_historical_files_rechecked": len(old["inventory_sha256"]), "historical_files_changed": changed,
        "gate11_passed": False, "phase12_started": False,
        "summarizer_sha256": file_hash(Path(__file__)),
        "artifacts_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sorted(run.rglob("*")) if p.is_file()},
        "lab_artifacts_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p)
                                  for p in sorted((ROOT / "data/runs/lab").rglob("*")) if p.is_file()}}
    path = ROOT / "data/manifests/phase11_gpu_calibration_result_manifest.json"
    require(not path.exists(), "Preserve the previous audit manifest")
    checkpoint(path, summary)
    print(json.dumps({k: summary[k] for k in ("comparable_questions", "health_gate", "fixed_units_audited",
                     "parser_check", "order_flip_questions", "repeat_flip_questions", "quality_transitions")}, indent=2))


if __name__ == "__main__":
    main()
