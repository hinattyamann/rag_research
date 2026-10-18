"""Order-independent output constraints; evidence choices contain no gold labels."""

import re
from copy import deepcopy

from rag_research.evaluation.claims import validate_claims
from rag_research.experiments.frozen_trace import require, validate_documents


def object_schema(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


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


def output_schema(task, payload, *, bounded=False):
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
        "quote": {"enum": quote_candidates(d["text"])},
    }) for d in sorted(documents, key=lambda d: d["passage_id"])]}
    verdict = object_schema({
        "claim_id": {"enum": [c["claim_id"] for c in claims]},
        "label": {"enum": ["supported", "contradicted", "not_supported"]},
        "evidence": {"type": "array", "items": evidence},
        "reason": {"type": "string", "minLength": 1},
    })
    if bounded:
        verdict["properties"]["evidence"]["maxItems"] = 2
        verdict["properties"]["reason"]["maxLength"] = 200
        ordered = []
        for claim in claims:
            entry = deepcopy(verdict)
            entry["properties"]["claim_id"] = {"const": claim["claim_id"]}
            ordered.append(entry)
        # Draft-7 tuple items are supported by this pinned runtime; avoid prefixItems.
        return object_schema({"verdicts": {"type": "array", "items": ordered,
                                           "minItems": len(claims), "maxItems": len(claims)}})
    return object_schema({"verdicts": {"type": "array", "items": verdict,
                                       "minItems": len(claims), "maxItems": len(claims)}})
