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
