"""Phase 8 reuses the Phase 7 assets, with an explicit inference whitelist."""

from pathlib import Path

import yaml

from rag_research.evaluation.claims import validate_claims
from rag_research.experiments.decisions import decide
from rag_research.experiments.frozen_trace import require, validate_documents
from rag_research.generation.auxiliary_config import AuxiliaryGenerationConfig
from rag_research.generation.config import GenerationConfig
from rag_research.generation.context import literal_json

ROOT = Path(__file__).resolve().parents[3]
FIELDS = {"extract_claims": ["answer"],
          "verify_claims": ["question", "answer", "claims", "documents"],
          "rewrite_answer": ["question", "answer", "documents"]}


def load_protocol(path, *, split="development"):
    require(split in {"development", "calibration"}, "Evaluation is not available for calibration")
    config = yaml.safe_load(Path(path).read_text("utf-8"))
    require(config["schema_version"] == 1, "Unsupported protocol schema")
    purposes = ({"phase7-development-protocol", "phase8-development-protocol"}
                if split == "development" else {"phase11-calibration-protocol"})
    require(config["purpose"] in purposes,
            "Unexpected protocol purpose")
    require(config["data"]["split"] == split, "Protocol split differs from requested stage")
    require(config["data"]["answerable_only"] is True, "Phase 8 uses Answerable QA")
    require(config["data"]["qa_path"] ==
            f"data/processed/clapnq/c508d78-split-v1/{split}.jsonl", "Unexpected QA path")
    trials = config["trials"]
    for field in ("repeated_prompt_result_cache", "regenerate_claims_per_trial",
                  "regenerate_answer_per_trial", "repack_or_truncate_per_trial"):
        require(trials[field] is False, f"Comparison changes inputs or skips calls: {field}")
    require(trials["same_order_total_trials"] == 5 and
            trials["share_original_first_trial"] is True, "Expected five repeats with shared first")
    require(trials["deduplicate_order_permutations"] is True, "Deduplicate orders explicitly")
    require(trials["generation_seed_policy"] == "same_fixed_seed_for_every_trial",
            "Unexpected generation seed policy")
    for field in ("shuffle_seed", "execution_order_seed"):
        require(type(trials[field]) is int and trials[field] >= 0, "Invalid trial seed")
    require(config["errors"]["automatic_retries"] == 0, "Automatic retries must be zero")
    require(config["errors"]["input_overflow_action"] == "record_error_without_truncating",
            "Overflow must not truncate evidence")
    decision = config["decision"]
    require(decision["no_claims_score"] is None, "No-claim score must be null")
    require(decision["score"] == "supported_claims_divided_by_fixed_claims" and
            decision["accept_when"] == "score_greater_than_or_equal_to_threshold" and
            decision["unscorable_action"] == "keep_initial_answer_with_separate_fallback_status",
            "Unsupported decision rule")
    decide(None, decision["threshold"])
    require(config["auxiliary_runtime"]["repack"] is False, "Runtime repacking is forbidden")
    require(config.get("output_constraints", "none") in {
                "none", "json_schema_source_spans_v1", "json_schema_source_spans_bounded_v2",
                "json_schema_source_spans_compact_v3", "json_schema_verdicts_aligned_v4",
                "thinking_json_passage_ids_v1", "thinking_json_passage_ids_v2"},
            "Unsupported output constraints")
    if split == "development":
        require(config["quality"]["llm_labels_are_final"] is False, "Manual quality is still required")
    else:
        require(config["quality"]["annotator"] == "Codex_AI" and
                config["quality"]["human_reviewed"] is False and
                config["quality"]["internal_judge_is_quality_truth"] is False,
                "Calibration needs separate external AI quality")
    prompt_path = (ROOT / config["prompts"]).resolve()
    require(prompt_path.is_relative_to(ROOT), "Prompt path escapes repository")
    prompts = yaml.safe_load(prompt_path.read_text("utf-8"))
    require(prompts["schema_version"] == 1 and set(prompts["tasks"]) == set(FIELDS),
            "Unexpected prompt schema/tasks")
    for task, fields in FIELDS.items():
        spec = prompts["tasks"][task]
        expected_fields = (["question", "claims", "documents"] if task == "verify_claims" and
                           prompts.get("judge_payload") == "fixed_claims_only" else fields)
        require(spec["input_fields"] == expected_fields, "Unexpected model input fields")
        require(isinstance(spec["system"], str) and bool(spec["system"].strip()), "Empty system")
        task_config(config, task)
    require(prompts.get("judge_layout") in {None, "premise_then_claims"}, "Unknown Judge input layout")
    require(prompts.get("judge_payload") in {None, "fixed_claims_only"}, "Unknown Judge payload")
    require(prompts.get("judge_checks") in {None, "conflict_then_complete_v1"}, "Unknown Judge checks")
    require(prompts.get("rewrite_format") in {None, "checked_json_v1", "thinking_checked_json_v2"}, "Unknown rewrite format")
    require(prompts.get("rewrite_layout") in {None, "draft_sources_question"}, "Unknown rewrite layout")
    return config, prompts, prompt_path


def task_config(config, task):
    if "sampling" in config:
        sampling = dict(config["sampling"])
        require(sampling.pop("version") == "auxiliary-sampling-v1", "Unknown sampling version")
        return AuxiliaryGenerationConfig(**config["auxiliary_runtime"], **sampling,
                                         max_output_tokens=config["tasks"][task]["max_output_tokens"])
    return GenerationConfig(**config["auxiliary_runtime"],
                            max_output_tokens=config["tasks"][task]["max_output_tokens"])


def build_messages(prompts, task, payload):
    require(task in FIELDS and set(payload) == set(FIELDS[task]),
            "Missing or forbidden model input field")
    require(isinstance(payload["answer"], str), "Answer must be text")
    if "question" in payload:
        require(isinstance(payload["question"], str), "Question must be text")
    if "claims" in payload:
        validate_claims(payload["claims"])
    if "documents" in payload:
        validate_documents(payload["documents"])
    if task == "verify_claims" and prompts.get("judge_layout") == "premise_then_claims":
        payload = {k: payload[k] for k in ("documents", "question", "answer", "claims")}
    if task == "verify_claims" and prompts.get("judge_payload") == "fixed_claims_only":
        payload = {k: payload[k] for k in ("documents", "question", "claims")}
    if task == "rewrite_answer" and prompts.get("rewrite_layout") == "draft_sources_question":
        payload = {k: payload[k] for k in ("answer", "documents", "question")}
    return [{"role": "system", "content": prompts["tasks"][task]["system"]},
            {"role": "user", "content": "Input JSON:\n" + literal_json(payload)}]
