"""Preregistered known/synthetic diagnostic gates; no QA loading or answer generation."""

import json
import re
from pathlib import Path

import yaml

from rag_research.evaluation.claims import validate_claims
from rag_research.evaluation.claimwise import atomic_steps, verify_once
from rag_research.evaluation.claimwise import pending as verification_pending
from rag_research.evaluation.sentence_claims import extract_sentence_units
from rag_research.experiments.bilingual_runner import immutable
from rag_research.experiments.frozen_trace import (
    assert_same_evidence,
    digest,
    require,
    validate_documents,
)
from rag_research.experiments.protocol import ROOT, task_config, validate_task_contract
from rag_research.experiments.storage import (
    next_session,
    read_json,
    run_lock,
    verify_checkpoint,
    write_json,
)
from rag_research.generation.auxiliary import auxiliary_identity, auxiliary_server_kwargs
from rag_research.generation.cuda_runtime import execution_identity
from rag_research.generation.local import LocalServer
from rag_research.retrieval.common import file_hash


def local(value):
    path = (ROOT / value).resolve()
    require(path.is_relative_to(ROOT), "Diagnostic input escapes repository")
    return path


def load_config(path):
    config = yaml.safe_load(Path(path).read_text())
    require(config["schema_version"] == 1 and config["purpose"] == "phase11-bilingual-semantic-candidate" and
            config["status"] == "candidate_not_frozen" and config["phase12_allowed"] is False,
            "Diagnostic Development config required")
    plan_path = local(config["diagnostics"])
    plan = read_json(plan_path)
    require(plan["schema_version"] == 1 and plan["purpose"] == "phase11-known-bilingual-semantic-diagnostics" and
            plan["phase12_allowed"] is False and plan["orders"] == ["original", "reversed"], "Unsupported diagnostic plan")
    require(plan["gate"] == {"stop_on_task_error": True, "stop_after_critical_failure": True,
            "critical_all_exact": True, "synthetic_min_accuracy_per_language": .9,
            "synthetic_max_false_support": 0}, "Preserve preregistered diagnostic criteria")
    cases = plan["cases"]
    mode = config.get("verification_mode", "joint")
    require(plan.get("verification_mode", "joint") == mode, "Diagnostic plan verification mode differs")
    expected_budget = 2 * sum((len(c["claims"]) + (mode == "source-reading-v1")) if mode != "joint" else 1 for c in cases)
    require(cases and len({c["id"] for c in cases}) == len(cases) and
            plan["max_completion_attempts"] == expected_budget, "Invalid case IDs/call budget")
    require(any(c["critical_claim_ids"] for c in cases) and
            {c["language"] for c in cases if c["scope"] == "synthetic_development"} == {"en", "ja"},
            "Known critical and both-language synthetic cases required")
    for case in cases:
        require(re.fullmatch(r"[a-z0-9-]+", case["id"]) and case["language"] in {"en", "ja"} and
                case["scope"] in {"known_used_calibration", "synthetic_development"}, "Unsupported case scope")
        validate_documents(case["documents"])
        validate_claims(case["claims"])
        require(isinstance(case["question"], str) and case["question"].strip() and
                isinstance(case["answer"], str), "Missing diagnostic text")
        ids = {c["claim_id"] for c in case["claims"]}
        require(set(case["expected"]) == ids and set(case["critical_claim_ids"]) <= ids and
                all(label in {"supported", "contradicted", "not_supported", None} for label in case["expected"].values())
                and all(case["expected"][i] is not None for i in case["critical_claim_ids"]) and
                (case["scope"] != "synthetic_development" or None not in case["expected"].values()),
                "Expected claim set differs")
    for name, expected in plan["source_sha256"].items():
        require(file_hash(local(name)) == expected, "Known diagnostic source changed")
    annotation = plan["expected_annotations"]
    require(annotation["human_reviewed"] is False and
            file_hash(local(annotation["known_trace_expected_source"])) == annotation["known_trace_expected_sha256"],
            "Known AI expected annotation changed")
    old_annotations = read_json(local(annotation["known_trace_expected_source"]))["claims"]
    for case in cases:
        if case["scope"] != "known_used_calibration":
            continue
        paths = [name for name, sha in plan["source_sha256"].items() if sha == case["source_trace_sha256"]]
        require(len(paths) == 1, "Known trace source binding missing")
        trace = read_json(local(paths[0]))
        expected = {a["claim_id"]: None if a["ambiguous_scope"] else a["expected_label"]
                    for a in old_annotations if a["record_id"] == case["original_record_id"]}
        require(trace["record_id"] == case["original_record_id"] and
                all(case[k] == trace[k] for k in ("question", "answer", "documents")) and
                case["claims"] == extract_sentence_units(trace["answer"])["claims"] and
                case["expected"] == expected, "Known trace/expected labels differ from the preserved source")
    require(set(config["prompts"]) == {"en", "ja"}, "Both language prompts required")
    prompts = {lang: yaml.safe_load(local(name).read_text()) for lang, name in config["prompts"].items()}
    for value in prompts.values():
        validate_task_contract(config, value)
    require(prompts["en"]["tasks"]["verify_claims"] == prompts["ja"]["tasks"]["verify_claims"],
            "Use the same Judge instructions for both languages")
    return config, plan, prompts, plan_path


