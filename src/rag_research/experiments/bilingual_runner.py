"""Development connection runner using the common inference/task/checkpoint primitives."""

import gc
import json
import os
from collections import Counter
from pathlib import Path

import yaml

from rag_research.data.study_assets import load_assets, load_rows, parent_map
from rag_research.evaluation.order import trial_plan
from rag_research.evaluation.sentence_claims import claim_unit_language
from rag_research.experiments.frozen_trace import digest, freeze_record, require
from rag_research.experiments.order_runner import evaluate_traces
from rag_research.experiments.protocol import ROOT, task_config, validate_task_contract
from rag_research.experiments.storage import read_json, run_lock, verify_checkpoint, write_json
from rag_research.generation.artifacts import model_identity
from rag_research.generation.auxiliary import auxiliary_identity, auxiliary_server_kwargs
from rag_research.generation.config import load_config as load_baseline_config
from rag_research.generation.context import PromptSpec
from rag_research.generation.cuda_runtime import execution_identity, execution_kwargs
from rag_research.generation.local import LocalServer
from rag_research.pilot.baseline import baseline_once
from rag_research.recovery.answer_rewrite import rewrite_once
from rag_research.retrieval.bilingual import load_retriever
from rag_research.retrieval.common import file_hash, json_bytes
from rag_research.retrieval.parent_metrics import retrieval_metrics


def immutable(path, value):
    if path.exists():
        require(read_json(path) == value, "Bilingual run binding changed; preserve and use a new run")
    else:
        write_json(path, value)


def load_config(path):
    config = yaml.safe_load(Path(path).read_text("utf-8"))
    require(config["schema_version"] == 1 and config["purpose"] == "phase11-bilingual-development-candidate"
            and config["status"] == "candidate_not_frozen" and config["phase12_allowed"] is False,
            "This entry point is Development only, not Calibration/Evaluation")
    language = config["language"]
    require(language in {"en", "ja"} and config["data"]["split"] == "development", "Development language required")
    require(config["execution_scope"] == "connection_smoke_only", "Predeclare a new protocol for the main pilot")
    quality = config["quality"]
    require(quality["annotator"] == "Codex_AI" and quality["human_reviewed"] is False and
            quality["internal_judge_is_quality_truth"] is False and quality["llm_labels_are_final"] is False and
            set(quality["hide"]) >= {"condition", "score", "decision", "answer_stage", "judge_claims", "judge_reasons"},
            "Separate blinded external AI quality is required")
    asset_path = (ROOT / config["assets"]).resolve()
    require(asset_path.is_relative_to(ROOT), "Assets escape repository")
    assets = load_assets(asset_path)
    rows, qa_path = load_rows(assets, language, "development")
    baseline_path = (ROOT / config["baseline_config"]).resolve()
    require(baseline_path.is_relative_to(ROOT), "Baseline config escapes repository")
    baseline, generation = load_baseline_config(baseline_path)
    require(baseline["purpose"] == "phase11-bilingual-baseline-candidate" and
            baseline["retrieval"] == assets["retrieval"], "Baseline/asset retrieval conditions differ")
    prompt_path = (ROOT / config["prompts"]).resolve()
    initial_path = (ROOT / config["baseline_prompts"]).resolve()
    require(prompt_path.is_relative_to(ROOT) and initial_path.is_relative_to(ROOT), "Prompts escape repository")
    prompts = yaml.safe_load(prompt_path.read_text("utf-8"))
    validate_task_contract(config, prompts)
    require(claim_unit_language(prompts.get("claim_units")) == language, "Claim unit language differs")
    prompt = PromptSpec(**yaml.safe_load(initial_path.read_text("utf-8")))
    ids = config["data"]["record_ids"]
    lookup = {r["record_id"]: r for r in rows}
    require(ids and len(ids) <= 2 and len(ids) == len(set(ids)) and set(ids) <= set(lookup),
            "Explicit unique small Development connection IDs required")
    chosen = [lookup[i] for i in ids]
    require(all(r["is_answerable"] for r in chosen), "Bilingual connection uses source-answered QA")
    return config, assets, chosen, qa_path, baseline, generation, prompt, prompts


