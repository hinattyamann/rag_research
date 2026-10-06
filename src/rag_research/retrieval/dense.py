"""Pinned CPU ONNX embeddings and exact cosine search with memory-mapped vectors."""

import hashlib
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

from rag_research.retrieval.common import (
    MODEL_ROOT,
    CorpusStore,
    IndexValidationError,
    ResourceMonitor,
    file_hash,
    finalize_index,
    package_versions,
    ranked_rows,
    read_json,
    validate_query,
    verify_index,
    write_json,
)

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_FILES = (
    "onnx/model_quint8_avx2.onnx",
    "tokenizer.json",
    "config.json",
    "sentence_bert_config.json",
    "1_Pooling/config.json",
    "modules.json",
)
DIMENSION = 384
MAX_LENGTH = 256


def prepare_model(model_root: Path = MODEL_ROOT, *, offline: bool = False) -> Path:
    """Download only fixed official files into the workspace; no remote model code."""
    destination = model_root / MODEL_REVISION
    if not offline and (destination / "model_manifest.json").exists():
        return prepare_model(model_root, offline=True)
    if not offline:
        destination.mkdir(parents=True, exist_ok=True)
        for name in MODEL_FILES:
            print(f"Model file: {name}", flush=True)
            hf_hub_download(
                MODEL_ID, name, revision=MODEL_REVISION, local_dir=destination, token=False
            )
        write_json(
            destination / "model_manifest.json",
            {
                "model_id": MODEL_ID,
                "revision": MODEL_REVISION,
                "files": {name: file_hash(destination / name) for name in MODEL_FILES},
            },
        )
    manifest_path = destination / "model_manifest.json"
    if not manifest_path.exists():
        raise IndexValidationError("Pinned model not prepared; run download_embedding_model.py")
    manifest = read_json(manifest_path)
    if manifest.get("model_id") != MODEL_ID or manifest.get("revision") != MODEL_REVISION:
        raise IndexValidationError("Model identity mismatch")
    if set(manifest.get("files", {})) != set(MODEL_FILES):
        raise IndexValidationError("Model file set mismatch")
    for name in MODEL_FILES:
        if file_hash(destination / name) != manifest["files"][name]:
            raise IndexValidationError(f"Model file hash mismatch: {name}")
    return destination


class OnnxEncoder:
    def __init__(self, model_root: Path = MODEL_ROOT, *, threads: int = 6):
        if threads < 1:
            raise ValueError("threads must be positive")
        directory = prepare_model(model_root, offline=True)
        self.model_manifest = read_json(directory / "model_manifest.json")
        self.threads = threads
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=MAX_LENGTH)
        self.tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(directory / MODEL_FILES[0]),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        self.truncated_count = 0

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, DIMENSION), dtype=np.float32)
        encodings = self.tokenizer.encode_batch(texts)
        self.truncated_count += sum(bool(encoding.overflowing) for encoding in encodings)
        inputs = {
            "input_ids": np.asarray([item.ids for item in encodings], dtype=np.int64),
            "attention_mask": np.asarray(
                [item.attention_mask for item in encodings], dtype=np.int64
            ),
            "token_type_ids": np.asarray([item.type_ids for item in encodings], dtype=np.int64),
        }
        hidden = self.session.run(
            None, {node.name: inputs[node.name] for node in self.session.get_inputs()}
        )[0]
        mask = inputs["attention_mask"].astype(np.float32)
        pooled = np.einsum("bsh,bs->bh", hidden, mask) / mask.sum(axis=1)[:, None]
        vectors = pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
        return vectors.astype(np.float32)


def dense_config(encoder, batch_size: int) -> dict:
    return {
        "kind": "embedding",
        "algorithm": "minilm-onnx-cosine-v1",
        "model": encoder.model_manifest,
        "quantization": "official-quint8-avx2",
        "input": "text",
        "dimension": DIMENSION,
        "max_length": MAX_LENGTH,
        "pooling": "attention_mask_mean",
        "normalization": "l2",
        "dtype": "float32",
        "metric": "cosine",
        "search": "numpy-exact-block-dot",
        "tie_break": "corpus_row_ascending",
        "batch_size": batch_size,
        "threads": encoder.threads,
        "provider": "CPUExecutionProvider",
        "packages": package_versions(["numpy", "onnxruntime", "tokenizers"]),
    }


