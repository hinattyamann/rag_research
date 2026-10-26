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
from rag_research.experiments.phase11_autonomy import validate_chain_identity
from rag_research.experiments.protocol import ROOT, task_config, validate_task_contract
from rag_research.experiments.semantic_adoption import BINARY, KNOWN_GATE_V2, summarize, version
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


def load_config(path, *, allow_reused_view=False):
    config = yaml.safe_load(Path(path).read_text())
    require(config["schema_version"] == 1 and config["purpose"] == "phase11-bilingual-semantic-candidate" and
            config["status"] == "candidate_not_frozen" and config["phase12_allowed"] is False,
            "Diagnostic Development config required")
    plan_path = local(config["diagnostics"])
    plan = read_json(plan_path)
    chain = validate_chain_identity(config, plan, root=ROOT)
    regression = plan["purpose"] == "phase11-known-trace-semantic-regression"
    require(plan["schema_version"] == 1 and plan["purpose"] in {
            "phase11-known-bilingual-semantic-diagnostics", "phase11-known-trace-semantic-regression"} and
            plan["phase12_allowed"] is False and plan["orders"] == ["original", "reversed"], "Unsupported diagnostic plan")
    expected_gate = ({"stop_on_task_error": True, "stop_after_critical_failure": True,
        "critical_all_exact": True, "known_min_accuracy": .9, "known_min_supported_accuracy": .9,
        "known_max_false_support": 0} if regression else {"stop_on_task_error": True, "stop_after_critical_failure": True,
            "critical_all_exact": True, "synthetic_min_accuracy_per_language": .9,
            "synthetic_max_false_support": 0})
    adoption_version = version(plan["gate"])
    if adoption_version == BINARY:
        require(regression, "Binary v2 is registered for the complete known regression")
        expected_gate = KNOWN_GATE_V2
    require(plan["gate"] == expected_gate, "Preserve preregistered diagnostic criteria")
    if regression:
        prerequisite = local(plan["prerequisite"]["report_path"])
        require(file_hash(prerequisite) == plan["prerequisite"]["sha256"], "Prerequisite report changed")
        prior_report, prior_manifest = read_json(prerequisite), read_json(prerequisite.parent / "manifest.json")
        prior_plan_path = local(prior_manifest["config"]["diagnostics"])
        prior_plan = read_json(prior_plan_path)
        reused = None
        if chain:
            if config.get("semantic_evidence_reuse"):
                from rag_research.experiments.evidence_reuse import validate_reuse

                reused = validate_reuse(config, root=ROOT, report_override=prerequisite)
                require(reused["paths"]["source_report"] == prerequisite and
                        reused["source_config"] == prior_manifest["config"] and
                        reused["source_plan"] == prior_plan, "Known prerequisite differs from explicit reused evidence")
            else:
                validate_chain_identity(config, plan, prior_manifest, prior_report, prior_plan,
                                        prior_manifest["config"], root=ROOT)
        prior_mode = prior_manifest["config"].get("verification_mode", "joint")
        prior_calls = 2 * sum(len(c["claims"]) + (prior_mode == "source-reading-v1") for c in prior_plan["cases"])
        require(prior_mode in {"claimwise-v1", "source-reading-v1"} and
                prior_plan["purpose"] == "phase11-known-bilingual-semantic-diagnostics" and
                prior_plan.get("verification_mode") == prior_mode and
                prior_manifest["plan_sha256"] == file_hash(prior_plan_path) and
                prior_report["diagnostic_gate_passed"] is True and not prior_report["not_attempted_ids"] and
                prior_report["completed_conditions"] == prior_report["planned_conditions"] == len(specs(prior_plan)) and
                prior_report["completion_attempts_recorded"] == prior_plan["max_completion_attempts"] == prior_calls and
                prior_report["cost_incomplete"] is False and prior_report["manifest_sha256"] == digest(prior_manifest),
                "Passing full bilingual diagnostics required")
        passing_config = prior_manifest["config"]
        if reused:
            passing_config = {**passing_config, "candidate_identity_sha256": config["candidate_identity_sha256"],
                              "semantic_evidence_reuse": config["semantic_evidence_reuse"]}
        require({k: v for k, v in config.items() if k not in {"study_version", "diagnostics"}} ==
                {k: v for k, v in passing_config.items() if k not in {"study_version", "diagnostics"}},
                "Known regression must use the passing candidate settings")
        require(prior_manifest["model"] == auxiliary_identity(config) and
                all(prior_manifest.get(k) == v for k, v in execution_identity(config).items()),
                "Passing Model/Runtime identity changed")
        for name, sha in prior_manifest["source_sha256"].items():
            if name.startswith(("src/rag_research/evaluation/", "src/rag_research/generation/")) or name in {
                    "src/rag_research/experiments/protocol.py", "src/rag_research/experiments/frozen_trace.py",
                    "src/rag_research/experiments/storage.py"}:
                require(file_hash(local(name)) == sha, "Passing Judge implementation changed")
    else:
        require(not config.get("semantic_evidence_reuse") or allow_reused_view,
                "Reused semantic candidate is a read-only condition view; execute its fresh Known regression instead")
    cases = plan["cases"]
    mode = config.get("verification_mode", "joint")
    require(not regression or mode in {"claimwise-v1", "source-reading-v1"}, "Known regression requires the passing fixed-unit mode")
    require(plan.get("verification_mode", "joint") == mode, "Diagnostic plan verification mode differs")
    expected_budget = 2 * sum((len(c["claims"]) + (mode == "source-reading-v1")) if mode != "joint" else 1 for c in cases)
    require(cases and len({c["id"] for c in cases}) == len(cases) and
            plan["max_completion_attempts"] == expected_budget, "Invalid case IDs/call budget")
    require(any(c["critical_claim_ids"] for c in cases) and (regression or
            {c["language"] for c in cases if c["scope"] == "synthetic_development"} == {"en", "ja"}),
            "Known critical and both-language synthetic cases required")
    if regression:
        require(all(c["scope"] in {"known_used_calibration", "known_used_development"} for c in cases),
                "Known regression must not load new QA")
    for case in cases:
        require(re.fullmatch(r"[a-z0-9-]+", case["id"]) and case["language"] in {"en", "ja"} and
                case["scope"] in {"known_used_calibration", "known_used_development", "synthetic_development"}, "Unsupported case scope")
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
        if regression:
            require(set(case["critical_claim_ids"]) == {i for i, label in case["expected"].items()
                    if label in {"contradicted", "not_supported"}}, "All definite negative units must remain critical")
    for name, expected in plan["source_sha256"].items():
        require(file_hash(local(name)) == expected, "Known diagnostic source changed")
    annotation = plan["expected_annotations"]
    require(annotation["human_reviewed"] is False and
            file_hash(local(annotation["known_trace_expected_source"])) == annotation["known_trace_expected_sha256"],
            "Known AI expected annotation changed")
    annotation_file = read_json(local(annotation["known_trace_expected_source"]))
    old_annotations = annotation_file["claims"]
    if regression:
        original_audit = local(annotation_file["preserved_audit_path"])
        require(file_hash(original_audit) == annotation_file["preserved_audit_sha256"] and
                all(a in old_annotations for a in read_json(original_audit)["claims"]), "Old expected annotations changed")
        for entry in plan["bare_refusal_cases_retained_separately"]:
            trace = read_json(local(entry["trace_path"]))
            units = extract_sentence_units(trace["answer"])
            require(trace["record_id"] == entry["record_id"] and units["claims"] == [] and
                    units["exclusion"] == "standalone_refusal" and entry["score"] is None,
                    "Preserve bare-refusal QA separately")
    for case in cases:
        if case["scope"] not in {"known_used_calibration", "known_used_development"}:
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
    result = assess_legacy(plan, results)
    if version(plan.get("gate", {})) == BINARY:
        selected = specs(plan)
        observations = []
        for case, _, key in selected:
            task = results.get(key, {})
            actual = {v["claim_id"]: v["label"] for v in task["parsed"]["verdicts"]} if task.get("status") == "ok" else {}
            group = case.get("document_group_id", case.get("original_record_id", case["id"]))
            observations.extend((group, (case["id"], i), label, actual.get(i)) for i, label in case["expected"].items())
        healthy = (set(results) == {key for _, _, key in selected} and
                   all(t["status"] == "ok" and not t.get("cost_incomplete", False) for t in results.values()))
        result["binary_adoption"] = summarize(observations, healthy=healthy)
        result["semantic_adoption_version"] = BINARY
        result["diagnostic_gate_passed"] = result["binary_adoption"]["passed"]
    return result


