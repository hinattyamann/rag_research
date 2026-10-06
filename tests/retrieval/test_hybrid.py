"""Fusion correctness, independent selection and frozen-condition enforcement."""

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from rag_research.retrieval import factory
from rag_research.retrieval.calibration import (
    evaluate_grid,
    frozen_json,
    load_calibration,
    load_protocol,
    retrieval_metrics,
    select_condition,
)
from rag_research.retrieval.common import IndexValidationError, RetrievalHit, file_hash, write_json
from rag_research.retrieval.hybrid import HybridRetriever, fuse_rankings


def hit(identifier, rank, score=1.0):
    return RetrievalHit(
        identifier, f"Title {identifier}", f"Evidence {identifier}", "revision", score, rank
    )


def test_fusion_uses_rank_not_raw_score_and_merges_overlapping_ids():
    lexical = [hit("a", 1, 999), hit("b", 2, 0.1)]
    dense = [hit("c", 1, -0.1), hit("b", 2, -0.9)]
    result = fuse_rankings(lexical, dense, {"a": 0, "b": 1, "c": 2}, rrf_constant=60, top_k=3)
    assert [h.passage_id for h in result] == ["b", "a", "c"]
    assert result[0].score == pytest.approx(2 / 62)
    assert result[1].score == pytest.approx(1 / 61)
    assert result[0].bm25_rank == result[0].embedding_rank == 2
    assert result[1].embedding_rank is None
    assert result[2].bm25_score is None
    assert result[0].to_dict()["embedding_score"] == -0.9


def test_fusion_empty_lists_and_canonical_ties():
    assert fuse_rankings([], [], {}, rrf_constant=60, top_k=5) == []
    result = fuse_rankings(
        [hit("later", 1)],
        [hit("earlier", 1)],
        {"earlier": 0, "later": 1},
        rrf_constant=60,
        top_k=1,
    )
    assert result[0].passage_id == "earlier"
    assert fuse_rankings([], [hit("earlier", 1)], {"earlier": 0}, rrf_constant=20, top_k=10)[
        0
    ].score == pytest.approx(1 / 21)


@pytest.mark.parametrize(
    "bad",
    [
        [hit("a", 2)],
        [hit("a", 1), hit("a", 2)],
        [hit("unknown", 1)],
        [hit("a", 1, float("nan"))],
        [{"passage_id": "a", "gold": True}],
    ],
)
def test_bad_rankings_are_rejected(bad):
    with pytest.raises(IndexValidationError):
        fuse_rankings(bad, [], {"a": 0}, rrf_constant=60, top_k=5)


def test_same_id_with_different_context_is_rejected():
    with pytest.raises(IndexValidationError, match="content"):
        fuse_rankings(
            [hit("a", 1)],
            [replace(hit("a", 1), text="changed")],
            {"a": 0},
            rrf_constant=60,
            top_k=5,
        )


class Retriever:
    def __init__(self, kind, hits, ids=None):
        self.hits = hits
        self.calls = []
        self.manifest = {"config": {"kind": kind}, "corpus": {"sha256": "same"}}
        self.store = SimpleNamespace(ids=ids or ["a", "b", "c"], path=Path("same.jsonl"))

    def search(self, question, *, top_k):
        assert question == "public question"
        self.calls.append((question, top_k))
        return self.hits[:top_k]


def test_hybrid_search_validates_mapping_and_passes_only_original_question():
    bm25 = Retriever("bm25", [hit("a", 1), hit("b", 2)])
    embedding = Retriever("embedding", [hit("c", 1), hit("b", 2)])
    retriever = HybridRetriever(bm25, embedding, candidate_count=20)
    assert retriever.search("public question", top_k=3)[0].passage_id == "b"
    assert bm25.calls == embedding.calls == [("public question", 20)]
    assert retriever.last_search_details["unique_candidates"] == 3
    with pytest.raises(ValueError, match="QA/Gold"):
        retriever.search({"question": "public question", "reference": "SECRET"})
    with pytest.raises(ValueError, match="exceed"):
        retriever.search("public question", top_k=21)
    with pytest.raises(IndexValidationError, match="ordered Corpus"):
        HybridRetriever(bm25, Retriever("embedding", [], ids=["c", "b", "a"]))


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_fusion_constants(value):
    with pytest.raises(ValueError):
        fuse_rankings([], [], {}, rrf_constant=value, top_k=5)


def test_metrics_distinguish_success_from_multi_gold_recall():
    metrics = retrieval_metrics(["wrong", "a"], ["a", "b"], [3, 5, 10])
    assert metrics["success_at_5"] == 1.0
    assert metrics["gold_recall_at_5"] == 0.5
    assert metrics["mrr_at_10"] == 0.5
    assert metrics["ndcg_at_10"] == pytest.approx(0.386852807)
    assert retrieval_metrics([], ["a"], [3, 5, 10])["ndcg_at_10"] == 0
    with pytest.raises(ValueError):
        retrieval_metrics(["random_provided"], [], [5, 10])


