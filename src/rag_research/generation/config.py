"""Validated, versioned development conditions; no experiment tuning here."""

from dataclasses import asdict, dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class GenerationConfig:
    context_tokens: int = 4096
    max_output_tokens: int = 512
    passage_tokens: int = 512
    temperature: float = 0.0
    seed: int = 42
    threads: int = 6
    batch_tokens: int = 128
    repack: bool = False
    timeout_seconds: int = 300
    startup_timeout_seconds: int = 120

    def __post_init__(self):
        for key, value in asdict(self).items():
            if key in {"temperature", "seed", "repack"}:
                continue
            if type(value) is not int or value < 1:
                raise ValueError(f"{key} must be a positive integer")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if type(self.repack) is not bool:
            raise ValueError("repack must be a boolean")
        if self.temperature != 0.0 or isinstance(self.temperature, bool):
            raise ValueError("Phase 5 fixes temperature to zero")
        if self.max_output_tokens >= self.context_tokens:
            raise ValueError("Output reservation leaves no input context")


def load_config(path=Path("configs/phase5.yaml")):
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if value["schema_version"] != 1 or value["purpose"] not in {
        "phase5-development-only",
        "phase6-hybrid-baseline",
    }:
        raise ValueError("Unsupported baseline config")
    if value["purpose"] == "phase5-development-only" and value["retrieval"]["kind"] != "embedding":
        raise ValueError("Phase 5 uses the fixed Embedding retriever")
    top_k = value["retrieval"]["top_k"]
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    if value["purpose"] == "phase6-hybrid-baseline":
        retrieval = value["retrieval"]
        if retrieval["kind"] != "hybrid":
            raise ValueError("Phase 6 uses Hybrid retrieval")
        for key in ("candidate_count", "rrf_constant"):
            if type(retrieval[key]) is not int or retrieval[key] < 1:
                raise ValueError(f"{key} must be a positive integer")
        if top_k > retrieval["candidate_count"]:
            raise ValueError("top_k must not exceed candidate_count")
    return value, GenerationConfig(**value["generation"])
