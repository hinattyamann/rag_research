"""Phase 9 reads completed Phase 8 artifacts without rerunning the Judge."""

import json
from dataclasses import asdict
from pathlib import Path

import yaml

from rag_research.experiments.decisions import decide
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.order_runner import load_traces
from rag_research.experiments.protocol import ROOT, load_protocol, task_config
from rag_research.experiments.storage import read_json, run_lock, verify_checkpoint, write_json
from rag_research.generation.auxiliary import auxiliary_identity, auxiliary_server_kwargs
from rag_research.generation.local import LocalServer
from rag_research.recovery.answer_rewrite import rewrite_once
from rag_research.retrieval.common import file_hash


def local_path(value, parent=ROOT):
    path = (ROOT / value).resolve()
    require(path.is_relative_to(parent.resolve()), "Path escapes permitted directory")
    return path


def load_source(config):
    source = local_path(config["source_order_run"], ROOT / "data/runs/order_sensitivity")
    baseline = local_path(config["baseline_answers"], ROOT / "data/runs")
    protocol_path = local_path(config["evaluation_config"])
    protocol, prompts, prompt_path = load_protocol(protocol_path)
    manifest, report = read_json(source / "manifest.json"), read_json(source / "report.json")
    require(report["manifest_sha256"] == digest(manifest), "Phase 8 manifest binding mismatch")
    require(manifest["config_sha256"] == file_hash(protocol_path) and
            manifest["prompts_sha256"] == file_hash(prompt_path), "Phase 8 protocol changed")
    require(manifest["baseline_answers_sha256"] == file_hash(baseline), "Baseline changed")
    # Historical manifests bind their own sources; new modules are not a reason to rerun Judge.
    for name, expected in manifest["source_sha256"].items():
        require(file_hash(local_path(name)) == expected, f"Historical Phase 8 source changed: {name}")
    ids = [e["record_id"] for e in manifest["traces"]]
    require(len(ids) == len(set(ids)) == report["record_count"], "Phase 8 record set mismatch")
    traces, qa_path = load_traces(protocol, baseline, ids)
    traces = {t["record_id"]: t for t in traces}
    records = {r["record_id"]: r for r in report["records"]}
    require(set(records) == set(ids), "Phase 8 report records mismatch")
    bindings = {"manifest.json": file_hash(source / "manifest.json"),
                "report.json": file_hash(source / "report.json")}
    output = []
    for entry in manifest["traces"]:
        identifier = entry["record_id"]
        folder = local_path((source / entry["directory"]).as_posix(), source)
        trace = read_json(folder / "trace.json")
        require(trace == traces[identifier] and trace["trace_sha256"] == entry["trace_sha256"],
                "Frozen trace differs from baseline")
        row = records[identifier]
        require(read_json(folder / "summary.json") == row, "Phase 8 summary differs from report")
        claims = read_json(folder / "claims.json")
        verify_checkpoint(claims)
        require(claims["result_sha256"] == row["extraction_result_sha256"], "Claims changed")
        require(claims["binding"]["manifest_sha256"] == digest(manifest) and
                claims["binding"]["trace_sha256"] == trace["trace_sha256"], "Claims binding differs")
        require(row["plan"] == entry["plan"] and row["threshold"] == protocol["decision"]["threshold"],
                "Phase 8 trial plan or threshold differs")
        require([{k: t[k] for k in spec} for t, spec in
                 zip(row["trials"], entry["plan"]["trials"], strict=True)] ==
                entry["plan"]["trials"], "Phase 8 trial inputs differ")
        tasks = {"extraction": claims, "judges": {}}
        for trial in row["trials"]:
            if "task_file" in trial:
                task_path = local_path((source / trial["task_file"]).as_posix(), source)
                task = read_json(task_path)
                verify_checkpoint(task)
                require(task["result_sha256"] == trial["result_sha256"], "Judge result changed")
                require(task["binding"]["manifest_sha256"] == digest(manifest) and
                        task["binding"]["trace_sha256"] == trace["trace_sha256"] and
                        task["binding"]["trial_id"] == trial["trial_id"], "Judge binding differs")
                score = task["parsed"]["score"] if task["status"] == "ok" else None
                require(trial["status"] == task["status"] and trial["score"] == score,
                        "Judge summary score differs")
                tasks["judges"][trial["trial_id"]] = task
            else:
                require(claims["status"] != "ok" and trial["score"] is None,
                        "Missing scorable Judge task")
            require(all(trial[k] == v for k, v in decide(trial["score"], row["threshold"]).items()),
                    "Phase 8 decision differs")
        for path in [folder / "trace.json", folder / "summary.json", folder / "claims.json"]:
            bindings[path.relative_to(source).as_posix()] = file_hash(path)
        for trial in row["trials"]:
            if "task_file" in trial:
                bindings[trial["task_file"]] = file_hash(source / trial["task_file"])
        output.append({"trace": trace, "evaluation": row, "tasks": tasks})
    baseline_rows = {r["record_id"]: r for r in
                     map(json.loads, baseline.read_text("utf-8").splitlines())}
    return protocol, prompts, prompt_path, qa_path, source, bindings, output, baseline_rows


