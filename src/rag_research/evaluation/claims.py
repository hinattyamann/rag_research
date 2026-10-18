"""Strict JSON validation: malformed extraction is never an empty-claim success."""

import json

from rag_research.experiments.frozen_trace import require


def _object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def parse_json(text):
    require(isinstance(text, str) and bool(text.strip()), "Empty model output")
    result = json.loads(text, object_pairs_hook=_object)
    require(isinstance(result, dict), "Output must be a JSON object")
    return result


def validate_claims(claims):
    require(isinstance(claims, list), "Claims must be a list")
    for index, claim in enumerate(claims, 1):
        require(isinstance(claim, dict) and set(claim) == {"claim_id", "text"},
                "Unexpected claim fields")
        require(claim["claim_id"] == f"c{index}", "Claim IDs must be consecutive")
        require(isinstance(claim["text"], str) and bool(claim["text"].strip()), "Empty claim text")
    return claims


def parse_claims(text):
    value = parse_json(text)
    require(set(value) == {"claims"}, "Unexpected extraction fields")
    return validate_claims(value["claims"])
