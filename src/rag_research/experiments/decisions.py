"""A support fraction is not a correctness probability."""

import math


def decide(score, threshold):
    if not isinstance(threshold, (float, int)) or isinstance(threshold, bool):
        raise ValueError("Invalid threshold")
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Invalid threshold")
    if score is None:
        return {"score": None, "decision": "unscorable", "action": "keep_initial_fallback"}
    if isinstance(score, bool) or not isinstance(score, (float, int)):
        raise ValueError("Invalid support fraction")
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError("Invalid support fraction")
    decision = "accept" if score >= threshold else "rewrite"
    return {"score": score, "decision": decision,
            "action": "keep_initial" if decision == "accept" else "rewrite_requested"}


def decide_with_refusal(score, threshold, extraction, *, policy="keep_initial"):
    """A recognized bare refusal can request one rewrite while its score stays null."""
    if policy not in {"keep_initial", "rewrite_once"}:
        raise ValueError("Unknown bare-refusal policy")
    result = decide(score, threshold)
    bare_refusal = (extraction.get("status") == "not_applicable" and
                    extraction.get("extraction_kind") == "verbatim_sentence_units" and
                    extraction.get("unit_audit", {}).get("exclusion") == "standalone_refusal" and
                    extraction.get("parsed") == {"claims": []})
    if score is None and policy == "rewrite_once" and bare_refusal:
        result["action"] = "rewrite_requested"
    return result
