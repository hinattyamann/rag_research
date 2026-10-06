"""Offline Calibration-only selection; Gold is never passed to search()."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import yaml

from rag_research.retrieval.common import IndexValidationError, file_hash, json_bytes
from rag_research.retrieval.hybrid import fuse_rankings, positive_integer

CALIBRATION_PATH = Path("data/processed/clapnq/c508d78-split-v1/calibration.jsonl")
SPLIT_MANIFEST = Path("data/manifests/clapnq_split_manifest.json")


def frozen_json(path, value):
    """Never overwrite a finalized artifact; allow only byte-identical reuse."""
    frozen_bytes(path, json_bytes(value))


def frozen_bytes(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as target:
            target.write(payload)
    except FileExistsError:
        if path.read_bytes() != payload:
            raise IndexValidationError(
                f"Frozen artifact differs; use a new version: {path}"
            ) from None


def load_protocol(path):
    protocol = yaml.safe_load(path.read_text(encoding="utf-8"))
    if (
        protocol["schema_version"] != 1
        or protocol["purpose"] != "phase6-retrieval-calibration"
        or protocol["selection_metric"] != "ndcg_at_10"
        or protocol["seed"] != 42
        or protocol["reranker"] is not None
        or protocol["tie_break"]
        != ["success_at_10", "smaller_candidate_count", "rrf_closest_to_60", "smaller_rrf_constant"]
    ):
        raise ValueError("Unsupported Calibration protocol")
    for key in ("candidate_counts", "rrf_constants", "top_k_candidates"):
        values = protocol[key]
        if not isinstance(values, list) or not values or values != sorted(set(values)):
            raise ValueError(f"{key} must be a nonempty sorted unique list")
        for value in values:
            positive_integer(value, key)
    if min(protocol["candidate_counts"]) < 10 or max(protocol["top_k_candidates"]) != 10:
        raise ValueError("All conditions must support rank 10")
    if max(protocol["candidate_counts"]) > 100:
        raise ValueError("Phase 6 limits candidate counts to 100")
    gap = protocol["top_k_max_success_drop"]
    if type(gap) not in (float, int) or not 0 <= gap <= 1:
        raise ValueError("Invalid top-k success tolerance")
    return protocol


def load_calibration(path, manifest):
    """Require the complete frozen Calibration artifact, not a caller-selected subset."""
    if file_hash(path) != manifest["outputs"]["calibration.jsonl"]["sha256"]:
        raise IndexValidationError("Calibration file differs from Split Manifest")
    with path.open(encoding="utf-8") as source:
        rows = [json.loads(line) for line in source]
    identifiers = [row["record_id"] for row in rows]
    if (
        not rows
        or len(identifiers) != len(set(identifiers))
        or set(identifiers) != set(manifest["record_ids_by_split"]["calibration"])
        or any(row["research_split"] != "calibration" for row in rows)
        or any(type(row["is_answerable"]) is not bool for row in rows)
        or any(not row["gold_passage_ids"] for row in rows if row["is_answerable"])
        or any(row["gold_passage_ids"] for row in rows if not row["is_answerable"])
    ):
        raise IndexValidationError("Invalid or incomplete Calibration records")
    answerable = [row for row in rows if row["is_answerable"]]
    if not answerable:
        raise IndexValidationError("Calibration contains no Answerable records")
    answerable.sort(key=lambda row: hashlib.sha256(f"42:{row['record_id']}".encode()).hexdigest())
    return answerable, len(rows) - len(answerable)


def retrieval_metrics(identifiers, gold, top_ks):
    gold = set(gold)
    if not gold or len(identifiers) != len(set(identifiers)):
        raise ValueError("Metrics require Gold and unique retrieval IDs")
    metrics = {}
    for k in top_ks:
        found = set(identifiers[:k]) & gold
        metrics[f"success_at_{k}"] = float(bool(found))
        metrics[f"gold_recall_at_{k}"] = len(found) / len(gold)
    relevance = [int(identifier in gold) for identifier in identifiers[:10]]
    dcg = sum(rel / math.log2(rank + 2) for rank, rel in enumerate(relevance))
    idcg = sum(1 / math.log2(rank + 2) for rank in range(min(10, len(gold))))
    first = next((rank for rank, rel in enumerate(relevance, 1) if rel), None)
    metrics["ndcg_at_10"] = dcg / idcg
    metrics["mrr_at_10"] = 1 / first if first else 0.0
    return metrics


def mean_metrics(records):
    if not records:
        raise ValueError("Cannot aggregate empty metrics")
    return {key: float(np.mean([row[key] for row in records])) for key in records[0]}


def select_condition(grid, protocol):
    winner = max(
        grid,
        key=lambda row: (
            round(row["metrics"]["ndcg_at_10"], 12),
            round(row["metrics"]["success_at_10"], 12),
            -row["candidate_count"],
            -abs(row["rrf_constant"] - 60),
            -row["rrf_constant"],
        ),
    )
    target = winner["metrics"]["success_at_10"] - protocol["top_k_max_success_drop"]
    k = next(
        k
        for k in protocol["top_k_candidates"]
        if winner["metrics"][f"success_at_{k}"] >= target - 1e-12
    )
    return {
        "kind": "hybrid",
        "candidate_count": winner["candidate_count"],
        "rrf_constant": winner["rrf_constant"],
        "top_k": k,
    }


def evaluate_grid(rows, bm25, embedding, protocol, *, progress=None):
    corpus_rows = {identifier: index for index, identifier in enumerate(bm25.store.ids)}
    conditions = [
        (count, constant)
        for count in protocol["candidate_counts"]
        for constant in protocol["rrf_constants"]
    ]
    measurements = {condition: [] for condition in conditions}
    standalone = {name: [] for name in ("bm25", "embedding")}
    queries = []
    maximum = max(protocol["candidate_counts"])
    for index, row in enumerate(rows, start=1):
        if not set(row["gold_passage_ids"]) <= corpus_rows.keys():
            raise IndexValidationError("Calibration Gold missing from Corpus")
        # Only the original string enters either retriever, never the QA dictionary.
        lexical = bm25.search(row["question"], top_k=maximum)
        dense = embedding.search(row["question"], top_k=maximum)
        query = {"record_id": row["record_id"], "rankings": {}, "hybrid_top_10": {}}
        for name, hits in (("bm25", lexical), ("embedding", dense)):
            query["rankings"][name] = [
                {"passage_id": hit.passage_id, "rank": hit.rank, "score": hit.score} for hit in hits
            ]
            standalone[name].append(
                retrieval_metrics(
                    [hit.passage_id for hit in hits],
                    row["gold_passage_ids"],
                    protocol["top_k_candidates"],
                )
            )
        for count, constant in conditions:
            fused = fuse_rankings(
                lexical[:count], dense[:count], corpus_rows, rrf_constant=constant, top_k=10
            )
            identifiers = [hit.passage_id for hit in fused]
            query["hybrid_top_10"][f"{count}:{constant}"] = identifiers
            measurements[(count, constant)].append(
                retrieval_metrics(
                    identifiers, row["gold_passage_ids"], protocol["top_k_candidates"]
                )
            )
        queries.append(query)
        if progress and (index % 25 == 0 or index == len(rows)):
            progress(index, len(rows))
    return {
        "standalone": {name: mean_metrics(values) for name, values in standalone.items()},
        "grid": [
            {
                "candidate_count": count,
                "rrf_constant": constant,
                "metrics": mean_metrics(measurements[(count, constant)]),
            }
            for count, constant in conditions
        ],
        "queries": queries,
    }
