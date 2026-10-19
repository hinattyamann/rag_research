"""Development-only Phase 8: freeze, extract once, evaluate orders/repeats and checkpoint."""

import json
import platform
from collections import Counter
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path

import yaml

from rag_research.evaluation.order import trial_plan
from rag_research.evaluation.tasks import execute_task
from rag_research.experiments.decisions import decide
from rag_research.experiments.frozen_trace import (
    assert_same_evidence,
    digest,
    freeze_record,
    require,
)
from rag_research.experiments.protocol import ROOT, load_protocol, task_config
from rag_research.experiments.storage import read_json, run_lock, write_json
from rag_research.generation.artifacts import model_identity
from rag_research.generation.auxiliary import auxiliary_identity, auxiliary_server_kwargs
from rag_research.generation.local import LocalServer
from rag_research.retrieval.common import file_hash


def load_traces(config, baseline_path, identifiers=None, *, split="development"):
    require(split in {"development", "calibration"}, "Evaluation is not available for calibration")
    qa_path = ROOT / config["data"]["qa_path"]
    qa = {}
    for line in qa_path.read_text("utf-8").splitlines():
        row = json.loads(line)
        require(row["research_split"] == split, "QA split differs from requested stage")
        qa[row["record_id"]] = row
    rows = [json.loads(line) for line in baseline_path.read_text("utf-8").splitlines()]
    provenance = read_json(baseline_path.parent / "run_manifest.json")
    baseline_config = yaml.safe_load((ROOT / config["baseline_config"]).read_text("utf-8"))
    require(provenance["status"] == "completed" and provenance["split"] == split,
            "Baseline provenance is not completed requested split")
    require(provenance["config"] == baseline_config and
            provenance["config_sha256"] == file_hash(ROOT / config["baseline_config"]),
            "Baseline conditions differ from Phase 6")
    require(provenance[f"{split}_sha256"] == file_hash(qa_path) and
            provenance["generator"] == model_identity(), "Baseline data/model identity differs")
    require(provenance["prompts_sha256"] == file_hash(ROOT / "configs/prompts.yaml"),
            "Baseline prompt identity differs")
    require({r["record_id"] for r in rows} ==
            {r["record_id"] for r in provenance["questions"]}, "Baseline/provenance record set differs")
    original_smoke = ROOT / config["data"]["preflight_baseline_answers"]
    if baseline_path.resolve() == original_smoke.resolve():
        smoke = read_json(ROOT / "data/manifests/phase6_smoke_report.json")
        require(file_hash(baseline_path) == smoke["artifacts"]["answers_sha256"],
                "Frozen Phase 6 answers hash differs")
    require(len({r["record_id"] for r in rows}) == len(rows), "Duplicate baseline record ID")
    selected = []
    for row in rows:
        identifier = row["record_id"]
        require(identifier in qa, "Baseline record is not in requested split")
        require(qa[identifier]["question"] == row["question"], "Baseline question differs from QA")
        if qa[identifier]["is_answerable"] and (not identifiers or identifier in identifiers):
            selected.append(freeze_record(row))
    require(bool(selected), "No eligible Development Answerable records")
    if identifiers:
        require(set(identifiers) == {t["record_id"] for t in selected},
                "Requested record IDs are missing or not Answerable")
    return selected, qa_path


