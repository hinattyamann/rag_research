"""Equal-weight Reciprocal Rank Fusion over one canonical Corpus."""

import math
import time
from dataclasses import dataclass

from rag_research.retrieval.common import IndexValidationError, RetrievalHit, validate_query


@dataclass(frozen=True, slots=True)
class HybridHit(RetrievalHit):
    bm25_rank: int | None
    bm25_score: float | None
    embedding_rank: int | None
    embedding_score: float | None


def positive_integer(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def fuse_rankings(bm25_hits, embedding_hits, corpus_rows, *, rrf_constant, top_k):
    """Ranks are one-based; missing ranks contribute zero, never a guessed rank."""
    positive_integer(rrf_constant, "rrf_constant")
    validate_query("fusion", top_k)
    documents, signals = {}, {}
    for name, hits in (("bm25", bm25_hits), ("embedding", embedding_hits)):
        seen = set()
        for rank, hit in enumerate(hits, start=1):
            if (
                not isinstance(hit, RetrievalHit)
                or hit.rank != rank
                or not math.isfinite(hit.score)
                or hit.passage_id not in corpus_rows
                or hit.passage_id in seen
            ):
                raise IndexValidationError("Invalid, duplicate or unknown ranked Passage")
            seen.add(hit.passage_id)
            previous = documents.get(hit.passage_id)
            if previous is not None and (
                previous.title,
                previous.text,
                previous.source_revision,
            ) != (hit.title, hit.text, hit.source_revision):
                raise IndexValidationError("The two retrievers disagree on Passage content")
            documents[hit.passage_id] = hit
            signals.setdefault(hit.passage_id, {})[name] = (rank, hit.score)
    scores = {
        identifier: sum(1.0 / (rrf_constant + rank) for rank, _ in values.values())
        for identifier, values in signals.items()
    }
    ordered = sorted(scores, key=lambda identifier: (-scores[identifier], corpus_rows[identifier]))
    results = []
    for rank, identifier in enumerate(ordered[:top_k], start=1):
        hit = documents[identifier]
        bm25_rank, bm25_score = signals[identifier].get("bm25", (None, None))
        dense_rank, dense_score = signals[identifier].get("embedding", (None, None))
        results.append(
            HybridHit(
                identifier,
                hit.title,
                hit.text,
                hit.source_revision,
                scores[identifier],
                rank,
                bm25_rank,
                bm25_score,
                dense_rank,
                dense_score,
            )
        )
    return results


class HybridRetriever:
    def __init__(self, bm25, embedding, *, candidate_count=50, rrf_constant=60):
        positive_integer(candidate_count, "candidate_count")
        positive_integer(rrf_constant, "rrf_constant")
        if (
            bm25.manifest["config"]["kind"] != "bm25"
            or embedding.manifest["config"]["kind"] != "embedding"
            or bm25.manifest["corpus"] != embedding.manifest["corpus"]
            or bm25.store.ids != embedding.store.ids
            or bm25.store.path.resolve() != embedding.store.path.resolve()
        ):
            raise IndexValidationError("Hybrid retrievers must share the same ordered Corpus")
        self.bm25, self.embedding = bm25, embedding
        self.candidate_count, self.rrf_constant = candidate_count, rrf_constant
        self.corpus_rows = {identifier: row for row, identifier in enumerate(bm25.store.ids)}
        self.manifest = {
            "config": {
                "kind": "hybrid",
                "algorithm": "equal-weight-rrf-v1",
                "candidate_count": candidate_count,
                "rrf_constant": rrf_constant,
                "rank_origin": 1,
                "missing_rank_contribution": 0,
                "tie_break": "corpus_row_ascending",
                "reranker": None,
            },
            "corpus": bm25.manifest["corpus"],
            "indexes": {"bm25": bm25.manifest, "embedding": embedding.manifest},
        }
        self.last_search_details = {}

    def search(self, question: str, *, top_k: int = 5):
        validate_query(question, top_k)
        if top_k > self.candidate_count:
            raise ValueError("top_k must not exceed candidate_count")
        self.last_search_details = {}
        started = time.perf_counter()
        bm25_hits = self.bm25.search(question, top_k=self.candidate_count)
        after_bm25 = time.perf_counter()
        dense_hits = self.embedding.search(question, top_k=self.candidate_count)
        after_dense = time.perf_counter()
        hits = fuse_rankings(
            bm25_hits,
            dense_hits,
            self.corpus_rows,
            rrf_constant=self.rrf_constant,
            top_k=top_k,
        )
        self.last_search_details = {
            "bm25_seconds": after_bm25 - started,
            "embedding_seconds": after_dense - after_bm25,
            "fusion_seconds": time.perf_counter() - after_dense,
            "bm25_candidates": len(bm25_hits),
            "embedding_candidates": len(dense_hits),
            "unique_candidates": len({h.passage_id for h in (*bm25_hits, *dense_hits)}),
            "returned_documents": len(hits),
        }
        return hits
