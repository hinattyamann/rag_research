"""Audit the actual generated token boundary, including runtime-forced closure."""

from rag_research.experiments.frozen_trace import require
from rag_research.generation.auxiliary_config import THINK_PREFILL

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
    prefilled = getattr(config, "reasoning_prefill_mode", "none") == "chatml_think_suffix_v1"
    if prefilled:
        require(response.get("generation_settings", {}).get("generation_prompt") == THINK_PREFILL,
                "Runtime did not preserve the verified reasoning prefill")
        require(not beginnings, "Prefilled reasoning unexpectedly reopened in generated tokens")
    origin = beginnings[0] + 1 if beginnings else 0
    size = endings[0] - origin
    message_size = len(client.tokenize(BUDGET_MESSAGE, special=True))
    require(0 <= size <= budget + message_size + 2, "Runtime did not honor reasoning token budget")
    result = {"budget": budget, "tokens_before_end_marker": size,
            "budget_message_tokens": message_size, "full_response_tokens": len(tokens),
            "includes_runtime_budget_message_when_forced": True}
    if prefilled:
        result.update(reasoning_prefill_mode="chatml_think_suffix_v1",
                      native_generation_prompt_verified=True,
                      prefilled_opening_marker_excluded_from_generated_tokens=True)
    return result