def specs(plan):
    # Always complete both known examples before deciding on synthetic expansion.
    cases = sorted(enumerate(plan["cases"]), key=lambda pair: (not bool(pair[1]["critical_claim_ids"]), pair[0]))
    return [(case, order, case["id"] + "-" + order) for _, case in cases for order in plan["orders"]]


def matches(case, task, *, critical=False):
    if task["status"] != "ok":
        return False
    observed = {v["claim_id"]: v["label"] for v in task["parsed"]["verdicts"]}
    ids = case["critical_claim_ids"] if critical else [i for i, expected in case["expected"].items() if expected is not None]
    return all(observed.get(i) == case["expected"][i] for i in ids)


def assess(plan, results):
    selected = specs(plan)
    critical = [(case, key) for case, _, key in selected if case["critical_claim_ids"]]
    critical_passed = bool(critical) and all(key in results and matches(case, results[key], critical=True) for case, key in critical)
    metrics = {}
    for language in ("en", "ja"):
        planned = [(case, key) for case, _, key in selected
                   if case["scope"] == "synthetic_development" and case["language"] == language]
        completed = [(case, results[key]) for case, key in planned if key in results]
        valid = [(case, task) for case, task in completed if task["status"] == "ok"]
        correct = sum(matches(case, task) for case, task in valid)
        false_support = sum(v["label"] == "supported" and case["expected"][v["claim_id"]] in
                            {"contradicted", "not_supported"} for case, task in valid for v in task["parsed"]["verdicts"])
        metrics[language] = {"planned_conditions": len(planned), "completed_conditions": len(completed),
                             "valid_conditions": len(valid), "exact_correct_conditions": correct,
                             "accuracy_of_all_planned": correct / len(planned) if len(completed) == len(planned) else None,
                             "false_support_count": false_support}
    passed = critical_passed and len(results) == len(selected) and all(t["status"] == "ok" for t in results.values())
    passed = passed and all(m["accuracy_of_all_planned"] is not None and
                           m["accuracy_of_all_planned"] >= .9 and m["false_support_count"] == 0 for m in metrics.values())
    return {"critical_planned_conditions": len(critical),
            "critical_completed_conditions": sum(key in results for _, key in critical),
            "critical_exact_correct_conditions": sum(key in results and matches(case, results[key], critical=True)
                                                      for case, key in critical),
            "critical_passed": critical_passed, "synthetic": metrics, "diagnostic_gate_passed": passed}


