"""Pinned official multilingual E5 candidate; explicit query/passage roles, no truncation."""

from pathlib import Path

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

from rag_research.retrieval.common import (
    IndexValidationError,
    file_hash,
    package_versions,
    read_json,
    write_json,
)

ROOT = Path(__file__).resolve().parents[3]
MODEL_ID = "intfloat/multilingual-e5-small"
MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
MODEL_ROOT = ROOT / "data/models/multilingual-e5-small"
SPEC_PATH = ROOT / "configs/phase11_multilingual_embedding_v1.json"
DIMENSION, MAX_LENGTH = 384, 512
MODEL_FILES = {"onnx/model.onnx", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
               "config.json", "sentence_bert_config.json", "1_Pooling/config.json", "modules.json", "README.md"}


def prepare_model(model_root=MODEL_ROOT, *, offline=False):
    spec = read_json(SPEC_PATH)
    if (spec["model_id"] != MODEL_ID or spec["revision"] != MODEL_REVISION or
            set(spec["files"]) != MODEL_FILES or spec["dimension"] != DIMENSION or
            spec["max_length"] != MAX_LENGTH or spec["pooling"] != "attention_mask_mean" or
            spec["normalization"] != "l2" or spec["quantization"] != "none_fp32_official_onnx" or
            spec["query_prefix"] != "query: " or spec["passage_prefix"] != "passage: " or
            spec["overflow"] != "error_without_truncating"):
        raise IndexValidationError("Unknown multilingual embedding specification")
    directory = Path(model_root) / MODEL_REVISION
    for name, expected in spec["files"].items():
        path = directory / name
        if not path.exists():
            if offline:
                raise IndexValidationError(f"Pinned multilingual model artifact missing: {name}")
            hf_hub_download(MODEL_ID, name, revision=MODEL_REVISION, local_dir=directory, token=False)
        if path.stat().st_size != expected["bytes"] or file_hash(path) != expected["sha256"]:
            raise IndexValidationError(f"Pinned multilingual model artifact changed: {name}")
    manifest = {"schema_version": 1, "purpose": "phase11-multilingual-embedding-candidate",
                "model_id": MODEL_ID, "revision": MODEL_REVISION, "files": spec["files"],
                "quantization": "none_fp32_official_onnx", "remote_model_code_executed": False,
                "final_model_adopted": False}
    path = directory / "model_manifest.json"
    if path.exists():
        if read_json(path) != manifest:
            raise IndexValidationError("Pinned multilingual model manifest changed")
    elif offline:
        raise IndexValidationError("Pinned multilingual model manifest missing")
    else:
        write_json(path, manifest)
    return directory


class E5Tokenizer:
    """Untruncated tokenizer shared by semantic encoding, lexical search and chunking."""

    def __init__(self, model_root=MODEL_ROOT):
        self.directory = prepare_model(model_root, offline=True)
        self.model_manifest = read_json(self.directory / "model_manifest.json")
        self.raw = Tokenizer.from_file(str(self.directory / "tokenizer.json"))
        self.raw.no_truncation()
        self.raw.no_padding()
        self.pad_id = self.raw.token_to_id(read_json(self.directory / "tokenizer_config.json")["pad_token"])
        if self.pad_id is None:
            raise IndexValidationError("Multilingual tokenizer has no declared padding token")

    def encode(self, text, *, kind):
        if kind not in {"query", "passage"} or not isinstance(text, str) or not text.strip():
            raise ValueError("Explicit query/passage role and nonblank text are required")
        return self.raw.encode(f"{kind}: " + text)

    def count(self, text, *, kind="passage"):
        return len(self.encode(text, kind=kind).ids)

    def tokenize(self, texts, *, return_ids=True):
        # BM25 gets the same subword vocabulary for both languages, without E5 prefixes.
        from rag_research.retrieval.bm25 import tokenize

        encoded = self.raw.encode_batch(texts, add_special_tokens=False)
        strings = [" ".join(str(value) for value in item.ids) for item in encoded]
        return tokenize(strings, return_ids=return_ids)

    def bm25_config(self):
        return {"tokenization": "e5-subword-token-ids-without-prefix-or-specials-v1",
                "tokenizer_model_id": MODEL_ID, "tokenizer_revision": MODEL_REVISION,
                "tokenizer_sha256": self.model_manifest["files"]["tokenizer.json"]["sha256"],
                "truncation": None, "word_stemmer": None}


