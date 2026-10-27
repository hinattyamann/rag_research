"""Invented tokenizer and transport only; bare-template prefill, never Native."""

import json

import pytest

from rag_research.evaluation.tasks import execute_task
from rag_research.experiments.storage import verify_checkpoint
from rag_research.generation.auxiliary_config import (
    CHATML_THINK_SUFFIX,
    THINK_PREFILL,
    AuxiliaryGenerationConfig,
    apply_reasoning_prefill,
    tokenize_reasoning_prompt,
)
from rag_research.generation.local import LlamaClient
from rag_research.recovery.answer_rewrite import rewrite_once

BARE = "<|im_start|>assistant\n"


class Client:
    """Reversible invented IDs; actual Core complete is only used via fake request."""

    def __init__(self, *, language="en", suffix=BARE):
        self.calls = 0
        self.suffix = suffix
        self.language = language

    def render(self, messages):
        self.messages = messages
        return json.dumps(messages, ensure_ascii=False) + self.suffix

    def tokenize(self, text, *, special=False):
        result = []
        while text:
            if text.startswith("<think>"):
                result.append(70001)
                text = text[7:]
            else:
                result.append(ord(text[0]) + 1000)
                text = text[1:]
        return result

    def detokenize(self, tokens):
        return "".join("<think>" if token == 70001 else chr(token - 1000) for token in tokens)

    def complete(self, tokens, config, **kwargs):
        self.calls += 1
        self.sent_tokens = list(tokens)
        assert self.detokenize(tokens).endswith(CHATML_THINK_SUFFIX)
        data = json.loads(self.messages[1]["content"].removeprefix("Input JSON:\n"))
        if set(data) == {"answer"}:
            value = {"claims": [{"claim_id": "c1", "text": "Invented fact."}]}
        elif "claims" in data:
            value = {"verdicts": [{"claim_id": "c1", "label": "supported", "reason": "Fixture",
                "evidence": [{"passage_id": "d", "quote": "Invented fact."}]}]}
        else:
            return {"content": "Invented answer. [d]", "tokens": [1], "stop_type": "eos", "truncated": False}
        return {"content": json.dumps(value), "tokens": [1], "stop_type": "eos", "truncated": False}


@pytest.mark.parametrize("text", ["Question?", "質問？"])
def test_bare_template_gets_exact_once_prefill_with_audited_raw_and_added_ids(text):
    raw = text + BARE
    client = Client()
    prepared = tokenize_reasoning_prompt(client, raw, "chatml_think_suffix_v1")
    assert prepared["raw_rendered_prompt"] == raw
    assert prepared["rendered_prompt"] == raw + THINK_PREFILL
    assert prepared["prompt_tokens"] == prepared["raw_prompt_tokens"] + client.tokenize(THINK_PREFILL, special=True)
    assert prepared["reasoning_prefill_audit"]["added_tokens"] == client.tokenize(THINK_PREFILL, special=True)
    assert prepared["reasoning_prefill_audit"]["applied"] is True
    assert apply_reasoning_prefill(prepared["rendered_prompt"], "chatml_think_suffix_v1") == prepared["rendered_prompt"]
    assert client.calls == 0


@pytest.mark.parametrize("raw", ["Question?" + BARE, "Question?" + CHATML_THINK_SUFFIX, "ordinary baseline template"])
def test_default_none_keeps_baseline_text_and_token_bytes_unchanged(raw):
    client = Client()
    result = tokenize_reasoning_prompt(client, raw)
    assert result["raw_rendered_prompt"] == result["rendered_prompt"] == raw
    assert result["raw_prompt_tokens"] == result["prompt_tokens"] == client.tokenize(raw, special=True)
    assert result["reasoning_prefill_audit"]["applied"] is False
    assert result["reasoning_prefill_audit"]["added_tokens"] == []


def test_existing_full_suffix_is_byte_and_token_unchanged():
    result = tokenize_reasoning_prompt(Client(), "Question?" + CHATML_THINK_SUFFIX, "chatml_think_suffix_v1")
    assert result["rendered_prompt"] == result["raw_rendered_prompt"]
    assert result["prompt_tokens"] == result["raw_prompt_tokens"]
    assert result["reasoning_prefill_audit"]["applied"] is False