def internal_complete(internal, binding):
    for entry in binding["traces"]:
        folder = internal / entry["directory"]
        if not (folder / "claims.json").exists() or not (folder / "rewrite.json").exists():
            return False
        claims = read_json(folder / "claims.json")
        if claims["status"] == "ok" and not all((folder / (t["trial_id"] + ".json")).exists()
                                                for t in entry["plan"]["trials"]):
            return False
    return True


def run(config_path, output, *, stage="all"):
    config_path, output = Path(config_path).resolve(), Path(output).resolve()
    parent = ROOT / "data/runs/bilingual_development"
    require(Path.cwd().resolve() == ROOT and output.is_relative_to(parent) and output != parent,
            "Run from repository root into a new bilingual Development run")
    require(stage in {"baseline", "internal", "all"}, "Unknown execution stage")
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    config, assets, rows, qa_path, baseline, generation, initial_prompt, prompts = load_config(config_path)
    sources = sorted((ROOT / "src/rag_research").rglob("*.py"))
    sources += [config_path, ROOT / config["assets"], ROOT / config["baseline_config"],
                ROOT / config["baseline_prompts"], ROOT / config["prompts"], ROOT / "scripts/run_bilingual_development.py"]
    selection = [{"record_id": r["record_id"], "question": r["question"]} for r in rows]
    manifest = {"schema_version": 1, "purpose": config["purpose"], "status": "candidate_not_frozen",
                "language": config["language"], "config": config, "baseline": baseline,
                "baseline_model": model_identity(), "auxiliary_model": auxiliary_identity(config),
                **execution_identity(baseline),
                "qa_path": qa_path.relative_to(ROOT).as_posix(), "qa_sha256": file_hash(qa_path),
                "selection": selection, "selection_scope": "known_development_connection_not_calibration",
                "source_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sources},
                "gate11_passed": False, "phase12_allowed": False}
    with run_lock(output):
        immutable(output / "manifest.json", manifest)
        base_dir = output / "baseline"
        base_dir.mkdir(exist_ok=True)
        records = []

        def collect_baseline(client, retriever):
            for spec in selection:
                folder = base_dir / digest(spec["record_id"])[:24]
                folder.mkdir(exist_ok=True)
                records.append(baseline_once(client, retriever, generation, initial_prompt,
                               baseline["retrieval"]["top_k"], spec, folder,
                               {"manifest_sha256": digest(manifest)}))
                print(json.dumps({"stage": "baseline", "completed": len(records),
                                  "planned": len(selection), "status": records[-1]["status"]}), flush=True)

        if stage in {"baseline", "all"}:
            pending = any(not (base_dir / digest(r["record_id"])[:24] / "record.json").exists() for r in selection)
            session = len(list(base_dir.glob("session-*.json"))) + 1
            if pending:
                retriever = load_retriever(assets, config["language"])
                with LocalServer(generation, base_dir / f"server-{session}.log", **execution_kwargs(baseline)) as server:
                    collect_baseline(server.client, retriever)
                    write_json(base_dir / f"session-{session}.json", server.report())
                del retriever
                gc.collect()
            else:
                collect_baseline(None, None)
            (base_dir / "answers.jsonl").write_bytes(b"".join(json_bytes(r) for r in records))
        else:
            for spec in selection:
                saved = read_json(base_dir / digest(spec["record_id"])[:24] / "record.json")
                verify_checkpoint(saved)
                require(saved["binding"] == {"manifest_sha256": digest(manifest)} and
                        saved["question"] == spec["question"], "Baseline provenance differs")
                records.append(saved)
        mapping = parent_map(assets, config["language"])
        metadata = {r["record_id"]: r for r in rows}
        offline = [{"record_id": r["record_id"], "status": r["status"],
                    "retrieval_metrics": retrieval_metrics(
                        [h["passage_id"] for h in r.get("retrieved_context", [])], mapping,
                        metadata[r["record_id"]]["gold_parent_ids"],
                        missing_source_units=metadata[r["record_id"]]["unavailable_cited_reference_ids"])} for r in records]
        write_json(output / "retrieval.offline.json", {"scope": "offline_only_not_quality_truth", "records": offline})
        if stage == "baseline":
            return {"stage": stage, "baseline_count": len(records), "baseline_ok": sum(r["status"] == "ok" for r in records)}
        traces, failures = [], []
        for record in records:
            if record["status"] == "ok" and record.get("used_context"):
                traces.append(freeze_record(record))
            else:
                failures.append({"record_id": record["record_id"], "status": record["status"],
                                 "error": record.get("error"), "reason": "baseline_not_freezable"})
        internal = output / "internal"
        internal.mkdir(exist_ok=True)
        binding = {"manifest_sha256": digest(manifest), "traces": [
            {"record_id": t["record_id"], "directory": digest(t["record_id"])[:24],
             "trace_sha256": t["trace_sha256"], "plan": trial_plan(t, config)} for t in traces]}
        immutable(internal / "manifest.json", binding)
        assembled = []

        def collect_internal(client):
            def public(message, **kwargs):
                value = json.loads(message)
                print(json.dumps({k: v for k, v in value.items() if k in {"task", "status", "error"}}), flush=True)
                require(value.get("error_code") != "input_overflow", "Input overflow stops the connection run")
            for trace, entry in zip(traces, binding["traces"], strict=True):
                per_manifest = {**binding, "traces": [entry]}
                evaluations, _ = evaluate_traces(client, config, prompts, [trace], per_manifest, internal, notify=public)
                folder = internal / entry["directory"]
                rewritten = rewrite_once(client, task_config(config, "rewrite_answer"), prompts, trace,
                                          folder / "rewrite.json", {"manifest_sha256": digest(per_manifest),
                                                                    "trace_sha256": trace["trace_sha256"]})
                require(rewritten.get("error_code") != "input_overflow", "Rewrite input overflow stops the connection run")
                tasks = {"extraction": read_json(folder / "claims.json"), "judges": {
                    t["trial_id"]: read_json(internal / t["task_file"]) for t in evaluations[0]["trials"] if "task_file" in t}}
                original_record = next(r for r in records if r["record_id"] == trace["record_id"])
                assembled.append({"trace": trace, "evaluation": evaluations[0], "tasks": tasks,
                                  "rewrite": rewritten, "baseline_cost": {k: original_record.get(k) for k in
                                  ("input_tokens", "output_tokens", "generation_seconds", "context_seconds", "answer_generation_calls")}})
                print(json.dumps({"stage": "internal", "completed": len(assembled),
                                  "rewrite_status": rewritten["status"]}), flush=True)
        session = len(list(internal.glob("session-*.json"))) + 1
        if traces and not internal_complete(internal, binding):
            with LocalServer(task_config(config, "verify_claims"), internal / f"server-{session}.log",
                             **auxiliary_server_kwargs(config)) as server:
                collect_internal(server.client)
                write_json(internal / f"session-{session}.json", server.report())
        else:
            collect_internal(None)
        report = {"schema_version": 1, "purpose": config["purpose"], "manifest_sha256": digest(manifest),
                  "language": config["language"], "selected_qa_count": len(rows), "records": assembled,
                  "failures": failures, "quality_status": "pending_external_blinded_annotation",
                  "gate11_passed": False, "phase12_allowed": False}
        write_json(output / "report.private.json", report)
        return {"selected_qa_count": len(rows), "trace_count": len(assembled), "baseline_failures": len(failures),
                "judge_status_counts": dict(Counter(t["status"] for r in assembled for t in r["evaluation"]["trials"])),
                "rewrite_statuses": [r["rewrite"]["status"] for r in assembled], "quality_status": report["quality_status"]}