def build_dense(corpus_path: Path, output_dir: Path, encoder, *, batch_size: int = 1) -> dict:
    """Resume only when Corpus, model bytes and execution config match exactly."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    config = dense_config(encoder, batch_size)
    if output_dir.exists():
        return verify_index(output_dir, corpus_path, config)
    stage = output_dir.with_name(output_dir.name + ".building")
    if (stage / "manifest.json").exists():
        manifest = verify_index(stage, corpus_path, config)
        stage.rename(output_dir)
        return manifest
    with ResourceMonitor() as monitor:
        if stage.exists():
            checkpoint_path = stage / "checkpoint.json"
            if not checkpoint_path.exists():
                raise IndexValidationError("Incomplete initialization; use another output path")
            checkpoint = read_json(checkpoint_path)
            if checkpoint["config"] != config or checkpoint["corpus"]["sha256"] != file_hash(
                corpus_path
            ):
                raise IndexValidationError("Resume conditions changed; use a new output path")
            metadata = checkpoint["corpus"]
            if any(
                file_hash(stage / name) != digest
                for name, digest in checkpoint["mapping_hashes"].items()
            ):
                raise IndexValidationError("Resume Corpus mapping was modified")
            vectors = np.load(stage / "vectors.npy", mmap_mode="r+", allow_pickle=False)
            next_row = checkpoint["next_row"]
            if (
                hashlib.sha256(memoryview(vectors[:next_row])).hexdigest()
                != checkpoint["committed_vectors_sha256"]
            ):
                raise IndexValidationError("Committed resume vectors were modified")
            encoder.truncated_count = checkpoint["truncated_passages"]
        else:
            stage.mkdir(parents=True)
            metadata = CorpusStore.prepare(corpus_path, stage)
            vectors = np.lib.format.open_memmap(
                stage / "vectors.npy",
                mode="w+",
                dtype=np.float32,
                shape=(metadata["record_count"], DIMENSION),
            )
            next_row = 0
            checkpoint = {
                "config": config,
                "corpus": metadata,
                "mapping_hashes": {
                    name: file_hash(stage / name) for name in ("passage_ids.json", "offsets.npy")
                },
                "next_row": 0,
                "truncated_passages": 0,
                "committed_vectors_sha256": hashlib.sha256(b"").hexdigest(),
            }
            write_json(stage / "checkpoint.json", checkpoint)
        if (
            vectors.shape != (metadata["record_count"], DIMENSION)
            or vectors.dtype != np.float32
            or not 0 <= next_row <= len(vectors)
        ):
            raise IndexValidationError("Invalid resumable vector shape or cursor")
        store = CorpusStore(corpus_path, stage, metadata)
        started = time.perf_counter()
        start_row = next_row
        last_message = started
        batch = []
        for index, text in enumerate(store.iter_texts()):
            if index < next_row:
                continue
            batch.append(text)
            if len(batch) < batch_size and index + 1 < len(vectors):
                continue
            encoded = encoder.encode(batch)
            if encoded.shape != (len(batch), DIMENSION) or not np.isfinite(encoded).all():
                raise IndexValidationError("Encoder returned invalid vectors")
            vectors[index + 1 - len(batch) : index + 1] = encoded
            batch.clear()
            now = time.perf_counter()
            if now - last_message >= 20 or index + 1 == len(vectors):
                vectors.flush()
                checkpoint.update(
                    next_row=index + 1,
                    truncated_passages=encoder.truncated_count,
                    committed_vectors_sha256=hashlib.sha256(
                        memoryview(vectors[: index + 1])
                    ).hexdigest(),
                )
                write_json(stage / "checkpoint.json", checkpoint)
                rate = (index + 1 - start_row) / max(now - started, 1e-9)
                print(f"Embedding: {index + 1}/{len(vectors)} ({rate:.1f} passages/s)", flush=True)
                last_message = now
        vectors.flush()
        for start in range(0, len(vectors), 8192):
            block = vectors[start : start + 8192]
            if not np.isfinite(block).all() or not np.allclose(
                np.linalg.norm(block, axis=1), 1.0, atol=1e-5
            ):
                raise IndexValidationError("Stored embeddings are not finite L2 unit vectors")
        del block
        del vectors  # Windows requires closing the mmap before renaming the directory.
        del store
    write_json(
        stage / "build_measurements.json",
        {
            **monitor.report(),
            "resumed_from_row": start_row,
            "truncated_passages": encoder.truncated_count,
        },
    )
    (stage / "checkpoint.json").unlink()
    return finalize_index(stage, output_dir, config, metadata)


class DenseRetriever:
    def __init__(self, corpus_path: Path, index_dir: Path, encoder, *, block_size: int = 8192):
        self.manifest = verify_index(index_dir, corpus_path)
        config = self.manifest["config"]
        if config != dense_config(encoder, config["batch_size"]):
            raise IndexValidationError("Query encoder differs from the Index encoder")
        if block_size < 1:
            raise ValueError("block_size must be positive")
        self.encoder = encoder
        self.block_size = block_size
        self.store = CorpusStore(corpus_path, index_dir, self.manifest["corpus"])
        self.vectors = np.load(index_dir / "vectors.npy", mmap_mode="r", allow_pickle=False)
        if self.vectors.shape != (len(self.store.ids), DIMENSION):
            raise IndexValidationError("Index vector shape mismatch")

    def search(self, question: str, *, top_k: int = 5):
        validate_query(question, top_k)
        query = self.encoder.encode([question])[0]
        scores = np.empty(len(self.vectors), dtype=np.float32)
        for start in range(0, len(scores), self.block_size):
            end = min(start + self.block_size, len(scores))
            scores[start:end] = self.vectors[start:end] @ query
        return self.store.hits(ranked_rows(scores, top_k), scores)
