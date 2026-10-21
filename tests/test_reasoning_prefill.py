"""Already-prefilled thinking must start the native budget without changing inputs."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from rag_research.evaluation.reasoning_budget import audit_reasoning_budget
from rag_research.generation.auxiliary_config import (
    CHATML_THINK_SUFFIX,
    THINK_PREFILL,
    AuxiliaryGenerationConfig,
)
from rag_research.generation.config import GenerationConfig
from rag_research.generation.local import GenerationError, LlamaClient


def settings():
    return AuxiliaryGenerationConfig(temperature=1.0, reasoning_budget_tokens=10,
        final_json_grammar=True, final_json_grammar_mode="closing_tag_root_v3",
        reasoning_prefill_mode="chatml_think_suffix_v1")


@pytest.mark.parametrize("question", ["When did it open?", "いつ開館したか。"])
def test_native_prefill_is_bound_to_exact_counted_input_and_never_appended(monkeypatch, question):
    client = LlamaClient(1)
    prompt_tokens = [17, 18, 101, 3]
    requests = []

    def request(route, payload):
        requests.append((route, payload))
        if route == "/detokenize":
            assert payload["tokens"] == prompt_tokens
            return {"content": "<|im_start|>user\n" + question + "<|im_end|>\n" + CHATML_THINK_SUFFIX}
        if route == "/tokenize":
            assert payload["content"] == THINK_PREFILL and payload["parse_special"] is True
            return {"tokens": [101, 3]}
        assert route == "/completion"
        return {"generation_settings": {"generation_prompt": payload["generation_prompt"]}}

    monkeypatch.setattr(client, "request", request)
    result = client.complete(prompt_tokens, settings())
    payload = requests[-1][1]
    assert payload["prompt"] == prompt_tokens == [17, 18, 101, 3]
    assert payload["generation_prompt"] == THINK_PREFILL
    assert payload["reasoning_budget_tokens"] == 10
    assert result["generation_settings"]["generation_prompt"] == THINK_PREFILL
    assert client.completion_attempts == 1


@pytest.mark.parametrize("rendered,token_suffix", [
    ("<|im_start|>assistant\n", [101, 3]),
    (CHATML_THINK_SUFFIX + "extra", [101, 3]),
    ("<|im_start|>user\n<think>\n", [101, 3]),
    (CHATML_THINK_SUFFIX, [101, 4]),
    (CHATML_THINK_SUFFIX, []),
])
def test_invalid_or_unbound_suffix_stops_before_any_completion(monkeypatch, rendered, token_suffix):
    client = LlamaClient(1)
    calls = []
    monkeypatch.setattr(client, "detokenize", lambda tokens: rendered)
    monkeypatch.setattr(client, "tokenize", lambda *args, **kwargs: token_suffix)
    monkeypatch.setattr(client, "request", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(GenerationError, match="actual ChatML"):
        client.complete([17, 101, 3], settings())
    assert calls == [] and client.completion_attempts == 0


def test_default_baseline_and_auxiliary_requests_do_not_enable_prefill(monkeypatch):
    client = LlamaClient(1)
    requests = []
    monkeypatch.setattr(client, "request", lambda route, payload: requests.append((route, payload)) or {})
    for config in [GenerationConfig(), replace(settings(), reasoning_prefill_mode="none")]:
        client.complete([17], config)
    assert len(requests) == 2 and all(route == "/completion" for route, _ in requests)
    assert all("generation_prompt" not in payload for _, payload in requests)


def test_prefill_audit_requires_native_echo_single_closure_and_enforced_budget():
    client = SimpleNamespace(tokenize=lambda text, special: [101] if text == "<think>" else (
        [102] if text == "</think>" else [3] * 5))
    response = {"tokens": [3] * 10 + [102, 9],
                "generation_settings": {"generation_prompt": THINK_PREFILL}}
    audit = audit_reasoning_budget(client, response, settings())
    assert audit["native_generation_prompt_verified"] and audit["tokens_before_end_marker"] == 10
    for corrupted in [
        {**response, "generation_settings": {}},
        {**response, "generation_settings": {"generation_prompt": "<think>"}},
        {**response, "tokens": [101, 3, 102]},
        {**response, "tokens": [3] * 50 + [102]},
        {**response, "tokens": [3] * 10},
        {**response, "tokens": [3, 102, 102]},
    ]:
        with pytest.raises(ValueError):
            audit_reasoning_budget(client, corrupted, settings())


def test_unknown_prefill_or_unbounded_budget_is_rejected():
    with pytest.raises(ValueError, match="Unknown reasoning prefill"):
        replace(settings(), reasoning_prefill_mode="assume_open")
    with pytest.raises(ValueError, match="explicit token budget"):
        replace(settings(), reasoning_budget_tokens=-1)
