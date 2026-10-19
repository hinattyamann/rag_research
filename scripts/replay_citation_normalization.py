"""Post-hoc parser regression on immutable v14 outputs; zero new model calls."""

import copy
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.evaluation.judge import parse_verdicts  # noqa: E402
from rag_research.evaluation.reasoned_json import (  # noqa: E402
    attach_cited_passages,
    audit_final_json_grammar,
    citation_id_audit,
    final_json,
)
from rag_research.experiments.decisions import decide  # noqa: E402
from rag_research.experiments.frozen_trace import digest, require  # noqa: E402
from rag_research.experiments.order_runner import group_summary  # noqa: E402
from rag_research.experiments.quality import reconstruct  # noqa: E402
from rag_research.experiments.storage import checkpoint, read_json, verify_checkpoint  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def verify_native_audits(task):
    response = task["runtime_response"]
    audit_final_json_grammar(response, SimpleNamespace(**task["settings"]))
    budget = task["reasoning_budget_audit"]
    require(response.get("stop_type") in {"eos", "word"} and not response.get("truncated"),
            "Original response was truncated or incomplete")
    require(task["input_tokens"] + task["settings"]["max_output_tokens"] <= task["settings"]["context_tokens"],
            "Input reservation exceeded")
    require(budget["budget"] == task["settings"]["reasoning_budget_tokens"] and
            0 <= budget["tokens_before_end_marker"] <= budget["budget"] + budget["budget_message_tokens"] + 2 and
            budget["full_response_tokens"] == len(response["tokens"]) == task["output_tokens"],
            "Stored native token audit differs")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    original_path = ROOT / "data/manifests/phase10_recheck_result_manifest.json"
    original = read_json(original_path)
    verify_checkpoint(original)
    for path, sha in original["raw_artifacts_sha256"].items():
        require(file_hash(ROOT / path) == sha, f"Original artifact changed: {path}")
    freeze = read_json(ROOT / "data/manifests/phase10_recheck_quality_freeze.json")
    verify_checkpoint(freeze)
    require(file_hash(ROOT / "data/manifests/phase10_recheck_quality_freeze.json") ==
            original["quality_freeze_sha256"], "Quality freeze changed")
    output = ROOT / "data/runs/measurement/phase10-citation-replay-v15"
    output.mkdir(parents=True, exist_ok=True)
    rows, labels, changes, source_archive = [], {}, [], {}
    unchanged_valid = 0
    for name in ("phase10-five-v2", "phase10-five-extra-v2"):
        run = ROOT / "data/runs/pilot" / name
        binding = read_json(run / "internal/manifest.json")
        for path, sha in binding["source_sha256"].items():
            source = ROOT / path
            if file_hash(source) != sha:
                source = ROOT / "data/runs/measurement/phase10-revision-v14/source_snapshot" / path
            require(source.exists() and file_hash(source) == sha, f"Original source unavailable: {path}")
            destination = output / "original_source_snapshot" / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
            source_archive[path] = sha
        annotations = read_json(run / "quality/quality-annotations.ai.json")
        expected_freeze = next(c for c in freeze["cohorts"] if c["run"].endswith(name))
        require(file_hash(run / "quality/quality-annotations.ai.json") ==
                expected_freeze["annotations_sha256"], "Frozen labels changed")
        by_id = {a["annotation_id"]: a["label"] for a in annotations["annotations"]}
        mapping = read_json(run / "quality/final/mapping.private.json")
        verify_checkpoint(mapping)
        labels.update({(a["record_id"], a["stage"]): by_id[key]
                       for key, values in mapping["assignments"].items() for a in values})
        for original_row in read_json(run / "internal/report.private.json")["records"]:
            verify_checkpoint(original_row)
            row = copy.deepcopy(original_row)
            row.pop("result_sha256")
            identifier = row["trace"]["record_id"]
            folder = output / digest(identifier)[:24]
            folder.mkdir(exist_ok=True)
            by_document = {d["passage_id"]: d for d in row["trace"]["documents"]}
            claims = row["tasks"]["extraction"]["parsed"]["claims"]
            verify_native_audits(row["rewrite"])
            require(row["rewrite"]["final_answer_tokens"] <= 512, "Rewrite answer budget exceeded")
            for trial in row["evaluation"]["trials"]:
                trial_id = trial["trial_id"]
                if trial_id not in row["tasks"]["judges"]:
                    continue
                task = row["tasks"]["judges"][trial_id]
                verify_checkpoint(task)
                original_sha, original_status = task["result_sha256"], task["status"]
                require(original_status == "ok" or task["error"] == "Invalid or duplicate citation IDs",
                        "This repair cannot recover another failure mode")
                verify_native_audits(task)
                text, _ = final_json(task["raw_output"])
                documents = [by_document[i] for i in trial["document_ids"]]
                text, raw = attach_cited_passages(text, documents, boolean_checks=True)
                parsed = parse_verdicts(text, claims, documents)
                audit = citation_id_audit(raw)
                if original_status == "ok":
                    require(parsed == task["parsed"], "A previously valid semantic verdict changed")
                    unchanged_valid += 1
                else:
                    require(bool(audit["deduplicated_claim_ids"]), "Failure was not a duplicate citation")
                    changes.append({"record_id": identifier, "question": row["trace"]["question"],
                                    "trial_id": trial_id, "original_result_sha256": original_sha,
                                    "original_error": task["error"], "normalization": audit,
                                    "derived_score": parsed["score"]})
                task.pop("result_sha256")
                task.update(status="ok", error=None, error_code=None, parsed=parsed,
                            raw_cited_verdicts=raw, citation_normalization=audit,
                            derivation={"kind": "posthoc_parser_replay_not_new_completion",
                                        "original_status": original_status,
                                        "original_result_sha256": original_sha,
                                        "additional_model_calls": 0})
                task = checkpoint(folder / f"{trial_id}.json", task)
                row["tasks"]["judges"][trial_id] = task
                trial.update(status="ok", score=parsed["score"], error=None, error_code=None,
                             result_sha256=task["result_sha256"],
                             task_file=(folder / f"{trial_id}.json").relative_to(output).as_posix())
                trial.update(decide(trial["score"], row["evaluation"]["threshold"]))
            for group in ("order_group", "repeat_group"):
                row["evaluation"][group] = group_summary(row["evaluation"]["trials"],
                                                        row["evaluation"]["plan"][group])
            row["derivation"] = {"kind": "posthoc_citation_parser_replay",
                                 "original_row_sha256": original_row["result_sha256"]}
            rows.append(checkpoint(folder / "derived_record.json", row))
    analysis = reconstruct(rows, labels)
    checkpoint(output / "derived_report.json", {"records": rows, "analysis": analysis})
    comparable = [r for r in rows if all(r["evaluation"][g]["valid_trials"] ==
                  r["evaluation"][g]["planned_trials"] and r["evaluation"][g]["valid_pairs"] > 0
                  for g in ("order_group", "repeat_group"))]
    route_summary = {}
    for route in sorted({r["route"] for r in analysis["routes"]}):
        selected = [r for r in analysis["routes"] if r["route"] == route]
        route_summary[route] = {
            "quality_status_counts": dict(Counter(r["quality_status"] for r in selected)),
            "missed_improvement_questions": sum(r["missed_improvement"] is True for r in selected),
            "harmful_rewrite_questions": sum(r["harmful_rewrite"] is True for r in selected),
            "operational_completion_attempts": sum(r["operational_cost"]["recorded_completion_attempts"] for r in selected)}
    checks = {"all_ten_questions_preserved": len(rows) == 10,
              "all_36_stored_judges_valid_after_replay": sum(len(r["tasks"]["judges"]) for r in rows) == 36,
              "all_35_previously_valid_verdicts_unchanged": unchanged_valid == 35,
              "only_one_duplicate_id_failure_recovered": len(changes) == 1,
              "minimum_three_complete_questions": len(comparable) >= 3,
              "all_ten_rewrites_preserved": all(r["rewrite"]["status"] == "ok" for r in rows),
              "all_quality_labels_fixed": len(labels) == 20 and "pending" not in labels.values(),
              "fifteen_diagnostics_preserved": original["strict_diagnostic_passed"] == 15}
    for path, sha in original["raw_artifacts_sha256"].items():
        require(file_hash(ROOT / path) == sha, f"Replay modified original artifact: {path}")
    manifest = {"purpose": "posthoc_syntax_repair_replay_not_new_model_experiment",
                "recorded_at_utc": datetime.now(UTC).isoformat(), "phase11_started": False,
                "new_model_completion_attempts": 0, "human_reviewed": False,
                "original_result_manifest_sha256": file_hash(original_path),
                "original_prespecified_gate_passed": original["combined_development_gate"]["passed"],
                "original_judge_status_counts": original["judge_status_counts"],
                "original_comparable_questions": original["comparable_questions"],
                "original_artifacts_unchanged": True, "original_sources_archived_sha256": source_archive,
                "changed_trials": changes, "replayed_judges": 36, "comparable_questions": len(comparable),
                "original_native_budget_and_grammar_audits_verified": 46,
                "quality_transitions": analysis["quality_transitions"],
                "route_summary": route_summary,
                "questions_with_order_decision_flip": sum(r["evaluation"]["order_group"]["both_decisions_observed"]
                                                           for r in comparable),
                "questions_with_repeat_decision_flip": sum(r["evaluation"]["repeat_group"]["both_decisions_observed"]
                                                            for r in comparable),
                "posthoc_development_readiness": {"checks": checks, "passed": all(checks.values())},
                "source_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in
                    [Path(__file__), ROOT / "src/rag_research/evaluation/reasoned_json.py",
                     ROOT / "src/rag_research/evaluation/tasks.py"]},
                "derived_report_sha256": file_hash(output / "derived_report.json"),
                "derived_artifacts_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p)
                                             for p in sorted(output.glob("*/*.json"))},
                "limits": ["Prespecified v14 gate remains failed; this post-hoc repair does not overwrite it",
                           "Only redundant existing citation IDs were removed; booleans and reasons are unchanged",
                           "No fresh model sample, native retry, quality relabeling or threshold tuning",
                           "Replay does not repair false support or false rejection; calibration remains necessary"]}
    checkpoint(ROOT / "data/manifests/phase10_citation_replay_manifest.json", manifest)
    print(json.dumps({k: v for k, v in manifest.items() if k not in
                     {"source_sha256", "derived_artifacts_sha256", "original_sources_archived_sha256"}},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
