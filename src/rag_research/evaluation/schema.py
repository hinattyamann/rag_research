"""Order-independent output constraints; evidence choices contain no gold labels."""

import re
from copy import deepcopy

from rag_research.evaluation.claims import validate_claims
from rag_research.experiments.frozen_trace import require, validate_documents


def object_schema(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def cited_verdict_schema(payload, *, boolean_checks=False, require_cited_decisions=False):
    """Small final-only grammar; its definition is invariant to passage order."""
    claims, documents = payload["claims"], payload["documents"]
    validate_claims(claims)
    validate_documents(documents)
    require(bool(claims), "No Judge schema for empty claims")
    require(not require_cited_decisions or boolean_checks, "Cited decisions require Boolean checks")
    items = []
    for claim in claims:
        fields = {"claim_id": {"const": claim["claim_id"]}}
        fields.update({"has_explicit_conflict": {"type": "boolean"},
                       "all_details_supported": {"type": "boolean"}} if boolean_checks else
                      {"label": {"enum": ["supported", "contradicted", "not_supported"]}})
        fields.update(reason={"type": "string", "minLength": 1, "maxLength": 160},
                      evidence_ids={"type": "array", "maxItems": 2,
                                    "items": {"enum": sorted(d["passage_id"] for d in documents)}})
        if require_cited_decisions:
            variants = []
            for conflict, complete in ((True, False), (False, True), (False, False)):
                variant = deepcopy(fields)
                variant["has_explicit_conflict"] = {"const": conflict}
                variant["all_details_supported"] = {"const": complete}
                variant["evidence_ids"]["minItems"] = int(conflict or complete)
                variants.append(object_schema(variant))
            items.append({"anyOf": variants})
        else:
            items.append(object_schema(fields))
    return object_schema({"verdicts": {"type": "array", "items": items,
                                       "minItems": len(items), "maxItems": len(items)}})


def quote_candidates(text):
    # Exact single segments, adjacent pairs, and full text. No source text is rewritten.
    boundaries = [0] + [m.end() for m in re.finditer(r"[.!?;]\s+", text)] + [len(text)]
    spans = set()
    for index in range(len(boundaries) - 1):
        for count in (1, 2):
            end = min(index + count, len(boundaries) - 1)
            span = text[boundaries[index]:boundaries[end]].strip()
            if span:
                spans.add(span)
    spans.add(text.strip())
    return sorted(spans)


def compact_quote_candidates(text):
    spans = {s for s in quote_candidates(text) if len(s) <= 320}
    # Long sentences still have exact substrings available, never paraphrases.
    words = list(re.finditer(r"\S+", text))
    for start in range(0, len(words), 12):
        for count in (12, 24):
            end = min(start + count, len(words))
            snippet = text[words[start].start():words[end - 1].end()]
            if len(snippet) <= 320:
                spans.add(snippet)
    if not spans and text.strip():
        spans.add(text.strip()[:320])
    return sorted(spans)


def output_schema(task, payload, *, bounded=False, compact=False, aligned=False):
    if task == "extract_claims":
        claim = object_schema({"claim_id": {"type": "string", "pattern": "^c[1-9][0-9]*$"},
                               "text": {"type": "string", "minLength": 1}})
        return object_schema({"claims": {"type": "array", "items": claim}})
    require(task == "verify_claims", "No constrained rewrite in Phase 8")
    claims, documents = payload["claims"], payload["documents"]
    validate_claims(claims)
    validate_documents(documents)
    require(bool(claims), "No Judge schema for empty claims")
    # Sorting is essential: the decoder grammar must not change with evidence order.
    evidence = {"anyOf": [object_schema({
        "passage_id": {"const": d["passage_id"]},
        "quote": ({"type": "string", "minLength": 1, "maxLength": 320} if aligned else
                  {"enum": (compact_quote_candidates if compact else quote_candidates)(d["text"])}),
    }) for d in sorted(documents, key=lambda d: d["passage_id"])]}
    verdict = object_schema({
        "claim_id": {"enum": [c["claim_id"] for c in claims]},
        "label": {"enum": ["supported", "contradicted", "not_supported"]},
        "evidence": {"type": "array", "items": evidence},
        "reason": {"type": "string", "minLength": 1},
    })
    if bounded:
        verdict["properties"]["evidence"]["maxItems"] = 2
        verdict["properties"]["reason"]["maxLength"] = 400 if aligned else (120 if compact else 200)
        if compact:
            # Compare source meaning before committing to a label. This decoder
            # order is identical for all evidence permutations and repeat trials.
            fields = verdict["properties"]
            order = ("claim_id", "reason", "label", "evidence") if aligned else (
                "claim_id", "reason", "evidence", "label")
            verdict = object_schema({k: fields[k] for k in order})
        ordered = []
        for claim in claims:
            entry = deepcopy(verdict)
            entry["properties"]["claim_id"] = {"const": claim["claim_id"]}
            if compact:
                variants = []
                for label in ("supported", "contradicted", "not_supported"):
                    variant = deepcopy(entry)
                    variant["properties"]["label"] = {"const": label}
                    if label != "not_supported":
                        variant["properties"]["evidence"]["minItems"] = 1
                    variants.append(variant)
                ordered.append({"anyOf": variants})
            else:
                ordered.append(entry)
        # Draft-7 tuple items are supported by this pinned runtime; avoid prefixItems.
        return object_schema({"verdicts": {"type": "array", "items": ordered,
                                           "minItems": len(claims), "maxItems": len(claims)}})
    return object_schema({"verdicts": {"type": "array", "items": verdict,
                                       "minItems": len(claims), "maxItems": len(claims)}})