@pytest.mark.parametrize("raw", [None, "", "<|im_start|>user\n", BARE + " ", CHATML_THINK_SUFFIX + "extra",
    BARE + "<think>\n<think>\n", "<|im_start|>assistant\n<think>"])
def test_unknown_template_suffix_is_rejected_without_a_completion(raw):
    with pytest.raises(ValueError, match="Reasoning prefill"):
        apply_reasoning_prefill(raw, "chatml_think_suffix_v1")


def test_unknown_mode_and_token_prefix_mutation_are_rejected():
    with pytest.raises(ValueError, match="Unknown"):
        apply_reasoning_prefill(BARE, "assume_open")

    class ChangingClient(Client):
        def tokenize(self, text, *, special=False):
            tokens = super().tokenize(text, special=special)
            return [99, *tokens] if text.endswith(CHATML_THINK_SUFFIX) else tokens

    with pytest.raises(ValueError, match="changed prior tokens"):
        tokenize_reasoning_prompt(ChangingClient(), BARE, "chatml_think_suffix_v1")


@pytest.mark.parametrize("task", ["extract_claims", "verify_claims", "rewrite_answer"])
@pytest.mark.parametrize("language", ["en", "ja"])
def test_common_task_and_rewrite_paths_count_and_store_effective_prefill(task, language, tmp_path):
    client = Client(language=language)
    config = AuxiliaryGenerationConfig(context_tokens=12288, max_output_tokens=512, temperature=0.2,
        reasoning_budget_tokens=128, reasoning_prefill_mode="chatml_think_suffix_v1")
    prompts = {"tasks": {name: {"system": "人工入力" if language == "ja" else "Invented input"}
        for name in ("extract_claims", "verify_claims", "rewrite_answer")}}
    docs = [{"passage_id": "d", "title": "Invented title", "text": "Invented fact."}]
    payload = {"answer": "Invented fact."} if task == "extract_claims" else {
        "question": "Q?", "answer": "Invented fact.", "claims": [{"claim_id": "c1", "text": "Invented fact."}], "documents": docs}
    if task == "rewrite_answer":
        result = rewrite_once(client, config, prompts, {k: payload[k] for k in ("question", "answer", "documents")},
            tmp_path / "rewrite.json", {"fixture_only": True})
    else:
        result = execute_task(client, config, prompts, task, payload, tmp_path / "task.json", {"fixture_only": True})
    assert result["status"] == "ok" and client.calls == 1
    assert result["raw_rendered_prompt"].endswith(BARE)
    assert result["rendered_prompt"] == result["raw_rendered_prompt"] + THINK_PREFILL
    assert result["prompt_tokens"] == client.sent_tokens
    assert result["input_tokens"] == len(client.sent_tokens)
    assert result["reasoning_prefill_audit"]["added_tokens"] == client.tokenize(THINK_PREFILL, special=True)
    verify_checkpoint(result)


def test_prepared_bare_prompt_uses_existing_native_generation_prompt_contract():
    fake = Client()
    prepared = tokenize_reasoning_prompt(fake, "Invented input" + BARE, "chatml_think_suffix_v1")
    # Instantiate no real HTTP client, socket or Runtime; exercise actual method on a fake self.
    fake.completion_attempts = 0
    requests = []
    fake.request = lambda route, payload: requests.append((route, payload)) or {"fixture_only": True}
    config = AuxiliaryGenerationConfig(temperature=0.2, reasoning_budget_tokens=128,
        reasoning_prefill_mode="chatml_think_suffix_v1")
    LlamaClient.complete(fake, prepared["prompt_tokens"], config)
    assert len(requests) == fake.completion_attempts == 1
    assert requests[0][0] == "/completion"
    assert requests[0][1]["prompt"] == prepared["prompt_tokens"]
    assert requests[0][1]["generation_prompt"] == THINK_PREFILL
    assert requests[0][1]["reasoning_budget_tokens"] == 128
