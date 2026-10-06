"""Search contracts, persisted mapping, frozen artifacts and resumable encoding."""

import hashlib
import itertools
import json

import numpy as np
import pytest

from rag_research.retrieval.bm25 import BM25Retriever, build_bm25
from rag_research.retrieval.common import (
    CorpusStore,
    IndexValidationError,
    file_hash,
    ranked_rows,
    read_json,
    write_json,
)
from rag_research.retrieval.dense import DIMENSION, DenseRetriever, build_dense
from rag_research.retrieval.validation import (
    build_retrieval_manifest,
    development_smoke,
    validate_gold_mapping,
)


@pytest.fixture
def corpus(tmp_path):
    path = tmp_path / "corpus.jsonl"
    texts = ["cat cat sleeps on a sofa", "dog runs through a park", "cat naps", "123 café"]
    rows = [
        {
            "passage_id": f"p{i}",
            "text": text,
            "title": f"Title {i}",
            "source_dataset": "CLAPNQ",
            "source_revision": "a" * 40,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
        for i, text in enumerate(texts)
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


class FakeEncoder:
    """Distinct orthogonal vectors, to test exact search without model downloads."""

    threads = 6
    model_manifest = {"model_id": "test-only", "revision": "test-v1", "files": {}}
    truncated_count = 0

    def __init__(self):
        self.calls = []

    def encode(self, texts):
        self.calls.extend(texts)
        vectors = np.zeros((len(texts), DIMENSION), dtype=np.float32)
        for i, text in enumerate(texts):
            vectors[i, 1 if "dog" in text else 0] = 1
        return vectors


def qa_record(identifier="q0", question="cat", gold=None, split="development"):
    return {
        "record_id": identifier,
        "question": question,
        "gold_passage_ids": gold or ["p0"],
        "is_answerable": True,
        "research_split": split,
        "reference_answers": ["secret reference must not enter retrieval"],
        "selected_sentences_by_reference": [["secret evidence"]],
    }


def test_bm25_text_search_persistence_and_query_contract(corpus, tmp_path):
    directory = tmp_path / "bm25"
    manifest = build_bm25(corpus, directory)
    retriever = BM25Retriever(corpus, directory)
    hits = retriever.search("DOG!", top_k=10)
    assert [hit.passage_id for hit in hits] == ["p1"]
    assert hits[0].text == "dog runs through a park"
    assert hits[0].score > 0 and hits[0].rank == 1
    assert retriever.search("unknownword") == []
    assert retriever.search("...") == []
    assert retriever.search("123")[0].passage_id == "p3"
    assert retriever.search("CAFÉ")[0].passage_id == "p3"
    assert retriever.search("a")[0].passage_id in {"p0", "p1"}
    assert manifest["corpus"]["record_count"] == 4
    assert build_bm25(corpus, directory) == manifest
    with pytest.raises(ValueError, match="QA/Gold"):
        retriever.search(qa_record())


def test_bm25_rebuild_matches_bytes(corpus, tmp_path):
    first = build_bm25(corpus, tmp_path / "one")
    second = build_bm25(corpus, tmp_path / "two")
    assert first == second


@pytest.mark.parametrize("top_k", [0, -1, 1.5, True])
def test_bad_top_k_rejected(corpus, tmp_path, top_k):
    directory = tmp_path / "index"
    build_bm25(corpus, directory)
    with pytest.raises(ValueError, match="top_k"):
        BM25Retriever(corpus, directory).search("cat", top_k=top_k)


def test_stable_ties_include_partition_boundary():
    scores = np.array([1, 2, 2, 2, 0], dtype=np.float32)
    assert ranked_rows(scores, 2).tolist() == [1, 2]
    assert ranked_rows(scores, 99).tolist() == [1, 2, 3, 0, 4]
    with pytest.raises(IndexValidationError):
        ranked_rows(np.array([np.nan]), 1)


def test_modified_corpus_rejected_without_overwrite(corpus, tmp_path):
    directory = tmp_path / "index"
    build_bm25(corpus, directory)
    before = file_hash(directory / "manifest.json")
    corpus.write_bytes(corpus.read_bytes() + b"\n")
    with pytest.raises(IndexValidationError, match="Corpus hash"):
        build_bm25(corpus, directory)
    assert file_hash(directory / "manifest.json") == before


def test_corrupt_index_rejected(corpus, tmp_path):
    directory = tmp_path / "index"
    build_bm25(corpus, directory)
    (directory / "passage_ids.json").write_text('["bad"]', encoding="utf-8")
    with pytest.raises(IndexValidationError, match="hash mismatch"):
        BM25Retriever(corpus, directory)


def test_duplicate_or_modified_text_rejected(corpus, tmp_path):
    rows = corpus.read_text().splitlines()
    corpus.write_text("\n".join(rows + [rows[0]]) + "\n", encoding="utf-8")
    directory = tmp_path / "store"
    directory.mkdir()
    with pytest.raises(IndexValidationError, match="unique"):
        CorpusStore.prepare(corpus, directory)
    row = json.loads(rows[0])
    row["text"] = "tampered text"
    corpus.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(IndexValidationError, match="Invalid Corpus"):
        CorpusStore.prepare(corpus, directory)


def test_dense_exact_cosine_and_canonical_row_mapping(corpus, tmp_path):
    encoder = FakeEncoder()
    directory = tmp_path / "dense"
    manifest = build_dense(corpus, directory, encoder, batch_size=2)
    assert all(isinstance(text, str) for text in encoder.calls)
    assert encoder.calls[0] == "cat cat sleeps on a sofa"
    retriever = DenseRetriever(corpus, directory, encoder, block_size=1)
    assert [hit.passage_id for hit in retriever.search("dog", top_k=4)] == ["p1", "p0", "p2", "p3"]
    assert retriever.search("dog")[0].score == pytest.approx(1)
    assert build_dense(corpus, directory, encoder, batch_size=2) == manifest
    with pytest.raises(IndexValidationError, match="different settings"):
        build_dense(corpus, directory, encoder, batch_size=3)
    encoder.model_manifest = {"revision": "changed"}
    with pytest.raises(IndexValidationError, match="differs"):
        DenseRetriever(corpus, directory, encoder)


def test_dense_resume_after_interruption(corpus, tmp_path, monkeypatch):
    class InterruptedEncoder(FakeEncoder):
        def encode(self, texts):
            if self.calls:
                raise KeyboardInterrupt
            return super().encode(texts)

    directory = tmp_path / "resumed"
    clock = itertools.count(step=30)
    monkeypatch.setattr("rag_research.retrieval.dense.time.perf_counter", lambda: next(clock))
    with pytest.raises(KeyboardInterrupt):
        build_dense(corpus, directory, InterruptedEncoder(), batch_size=2)
    assert directory.with_name("resumed.building").exists()
    checkpoint = read_json(directory.with_name("resumed.building") / "checkpoint.json")
    assert checkpoint["next_row"] == 2
    monkeypatch.undo()
    encoder = FakeEncoder()
    resumed = build_dense(corpus, directory, encoder, batch_size=2)
    assert encoder.calls == ["cat naps", "123 café"]
    continuous = build_dense(corpus, tmp_path / "continuous", FakeEncoder(), batch_size=2)
    assert resumed == continuous
    assert not directory.with_name("resumed.building").exists()


def test_dense_resume_rejects_modified_committed_vectors(corpus, tmp_path, monkeypatch):
    class InterruptedEncoder(FakeEncoder):
        def encode(self, texts):
            if self.calls:
                raise KeyboardInterrupt
            return super().encode(texts)

    clock = itertools.count(step=30)
    monkeypatch.setattr("rag_research.retrieval.dense.time.perf_counter", lambda: next(clock))
    directory = tmp_path / "dense"
    with pytest.raises(KeyboardInterrupt):
        build_dense(corpus, directory, InterruptedEncoder(), batch_size=2)
    monkeypatch.undo()
    vector_path = directory.with_name("dense.building") / "vectors.npy"
    vectors = np.load(vector_path, mmap_mode="r+", allow_pickle=False)
    vectors[0] = 0
    vectors[0, 3] = 1  # Still a unit vector, but no longer the committed vector.
    vectors.flush()
    del vectors
    with pytest.raises(IndexValidationError, match="Committed resume vectors"):
        build_dense(corpus, directory, FakeEncoder(), batch_size=2)


def test_dense_resume_rejects_changed_config(corpus, tmp_path):
    class InterruptedEncoder(FakeEncoder):
        def encode(self, texts):
            raise KeyboardInterrupt

    directory = tmp_path / "dense"
    with pytest.raises(KeyboardInterrupt):
        build_dense(corpus, directory, InterruptedEncoder())
    with pytest.raises(IndexValidationError, match="Resume conditions changed"):
        build_dense(corpus, directory, FakeEncoder(), batch_size=2)


def test_gold_coverage_and_development_metrics_are_offline(corpus, tmp_path):
    directory = tmp_path / "bm25"
    build_bm25(corpus, directory)
    retriever = BM25Retriever(corpus, directory)
    path = tmp_path / "qa.jsonl"
    write_json(path, qa_record(question="dog", gold=["p1"]))
    assert validate_gold_mapping(path, retriever.store.ids)["missing_gold_passage_ids"] == 0
    report = development_smoke(retriever, path)
    assert report["sample_count"] == 1
    assert report["metrics"] == {
        "recall_at_5": 1.0,
        "recall_at_10": 1.0,
        "mrr_at_10": 1.0,
        "ndcg_at_10": 1.0,
    }
    assert report["queries"][0]["retrieved_passage_ids"] == ["p1"]
    write_json(path, qa_record(gold=["missing"]))
    with pytest.raises(IndexValidationError, match="missing"):
        validate_gold_mapping(path, retriever.store.ids)


@pytest.mark.parametrize("split", ["calibration", "evaluation", None])
def test_smoke_cannot_use_other_splits(tmp_path, split):
    path = tmp_path / "qa.jsonl"
    write_json(path, qa_record(split=split))
    with pytest.raises(IndexValidationError, match="Development"):
        development_smoke(None, path)


def test_metrics_multiple_gold_and_no_gold_input(tmp_path):
    from rag_research.retrieval.common import RetrievalHit

    class QueryOnlyRetriever:
        manifest = {}

        def search(self, question, *, top_k):
            assert question == "public question"
            assert top_k == 10
            return [
                RetrievalHit("wrong", "title", "text", "revision", 2, 1),
                RetrievalHit("p0", "title", "text", "revision", 1, 2),
            ]

    path = tmp_path / "qa.jsonl"
    write_json(path, qa_record(question="public question", gold=["p0", "p1"]))
    report = development_smoke(QueryOnlyRetriever(), path)
    assert report["metrics"]["recall_at_5"] == 0.5
    assert report["metrics"]["mrr_at_10"] == 0.5
    assert report["metrics"]["ndcg_at_10"] == pytest.approx(0.386852807)


def test_manifest_stores_only_relative_artifact_paths(corpus, tmp_path):
    manifest = build_bm25(corpus, tmp_path / "bm25")
    assert manifest == read_json(tmp_path / "bm25" / "manifest.json")
    assert not any(name.startswith(("/", "C:")) for name in manifest["files"])
    assert "build_measurements.json" not in manifest["files"]


def test_combined_manifest_verifies_shared_corpus_and_all_gold(corpus, tmp_path):
    root = tmp_path / "indexes-v1"
    build_bm25(corpus, root / "bm25")
    build_dense(corpus, root / "embedding", FakeEncoder())
    qa_path = tmp_path / "qa.jsonl"
    write_json(qa_path, qa_record(gold=["p0", "p1"]))
    manifest = build_retrieval_manifest(corpus, root, qa_path)
    assert manifest["gold_coverage"]["unique_gold_passage_ids"] == 2
    assert manifest["corpus"]["record_count"] == 4
    assert set(manifest["indexes"]) == {"bm25", "embedding"}


def test_combined_manifest_rejects_wrong_index_kind(corpus, tmp_path):
    root = tmp_path / "indexes"
    build_bm25(corpus, root / "bm25")
    build_bm25(corpus, root / "embedding")
    with pytest.raises(IndexValidationError, match="Index kind"):
        build_retrieval_manifest(corpus, root, tmp_path / "unused.jsonl")