def run(config_path, output):
    config_path, output = Path(config_path).resolve(), Path(output).resolve()
    parent = ROOT / "data/runs/semantic_diagnostics"
    require(Path.cwd().resolve() == ROOT and output.is_relative_to(parent) and output != parent, "Unexpected diagnostic run")
    config, plan, prompts, plan_path = load_config(config_path)
    sources = [*sorted((ROOT / "src/rag_research").rglob("*.py")), config_path, plan_path,
               *[local(p) for p in config["prompts"].values()], ROOT / "scripts/run_semantic_diagnostics.py"]
    manifest = {"schema_version": 1, "purpose": config["purpose"], "config": config,
                "plan_sha256": file_hash(plan_path), "model": auxiliary_identity(config), **execution_identity(config),
                "source_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sources},
                "phase12_allowed": False}
    selected = specs(plan)
    with run_lock(output):
        immutable(output / "manifest.json", manifest)
        tasks = output / "tasks"
        tasks.mkdir(exist_ok=True)
        cached = {key: read_json(tasks / (key + ".json")) for _, _, key in selected if (tasks / (key + ".json")).exists()}
        for task in cached.values():
            if task["status"] != "started":
                verify_checkpoint(task)
        mode = config.get("verification_mode", "joint")

        def attempt(client, case, order, key):
            documents = case["documents"] if order == "original" else list(reversed(case["documents"]))
            assert_same_evidence(case["documents"], documents)
            return verify_once(client, task_config(config, "verify_claims"), prompts[case["language"]],
                                {"question": case["question"], "answer": case["answer"],
                                 "claims": case["claims"], "documents": documents}, tasks / (key + ".json"),
                                {"manifest_sha256": digest(manifest), "case_id": case["id"], "order": order},
                                constraints=config["output_constraints"], mode=mode,
                                reader_generation=task_config(config, "read_sources") if mode == "source-reading-v1" else None)

        # A final child may be durable even if the aggregate replacement was interrupted.
        for case, order, key in selected:
            if (key in cached and cached[key]["status"] == "partial" and
                    not verification_pending(tasks / (key + ".json"), mode)):
                cached[key] = attempt(None, case, order, key)
        health_stopped = any(t["status"] in {"error", "started"} for t in cached.values())
        critical_pending = any(verification_pending(tasks / (key + ".json"), mode)
                               for c, _, key in selected if c["critical_claim_ids"])
        expanded = assess(plan, cached)["critical_passed"]
        pending = not health_stopped and (critical_pending or (expanded and any(
                  verification_pending(tasks / (key + ".json"), mode) for _, _, key in selected)))
        results = {}

        def collect(client):
            for case, order, key in selected:
                if not case["critical_claim_ids"] and not assess(plan, results)["critical_passed"]:
                    break
                task = attempt(client, case, order, key)
                results[key] = task
                print(json.dumps({"completed": len(results), "planned": len(selected), "status": task["status"]}), flush=True)
                if task["status"] == "error":
                    break

        session = next_session(output)
        if pending:
            with LocalServer(task_config(config, "verify_claims"), output / f"server-{session}.log",
                             **auxiliary_server_kwargs(config)) as server:
                collect(server.client)
                write_json(output / f"session-{session}.json", server.report())
        else:
            collect(None)
        # A stopped/resumed report must not relabel any existing attempts as never attempted.
        for case, order, key in selected:
            if key in cached and key not in results:
                results[key] = attempt(None, case, order, key)
        gate = assess(plan, results)
        report = {"schema_version": 1, "purpose": config["purpose"], "manifest_sha256": digest(manifest), **gate,
                  "planned_conditions": len(selected), "completed_conditions": len(results),
                  "not_attempted_ids": [key for _, _, key in selected if key not in results],
                  "planned_completion_limit": plan["max_completion_attempts"],
                  "completion_attempts_recorded": sum(bool(t["completion_attempted"]) for t in atomic_steps(results.values())),
                  "cost_incomplete": any(t["cost_incomplete"] for t in results.values()),
                  "input_tokens": sum(t["input_tokens"] or 0 for t in results.values()),
                  "output_tokens": sum(t["output_tokens"] or 0 for t in results.values()),
                  "summed_task_seconds": sum(t["elapsed_seconds"] for t in results.values()),
                  "task_result_sha256": {key: task["result_sha256"] for key, task in results.items()},
                  "gate11_passed": False, "phase12_allowed": False}
        write_json(output / "report.json", report)
        return report
