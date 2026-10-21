"""Phase 8 reuses the Phase 7 assets, with an explicit inference whitelist."""

from pathlib import Path

import yaml

from rag_research.evaluation.claims import validate_claims
from rag_research.evaluation.sentence_claims import claim_unit_language
from rag_research.experiments.decisions import decide
from rag_research.experiments.frozen_trace import require, validate_documents
from rag_research.generation.auxiliary_config import AuxiliaryGenerationConfig
from rag_research.generation.config import GenerationConfig
from rag_research.generation.context import literal_json

ROOT = Path(__file__).resolve().parents[3]
FIELDS = {"extract_claims": ["answer"],
          "verify_claims": ["question", "answer", "claims", "documents"],
          "rewrite_answer": ["question", "answer", "documents"],
          "read_sources": ["question", "documents"]}


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
    validate_task_contract(config, prompts)
    return config, prompts, prompt_path


def validate_task_contract(config, prompts):
    """Shared comparison/model-input constraints, independent of dataset paths and stage."""
    trials = config["trials"]
    mode = config.get("verification_mode", "joint")
    require(mode in {"joint", "claimwise-v1", "source-reading-v1"}, "Unknown verification mode")
    require(mode == "joint" or (config["purpose"].startswith("phase11-bilingual-") and
            prompts.get("judge_payload") is None), "Claimwise candidate needs fixed full answer context")
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
    policy = decision.get("bare_refusal_policy", "keep_initial")
    require(policy in {"keep_initial", "rewrite_once"}, "Unknown bare-refusal policy")
    require(policy == "keep_initial" or config["purpose"] in {
            "phase11-bilingual-development-candidate", "phase11-bilingual-calibration-candidate"},
            "Bare-refusal rewrite requires a separate bilingual candidate protocol")
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
    require(config.get("sampling", {}).get("final_json_grammar_mode", "brace_trigger_v1") not in {"closing_tag_root_v2", "closing_tag_root_v3"} or
            (config.get("output_constraints") == "thinking_json_passage_ids_v2" and
             config.get("sampling", {}).get("final_json_grammar") is True), "Closing-tag grammar needs the thinking candidate")
    tasks = set(FIELDS) if mode == "source-reading-v1" else set(FIELDS) - {"read_sources"}
    require(prompts["schema_version"] == 1 and set(prompts["tasks"]) == tasks,
            "Unexpected prompt schema/tasks")
    require((prompts.get("source_reading_auxiliary") == "untrusted_reading_v1") == (mode == "source-reading-v1"),
            "Source reading requires its explicit candidate mode")
    require(prompts.get("source_reading_schema") in {None, "free_quote_coverage_v1", "fixed_ids_exact_quotes_v2"} and
            (prompts.get("source_reading_schema") is None or mode == "source-reading-v1"),
            "Unsupported reading schema candidate")
    claim_unit_language(prompts.get("claim_units"))
    for task, fields in FIELDS.items():
        if task not in tasks:
            continue
        spec = prompts["tasks"][task]
        expected_fields = (["question", "claims", "documents"] if task == "verify_claims" and
                           prompts.get("judge_payload") == "fixed_claims_only" else fields)
        if task == "verify_claims" and mode == "source-reading-v1":
            expected_fields = fields + ["source_reading"]
        require(spec["input_fields"] == expected_fields, "Unexpected model input fields")
        require(isinstance(spec["system"], str) and bool(spec["system"].strip()), "Empty system")
        task_config(config, task)
    require(prompts.get("judge_layout") in {None, "premise_then_claims", "draft_sources_target"}, "Unknown Judge input layout")
    require(prompts.get("judge_layout") != "draft_sources_target" or mode in {"claimwise-v1", "source-reading-v1"},
            "Draft/source/target layout is limited to the claimwise candidate")
    require(prompts.get("judge_payload") in {None, "fixed_claims_only"}, "Unknown Judge payload")
    require(prompts.get("judge_checks") in {None, "conflict_then_complete_v1"}, "Unknown Judge checks")
    require(prompts.get("rewrite_format") in {None, "checked_json_v1", "thinking_checked_json_v2"}, "Unknown rewrite format")
    require(prompts.get("rewrite_layout") in {None, "draft_sources_question"}, "Unknown rewrite layout")


def task_config(config, task):
    if "sampling" in config:
        sampling = dict(config["sampling"])
        require(sampling.pop("version") == "auxiliary-sampling-v1", "Unknown sampling version")
        return AuxiliaryGenerationConfig(**config["auxiliary_runtime"], **sampling,
                                         max_output_tokens=config["tasks"][task]["max_output_tokens"])
    return GenerationConfig(**config["auxiliary_runtime"],
                            max_output_tokens=config["tasks"][task]["max_output_tokens"])


def build_messages(prompts, task, payload):
    fields = FIELDS.get(task, [])
    reading = task == "verify_claims" and prompts.get("source_reading_auxiliary") == "untrusted_reading_v1"
    require(task in FIELDS and set(payload) == set(fields + (["source_reading"] if reading else [])),
            "Missing or forbidden model input field")
    if "answer" in payload:
        require(isinstance(payload["answer"], str), "Answer must be text")
    if "question" in payload:
        require(isinstance(payload["question"], str), "Question must be text")
    if "claims" in payload:
        validate_claims(payload["claims"])
    if "documents" in payload:
        validate_documents(payload["documents"])
    if reading:
        from rag_research.evaluation.source_reading import validate_reading

        validate_reading(payload["source_reading"], payload["documents"])
    if task == "verify_claims" and prompts.get("judge_layout") == "premise_then_claims":
        payload = {k: payload[k] for k in ("documents", "question", "answer", "claims",
                                          *(["source_reading"] if reading else []))}
    if task == "verify_claims" and prompts.get("judge_layout") == "draft_sources_target":
        payload = {k: payload[k] for k in ("answer", "documents", "question", "claims",
                                          *(["source_reading"] if reading else []))}
    if task == "verify_claims" and prompts.get("judge_payload") == "fixed_claims_only":
        payload = {k: payload[k] for k in ("documents", "question", "claims")}
    if task == "rewrite_answer" and prompts.get("rewrite_layout") == "draft_sources_question":
        payload = {k: payload[k] for k in ("answer", "documents", "question")}
    return [{"role": "system", "content": prompts["tasks"][task]["system"]},
            {"role": "user", "content": "Input JSON:\n" + literal_json(payload)}]