def _manifest(config_path, prompt_path, baseline_path, qa_path, config, traces, output):
    # Source hashes bind resume to the exact implementation, not only to prompts.
    paths = sorted((ROOT / "src/rag_research/evaluation").glob("*.py"))
    paths += sorted((ROOT / "src/rag_research/experiments").glob("*.py"))
    paths += [ROOT / "scripts/run_order_evaluation.py", ROOT / "pyproject.toml", ROOT / "uv.lock",
              ROOT / "src/rag_research/retrieval/common.py",
              ROOT / "src/rag_research/generation/local.py",
              ROOT / "src/rag_research/generation/config.py",
              ROOT / "src/rag_research/generation/context.py",
              ROOT / "src/rag_research/generation/artifacts.py"]
    identity_path = ROOT / config["identity_manifest"]
    require(identity_path.resolve().is_relative_to(ROOT), "Identity path escapes repository")
    identity = read_json(identity_path)
    require(identity["model"] == model_identity(), "Model identity mismatch")
    baseline_config = (ROOT / config["baseline_config"]).resolve()
    require(baseline_config.is_relative_to(ROOT), "Baseline config escapes repository")
    if "auxiliary_model_manifest" in config:
        paths.extend([ROOT / config["auxiliary_model_manifest"],
                      ROOT / "src/rag_research/generation/auxiliary.py"])
        if "sampling" in config:
            paths.append(ROOT / "src/rag_research/generation/auxiliary_config.py")
    return {
        "schema_version": 1, "purpose": "phase8-development-smoke-not-pilot-or-final-evaluation",
        "python_version": platform.python_version(),
        "study_version": config["study_version"], "run_id": output.relative_to(ROOT).as_posix(),
        "config_sha256": file_hash(config_path), "prompts_sha256": file_hash(prompt_path),
        "baseline_answers_sha256": file_hash(baseline_path),
        "baseline_provenance_sha256": file_hash(baseline_path.parent / "run_manifest.json"),
        "baseline_prompts_sha256": file_hash(ROOT / "configs/prompts.yaml"),
        "development_qa_sha256": file_hash(qa_path),
        "baseline_config_sha256": file_hash(baseline_config),
        "identity_manifest_sha256": file_hash(identity_path),
        "model": identity["model"], "runtime": identity["runtime"],
        **({"auxiliary_model": auxiliary_identity(config)} if "auxiliary_model_manifest" in config else {}),
        "source_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths},
        "traces": [{"record_id": t["record_id"], "trace_sha256": t["trace_sha256"],
                    "directory": digest(t["record_id"])[:24], "plan": trial_plan(t, config)}
                   for t in traces],
    }


def group_summary(rows, trial_ids):
    selected = [r for r in rows if r["trial_id"] in trial_ids]
    valid = [r for r in selected if r["status"] == "ok"]
    pairs = list(combinations(valid, 2))
    return {"planned_trials": len(trial_ids), "valid_trials": len(valid),
            "valid_pairs": len(pairs),
            "disagreeing_pairs": sum(a["decision"] != b["decision"] for a, b in pairs),
            "both_decisions_observed": len({r["decision"] for r in valid}) == 2}


def _report(manifest, records, results, sessions):
    attempted = [r for r in results if r["completion_attempted"]]
    unknown = [r for r in attempted if r["error_code"] == "interrupted_unknown_outcome"]
    return {
        "schema_version": 1, "purpose": manifest["purpose"],
        "run_id": manifest["run_id"], "manifest_sha256": digest(manifest),
        "updated_at_utc": datetime.now(UTC).isoformat(), "records": records,
        "record_count": len(records),
        "actual_completion_attempts": None if unknown else len(attempted),
        "known_completion_attempts": len(attempted) - len(unknown),
        "possible_additional_completion_attempts": len(unknown),
        "task_status_counts": dict(Counter(r["status"] for r in results)),
        "judge_status_counts": dict(Counter(t["status"] for r in records for t in r["trials"])),
        "task_input_tokens": sum(r["input_tokens"] or 0 for r in attempted),
        "task_output_tokens": sum(r["output_tokens"] or 0 for r in attempted),
        "summed_task_elapsed_seconds": sum(r.get("elapsed_seconds", 0) for r in results),
        "cost_incomplete": any(r["cost_incomplete"] for r in results),
        "session_reports": sessions,
        "limits": ["Development smoke only; not an estimate of order sensitivity",
                   "Quote/JSON validation does not establish semantic correctness",
                   "No answer rewrite or independent answer quality labels in Phase 8",
                   "Token/time totals are auxiliary collection costs, not operational route costs"],
    }


