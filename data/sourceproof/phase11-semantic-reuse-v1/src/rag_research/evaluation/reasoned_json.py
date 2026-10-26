"""Separate explicitly closed model reasoning from the single final JSON response."""

import json
import re

from rag_research.evaluation.claims import parse_json
from rag_research.experiments.frozen_trace import require
from rag_research.generation.auxiliary_config import FINAL_JSON_TRIGGER_PATTERN
from rag_research.generation.json_grammar import closing_tag_grammar

CITATION_ID_NORMALIZATION = "stable_unique_passage_ids_v1"


def citation_id_audit(raw):
    """Keep redundant references visible; never change a label or its rationale."""
    return {"version": CITATION_ID_NORMALIZATION,
            "deduplicated_claim_ids": [v["claim_id"] for v in raw["verdicts"]
                if len(v["evidence_ids"]) != len(set(v["evidence_ids"]))],
            "semantic_labels_or_reasons_changed": False}


def audit_final_json_grammar(response, config, *, schema=None, client=None):
    if not getattr(config, "final_json_grammar", False):
        return None
    settings = response.get("generation_settings", {})
    mode = getattr(config, "final_json_grammar_mode", "brace_trigger_v1")
    if mode in {"closing_tag_root_v2", "closing_tag_root_v3"}:
        triggers = settings.get("grammar_triggers")
        correct_trigger = triggers == [{"type": 1, "value": "</think>"}]
        # b11433 converts a preserved one-token WORD to TOKEN in native settings.
        # The tokenizer must independently confirm its ID; no hardcoded model ID.
        if mode == "closing_tag_root_v3" and client is not None:
            end = client.tokenize("</think>", special=True)
            correct_trigger = correct_trigger or (len(end) == 1 and
                end[0] in settings.get("preserved_tokens", []) and
                triggers == [{"type": 0, "value": "</think>", "token": end[0]}])
        require(schema is not None and settings.get("grammar_lazy") is True and
                correct_trigger and settings.get("grammar") == closing_tag_grammar(schema,
                    bounded_whitespace=mode == "closing_tag_root_v3"), "Runtime closing-tag grammar differs")
        require("</think>" in response.get("content", "") and re.match(r"^\s*\{", response["content"].rpartition("</think>")[2]),
                "Final JSON did not follow the constrained closing tag")
        return {"version": mode, "runtime_settings_verified": True,
                "trigger_text_verified": True, "end_tag_consumed_by_declared_grammar": True,
                "does_not_verify_semantic_correctness": True}
    require(settings.get("grammar_lazy") is True and settings.get("grammar_triggers") ==
            [{"type": 2, "value": FINAL_JSON_TRIGGER_PATTERN}] and bool(settings.get("grammar")),
            "Runtime did not apply the requested final-only grammar")
    final = response.get("content", "").rpartition("</think>")[2]
    require(re.match(r"^[ \t\r\n\f\v]*\{", final) is not None,
            "Final JSON did not reach the declared grammar trigger")
    return {"runtime_settings_verified": True, "trigger_pattern": FINAL_JSON_TRIGGER_PATTERN,
            "trigger_text_verified": True, "does_not_verify_semantic_correctness": True}


def final_json(text):
    require(isinstance(text, str) and "</think>" in text, "Missing closed reasoning block")
    reasoning, _, final = text.rpartition("</think>")
    final = final.strip()
    fenced = final.startswith("```json\n") and final.endswith("\n```")
    if fenced:
        final = final[len("```json\n"):-len("\n```")].strip()
    value = parse_json(final)
    return json.dumps(value, ensure_ascii=False), {"text": reasoning,
            "closing_marker": "</think>", "final_fence_removed": fenced}


def attach_cited_passages(text, documents, *, boolean_checks=False):
    value = parse_json(text)
    require(set(value) == {"verdicts"} and isinstance(value["verdicts"], list), "Missing verdicts")
    sources = {d["passage_id"]: d["text"] for d in documents}
    normalized = []
    for verdict in value["verdicts"]:
        fields = {"claim_id", "reason", "evidence_ids"} | (
            {"has_explicit_conflict", "all_details_supported"} if boolean_checks else {"label"})
        require(isinstance(verdict, dict) and set(verdict) == fields, "Unexpected cited verdict fields")
        identifiers = verdict["evidence_ids"]
        require(isinstance(identifiers, list) and all(isinstance(i, str) for i in identifiers),
                "Citation IDs must be strings")
        require(len(identifiers) <= 2, "Too many citation IDs")
        require(all(isinstance(i, str) and i in sources for i in identifiers), "Unknown citation ID")
        # References denote a set of passages. Preserve the raw list above, but
        # attach each existing passage once, retaining its first occurrence.
        # Do not relax the original length cap or rescue unknown identifiers.
        identifiers = list(dict.fromkeys(identifiers))
        label = verdict.get("label")
        if boolean_checks:
            conflict, complete = verdict["has_explicit_conflict"], verdict["all_details_supported"]
            require(type(conflict) is bool and type(complete) is bool, "Entailment checks must be booleans")
            require(not (conflict and complete), "Contradiction and complete support are inconsistent")
            label = "contradicted" if conflict else ("supported" if complete else "not_supported")
        normalized.append({"claim_id": verdict["claim_id"], "label": label, "reason": verdict["reason"]} |
                          {"evidence": [{"passage_id": i, "quote": sources[i]} for i in identifiers]})
    return json.dumps({"verdicts": normalized}, ensure_ascii=False), value
