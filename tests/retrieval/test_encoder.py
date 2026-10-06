"""Verify padded-token exclusion, normalization and pinned model cache integrity."""

from types import SimpleNamespace

import numpy as np
import pytest

from rag_research.retrieval.common import IndexValidationError, file_hash, write_json
from rag_research.retrieval.dense import (
    DIMENSION,
    MODEL_FILES,
    MODEL_ID,
    MODEL_REVISION,
    OnnxEncoder,
    prepare_model,
)


@pytest.fixture
def model_root(tmp_path):
    directory = tmp_path / MODEL_REVISION
    directory.mkdir()
    for name in MODEL_FILES:
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"offline test fixture, not executable model weights")
    write_json(
        directory / "model_manifest.json",
        {
            "model_id": MODEL_ID,
            "revision": MODEL_REVISION,
            "files": {name: file_hash(directory / name) for name in MODEL_FILES},
        },
    )
    return tmp_path


def test_pinned_cache_reuse_is_offline_and_checks_existing_hashes(model_root, monkeypatch):
    def forbid_network(*args, **kwargs):
        raise AssertionError("Prepared model should be reused without network")

    monkeypatch.setattr("rag_research.retrieval.dense.hf_hub_download", forbid_network)
    assert prepare_model(model_root) == model_root / MODEL_REVISION
    (model_root / MODEL_REVISION / MODEL_FILES[0]).write_bytes(b"corrupt")
    with pytest.raises(IndexValidationError, match="Model file hash"):
        prepare_model(model_root)


def test_missing_offline_model_rejected(tmp_path):
    with pytest.raises(IndexValidationError, match="not prepared"):
        prepare_model(tmp_path, offline=True)


def test_encoder_ignores_padding_and_returns_unit_vectors(model_root, monkeypatch):
    class FakeTokenizer:
        def enable_truncation(self, *, max_length):
            assert max_length == 256

        def enable_padding(self, *, pad_id, pad_token):
            assert pad_id == 0 and pad_token == "[PAD]"

        def encode_batch(self, texts):
            assert texts == ["first text", "second text"]
            return [
                SimpleNamespace(
                    ids=[1, 2, 0],
                    attention_mask=[1, 1, 0],
                    type_ids=[0, 0, 0],
                    overflowing=[object()],
                ),
                SimpleNamespace(
                    ids=[3, 0, 0], attention_mask=[1, 0, 0], type_ids=[0, 0, 0], overflowing=[]
                ),
            ]

    class FakeSession:
        def __init__(self, path, *, sess_options, providers):
            assert providers == ["CPUExecutionProvider"]
            assert sess_options.intra_op_num_threads == 6

        def get_inputs(self):
            return [
                SimpleNamespace(name=name)
                for name in ("input_ids", "attention_mask", "token_type_ids")
            ]

        def run(self, outputs, inputs):
            assert inputs["input_ids"].dtype == np.int64
            hidden = np.zeros((2, 3, DIMENSION), dtype=np.float32)
            hidden[0, 0, 0] = 1
            hidden[0, 1, 1] = 1
            hidden[0, 2, 2] = 100  # Padding must have no effect on sentence vectors.
            hidden[1, 0, 3] = 2
            hidden[1, 1:, 4] = 100
            return [hidden]

    monkeypatch.setattr(
        "rag_research.retrieval.dense.Tokenizer.from_file", lambda path: FakeTokenizer()
    )
    monkeypatch.setattr("rag_research.retrieval.dense.ort.InferenceSession", FakeSession)
    encoder = OnnxEncoder(model_root)
    vectors = encoder.encode(["first text", "second text"])
    assert vectors.shape == (2, 384)
    assert vectors.dtype == np.float32
    assert np.linalg.norm(vectors, axis=1) == pytest.approx([1, 1])
    assert vectors[0, :3] == pytest.approx([2**-0.5, 2**-0.5, 0])
    assert vectors[1, 3:5] == pytest.approx([1, 0])
    assert encoder.truncated_count == 1
    assert encoder.encode([]).shape == (0, 384)
