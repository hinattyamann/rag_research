"""Read-only adoption and selection gates before a main Development run can start."""

from pathlib import Path

from rag_research.evaluation.claimwise import atomic_steps, verify_once
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.protocol import ROOT, task_config
from rag_research.experiments.storage import read_json, verify_checkpoint
from rag_research.generation.auxiliary import auxiliary_identity
from rag_research.generation.cuda_runtime import execution_identity
from rag_research.retrieval.common import file_hash


def bound_path(binding, *, root=None):
    root = ROOT if root is None else root
    require(isinstance(binding, dict) and set(binding) >= {"path", "sha256"}, "Missing preregistered evidence binding")
    require(isinstance(binding["path"], str) and not Path(binding["path"]).is_absolute(), "Evidence paths must be repository relative")
    path = (root / binding["path"]).resolve()
    require(path.is_relative_to(root) and path.is_file() and file_hash(path) == binding["sha256"], "Main Development evidence changed")
    return path


def passing_known_regression(binding):
    # Deferred import avoids the semantic runner's use of bilingual immutable().
    from rag_research.experiments.semantic_diagnostics import assess, load_config, specs

    report_path = bound_path(binding)
    require(report_path.is_relative_to(ROOT / "data/runs/semantic_diagnostics"), "Known evidence must stay in semantic diagnostics")
    report, manifest = read_json(report_path), read_json(report_path.parent / "manifest.json")
    require(report["diagnostic_gate_passed"] is True and report["completed_conditions"] ==
            report["planned_conditions"] == 30 and not report["not_attempted_ids"] and
            report["completion_attempts_recorded"] == 114 and report["cost_incomplete"] is False,
            "Known regression must be complete, passing and fully costed")
    config_path = bound_path(binding["config"])
    config, plan, prompts, _ = load_config(config_path)
    require(config == manifest["config"] and plan["purpose"] == "phase11-known-trace-semantic-regression" and
            len(plan["cases"]) == 15 and report["manifest_sha256"] == digest(manifest),
            "Use the complete passing known-15 regression, not the artificial diagnostic alone")
    require(manifest["model"] == auxiliary_identity(config) and
            all(manifest.get(k) == v for k, v in execution_identity(config).items()), "Known model/runtime changed")
    results = {}
    for case, order, key in specs(plan):
        path = report_path.parent / "tasks" / (key + ".json")
        saved = read_json(path)
        verify_checkpoint(saved)
        require(saved["status"] == "ok" and saved["result_sha256"] == report["task_result_sha256"][key],
                "Known regression raw task missing or changed")
        documents = case["documents"] if order == "original" else list(reversed(case["documents"]))
        result = verify_once(None, task_config(config, "verify_claims"), prompts[case["language"]],
            {"question": case["question"], "answer": case["answer"], "claims": case["claims"], "documents": documents},
            path, {"manifest_sha256": digest(manifest), "case_id": case["id"], "order": order},
            constraints=config["output_constraints"], mode="source-reading-v1",
            reader_generation=task_config(config, "read_sources"))
        require(result == saved, "Known raw reading/verdict/cost binding changed")
        results[key] = result
    assessed = assess(plan, results)
    require(all(report.get(k) == v for k, v in assessed.items()) and assessed["diagnostic_gate_passed"] and
            sum(bool(t["completion_attempted"]) for t in atomic_steps(results.values())) == 114,
            "Known adoption criteria do not agree with all saved raw results")
    return config, manifest


def validate_main(config, rows, qa_path):
    policy_path = bound_path(config.get("main_execution_policy"))
    policy = read_json(policy_path)
    require(policy["purpose"] == "phase11-main-development-execution-policy" and
            policy["status"] in {"preregistered_pending_known_regression", "preregistered"} and
            policy["phase12_allowed"] is False and policy["count_per_language"] == 20 and
            policy["selection_manifest"] == config.get("development_selection") and
            policy["limits_per_language"] == config.get("main_limits") and
            policy["quality"]["seal_all_candidates_both_languages_before_internal_unblinding"] is True,
            "Main execution policy/limits/selection/seal changed")
    selection_path = bound_path(config.get("development_selection"))
    selection = read_json(selection_path)
    verify_checkpoint(selection)
    require(selection["purpose"] == "phase11-main-development-preselected-ids-not-execution-approval" and
            selection["split"] == "development" and selection["phase12_allowed"] is False and
            selection["assets_sha256"] == file_hash(ROOT / config["assets"]) and
            selection["development_qa_sha256"][Path(qa_path).relative_to(ROOT).as_posix()] == file_hash(qa_path),
            "Main Development selection/assets changed")
    language = config["language"]
    selected = selection["languages"][language]["selected"]
    require(len(rows) == len(selected) == 20 and
            [r["record_id"] for r in rows] == [r["record_id"] for r in selected] and
            [r["document_group_id"] for r in rows] == [r["document_group_id"] for r in selected] and
            len({r["document_group_id"] for r in rows}) == 20,
            "Use the preselected 20 QA/groups in the original order; never refill")
    for name, sha in selection["used_baseline_input_sha256"].items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT) and file_hash(path) == sha, "Historical usage inventory changed")
    prior, manifest = passing_known_regression(config.get("adopted_known_regression"))
    keys = ("auxiliary_runtime", "sampling", "execution", "verification_mode", "output_constraints")
    require(all(config.get(k) == prior.get(k) for k in keys) and
            all(config["tasks"][t] == prior["tasks"][t] for t in ("read_sources", "verify_claims", "rewrite_answer")) and
            auxiliary_identity(config) == manifest["model"] and
            file_hash(ROOT / config["prompts"]) == manifest["source_sha256"][prior["prompts"][language]],
            "Main Judge model/runtime/prompts/budgets must match the adopted candidate")
    require(config["decision"]["threshold"] == prior["decision"]["threshold"] and
            config["decision"].get("bare_refusal_policy") == "rewrite_once", "Preserve threshold and explicit bare-refusal candidate")
    for name, sha in manifest["source_sha256"].items():
        if name.startswith(("src/rag_research/evaluation/", "src/rag_research/generation/")) or name in {
                "src/rag_research/experiments/protocol.py", "src/rag_research/experiments/frozen_trace.py",
                "src/rag_research/experiments/storage.py"}:
            require(file_hash(ROOT / name) == sha, "Adopted Judge core changed; repeat the semantic validation")
    require(config.get("main_limits") == {"maximum_completion_attempts": 1660, "maximum_new_qa_per_stage_session": 5,
            "stop_on_any_task_error": True, "automatic_refill": False}, "Preserve preregistered main limits")
