"""Role, padding, cache integrity and source boundaries without downloading weights."""

import hashlib
import importlib.metadata
import json
import subprocess
import sys
from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from rag_research.data.baobab_source import DATASET_ID, REVISION
from rag_research.retrieval import multilingual as module
from rag_research.retrieval.bm25 import BM25Retriever, build_bm25, tokenize
from rag_research.retrieval.common import (
    CorpusStore,
    IndexValidationError,
    file_hash,
    read_json,
    write_json,
)
from rag_research.retrieval.dense import DenseRetriever, build_dense


def test_model_cache_uses_pinned_expected_bytes_not_mutable_local_manifest(tmp_path, monkeypatch):
    spec = deepcopy(read_json(module.SPEC_PATH))
    directory = tmp_path / module.MODEL_REVISION
    directory.mkdir()
    for name in spec["files"]:
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = ("offline synthetic model fixture: " + name).encode()
        path.write_bytes(payload)
        spec["files"][name].update(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    spec_path = tmp_path / "spec.json"
    write_json(spec_path, spec)
    monkeypatch.setattr(module, "SPEC_PATH", spec_path)
    monkeypatch.setattr(module, "hf_hub_download", lambda *a, **kw: pytest.fail("Unexpected network"))
    assert module.prepare_model(tmp_path) == directory
    assert module.prepare_model(tmp_path, offline=True) == directory
    target = directory / "tokenizer.json"
    target.write_bytes(b"corrupt")
    manifest = read_json(directory / "model_manifest.json")
    manifest["files"]["tokenizer.json"].update(bytes=7, sha256=file_hash(target))
    write_json(directory / "model_manifest.json", manifest)
    with pytest.raises(IndexValidationError, match="artifact changed"):
        module.prepare_model(tmp_path, offline=True)


def test_model_cache_missing_and_changed_identity_fail_closed(tmp_path, monkeypatch):
    with pytest.raises(IndexValidationError, match="missing"):
        module.prepare_model(tmp_path, offline=True)
    spec = deepcopy(read_json(module.SPEC_PATH))
    spec["revision"] = "0" * 40
    path = tmp_path / "spec.json"
    write_json(path, spec)
    monkeypatch.setattr(module, "SPEC_PATH", path)
    with pytest.raises(IndexValidationError, match="specification"):
        module.prepare_model(tmp_path, offline=True)


def test_prefix_is_applied_by_role_and_bm25_uses_unprefixed_non_special_token_ids():
    tokenizer = object.__new__(module.E5Tokenizer)
    seen = []

    def encode(text):
        seen.append(text)
        return SimpleNamespace(ids=[1, 2, 3])

    def batch(texts, *, add_special_tokens):
        assert texts == ["猫", "犬"] and add_special_tokens is False
        return [SimpleNamespace(ids=[5, 5, 9]), SimpleNamespace(ids=[6])]

    tokenizer.raw = SimpleNamespace(encode=encode, encode_batch=batch)
    assert tokenizer.count("猫", kind="query") == 3
    tokenizer.encode("犬", kind="passage")
    assert seen == ["query: 猫", "passage: 犬"]
    assert tokenizer.tokenize(["猫", "犬"], return_ids=False) == [["5", "5", "9"], ["6"]]
    for text, kind in (("", "query"), ("猫", "unknown"), ({"question": "猫"}, "query")):
        with pytest.raises(ValueError):
            tokenizer.encode(text, kind=kind)


@pytest.fixture
def fake_encoder(tmp_path, monkeypatch):
    runs = []

    class Tokenizer:
        directory, model_manifest, pad_id = tmp_path, {"model_id": "synthetic"}, 7

        def __init__(self, root):
            pass

        def encode(self, text, *, kind):
            ids = [9 if kind == "query" else 4, 1, 2]
            if text == "short":
                ids.pop()
            if text == "overflow":
                ids = [1] * 513
            return SimpleNamespace(ids=ids, type_ids=[0] * len(ids))

    class Session:
        def __init__(self, *args, **kwargs):
            assert kwargs["providers"] == ["CPUExecutionProvider"]

        def get_inputs(self):
            return [SimpleNamespace(name=n) for n in ("input_ids", "attention_mask", "token_type_ids")]

        def run(self, _, inputs):
            runs.append(inputs)
            hidden = np.zeros((*inputs["input_ids"].shape, 384), dtype=np.float32)
            hidden[:, :, 0] = 1
            hidden[:, :, 1] = inputs["input_ids"]
            hidden[:, :, 2][inputs["attention_mask"] == 0] = 10000
            return [hidden]

    monkeypatch.setattr(module, "E5Tokenizer", Tokenizer)
    monkeypatch.setattr(module.ort, "InferenceSession", Session)
    return module.MultilingualE5Encoder(), runs


def test_role_aware_encoding_excludes_padding_and_normalizes_vectors(fake_encoder):
    encoder, runs = fake_encoder
    passage = encoder.encode_passages(["normal", "short"])
    query = encoder.encode_queries(["normal"])
    assert passage.shape == (2, 384) and passage.dtype == np.float32
    assert np.allclose(np.linalg.norm(passage, axis=1), 1)
    assert np.all(passage[:, 2] == 0)
    assert np.isclose(passage[0, 1] / passage[0, 0], 7 / 3)
    assert np.isclose(passage[1, 1] / passage[1, 0], 5 / 2)
    assert not np.allclose(query[0], passage[0])
    assert runs[0]["input_ids"][1, -1] == 7 and runs[0]["attention_mask"][1, -1] == 0
    assert encoder.encode_passages([]).shape == (0, 384)
    assert encoder.truncated_count == 0 and encoder.encoded_batches == 2
    with pytest.raises(TypeError):
        encoder.encode(["normal"])


def test_overflow_and_non_list_payload_fail_before_inference(fake_encoder):
    encoder, runs = fake_encoder
    with pytest.raises(IndexValidationError, match="nothing truncated"):
        encoder.encode_passages(["overflow"])
    with pytest.raises(ValueError):
        encoder.encode_queries({"question": "秘密", "gold": "秘密"})
    assert runs == [] and encoder.encoded_batches == 0


def japanese_corpus(path):
    rows = [{"passage_id": str(i), "source_dataset": DATASET_ID, "source_revision": REVISION,
             "language": "ja", "title": f"架空の資料{i}", "text": text,
             "text_sha256": hashlib.sha256(text.encode()).hexdigest()}
            for i, text in enumerate(("赤い猫です。", "青い犬です。"))]
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return rows


class RoleEncoder:
    truncated_count = 0

    def __init__(self):
        self.roles = []

    def retrieval_config(self, batch_size):
        return {"kind": "embedding", "algorithm": "synthetic-role-test", "batch_size": batch_size}

    def encode(self, texts):
        pytest.fail("A retrieval role was lost")

    def values(self, texts, role):
        self.roles.append(role)
        values = np.zeros((len(texts), 384), dtype=np.float32)
        for index, text in enumerate(texts):
            values[index, 0 if "猫" in text else 1] = 1
        return values

    def encode_passages(self, texts):
        return self.values(texts, "passage")

    def encode_queries(self, texts):
        return self.values(texts, "query")


class LexicalTokenizer:
    def tokenize(self, texts, *, return_ids=True):
        return tokenize([" ".join(str(ord(c)) for c in text) for text in texts], return_ids=return_ids)

    def bm25_config(self):
        return {"tokenization": "synthetic-character-test-v1"}


def test_new_corpus_requires_explicit_dataset_and_reuses_shared_search_without_gold(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    japanese_corpus(corpus)
    metadata_dir = tmp_path / "mapping"
    metadata_dir.mkdir()
    with pytest.raises(IndexValidationError, match="Invalid Corpus record"):
        CorpusStore.prepare(corpus, metadata_dir)
    encoder = RoleEncoder()
    dense = tmp_path / "dense"
    manifest = build_dense(corpus, dense, encoder, source_dataset=DATASET_ID, batch_size=2)
    assert manifest["corpus"]["source_dataset"] == DATASET_ID
    assert DenseRetriever(corpus, dense, encoder).search("猫について")[0].passage_id == "0"
    assert encoder.roles == ["passage", "query"]
    assert build_dense(corpus, dense, encoder, source_dataset=DATASET_ID, batch_size=2) == manifest
    assert encoder.roles == ["passage", "query"]
    with pytest.raises(IndexValidationError, match="source dataset"):
        build_dense(corpus, dense, encoder, batch_size=2)
    lexical = tmp_path / "lexical"
    tokens = LexicalTokenizer()
    build_bm25(corpus, lexical, tokenizer=tokens, source_dataset=DATASET_ID)
    retriever = BM25Retriever(corpus, lexical, tokenizer=tokens)
    assert retriever.search("猫")[0].passage_id == "0"
    with pytest.raises(ValueError, match="QA/Gold"):
        retriever.search({"question": "猫", "reference_answers": ["秘密"]})
    with pytest.raises(IndexValidationError, match="different settings"):
        BM25Retriever(corpus, lexical)
    with pytest.raises(IndexValidationError, match="source dataset"):
        build_bm25(corpus, lexical, tokenizer=tokens)


def test_mixed_source_corpus_is_rejected_even_with_an_explicit_dataset(tmp_path):
    path = tmp_path / "mixed.jsonl"
    rows = japanese_corpus(path)
    rows[1]["source_dataset"] = "CLAPNQ"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    mapping = tmp_path / "mapping"
    mapping.mkdir()
    with pytest.raises(IndexValidationError, match="Invalid Corpus record"):
        CorpusStore.prepare(path, mapping, source_dataset=DATASET_ID)


@pytest.fixture
def fake_cuda(fake_encoder, monkeypatch):
    cpu, runs = fake_encoder
    state = {"providers": ["CUDAExecutionProvider", "CPUExecutionProvider"],
             "options": {"device_id": "0", "use_tf32": "0"}, "fallback_disabled": False}
    original_version = importlib.metadata.version

    def gpu_version(name):
        if name == "onnxruntime":
            raise importlib.metadata.PackageNotFoundError(name)
        if name == "onnxruntime-gpu":
            return "1.30.0"
        return original_version(name)

    class Session(type(cpu.session)):
        def __init__(self, *args, **kwargs):
            state["requested"] = kwargs["providers"]
            state["session_options"] = kwargs["sess_options"]

        def get_providers(self):
            return state["providers"]

        def get_provider_options(self):
            return {"CUDAExecutionProvider": state["options"]}

        def disable_fallback(self):
            state["fallback_disabled"] = True

    monkeypatch.setattr(importlib.metadata, "version", gpu_version)
    monkeypatch.setattr(module.ort, "get_available_providers", lambda: ["CUDAExecutionProvider"])
    monkeypatch.setattr(module.ort, "preload_dlls", lambda **kw: state.update(preload=kw), raising=False)
    monkeypatch.setattr(module.ort, "InferenceSession", Session)
    return state, runs


def test_cuda_options_distribution_and_fallback_are_bound_to_index_identity(fake_cuda, tmp_path):
    state, runs = fake_cuda
    encoder = module.MultilingualE5Encoder(provider="cuda", profile_prefix=tmp_path / "profile")
    assert state["requested"] == [("CUDAExecutionProvider", {"device_id": "0", "use_tf32": "0"})]
    assert state["preload"] == {"directory": ""} and state["fallback_disabled"]
    assert state["session_options"].enable_profiling
    assert encoder.encode_passages(["normal", "short"]).shape == (2, 384)
    config = encoder.retrieval_config(2)
    assert config["provider"] == "CUDAExecutionProvider"
    assert config["packages"]["onnxruntime-gpu"] == "1.30.0"
    assert "onnxruntime" not in config["packages"]
    assert config["automatic_provider_fallback"] is False
    assert config["provider_options"]["use_tf32"] == "0"
    assert len(runs) == 1
    corpus = tmp_path / "corpus.jsonl"
    japanese_corpus(corpus)
    output = tmp_path / "index"
    build_dense(corpus, output, encoder, source_dataset=DATASET_ID, batch_size=2)
    count = len(runs)
    build_dense(corpus, output, encoder, source_dataset=DATASET_ID, batch_size=2)
    assert len(runs) == count
    encoder.provider_options = {"device_id": "1", "use_tf32": "0"}
    with pytest.raises(IndexValidationError, match="differs"):
        DenseRetriever(corpus, output, encoder)
    with pytest.raises(IndexValidationError, match="different settings"):
        build_dense(corpus, output, encoder, source_dataset=DATASET_ID, batch_size=2)


def test_cuda_cpu_only_fallback_fails_before_encoding(fake_cuda):
    state, runs = fake_cuda
    state["providers"] = ["CPUExecutionProvider"]
    with pytest.raises(IndexValidationError, match="fell back to CPU only"):
        module.MultilingualE5Encoder(provider="cuda")
    assert not runs and not state["fallback_disabled"]


@pytest.mark.parametrize("options", [{"device_id": "0", "use_tf32": "1"},
                                     {"device_id": "1", "use_tf32": "0"}, {}])
def test_cuda_changed_actual_options_are_rejected(fake_cuda, options):
    state, runs = fake_cuda
    state["options"] = options
    with pytest.raises(IndexValidationError, match="device/TF32"):
        module.MultilingualE5Encoder(provider="cuda")
    assert not runs


def test_cuda_missing_provider_is_rejected_without_loading_model(fake_cuda, monkeypatch):
    monkeypatch.setattr(module.ort, "get_available_providers", lambda: ["CPUExecutionProvider"])
    monkeypatch.setattr(module, "E5Tokenizer", lambda *a: pytest.fail("Do not load model without CUDA"))
    with pytest.raises(IndexValidationError, match="isolated"):
        module.MultilingualE5Encoder(provider="cuda")


@pytest.mark.parametrize("installed", [set(), {"onnxruntime", "onnxruntime-gpu"}])
def test_missing_or_ambiguous_runtime_distributions_fail_closed(monkeypatch, installed):
    def version(name):
        if name not in installed:
            raise importlib.metadata.PackageNotFoundError(name)
        return "1.30.0"

    monkeypatch.setattr(importlib.metadata, "version", version)
    with pytest.raises(IndexValidationError, match="exactly one"):
        module.MultilingualE5Encoder()


@pytest.mark.parametrize("kwargs", [{"provider": "auto"}, {"device_id": -1},
                                    {"device_id": True}, {"device_id": 1}, {"threads": False}])
def test_invalid_runtime_request_is_rejected_before_model_load(monkeypatch, kwargs):
    monkeypatch.setattr(module, "E5Tokenizer", lambda *a: pytest.fail("Unexpected model load"))
    with pytest.raises(ValueError):
        module.MultilingualE5Encoder(**kwargs)


@pytest.mark.parametrize("args", [["--encoder", "minilm", "--kind", "embedding"],
                                  ["--encoder", "multilingual-e5", "--kind", "bm25",
                                   "--output-dir", "unused"]])
def test_cli_rejects_cuda_for_unsupported_paths(args):
    result = subprocess.run([sys.executable, "scripts/build_retrieval_index.py", *args,
                             "--provider", "cuda"], capture_output=True, text=True)
    assert result.returncode == 2
    assert "apply only to multilingual E5 embedding" in result.stderr