def evaluate_traces(client, config, prompts, traces, manifest, output, notify=print):
    results, records = [], []
    for trace, entry in zip(traces, manifest["traces"], strict=True):
        folder = output / entry["directory"]
        folder.mkdir(exist_ok=True)
        frozen_path = folder / "trace.json"
        if frozen_path.exists():
            require(read_json(frozen_path) == trace, "Frozen trace hash mismatch")
        else:
            write_json(frozen_path, trace)
        binding = {"manifest_sha256": digest(manifest), "trace_sha256": trace["trace_sha256"]}
        extraction = execute_task(
            client, task_config(config, "extract_claims"), prompts, "extract_claims",
            {"answer": trace["answer"]}, folder / "claims.json", binding,
            constraints=config.get("output_constraints", "none"))
        results.append(extraction)
        claims = extraction["parsed"]["claims"] if extraction["status"] == "ok" else []
        notify(json.dumps({"record_id": trace["record_id"], "task": "extract_claims",
                           "status": extraction["status"], "claims": len(claims),
                           "error": extraction["error"]}), flush=True)
        trials = []
        documents_by_id = {d["passage_id"]: d for d in trace["documents"]}
        for spec in entry["plan"]["trials"]:
            task_path = folder / f"{spec['trial_id']}.json"
            row = {**spec, "score": None, "status": extraction["status"],
                   "error_code": "extraction_failed" if extraction["status"] == "error"
                   else "no_claims", "error": extraction["error"]}
            if extraction["status"] == "ok":
                documents = [documents_by_id[i] for i in spec["document_ids"]]
                assert_same_evidence(trace["documents"], documents)
                payload = {"question": trace["question"], "answer": trace["answer"],
                           "claims": claims, "documents": documents}
                evaluation = execute_task(
                    client, task_config(config, "verify_claims"), prompts, "verify_claims",
                    payload, task_path,
                    {**binding, "trial_id": spec["trial_id"], "claims_sha256": digest(claims)},
                    constraints=config.get("output_constraints", "none"))
                results.append(evaluation)
                row.update(status=evaluation["status"], error=evaluation["error"],
                           error_code=evaluation["error_code"],
                           task_file=task_path.relative_to(output).as_posix(),
                           json_schema_sha256=evaluation["json_schema_sha256"],
                           result_sha256=evaluation["result_sha256"])
                if evaluation["status"] == "ok":
                    row["score"] = evaluation["parsed"]["score"]
                notify(json.dumps({"record_id": trace["record_id"], "trial": spec["trial_id"],
                                   "status": row["status"], "score": row["score"],
                                   "error": row["error"]}), flush=True)
            row.update(decide(row["score"], config["decision"]["threshold"]))
            trials.append(row)
        records.append({"record_id": trace["record_id"], "trace_sha256": trace["trace_sha256"],
                        "extraction_status": extraction["status"], "claims": claims,
                        "extraction_audit_warnings": extraction.get("audit_warnings", []),
                        "claims_sha256": digest(claims) if claims else None,
                        "extraction_result_sha256": extraction["result_sha256"],
                        "threshold": config["decision"]["threshold"],
                        "plan": entry["plan"], "trials": trials,
                        "order_group": group_summary(trials, entry["plan"]["order_group"]),
                        "repeat_group": group_summary(trials, entry["plan"]["repeat_group"])})
        # Durable per-question derived summary; raw task journals already exist.
        write_json(folder / "summary.json", records[-1])
    return records, results


def run_evaluation(config_path, baseline_path, output, identifiers=None):
    config_path, baseline_path, output = (Path(p).resolve()
                                          for p in (config_path, baseline_path, output))
    require(Path.cwd().resolve() == ROOT, "Run from repository root")
    require(output.is_relative_to(ROOT / "data/runs/order_sensitivity") and
            output != ROOT / "data/runs/order_sensitivity", "Unexpected output directory")
    require(baseline_path.is_relative_to(ROOT / "data/runs"), "Baseline must be a local saved run")
    config, prompts, prompt_path = load_protocol(config_path)
    traces, qa_path = load_traces(config, baseline_path, identifiers)
    manifest = _manifest(config_path, prompt_path, baseline_path, qa_path, config, traces, output)
    with run_lock(output):
        path = output / "manifest.json"
        if path.exists():
            require(read_json(path) == manifest, "Run manifest hash mismatch; use a new run directory")
        else:
            require(set(p.name for p in output.iterdir()) == {".run.lock"},
                    "Run directory has unbound artifacts")
            write_json(path, manifest)
        session_index = 1
        while (output / f"server-{session_index}.log").exists():
            session_index += 1
        with LocalServer(task_config(config, "verify_claims"),
                         output / f"server-{session_index}.log",
                         **auxiliary_server_kwargs(config)) as server:
            records, results = evaluate_traces(
                server.client, config, prompts, traces, manifest, output)
            session = {"session": session_index, "completion_attempts_this_session":
                       server.client.completion_attempts, **server.report()}
            write_json(output / f"session-{session_index}.json", session)
        sessions = [read_json(p) for p in sorted(output.glob("session-*.json"))]
        report = _report(manifest, records, results, sessions)
        write_json(output / "report.json", report)
    return report
