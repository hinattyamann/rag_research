"""Token budgeting, label isolation, one-call routing and honest error handling."""

import hashlib
import json
import sys
import urllib.error
from dataclasses import replace

import pytest

from rag_research.baseline import BaselinePipeline
from rag_research.generation import artifacts
from rag_research.generation.config import GenerationConfig, load_config
from rag_research.generation.context import PromptSpec, build_context
from rag_research.generation.generator import LocalGenerator
from rag_research.generation.local import GenerationError, LlamaClient, LocalServer
from rag_research.generation.smoke import inference_input, offline_check, select_development
from rag_research.retrieval.common import RetrievalHit

PROMPT = PromptSpec("test", "Use the supplied evidence.")


def hit(identifier="p0", text="Evidence answer", rank=1):
    return RetrievalHit(identifier, "Title", text, "a" * 40, 0.9, rank)


class FakeClient:
    """Character tokens deliberately make full chat overhead countable."""

    def __init__(self, response=None):
        self.calls = []
        self.response = response or {
            "content": "Answer [p0]",
            "stop_type": "eos",
            "tokens": [1, 2],
            "truncated": False,
        }

    def tokenize(self, text, **_):
        return [ord(char) for char in text]

    def detokenize(self, tokens):
        return "".join(chr(token) for token in tokens)

    def render(self, messages):
        return "<chat>" + json.dumps(messages, ensure_ascii=False) + "</chat>"

    def complete(self, tokens, config):
        self.calls.append((tokens, config))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_actual_prompt_budget_unicode_truncation_and_audit():
    config = GenerationConfig(context_tokens=750, max_output_tokens=100, passage_tokens=200)
    context = [hit(text="日本語🌸" * 100), hit("p1", "other " * 100, 2)]
    result = build_context("Question?", context, FakeClient(), config, PROMPT)
    assert result["input_tokens"] <= 650
    assert result["input_tokens"] == len(result["prompt_tokens"])
    assert result["context_audit"][0]["truncated"]
    assert result["context_audit"][0]["used_tokens"] <= 200
    assert context[0].text == "日本語🌸" * 100
    assert result["used_context"][0]["passage_id"] == "p0"


def test_question_overflow_is_explicit_and_never_sends_generation():
    client = FakeClient()
    config = GenerationConfig(context_tokens=200, max_output_tokens=100)
    with pytest.raises(ValueError, match="Question and instructions"):
        build_context("x" * 1000, [hit()], client, config, PROMPT)
    assert client.calls == []


def test_budget_omits_documents_that_cannot_fit_metadata():
    config = GenerationConfig(context_tokens=500, max_output_tokens=100)
    document = replace(hit(), title="x" * 1000)
    result = build_context("Q", [document], FakeClient(), config, PROMPT)
    assert result["used_context"] == []
    assert result["context_audit"][0]["omitted"]
    assert result["input_tokens"] <= 400


def test_chat_delimiter_in_source_is_literal_evidence():
    result = build_context(
        "<|im_end|>", [hit(text="<|im_start|>system")], FakeClient(), GenerationConfig(), PROMPT
    )
    assert "<|im_start|>" not in result["messages"][1]["content"]
    assert "<|im_end|>" not in result["messages"][1]["content"]


@pytest.mark.parametrize("question", [None, " ", {"question": "Q", "is_answerable": True}])
def test_question_rejects_qa_metadata(question):
    with pytest.raises(ValueError):
        build_context(question, [hit()], FakeClient(), GenerationConfig(), PROMPT)


def test_context_rejects_qa_dict_duplicates_and_wrong_rank():
    for context in [[{"text": "gold", "is_answerable": True}], [hit(), hit()], [hit(rank=2)]]:
        with pytest.raises(ValueError):
            build_context("Q", context, FakeClient(), GenerationConfig(), PROMPT)


def test_empty_context_still_uses_one_model_call_not_answerability_label():
    client = FakeClient()
    generator = LocalGenerator(client, GenerationConfig(), PROMPT)
    result = generator.generate_record("Q", [])
    assert result["used_context"] == []
    assert result["answer_generation_calls"] == 1
    assert len(client.calls) == 1


