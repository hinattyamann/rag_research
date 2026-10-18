"""Fixed pilot inference; only question counters are exposed to the external assessor."""

import json
from dataclasses import asdict
from datetime import UTC, datetime

from rag_research.evaluation.order import trial_plan
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.order_runner import evaluate_traces, load_traces
from rag_research.experiments.protocol import ROOT, load_protocol, task_config
from rag_research.experiments.storage import (
    checkpoint,
    read_json,
    run_lock,
    verify_checkpoint,
    write_json,
)
from rag_research.generation.artifacts import model_identity
from rag_research.generation.local import LocalServer
from rag_research.pilot.materials import load_offline, publish
from rag_research.recovery.answer_rewrite import rewrite_once
from rag_research.retrieval.common import file_hash


def health_gate(records, rules):
    tasks = [t for r in records for t in [r["tasks"]["extraction"],
             *r["tasks"]["judges"].values(), r["rewrite"]]]
    if rules["stop_on_input_overflow"] and any(t.get("error_code") == "input_overflow" for t in tasks):
        return {"status": "stopped", "reason": "input_overflow", "checked_questions": len(records)}
    count = rules["after_questions"]
    if len(records) < count:
        return {"status": "pending", "checked_questions": len(records)}
    initial = records[:count]
    complete = sum(all(r["evaluation"][g]["valid_trials"] == r["evaluation"][g]["planned_trials"]
                       and r["evaluation"][g]["valid_pairs"] > 0 for g in ("order_group", "repeat_group"))
                   for r in initial)
    judges = [t for r in initial for t in r["tasks"]["judges"].values()]
    fraction = sum(t["status"] == "error" for t in judges) / len(judges) if judges else None
    reasons = []
    if complete < rules["minimum_complete_scorable_questions"]:
        reasons.append("too_few_complete_scorable_questions")
    if fraction is not None and fraction > rules["maximum_judge_error_fraction"]:
        reasons.append("judge_error_fraction_exceeded")
    return {"status": "stopped" if reasons else "passed", "reasons": reasons,
            "checked_questions": count, "complete_scorable_questions": complete,
            "judge_error_fraction": fraction}


def pilot_identity(config_path, config, selection, baseline, traces):
    paths = [config_path, ROOT / config["internal_protocol"],
             ROOT / config["quality_protocol"], ROOT / "configs/quality_ai_prompt_v1.txt",
             ROOT / "src/rag_research/generation/local.py", ROOT / "pyproject.toml", ROOT / "uv.lock"]
    for directory in ("pilot", "experiments", "evaluation", "recovery"):
        paths.extend(sorted((ROOT / "src/rag_research" / directory).glob("*.py")))
    protocol, _, prompt_path = load_protocol(ROOT / config["internal_protocol"])
    return {"schema_version": 1, "purpose": "phase10-development-pilot-not-final-evaluation",
            "study_version": config["study_version"], "selection_sha256": digest(selection),
            "config": config, "baseline_answers_sha256": file_hash(baseline),
            "baseline_provenance_sha256": file_hash(baseline.parent / "run_manifest.json"),
            "qa_sha256": file_hash(ROOT / config["qa_path"]), "model": model_identity(),
            "prompt_sha256": file_hash(prompt_path),
            "auxiliary_runtime": asdict(task_config(protocol, "verify_claims")),
            "quality_assessor": "Codex AI", "human_reviewed": False,
            "source_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths},
            "traces": [{"record_id": t["record_id"], "trace_sha256": t["trace_sha256"],
                        "directory": digest(t["record_id"])[:24], "plan": trial_plan(t, protocol)}
                       for t in traces]}


