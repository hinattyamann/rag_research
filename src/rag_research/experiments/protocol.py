"""Phase 8 reuses the Phase 7 assets, with an explicit inference whitelist."""

from pathlib import Path

import yaml

from rag_research.evaluation.claims import validate_claims
from rag_research.experiments.decisions import decide
from rag_research.experiments.frozen_trace import require, validate_documents
from rag_research.generation.config import GenerationConfig
from rag_research.generation.context import literal_json

ROOT = Path(__file__).resolve().parents[3]
FIELDS = {"extract_claims": ["answer"],
          "verify_claims": ["question", "answer", "claims", "documents"],
          "rewrite_answer": ["question", "answer", "documents"]}


def load_protocol(path):
    config = yaml.safe_load(Path(path).read_text("utf-8"))
    require(config["schema_version"] == 1, "Unsupported protocol schema")
    require(config["purpose"] in {"phase7-development-protocol", "phase8-development-protocol"},
            "Unexpected protocol purpose")
    require(config["data"]["split"] == "development", "Phase 8 only reads Development")
    require(config["data"]["answerable_only"] is True, "Phase 8 uses Answerable QA")
    require(config["data"]["qa_path"] ==
            "data/processed/clapnq/c508d78-split-v1/development.jsonl", "Unexpected QA path")
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
                "none", "json_schema_source_spans_v1", "json_schema_source_spans_bounded_v2"},
            "Unsupported output constraints")
    require(config["quality"]["llm_labels_are_final"] is False, "Manual quality is still required")
    prompt_path = (ROOT / config["prompts"]).resolve()
    require(prompt_path.is_relative_to(ROOT), "Prompt path escapes repository")
    prompts = yaml.safe_load(prompt_path.read_text("utf-8"))
    require(prompts["schema_version"] == 1 and set(prompts["tasks"]) == set(FIELDS),
            "Unexpected prompt schema/tasks")
    for task, fields in FIELDS.items():
        spec = prompts["tasks"][task]
        require(spec["input_fields"] == fields, "Unexpected model input fields")
        require(isinstance(spec["system"], str) and bool(spec["system"].strip()), "Empty system")
        task_config(config, task)
    return config, prompts, prompt_path


def task_config(config, task):
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
    return [{"role": "system", "content": prompts["tasks"][task]["system"]},
            {"role": "user", "content": "Input JSON:\n" + literal_json(payload)}]
