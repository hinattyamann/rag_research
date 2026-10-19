"""Measured model calls, exact prompt audit, strict parsing and zero automatic retries."""

import hashlib
import re
import time
from dataclasses import asdict
from datetime import UTC, datetime

from rag_research.evaluation.claims import parse_claims
from rag_research.evaluation.judge import parse_verdicts
from rag_research.evaluation.schema import output_schema
from rag_research.evaluation.sentence_claims import extract_sentence_units
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
    require(task in {"extract_claims", "verify_claims"}, "Phase 8 does not generate rewrite candidates")
    messages = build_messages(prompts, task, payload)
    require(constraints in {"none", "json_schema_source_spans_v1",
                            "json_schema_source_spans_bounded_v2",
                            "json_schema_source_spans_compact_v3"}, "Unknown output constraints")
    sentence_mode = task == "extract_claims" and prompts.get("claim_units") == "verbatim-sentences-v1"
    schema = (output_schema(task, payload, bounded=constraints.endswith(("bounded_v2", "compact_v3")),
                            compact=constraints.endswith("compact_v3"))
              if constraints != "none" else None)
    request = {"binding": binding, "task": task, "messages": messages,
               "settings": asdict(config), "json_schema": schema}
    if sentence_mode:
        request["claim_units"] = "verbatim-sentences-v1"
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
        units = extract_sentence_units(payload["answer"])
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
                result["parsed"] = parse_verdicts(text, payload["claims"], payload["documents"])
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