def run_internal(config_path, config, selection, output):
    baseline_path = output / "baseline/answers.jsonl"
    provenance = read_json(output / "baseline/run_manifest.json")
    require(provenance["status"] == "completed", "Baseline not completed")
    baseline_rows = list(map(json.loads, baseline_path.read_text("utf-8").splitlines()))
    selected_ids = {r["record_id"] for r in selection["records"]}
    require({r["record_id"] for r in baseline_rows} == selected_ids, "Baseline selection differs")
    successful = [r["record_id"] for r in baseline_rows if r["status"] == "ok"]
    require(bool(successful), "No successful baseline: preserve failures, do not replace questions")
    protocol, prompts, _ = load_protocol(ROOT / config["internal_protocol"])
    traces, _ = load_traces(protocol, baseline_path, successful)
    trace_map = {t["record_id"]: t for t in traces}
    baseline_map = {r["record_id"]: r for r in baseline_rows}
    traces = [trace_map[s["record_id"]] for s in selection["records"] if s["record_id"] in trace_map]
    manifest = pilot_identity(config_path, config, selection, baseline_path, traces)
    internal = output / "internal"
    qa, gold = load_offline(config, selected_ids)
    with run_lock(internal):
        path = internal / "manifest.json"
        if path.exists():
            require(read_json(path) == manifest, "Pilot conditions changed; preserve run and use new version")
        else:
            require({p.name for p in internal.iterdir()} == {".run.lock"}, "Unbound internal artifacts")
            write_json(path, manifest)
        missing = [entry for entry in manifest["traces"] if not
                   (internal / entry["directory"] / "completed.json").exists()]
        records = []
        stopped = None

        def progress():
            write_json(output / "progress.json", {
                "stage": "internal", "planned_questions": len(selection["records"]),
                "baseline_successful": len(successful), "baseline_failed": len(baseline_rows) - len(successful),
                "internal_completed_questions": len(records),
                "quality_ready_packets": len(records), "updated_at_utc": datetime.now(UTC).isoformat()})

        def collect(client):
            nonlocal stopped
            for index, (trace, entry) in enumerate(zip(traces, manifest["traces"], strict=True)):
                folder = internal / entry["directory"]
                folder.mkdir(exist_ok=True)
                complete_path = folder / "completed.json"
                if complete_path.exists():
                    row = read_json(complete_path)
                    verify_checkpoint(row)
                    require(row["pilot_manifest_sha256"] == digest(manifest) and row["trace"] == trace,
                            "Saved pilot question changed")
                else:
                    binding_manifest = {"purpose": manifest["purpose"], "run_id": output.relative_to(ROOT).as_posix(),
                                        "parent_manifest_sha256": digest(manifest), "traces": [entry]}
                    write_json(folder / "binding_manifest.json", binding_manifest)

                    def private_event(message, **kwargs):
                        with (folder / "events.private.jsonl").open("a", encoding="utf-8") as target:
                            target.write(message + "\n")

                    evaluations, _ = evaluate_traces(client, protocol, prompts, [trace], binding_manifest,
                                                     internal, notify=private_event)
                    claims = read_json(folder / "claims.json")
                    judges = {t["trial_id"]: read_json(internal / t["task_file"])
                              for t in evaluations[0]["trials"] if "task_file" in t}
                    rewritten = rewrite_once(
                        client, task_config(protocol, "rewrite_answer"), prompts, trace,
                        folder / "rewrite.json", {"manifest_sha256": digest(manifest),
                                                   "trace_sha256": trace["trace_sha256"]})
                    base = baseline_map[trace["record_id"]]
                    row = checkpoint(complete_path, {
                        "pilot_manifest_sha256": digest(manifest), "trace": trace,
                        "evaluation": evaluations[0], "rewrite": rewritten,
                        "tasks": {"extraction": claims, "judges": judges},
                        "baseline_cost": {k: base.get(k) for k in ("input_tokens", "output_tokens",
                            "generation_seconds", "context_seconds", "answer_generation_calls")}})
                records.append(row)
                publish(config, [row], qa, gold, digest(manifest), output / "quality" / f"ready-{index + 1:03d}")
                write_json(internal / "report.private.json", {
                    "schema_version": 1, "manifest_sha256": digest(manifest), "records": records,
                    "planned_questions": len(selection["records"]), "baseline_successful": len(successful),
                    "baseline_failures": [r["record_id"] for r in baseline_rows if r["status"] != "ok"]})
                progress()
                print(json.dumps({"stage": "internal", "completed": len(records),
                                  "eligible": len(successful), "quality_packet_ready": f"ready-{index + 1:03d}"}), flush=True)
                gate = health_gate(records, config["health_gate"])
                if gate["status"] == "stopped":
                    stopped = gate
                    write_json(internal / "health_gate.private.json", gate)
                    print(json.dumps({"stage": "health_gate_stopped", "completed": len(records),
                                      "note": "Predeclared feasibility stop; review public quality packets before private results"}), flush=True)
                    break

        progress()
        session_index = len(list(internal.glob("session-*.json"))) + 1
        if missing:
            with LocalServer(task_config(protocol, "verify_claims"),
                             internal / f"server-{session_index}.log") as server:
                collect(server.client)
                session = {"completion_attempts_this_session": server.client.completion_attempts, **server.report()}
        else:
            collect(None)
            session = {"completion_attempts_this_session": 0, "server_started": False}
        write_json(internal / f"session-{session_index}.json", session)
        publish(config, records, qa, gold, digest(manifest), output / "quality/final")
        write_json(internal / "completion.private.json", {
            "status": "health_gate_stopped" if stopped else "completed",
            "processed_questions": len(records), "eligible_questions": len(successful),
            "not_attempted_ids": [t["record_id"] for t in traces[len(records):]],
            "health_gate": stopped or health_gate(records, config["health_gate"])})
        write_json(output / "progress.json", {
            "stage": "awaiting_AI_quality_completion", "planned_questions": len(selection["records"]),
            "internal_completed_questions": len(records), "quality_ready_packets": len(records),
            "baseline_failed": len(baseline_rows) - len(successful), "updated_at_utc": datetime.now(UTC).isoformat()})
    return {"internal_completed_questions": len(records)}
