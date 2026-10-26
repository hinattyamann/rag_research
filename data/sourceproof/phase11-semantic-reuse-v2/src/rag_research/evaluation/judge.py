"""Validate every verdict and exact evidence quotes before computing F."""

from rag_research.evaluation.claims import parse_json, validate_claims
from rag_research.experiments.frozen_trace import require, validate_documents


def parse_verdicts(text, claims, documents):
    validate_claims(claims)
    validate_documents(documents)
    value = parse_json(text)
    require(set(value) == {"verdicts"} and isinstance(value["verdicts"], list),
            "Unexpected verification fields")
    verdicts = value["verdicts"]
    require(len(verdicts) == len(claims), "Missing/extra claim verdicts")
    sources = {d["passage_id"]: d["text"] for d in documents}
    for claim, verdict in zip(claims, verdicts, strict=True):
        require(isinstance(verdict, dict) and set(verdict) ==
                {"claim_id", "label", "evidence", "reason"}, "Unexpected verdict fields")
        require(verdict["claim_id"] == claim["claim_id"], "Missing, duplicate or reordered claim ID")
        require(verdict["label"] in {"supported", "contradicted", "not_supported"}, "Unknown label")
        require(isinstance(verdict["reason"], str) and bool(verdict["reason"].strip()), "Empty reason")
        require(isinstance(verdict["evidence"], list), "Evidence must be a list")
        if verdict["label"] != "not_supported":
            require(bool(verdict["evidence"]), "Supported/contradicted needs evidence")
        for evidence in verdict["evidence"]:
            require(isinstance(evidence, dict) and set(evidence) == {"passage_id", "quote"},
                    "Unexpected quote fields")
            identifier, quote = evidence["passage_id"], evidence["quote"]
            require(isinstance(identifier, str) and identifier in sources, "Unknown evidence ID")
            require(isinstance(quote, str) and bool(quote.strip()), "Empty evidence quote")
            require(quote in sources[identifier], "Quote is not verbatim in the given passage")
    score = (sum(v["label"] == "supported" for v in verdicts) / len(claims)) if claims else None
    return {"verdicts": verdicts, "score": score}
