"""Offline Development-only smoke metrics; Gold IDs never enter search()."""

import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np

from rag_research.retrieval.common import IndexValidationError, file_hash, read_json, verify_index


def build_retrieval_manifest(corpus_path: Path, index_root: Path, qa_path: Path) -> dict:
    """Verify both Index types, shared Corpus order and complete Gold-ID coverage."""
    manifests = {
        name: verify_index(index_root / name, corpus_path) for name in ("bm25", "embedding")
    }
    if any(manifest["config"].get("kind") != name for name, manifest in manifests.items()):
        raise IndexValidationError("Index kind does not match its directory")
    if manifests["bm25"]["corpus"] != manifests["embedding"]["corpus"]:
        raise IndexValidationError("The two Indexes do not share the same Corpus row mapping")
    ids = read_json(index_root / "bm25" / "passage_ids.json")
    coverage = validate_gold_mapping(qa_path, ids)
    return {
        "schema_version": 1,
        "index_version": index_root.name,
        "corpus": manifests["bm25"]["corpus"],
        "gold_coverage": coverage,
        "indexes": {
            name: {
                "manifest_sha256": file_hash(index_root / name / "manifest.json"),
                "config": manifest["config"],
                "files": manifest["files"],
            }
            for name, manifest in manifests.items()
        },
    }


def validate_gold_mapping(qa_path: Path, passage_ids: list[str]) -> dict:
    """Corpus coverage validation only; does not search or measure QA performance."""
    corpus_ids = set(passage_ids)
    gold_ids = set()
    records = 0
    with qa_path.open(encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            gold_ids.update(row["gold_passage_ids"])
            records += 1
    missing = sorted(gold_ids - corpus_ids)
    if missing:
        raise IndexValidationError(f"Gold IDs missing from Corpus: {missing[:5]}")
    return {
        "qa_sha256": file_hash(qa_path),
        "qa_count": records,
        "unique_gold_passage_ids": len(gold_ids),
        "missing_gold_passage_ids": 0,
    }


def development_smoke(retriever, qa_path: Path, *, limit: int = 50) -> dict:
    """Seeded hash order independent of search outcomes; answerable subset only."""
    if limit < 1:
        raise ValueError("limit must be positive")
    with qa_path.open(encoding="utf-8") as source:
        rows = [json.loads(line) for line in source]
    if not rows or any(row.get("research_split") != "development" for row in rows):
        raise IndexValidationError("Smoke metrics accept Development records only")
    rows = [row for row in rows if row["is_answerable"]]
    rows.sort(key=lambda row: hashlib.sha256(f"42:{row['record_id']}".encode()).hexdigest())
    rows = rows[:limit]
    if not rows:
        raise IndexValidationError("No answerable Development records")
    measurements = []
    for row in rows:
        started = time.perf_counter()
        hits = retriever.search(row["question"], top_k=10)
        elapsed = time.perf_counter() - started
        ids = [hit.passage_id for hit in hits]
        gold = set(row["gold_passage_ids"])
        if not gold:
            raise IndexValidationError("Answerable record has no Gold ID")
        relevance = [int(identifier in gold) for identifier in ids]
        dcg = sum(rel / math.log2(rank + 2) for rank, rel in enumerate(relevance))
        idcg = sum(1 / math.log2(rank + 2) for rank in range(min(10, len(gold))))
        first = next((rank for rank, rel in enumerate(relevance, start=1) if rel), None)
        measurements.append(
            {
                "record_id": row["record_id"],
                "retrieved_passage_ids": ids,
                "gold_passage_ids": sorted(gold),
                "recall_at_5": len(set(ids[:5]) & gold) / len(gold),
                "recall_at_10": len(set(ids) & gold) / len(gold),
                "mrr_at_10": 1 / first if first else 0.0,
                "ndcg_at_10": dcg / idcg,
                "latency_seconds": elapsed,
            }
        )
    metrics = {
        name: float(np.mean([item[name] for item in measurements]))
        for name in ("recall_at_5", "recall_at_10", "mrr_at_10", "ndcg_at_10")
    }
    latencies = [item["latency_seconds"] for item in measurements]
    return {
        "purpose": "development_smoke_not_final_evaluation",
        "split": "development",
        "selection": "sha256(42:record_id)-ascending-answerable-first-N-v1",
        "qa_sha256": file_hash(qa_path),
        "sample_count": len(rows),
        "metrics": metrics,
        "latency_p50_seconds": float(np.percentile(latencies, 50)),
        "latency_p95_seconds": float(np.percentile(latencies, 95)),
        "index_manifest": retriever.manifest,
        "queries": measurements,
    }