def run_rewrites(config_path, output):
    config_path, output = Path(config_path).resolve(), Path(output).resolve()
    require(Path.cwd().resolve() == ROOT, "Run from repository root")
    require(output.is_relative_to(ROOT / "data/runs/answer_rewrite") and
            output != ROOT / "data/runs/answer_rewrite", "Unexpected rewrite output directory")
    config = yaml.safe_load(config_path.read_text("utf-8"))
    require(config["schema_version"] == 1 and config["purpose"] == "phase9-development-smoke",
            "Unexpected Phase 9 config")
    require(config["generate_for_every_question"] is True and config["automatic_retries"] == 0,
            "All questions need one counterfactual; no retries")
    protocol, prompts, prompt_path, qa_path, source, bindings, items, baseline = load_source(config)
    require(protocol["rewrite"] == {
        "input_document_order": "original_used_context", "include_initial_answer": True,
        "include_judge_feedback": False, "reuse_one_candidate_across_trials": True,
        "retrieve_again": False, "maximum_answer_candidates": 2,
        "failure_action": "keep_initial_answer_with_rewrite_failed_status"}, "Rewrite contract changed")
    generation = task_config(protocol, "rewrite_answer")
    paths = [Path(__file__), ROOT / "src/rag_research/recovery/answer_rewrite.py",
             ROOT / "scripts/run_answer_rewrite.py"]
    manifest = {"schema_version": 1, "purpose": config["purpose"],
                "study_version": config["study_version"], "config": config,
                "config_sha256": file_hash(config_path), "source_order_run": str(source.relative_to(ROOT)),
                "source_artifacts": bindings, "qa_path": str(qa_path.relative_to(ROOT)),
                "qa_sha256": file_hash(qa_path), "prompts_sha256": file_hash(prompt_path),
                "rubric_sha256": file_hash(local_path(config["quality_rubric"])),
                "generation": asdict(generation),
                **({"auxiliary_model": auxiliary_identity(protocol)} if "auxiliary_model_manifest" in protocol else {}),
                "source_sha256": {str(p.relative_to(ROOT)): file_hash(p) for p in paths}}
    with run_lock(output):
        path = output / "manifest.json"
        if path.exists():
            require(read_json(path) == manifest, "Phase 9 manifest changed; use new output directory")
        else:
            require({p.name for p in output.iterdir()} == {".run.lock"}, "Unbound rewrite artifacts")
            write_json(path, manifest)
        pending = [item for item in items if not
                   (output / digest(item["trace"]["record_id"])[:24] / "rewrite.json").exists()]
        session_index = len(list(output.glob("session-*.json"))) + 1
        records = []

        def collect(client):
            for item in items:
                trace = item["trace"]
                folder = output / digest(trace["record_id"])[:24]
                folder.mkdir(exist_ok=True)
                rewritten = rewrite_once(client, generation, prompts, trace, folder / "rewrite.json",
                                         {"manifest_sha256": digest(manifest),
                                          "trace_sha256": trace["trace_sha256"]})
                row = {**item, "baseline_cost": baseline[trace["record_id"]], "rewrite": rewritten}
                # Keep model messages/Gold separate: baseline row used only for offline route accounting.
                row["baseline_cost"] = {k: row["baseline_cost"].get(k) for k in
                                        ("input_tokens", "output_tokens", "generation_seconds",
                                         "context_seconds", "answer_generation_calls")}
                records.append(row)
                print(json.dumps({"record_id": trace["record_id"], "rewrite_status": rewritten["status"],
                                  "error": rewritten["error"]}), flush=True)

        if pending:
            with LocalServer(generation, output / f"server-{session_index}.log",
                             **auxiliary_server_kwargs(protocol)) as server:
                collect(server.client)
                session = {"completion_attempts_this_session": server.client.completion_attempts,
                           **server.report()}
        else:
            collect(None)  # Cached or interrupted journals never need another model call.
            session = {"completion_attempts_this_session": 0, "server_started": False}
        write_json(output / f"session-{session_index}.json", session)
        report = {"schema_version": 1, "manifest_sha256": digest(manifest), "records": records,
                  "record_count": len(records), "quality_status": "pending_manual_annotation",
                  "rewrite_attempts": sum(r["rewrite"]["completion_attempted"] for r in records),
                  "sessions": [read_json(p) for p in sorted(output.glob("session-*.json"))]}
        write_json(output / "report.json", report)
    return report
