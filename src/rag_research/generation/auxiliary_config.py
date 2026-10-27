"""Explicit auxiliary sampling; the baseline's zero-temperature contract stays intact."""

import math
from dataclasses import asdict, dataclass

from rag_research.generation.config import GenerationConfig

FINAL_JSON_TRIGGER_PATTERN = r"</think>\s*(\{)"
CHATML_THINK_SUFFIX = "<|im_start|>assistant\n<think>\n"
THINK_PREFILL = "<think>\n"


def apply_reasoning_prefill(rendered, mode="none"):
    """Apply an explicitly configured prefix to exactly a bare assistant turn."""
    if mode == "none":
        return rendered
    if mode != "chatml_think_suffix_v1":
        raise ValueError("Unknown reasoning prefill mode")
    if not isinstance(rendered, str):
        raise ValueError("Reasoning prefill requires an actual rendered string")
    if rendered.endswith(CHATML_THINK_SUFFIX):
        return rendered
    bare = "<|im_start|>assistant\n"
    if rendered.endswith(bare):
        return rendered + THINK_PREFILL
    raise ValueError("Reasoning prefill requires the exact bare or prefilled ChatML assistant suffix")


def tokenize_reasoning_prompt(client, rendered, mode="none"):
    """Count raw/effective prompts and prove any addition leaves prior IDs intact."""
    effective = apply_reasoning_prefill(rendered, mode)
    raw_tokens = client.tokenize(rendered, special=True)
    tokens = raw_tokens if effective == rendered else client.tokenize(effective, special=True)
    added = []
    if effective != rendered:
        added = tokens[len(raw_tokens):]
        if (tokens[:len(raw_tokens)] != raw_tokens or
                added != client.tokenize(THINK_PREFILL, special=True)):
            raise ValueError("Reasoning prefill changed prior tokens or lacks its exact added token suffix")
    return {"raw_rendered_prompt": rendered, "raw_prompt_tokens": raw_tokens,
        "rendered_prompt": effective, "prompt_tokens": tokens, "input_tokens": len(tokens),
        "reasoning_prefill_audit": {"version": "reasoning-prefill-application-v1", "mode": mode,
            "applied": effective != rendered, "added_text": THINK_PREFILL if effective != rendered else "",
            "added_tokens": added, "raw_input_tokens": len(raw_tokens), "effective_input_tokens": len(tokens)}}


@dataclass(frozen=True)
class AuxiliaryGenerationConfig(GenerationConfig):
    top_k: int = 20
    top_p: float = 0.95
    min_p: float = 0.0
    presence_penalty: float = 0.0
    repeat_last_n: int = 64
    reasoning_budget_tokens: int = -1
    final_json_grammar: bool = False
    final_json_grammar_mode: str = "brace_trigger_v1"
    reasoning_prefill_mode: str = "none"

    def __post_init__(self):
        values = asdict(self)
        base = {k: v for k, v in values.items() if k in GenerationConfig.__dataclass_fields__}
        GenerationConfig(**{**base, "temperature": 0.0})
        if (isinstance(self.temperature, bool) or not math.isfinite(self.temperature)
                or not 0 < self.temperature <= 2):
            raise ValueError("Auxiliary sampling temperature must be in (0,2]")
        if type(self.top_k) is not int or self.top_k < 1:
            raise ValueError("Invalid auxiliary top_k")
        for key, lower, upper in (("top_p", 0, 1), ("min_p", 0, 1), ("presence_penalty", 0, 2)):
            value = values[key]
            if isinstance(value, bool) or not math.isfinite(value) or not lower <= value <= upper:
                raise ValueError(f"Invalid auxiliary {key}")
        if self.top_p == 0 or type(self.repeat_last_n) is not int or self.repeat_last_n < 1:
            raise ValueError("Invalid auxiliary sampler window")
        if type(self.reasoning_budget_tokens) is not int or self.reasoning_budget_tokens < -1:
            raise ValueError("Invalid reasoning token budget")
        if type(self.final_json_grammar) is not bool:
            raise ValueError("Final JSON grammar setting must be boolean")
        if self.final_json_grammar_mode not in {"brace_trigger_v1", "closing_tag_root_v2", "closing_tag_root_v3"}:
            raise ValueError("Unknown final JSON grammar mode")
        if self.reasoning_prefill_mode not in {"none", "chatml_think_suffix_v1"}:
            raise ValueError("Unknown reasoning prefill mode")
        if self.reasoning_prefill_mode != "none" and self.reasoning_budget_tokens < 0:
            raise ValueError("Reasoning prefill requires an explicit token budget")