class MultilingualE5Encoder:
    def __init__(self, model_root=MODEL_ROOT, *, threads=6):
        if type(threads) is not int or threads < 1:
            raise ValueError("threads must be a positive integer")
        self.tokenizer = E5Tokenizer(model_root)
        self.model_manifest = self.tokenizer.model_manifest
        self.threads, self.truncated_count, self.encoded_batches = threads, 0, 0
        options = ort.SessionOptions()
        options.intra_op_num_threads, options.inter_op_num_threads = threads, 1
        self.session = ort.InferenceSession(str(self.tokenizer.directory / "onnx/model.onnx"),
                                           sess_options=options, providers=["CPUExecutionProvider"])

    def encode(self, texts, *, kind):
        if not isinstance(texts, list) or kind not in {"query", "passage"}:
            raise ValueError("Text list and explicit query/passage role required")
        if not texts:
            return np.empty((0, DIMENSION), dtype=np.float32)
        encodings = [self.tokenizer.encode(text, kind=kind) for text in texts]
        if any(len(item.ids) > MAX_LENGTH for item in encodings):
            raise IndexValidationError("Multilingual input exceeds 512 tokens; nothing truncated")
        width = max(len(item.ids) for item in encodings)
        ids = np.full((len(texts), width), self.tokenizer.pad_id, dtype=np.int64)
        mask, types = np.zeros_like(ids), np.zeros_like(ids)
        for index, item in enumerate(encodings):
            ids[index, :len(item.ids)] = item.ids
            mask[index, :len(item.ids)] = 1
            types[index, :len(item.ids)] = item.type_ids
        available = {"input_ids": ids, "attention_mask": mask, "token_type_ids": types}
        inputs = {node.name: available[node.name] for node in self.session.get_inputs()}
        hidden = self.session.run(None, inputs)[0]
        self.encoded_batches += 1
        if hidden.shape != (*ids.shape, DIMENSION) or not np.isfinite(hidden).all():
            raise IndexValidationError("Multilingual runtime returned invalid hidden states")
        weights = mask.astype(np.float32)
        pooled = np.einsum("bsh,bs->bh", hidden.astype(np.float32), weights) / weights.sum(axis=1)[:, None]
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        if not np.isfinite(norms).all() or (norms <= 1e-12).any():
            raise IndexValidationError("Multilingual runtime returned invalid vector norms")
        return (pooled / norms).astype(np.float32)

    def encode_queries(self, texts):
        return self.encode(texts, kind="query")

    def encode_passages(self, texts):
        return self.encode(texts, kind="passage")

    def retrieval_config(self, batch_size):
        return {"kind": "embedding", "algorithm": "multilingual-e5-onnx-cosine-no-truncation-v1",
                "model": self.model_manifest, "quantization": "none_fp32_official_onnx",
                "input": "text", "query_prefix": "query: ", "passage_prefix": "passage: ",
                "dimension": DIMENSION, "max_length": MAX_LENGTH, "pooling": "attention_mask_mean",
                "normalization": "l2", "overflow": "error_without_truncating", "dtype": "float32",
                "metric": "cosine", "search": "numpy-exact-block-dot", "tie_break": "corpus_row_ascending",
                "batch_size": batch_size, "threads": self.threads, "provider": "CPUExecutionProvider",
                "packages": package_versions(["numpy", "onnxruntime", "tokenizers"])}