def test_calibration_rejects_other_splits_subsets_and_unanswerable_gold(tmp_path):
    path = tmp_path / "qa.jsonl"
    rows = [
        {
            "record_id": "q1",
            "research_split": "calibration",
            "is_answerable": True,
            "question": "public question",
            "gold_passage_ids": ["a"],
        },
        {
            "record_id": "q2",
            "research_split": "calibration",
            "is_answerable": False,
            "question": "public question",
            "gold_passage_ids": [],
        },
    ]

    def manifest():
        return {
            "outputs": {"calibration.jsonl": {"sha256": file_hash(path)}},
            "record_ids_by_split": {"calibration": ["q1", "q2"]},
        }

    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    selected, excluded = load_calibration(path, manifest())
    assert [row["record_id"] for row in selected] == ["q1"] and excluded == 1
    original = manifest()
    rows[0]["research_split"] = "evaluation"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(IndexValidationError, match="differs"):
        load_calibration(path, original)
    with pytest.raises(IndexValidationError, match="Invalid"):
        load_calibration(path, manifest())
    rows[0]["research_split"] = "calibration"
    rows[1]["gold_passage_ids"] = ["random_provided"]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(IndexValidationError, match="Invalid"):
        load_calibration(path, manifest())


def test_grid_reuses_prefixes_and_selection_rule_is_deterministic():
    protocol = load_protocol(Path("configs/phase6_calibration.yaml"))
    bm25 = Retriever("bm25", [hit("a", 1), hit("b", 2)])
    embedding = Retriever("embedding", [hit("c", 1), hit("b", 2)])
    rows = [
        {
            "record_id": "q",
            "question": "public question",
            "gold_passage_ids": ["b"],
            "reference_answers": ["SECRET"],
        }
    ]
    result = evaluate_grid(rows, bm25, embedding, protocol)
    assert bm25.calls == embedding.calls == [("public question", 100)]
    assert len(result["grid"]) == 9
    assert select_condition(result["grid"], protocol) == {
        "kind": "hybrid",
        "candidate_count": 20,
        "rrf_constant": 60,
        "top_k": 3,
    }
    assert select_condition(list(reversed(result["grid"])), protocol) == select_condition(
        result["grid"], protocol
    )
    boundary = [
        {
            "candidate_count": 20,
            "rrf_constant": 60,
            "metrics": {
                "ndcg_at_10": 0.5,
                "success_at_3": 0.7,
                "success_at_5": 0.75,
                "success_at_10": 0.8,
            },
        }
    ]
    assert select_condition(boundary, protocol)["top_k"] == 5


def test_frozen_artifacts_never_overwrite_different_content(tmp_path):
    path = tmp_path / "manifest.json"
    frozen_json(path, {"fixed": 1})
    frozen_json(path, {"fixed": 1})
    before = path.read_bytes()
    with pytest.raises(IndexValidationError, match="Frozen"):
        frozen_json(path, {"fixed": 2})
    assert path.read_bytes() == before


def test_hybrid_manifest_detects_selection_protocol_and_report_changes(tmp_path, monkeypatch):
    selection = {"kind": "hybrid", "top_k": 5, "candidate_count": 20, "rrf_constant": 60}
    retriever = SimpleNamespace(manifest={"fixed": "retriever"})
    for name in ("COMMON_MANIFEST", "CALIBRATION_PROTOCOL", "CALIBRATION_REPORT"):
        path = tmp_path / name
        monkeypatch.setattr(factory, name, path)
        write_json(path, {"selection": selection, "retriever": retriever.manifest})
    manifest = {
        "schema_version": 1,
        "purpose": "phase6-fixed-hybrid-retriever",
        "selection": selection,
        "retriever": retriever.manifest,
        "common_manifest_sha256": file_hash(factory.COMMON_MANIFEST),
        "protocol_sha256": file_hash(factory.CALIBRATION_PROTOCOL),
        "calibration_report_sha256": file_hash(factory.CALIBRATION_REPORT),
        "hybrid_implementation_sha256": file_hash(Path(factory.__file__).with_name("hybrid.py")),
    }
    path = tmp_path / "hybrid.json"
    write_json(path, manifest)
    assert factory.verify_hybrid(retriever, selection, path) == manifest
    with pytest.raises(IndexValidationError, match="frozen"):
        factory.verify_hybrid(retriever, {**selection, "top_k": 3}, path)
    factory.CALIBRATION_PROTOCOL.write_bytes(b"changed")
    with pytest.raises(IndexValidationError, match="frozen"):
        factory.verify_hybrid(retriever, selection, path)
