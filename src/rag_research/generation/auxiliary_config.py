"""Explicit auxiliary sampling; the baseline's zero-temperature contract stays intact."""

import math
from dataclasses import asdict, dataclass

from rag_research.generation.config import GenerationConfig

FINAL_JSON_TRIGGER_PATTERN = r"</think>\s*(\{)"


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
