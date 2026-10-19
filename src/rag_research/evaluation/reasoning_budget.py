"""Audit the actual generated token boundary, including runtime-forced closure."""

from rag_research.experiments.frozen_trace import require

BUDGET_MESSAGE = "\nReturn only the requested final JSON now.\n"


def audit_reasoning_budget(client, response, config):
    budget = getattr(config, "reasoning_budget_tokens", -1)
    if budget < 0:
        return None
    start = client.tokenize("<think>", special=True)
    end = client.tokenize("</think>", special=True)
    require(len(start) == len(end) == 1, "Expected single-token Qwen reasoning boundaries")
    tokens = response.get("tokens", [])
    endings = [i for i, token in enumerate(tokens) if token == end[0]]
    beginnings = [i for i, token in enumerate(tokens) if token == start[0]]
    require(len(endings) == 1 and len(beginnings) <= 1, "Missing or multiple reasoning token blocks")
    origin = beginnings[0] + 1 if beginnings else 0
    size = endings[0] - origin
    message_size = len(client.tokenize(BUDGET_MESSAGE, special=True))
    require(0 <= size <= budget + message_size + 2, "Runtime did not honor reasoning token budget")
    return {"budget": budget, "tokens_before_end_marker": size,
            "budget_message_tokens": message_size, "full_response_tokens": len(tokens),
            "includes_runtime_budget_message_when_forced": True}