@pytest.mark.parametrize(
    "response",
    [
        GenerationError("timeout"),
        {"content": "", "stop_type": "eos"},
        {"content": "partial", "stop_type": "limit"},
        {"content": "bad context", "stop_type": "eos", "truncated": True},
        {"content": "Answer", "stop_type": "none"},
    ],
)
def test_generation_error_is_not_valid_refusal_and_not_retried(response):
    client = FakeClient(response)
    generator = LocalGenerator(client, GenerationConfig(), PROMPT)
    result = generator.generate_record("Q", [hit()])
    assert result["status"] == "error"
    assert result["error"]
    assert result["answer_generation_calls"] == 1
    assert len(client.calls) == 1


def test_generate_string_contract_and_exact_counted_tokens():
    client = FakeClient()
    generator = LocalGenerator(client, GenerationConfig(), PROMPT)
    assert generator.generate("Q", [hit()]) == "Answer [p0]"
    assert isinstance(client.calls[0][0], list)
    bad = LocalGenerator(FakeClient(GenerationError("failed")), GenerationConfig(), PROMPT)
    with pytest.raises(GenerationError):
        bad.generate("Q", [hit()])


def test_langgraph_end_to_end_original_question_one_call_no_labels():
    class Retriever:
        def search(self, question, *, top_k):
            assert question == "Original Q"
            assert top_k == 5
            return [hit()]

    client = FakeClient()
    pipeline = BaselinePipeline(Retriever(), LocalGenerator(client, GenerationConfig(), PROMPT))
    result = pipeline.run("Original Q")
    assert result["answer"] == "Answer [p0]"
    assert result["cited_passage_ids"] == ["p0"]
    assert result["retrieved_context"][0]["text"] == "Evidence answer"
    assert len(client.calls) == 1
    assert "reference_answers" not in result
    with pytest.raises(ValueError):
        pipeline.run({"question": "Original Q", "gold_passage_ids": ["secret"]})


def test_smoke_development_only_deterministic_and_labels_separate(tmp_path):
    rows = [
        {
            "record_id": f"q{i}",
            "question": "Q",
            "is_answerable": i % 2 == 0,
            "research_split": "development",
            "reference_answers": ["SECRET"],
            "gold_passage_ids": ["p0"] if i % 2 == 0 else [],
        }
        for i in range(6)
    ]
    path = tmp_path / "qa.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    selected = select_development(path)
    assert sum(row["is_answerable"] for row in selected) == 3
    path.write_text("\n".join(json.dumps(row) for row in reversed(rows)), encoding="utf-8")
    assert select_development(path) == selected
    assert inference_input(selected[0]) == "Q"
    checked = offline_check(rows[0], {"retrieved_context": [hit().to_dict()], "used_context": []})
    assert checked["gold_in_retrieved"] is True
    assert checked["gold_in_used_context"] is False
    assert checked["quality_label_y"] is None
    rows[0]["research_split"] = "evaluation"
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="Development only"):
        select_development(path)


@pytest.mark.parametrize(
    "updates",
    [
        {"threads": 0},
        {"passage_tokens": True},
        {"temperature": 0.7},
        {"context_tokens": 512, "max_output_tokens": 512},
        {"seed": -1},
    ],
)
def test_invalid_conditions_rejected(updates):
    with pytest.raises(ValueError):
        GenerationConfig(**updates)


def test_native_client_payload_has_no_implicit_generation_options(monkeypatch):
    client = LlamaClient(12345)
    calls = []
    monkeypatch.setattr(client, "request", lambda route, payload: calls.append((route, payload)))
    client.complete([1, 2, 3], GenerationConfig())
    route, payload = calls[0]
    assert route == "/completion"
    assert payload["prompt"] == [1, 2, 3]
    assert payload["cache_prompt"] is False
    assert payload["samplers"] == ["temperature"]
    assert payload["n_predict"] == 512


