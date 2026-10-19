"""Durable single prose-generation attempt using only original evidence and answer."""

import hashlib
import re
import time
from dataclasses import asdict
from datetime import UTC, datetime

from rag_research.evaluation.claims import parse_json
from rag_research.evaluation.reasoned_json import final_json
from rag_research.evaluation.reasoning_budget import audit_reasoning_budget
from rag_research.evaluation.schema import object_schema
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.protocol import build_messages
from rag_research.experiments.storage import checkpoint, read_json, verify_checkpoint, write_json
from rag_research.generation.local import GenerationError


def rewrite_once(client, config, prompts, trace, path, binding):
    payload = {"question": trace["question"], "answer": trace["answer"],
               "documents": trace["documents"]}
    messages = build_messages(prompts, "rewrite_answer", payload)
    thinking = prompts.get("rewrite_format") == "thinking_checked_json_v2"
    checked = thinking or prompts.get("rewrite_format") == "checked_json_v1"
    final_grammar = thinking and getattr(config, "final_json_grammar", False)
    schema = object_schema({"source_facts": {"type": "string", "minLength": 1, "maxLength": 1200},
                            "draft_issues": {"type": "string", "minLength": 1, "maxLength": 600},
                            "answer": {"type": "string", "minLength": 1, "maxLength": 2400}}) if checked else None
    request = {"binding": binding, "messages": messages, "settings": asdict(config)}
    if checked:
        request.update(json_schema=schema, final_answer_token_limit=512)
    if thinking:
        request.update(json_schema=schema if final_grammar else None, output_parser="closed_thinking_checked_json_v2")
    request_hash = digest(request)
    if path.exists():
        saved = read_json(path)
        require(saved["request_sha256"] == request_hash, "Saved rewrite input hash mismatch")
        if saved["status"] == "started":
            saved.update(status="error", error_code="interrupted_unknown_outcome",
                         error="Interrupted attempt; no automatic retry", cost_incomplete=True)
            # Do not hash a previous checkpoint hash into a new checkpoint.
            saved.pop("result_sha256", None)
            return checkpoint(path, saved)
        verify_checkpoint(saved)
        return saved
    started = time.perf_counter()
    result = {"schema_version": 1, "task": "rewrite_answer", "binding": binding,
              "request_sha256": request_hash, "messages": messages, "settings": asdict(config),
              "status": "started", "started_at_utc": datetime.now(UTC).isoformat(),
              "completion_attempted": False, "input_tokens": None, "output_tokens": None,
              "answer": None, "error": None, "error_code": None, "cost_incomplete": False,
              "audit_warnings": []}
    write_json(path, result)
    try:
        rendered = client.render(messages)
        tokens = client.tokenize(rendered, special=True)
        result.update(rendered_prompt=rendered, prompt_tokens=tokens, input_tokens=len(tokens),
                      rendered_prompt_sha256=hashlib.sha256(rendered.encode("utf-8")).hexdigest())
        if len(tokens) + config.max_output_tokens > config.context_tokens:
            result.update(status="error", error_code="input_overflow",
                          error="Input plus output reservation exceeds context; nothing truncated")
        else:
            result["completion_attempted"] = True
            write_json(path, result)
            response = (client.complete(tokens, config, json_schema=schema) if schema and (not thinking or final_grammar)
                        else client.complete(tokens, config))
            result.update(runtime_response=response, raw_output=response.get("content"),
                          output_tokens=len(response.get("tokens", [])))
            write_json(path, result)
            require(not response.get("truncated"), "Runtime truncated input")
            require(response.get("stop_type") in {"eos", "word"}, "Incomplete rewrite output")
            answer = response.get("content")
            if thinking:
                result["reasoning_budget_audit"] = audit_reasoning_budget(client, response, config)
                answer, result["model_reasoning"] = final_json(answer)
            if checked:
                review = parse_json(answer)
                require(set(review) == {"source_facts", "draft_issues", "answer"}, "Unexpected rewrite review fields")
                require(all(isinstance(v, str) and v.strip() for v in review.values()), "Empty rewrite review")
                result["source_review"] = review
                result["review_json_schema"] = schema
                result["review_decoder_constrained"] = not thinking or final_grammar
                answer = review["answer"]
                result["final_answer_tokens"] = len(client.tokenize(answer, special=False))
                require(result["final_answer_tokens"] <= 512, "Final answer exceeds 512-token candidate budget")
            require(isinstance(answer, str) and bool(answer.strip()), "Empty rewrite output")
            citations = sorted(set(re.findall(r"\[([^\[\]\n]+)\]", answer)))
            known = {d["passage_id"] for d in trace["documents"]}
            unknown = sorted(set(citations) - known)
            result.update(status="ok", answer=answer.strip(), cited_passage_ids=citations,
                          unknown_citation_ids=unknown)
            if unknown:
                result["audit_warnings"].append("unknown_citations_require_manual_review")
    except GenerationError as error:
        result.update(status="error", error_code="runtime_error", error=str(error),
                      cost_incomplete=result["completion_attempted"])
    except (ValueError, TypeError, KeyError) as error:
        result.update(status="error", error_code="invalid_output", error=str(error))
    result["elapsed_seconds"] = time.perf_counter() - started
    return checkpoint(path, result)