def assess_legacy(plan, results):
    selected = specs(plan)
    critical = [(case, key) for case, _, key in selected if case["critical_claim_ids"]]
    critical_passed = bool(critical) and all(key in results and matches(case, results[key], critical=True) for case, key in critical)
    if plan.get("purpose") == "phase11-known-trace-semantic-regression":
        planned = [(case, key, i, label) for case, _, key in selected for i, label in case["expected"].items() if label is not None]
        observed = {key: {v["claim_id"]: v["label"] for v in task["parsed"]["verdicts"]}
                    for key, task in results.items() if task["status"] == "ok"}
        complete = len(results) == len(selected) and all(t["status"] == "ok" for t in results.values())
        correct = sum(observed.get(key, {}).get(i) == label for _, key, i, label in planned)
        positives = [(key, i) for _, key, i, label in planned if label == "supported"]
        supported_correct = sum(observed.get(key, {}).get(i) == "supported" for key, i in positives)
        false_support = sum(label != "supported" and observed.get(key, {}).get(i) == "supported" for _, key, i, label in planned)
        accuracy = correct / len(planned) if complete and planned else None
        positive_accuracy = supported_correct / len(positives) if complete and positives else None
        return {"critical_planned_conditions": len(critical),
                "critical_completed_conditions": sum(key in results for _, key in critical),
                "critical_exact_correct_conditions": sum(key in results and matches(case, results[key], critical=True) for case, key in critical),
                "critical_passed": critical_passed,
                "known_regression": {"planned_labeled_unit_conditions": len(planned), "exact_correct": correct,
                    "accuracy_of_all_planned": accuracy, "planned_supported_unit_conditions": len(positives),
                    "supported_exact_correct": supported_correct, "supported_accuracy": positive_accuracy,
                    "false_support_count": false_support, "ambiguous_unit_conditions_retained_in_F":
                    sum(label is None for case, _, key in selected for label in case["expected"].values())},
                "diagnostic_gate_passed": bool(critical_passed and accuracy is not None and accuracy >= .9 and
                                               positive_accuracy is not None and positive_accuracy >= .9 and false_support == 0)}
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
    manifest.update(validate_chain_identity(config, plan, root=ROOT) or {})
    if version(plan["gate"]) == BINARY:
        manifest["semantic_adoption_version"] = BINARY
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
        binary = version(plan["gate"]) == BINARY
        expanded = binary or assess(plan, cached)["critical_passed"]
        pending = not health_stopped and (critical_pending or (expanded and any(
                  verification_pending(tasks / (key + ".json"), mode) for _, _, key in selected)))
        results = {}

        def collect(client):
            for case, order, key in selected:
                if not binary and not case["critical_claim_ids"] and not assess(plan, results)["critical_passed"]:
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
        report.update(validate_chain_identity(config, plan, manifest, root=ROOT) or {})
        write_json(output / "report.json", report)
        return report