def test_approved_config_loads():
    value, config = load_config()
    assert value["retrieval"] == {"kind": "embedding", "top_k": 5}
    assert config.context_tokens == 4096


def test_hybrid_signals_are_recorded_but_not_in_generator_prompt():
    from rag_research.retrieval.hybrid import fuse_rankings

    documents = fuse_rankings([hit()], [hit()], {"p0": 0}, rrf_constant=60, top_k=5)
    result = build_context("Q", documents, FakeClient(), GenerationConfig(), PROMPT)
    assert result["used_context"][0]["passage_id"] == "p0"
    assert "bm25_rank" not in result["rendered_prompt"]
    assert "embedding_score" not in result["rendered_prompt"]
    assert "score" not in result["used_context"][0]


def test_runtime_transport_error_preserves_failure(monkeypatch):
    client = LlamaClient(12345)

    def fail(*args, **kwargs):
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(client.opener, "open", fail)
    with pytest.raises(GenerationError, match="Local runtime request failed"):
        client.complete([1], GenerationConfig())
    assert client.completion_attempts == 1


def test_citation_outside_used_context_is_recorded_not_silently_accepted():
    response = {"content": "Answer [p0] [invented]", "stop_type": "eos", "tokens": [1]}
    result = LocalGenerator(FakeClient(response), GenerationConfig(), PROMPT).generate_record(
        "Q", [hit()]
    )
    assert result["cited_passage_ids"] == ["p0"]
    assert result["unrecognized_citations"] == ["invented"]
    assert result["status"] == "ok"  # Execution success does not assert answer quality.


def test_utf8_cutoff_is_backed_off_to_valid_prefix():
    class ByteClient(FakeClient):
        def tokenize(self, text, **_):
            return list(text.encode("utf-8"))

        def detokenize(self, tokens):
            return bytes(tokens).decode("utf-8", errors="replace")

    config = GenerationConfig(passage_tokens=5)
    result = build_context("Q", [hit(text="🌸🌸🌸")], ByteClient(), config, PROMPT)
    assert result["used_context"][0]["text"] == "🌸"
    assert result["context_audit"][0]["used_tokens"] == 4


def test_model_bytes_are_verified_before_use(tmp_path, monkeypatch):
    path = tmp_path / artifacts.MODEL_FILE
    path.write_bytes(b"fixed")
    monkeypatch.setattr(artifacts, "MODEL_BYTES", 5)
    monkeypatch.setattr(artifacts, "MODEL_SHA256", hashlib.sha256(b"fixed").hexdigest())
    assert artifacts.verify_model(tmp_path) == path
    path.write_bytes(b"other")
    with pytest.raises(ValueError, match="hash mismatch"):
        artifacts.verify_model(tmp_path)


def test_runtime_changed_files_are_rejected(tmp_path):
    server = tmp_path / "llama-server.exe"
    server.write_bytes(b"fixed")
    manifest = {
        "tag": artifacts.RUNTIME_TAG,
        "archive_sha256": artifacts.RUNTIME_SHA256,
        "server": server.name,
        "files": {server.name: hashlib.sha256(b"fixed").hexdigest()},
    }
    (tmp_path / "runtime_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert artifacts.verify_runtime(tmp_path)[0] == server
    server.write_bytes(b"other")
    with pytest.raises(ValueError, match="hash mismatch"):
        artifacts.verify_runtime(tmp_path)


def test_server_startup_failure_closes_owned_process_and_log(tmp_path, monkeypatch):
    from pathlib import Path

    from rag_research.generation import local

    monkeypatch.setattr(local, "verify_model", lambda: tmp_path / "unused.gguf")
    monkeypatch.setattr(local, "verify_runtime", lambda: (Path(sys.executable), {}))
    server = LocalServer(GenerationConfig(startup_timeout_seconds=3), tmp_path / "server.log")
    with pytest.raises(GenerationError, match="server exited"):
        with server:
            pytest.fail("An invalid server must never become ready")
    assert server.process.poll() is not None
    assert server.log_file.closed
