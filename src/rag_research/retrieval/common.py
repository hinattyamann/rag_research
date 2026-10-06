"""Validated Corpus access and versioned Index artifacts."""

import hashlib
import importlib.metadata
import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import psutil

CORPUS_PATH = Path("data/processed/clapnq/c508d78-base-v1/passages.jsonl")
INDEX_ROOT = Path("data/indexes/clapnq/c508d78-retrieval-v1")
DEVELOPMENT_PATH = Path("data/processed/clapnq/c508d78-split-v1/development.jsonl")
MODEL_ROOT = Path("data/models/all-MiniLM-L6-v2")


class IndexValidationError(ValueError):
    """An Index is incompatible, incomplete or corrupt."""


def file_hash(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: object) -> None:
    """Atomically replace working-state/report files, never finalized Index files."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as target:
        target.write(json_bytes(value))
        target.flush()
        os.fsync(target.fileno())
    temporary.replace(path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def package_versions(names: list[str]) -> dict[str, str]:
    return {name: importlib.metadata.version(name) for name in names}


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    passage_id: str
    title: str
    text: str
    source_revision: str
    score: float
    rank: int

    def to_dict(self) -> dict:
        return asdict(self)


def validate_query(question: str, top_k: int) -> None:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a nonblank string; QA/Gold metadata is not accepted")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise ValueError("top_k must be a positive integer")


def ranked_rows(scores: np.ndarray, top_k: int) -> np.ndarray:
    """Score descending, ties by canonical Corpus row; include boundary ties."""
    if scores.ndim != 1 or not np.isfinite(scores).all():
        raise IndexValidationError("Scores must be a finite vector")
    count = min(top_k, len(scores))
    if count == 0:
        return np.array([], dtype=np.int64)
    threshold = np.partition(scores, len(scores) - count)[len(scores) - count]
    candidates = np.flatnonzero(scores >= threshold)
    return candidates[np.lexsort((candidates, -scores[candidates]))][:count]


class CorpusStore:
    """Read only retrieved rows using byte offsets; keep full text on disk."""

    def __init__(self, corpus_path: Path, index_dir: Path, metadata: dict):
        self.path = corpus_path
        self.ids = json.loads((index_dir / "passage_ids.json").read_text(encoding="utf-8"))
        self.offsets = np.load(index_dir / "offsets.npy", mmap_mode="r", allow_pickle=False)
        self.metadata = metadata
        if len(self.ids) != metadata["record_count"] or self.offsets.shape != (len(self.ids),):
            raise IndexValidationError("Corpus row mapping length mismatch")
        if len(set(self.ids)) != len(self.ids):
            raise IndexValidationError("Duplicate Corpus Passage ID")

    @staticmethod
    def prepare(corpus_path: Path, index_dir: Path) -> dict:
        ids, offsets, revisions = [], [], set()
        with corpus_path.open("rb") as source:
            while True:
                offset = source.tell()
                line = source.readline()
                if not line:
                    break
                row = json.loads(line)
                if (
                    not isinstance(row.get("passage_id"), str)
                    or not row["passage_id"]
                    or not isinstance(row.get("text"), str)
                    or not row["text"].strip()
                    or not isinstance(row.get("title"), str)
                    or not row["title"].strip()
                    or row.get("source_dataset") != "CLAPNQ"
                    or not isinstance(row.get("source_revision"), str)
                    or row.get("text_sha256")
                    != hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
                ):
                    raise IndexValidationError(f"Invalid Corpus record at byte {offset}")
                ids.append(row["passage_id"])
                offsets.append(offset)
                revisions.add(row["source_revision"])
        if not ids or len(set(ids)) != len(ids) or len(revisions) != 1:
            raise IndexValidationError("Corpus must be nonempty, unique and from one revision")
        write_json(index_dir / "passage_ids.json", ids)
        np.save(index_dir / "offsets.npy", np.asarray(offsets, dtype=np.int64), allow_pickle=False)
        return {
            "sha256": file_hash(corpus_path),
            "bytes": corpus_path.stat().st_size,
            "record_count": len(ids),
            "source_revision": revisions.pop(),
            "ordered_passage_ids_sha256": file_hash(index_dir / "passage_ids.json"),
        }

    def iter_texts(self):
        with self.path.open("rb") as source:
            for line in source:
                yield json.loads(line)["text"]

    def hits(self, rows: np.ndarray, scores: np.ndarray) -> list[RetrievalHit]:
        result = []
        with self.path.open("rb") as source:
            for rank, index in enumerate(rows, start=1):
                source.seek(int(self.offsets[index]))
                row = json.loads(source.readline())
                if row["passage_id"] != self.ids[index]:
                    raise IndexValidationError("Passage ID/offset mapping mismatch")
                result.append(
                    RetrievalHit(
                        row["passage_id"],
                        row["title"],
                        row["text"],
                        row["source_revision"],
                        float(scores[index]),
                        rank,
                    )
                )
        return result


def verify_index(index_dir: Path, corpus_path: Path, expected_config: dict | None = None) -> dict:
    manifest = read_json(index_dir / "manifest.json")
    if manifest.get("schema_version") != 1:
        raise IndexValidationError("Unsupported Index manifest schema")
    if expected_config is not None and manifest["config"] != expected_config:
        raise IndexValidationError("Existing Index has different settings; use a new output path")
    if file_hash(corpus_path) != manifest["corpus"]["sha256"]:
        raise IndexValidationError("Corpus hash mismatch")
    for relative, info in manifest["files"].items():
        path = index_dir / relative
        if path.stat().st_size != info["bytes"] or file_hash(path) != info["sha256"]:
            raise IndexValidationError(f"Index artifact hash mismatch: {relative}")
    return manifest


def finalize_index(stage: Path, output_dir: Path, config: dict, corpus: dict) -> dict:
    files = {
        path.relative_to(stage).as_posix(): {
            "sha256": file_hash(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(stage.rglob("*"))
        if path.is_file() and path.name not in {"checkpoint.json", "build_measurements.json"}
    }
    manifest = {"schema_version": 1, "config": config, "corpus": corpus, "files": files}
    write_json(stage / "manifest.json", manifest)
    if output_dir.exists():
        raise IndexValidationError("Output appeared during build; refusing to overwrite")
    stage.rename(output_dir)
    return manifest


class ResourceMonitor:
    """Sample process RSS, with a documented 100 ms sampling interval."""

    def __enter__(self):
        self.start = time.perf_counter()
        self.peak = psutil.Process().memory_info().rss
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()
        return self

    def _sample(self):
        process = psutil.Process()
        while not self._stop.wait(0.1):
            self.peak = max(self.peak, process.memory_info().rss)

    def __exit__(self, *_):
        self.peak = max(self.peak, psutil.Process().memory_info().rss)
        self._stop.set()
        self._thread.join()
        self.seconds = time.perf_counter() - self.start

    def report(self) -> dict:
        return {
            "wall_seconds": self.seconds,
            "sampled_peak_rss_bytes": self.peak,
            "rss_sample_interval_seconds": 0.1,
        }
