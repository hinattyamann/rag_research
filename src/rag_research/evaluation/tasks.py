"""Measured model calls, exact prompt audit, strict parsing and zero automatic retries."""

import hashlib
import re
import time
from dataclasses import asdict
from datetime import UTC, datetime

from rag_research.evaluation.claims import parse_claims
from rag_research.evaluation.judge import parse_verdicts
from rag_research.evaluation.quote_alignment import align_quotes
from rag_research.evaluation.reasoned_json import (
    attach_cited_passages,
    audit_final_json_grammar,
    citation_id_audit,
    final_json,
)
from rag_research.evaluation.reasoning_budget import audit_reasoning_budget
from rag_research.evaluation.schema import cited_verdict_schema, output_schema
from rag_research.evaluation.sentence_claims import claim_unit_language, extract_sentence_units
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.protocol import build_messages
from rag_research.experiments.storage import (
    checkpoint,
    read_json,
    verify_checkpoint,
    write_json,
)
from rag_research.generation.local import GenerationError


def execute_task(client, config, prompts, task, payload, path, binding, *, constraints="none"):
    require(task in {"extract_claims", "verify_claims", "read_sources"}, "Phase 8 does not generate rewrite candidates")
    messages = build_messages(prompts, task, payload)
    require(constraints in {"none", "json_schema_source_spans_v1",
                            "json_schema_source_spans_bounded_v2",
                            "json_schema_source_spans_compact_v3",
                            "json_schema_verdicts_aligned_v4", "thinking_json_passage_ids_v1",
                            "thinking_json_passage_ids_v2"}, "Unknown output constraints")
    unit_mode = prompts.get("claim_units")
    unit_language = claim_unit_language(unit_mode)
    sentence_mode = task == "extract_claims" and unit_language is not None
    aligned = constraints == "json_schema_verdicts_aligned_v4"
    thinking = constraints in {"thinking_json_passage_ids_v1", "thinking_json_passage_ids_v2"}
    schema = (output_schema(task, payload, bounded=aligned or constraints.endswith(("bounded_v2", "compact_v3")),
                            compact=aligned or constraints.endswith("compact_v3"), aligned=aligned)
              if constraints != "none" and not thinking and task != "read_sources" else None)
    if task == "read_sources":
        from rag_research.evaluation.source_reading import reading_schema

        require(constraints in {"none", "thinking_json_passage_ids_v2"}, "Unsupported source reading constraints")
        if constraints != "none":
            require(getattr(config, "final_json_grammar", False), "Source reading requires final grammar")
            schema = reading_schema(payload["documents"], prompts.get("source_reading_schema", "free_quote_coverage_v1"))
    if constraints == "thinking_json_passage_ids_v2" and task == "verify_claims":
        require(getattr(config, "final_json_grammar", False), "Final-only grammar must be enabled")
        schema = cited_verdict_schema(payload, boolean_checks=prompts.get("judge_checks") == "conflict_then_complete_v1")
    request = {"binding": binding, "task": task, "messages": messages,
               "settings": asdict(config), "json_schema": schema}
    if sentence_mode:
        request["claim_units"] = unit_mode
    if thinking:
        request["output_parser"] = "closed_thinking_json_cited_passages_v1"
    request_hash = digest(request)
    if path.exists():
        saved = read_json(path)
        require(saved.get("request_sha256") == request_hash, "Saved task input hash mismatch")
        if saved["status"] == "started":
            # Unknown completion outcome must not be silently resampled after a crash.
            saved.update(status="error", error_code="interrupted_unknown_outcome",
                         error="Interrupted journal; no automatic retry",
                         cost_incomplete=saved["completion_attempted"])
            return checkpoint(path, saved)
        verify_checkpoint(saved)
        return saved
    started = time.perf_counter()
    result = {"schema_version": 1, "task": task, "request_sha256": request_hash,
              "binding": binding, "status": "started", "messages": messages,
              "settings": asdict(config), "started_at_utc": datetime.now(UTC).isoformat(),
              "output_constraints": constraints, "json_schema": schema,
              "json_schema_sha256": digest(schema) if schema else None,
              "completion_attempted": False, "input_tokens": None, "output_tokens": None,
              "parsed": None, "error": None, "error_code": None, "cost_incomplete": False,
              "audit_warnings": []}
    write_json(path, result)
    if sentence_mode:
        units = extract_sentence_units(payload["answer"], language=unit_language)
        result.update(parsed={"claims": units["claims"]}, unit_audit=units,
                      status="ok" if units["claims"] else "not_applicable",
                      input_tokens=0, output_tokens=0, extraction_kind="verbatim_sentence_units",
                      elapsed_seconds=time.perf_counter() - started)
        return checkpoint(path, result)
    try:
        rendered = client.render(messages)
        tokens = client.tokenize(rendered, special=True)
        result.update(rendered_prompt=rendered,
                      rendered_prompt_sha256=hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
                      prompt_tokens=tokens, input_tokens=len(tokens),
                      prepare_seconds=time.perf_counter() - started)
        if len(tokens) + config.max_output_tokens > config.context_tokens:
            result.update(status="error", error_code="input_overflow",
                          error="Input plus output reservation exceeds context; nothing truncated")
        else:
            result["completion_attempted"] = True
            write_json(path, result)
            call_started = time.perf_counter()
            response = (client.complete(tokens, config, json_schema=schema) if schema
                        else client.complete(tokens, config))
            result.update(runtime_response=response, raw_output=response.get("content"),
                          generation_seconds=time.perf_counter() - call_started,
                          output_tokens=len(response.get("tokens", [])))
            write_json(path, result)
            require(not response.get("truncated"), "Runtime truncated the input")
            require(response.get("stop_type") in {"eos", "word"},
                    f"Incomplete output: finish={response.get('stop_type')}")
            text = response.get("content")
            if task == "extract_claims":
                result["parsed"] = {"claims": parse_claims(text)}
                result["status"] = "ok" if result["parsed"]["claims"] else "not_applicable"
                prose = re.sub(r"\[[^\[\]\n]*\]", "", payload["answer"]).strip()
                if not result["parsed"]["claims"] and prose:
                    result["audit_warnings"].append("empty_claims_on_prose_requires_review")
            elif task == "verify_claims":
                if thinking:
                    result["reasoning_budget_audit"] = audit_reasoning_budget(client, response, config)
                    result["final_grammar_audit"] = audit_final_json_grammar(response, config, schema=schema, client=client)
                    text, result["model_reasoning"] = final_json(text)
                    text, result["raw_cited_verdicts"] = attach_cited_passages(
                        text, payload["documents"], boolean_checks=prompts.get("judge_checks") == "conflict_then_complete_v1")
                    result["citation_normalization"] = citation_id_audit(result["raw_cited_verdicts"])
                    if result["citation_normalization"]["deduplicated_claim_ids"]:
                        result["audit_warnings"].append("duplicate_citation_ids_normalized_without_semantic_changes")
                    result["evidence_scope"] = "programmatically_attached_full_cited_passages_not_model_quotations"
                if aligned:
                    text, result["quote_alignment"] = align_quotes(text, payload["documents"])
                result["parsed"] = parse_verdicts(text, payload["claims"], payload["documents"])
                result["status"] = "ok"
            elif task == "read_sources":
                from rag_research.evaluation.source_reading import parse_reading

                if thinking:
                    result["reasoning_budget_audit"] = audit_reasoning_budget(client, response, config)
                    result["final_grammar_audit"] = audit_final_json_grammar(response, config, schema=schema, client=client)
                    text, result["model_reasoning"] = final_json(text)
                result["parsed"] = parse_reading(text, payload["documents"])
                result["status"] = "ok"
            else:
                raise ValueError("Phase 8 does not generate rewrite candidates")
    except GenerationError as error:
        result.update(status="error", error_code="runtime_error", error=str(error),
                      cost_incomplete=result["completion_attempted"])
    except (ValueError, TypeError, KeyError) as error:
        result.update(status="error", error_code="invalid_output", error=str(error))
    result["elapsed_seconds"] = time.perf_counter() - started
    return checkpoint(path, result)
