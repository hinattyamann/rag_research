"""Separate explicitly closed model reasoning from the single final JSON response."""

import json
import re

from rag_research.evaluation.claims import parse_json
from rag_research.experiments.frozen_trace import require
from rag_research.generation.auxiliary_config import FINAL_JSON_TRIGGER_PATTERN


def audit_final_json_grammar(response, config):
    if not getattr(config, "final_json_grammar", False):
        return None
    settings = response.get("generation_settings", {})
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
        require(len(identifiers) <= 2 and
                len(set(identifiers)) == len(identifiers), "Invalid or duplicate citation IDs")
        require(all(isinstance(i, str) and i in sources for i in identifiers), "Unknown citation ID")
        label = verdict.get("label")
        if boolean_checks:
            conflict, complete = verdict["has_explicit_conflict"], verdict["all_details_supported"]
            require(type(conflict) is bool and type(complete) is bool, "Entailment checks must be booleans")
            require(not (conflict and complete), "Contradiction and complete support are inconsistent")
            label = "contradicted" if conflict else ("supported" if complete else "not_supported")
        normalized.append({"claim_id": verdict["claim_id"], "label": label, "reason": verdict["reason"]} |
                          {"evidence": [{"passage_id": i, "quote": sources[i]} for i in identifiers]})
    return json.dumps({"verdicts": normalized}, ensure_ascii=False), value
