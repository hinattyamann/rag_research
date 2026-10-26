"""Offline parent relevance; duplicate children never earn another Gold hit."""

import math

from rag_research.data.token_bounded_corpus import parent_relevance
from rag_research.experiments.frozen_trace import require


def retrieval_metrics(child_ids, parent_of, gold_parent_ids, *, missing_source_units=(), top_ks=(5,)):
    require(all(type(k) is int and k > 0 for k in top_ks), "Invalid metric cutoffs")
    gold = set(gold_parent_ids)
    relevance = parent_relevance(child_ids, parent_of, gold)
    result = {"gold_parent_count_available": len(gold),
              "missing_cited_source_unit_count": len(set(missing_source_units)),
              "metric_scope": "conditional_on_available_annotated_parent_units",
              "ranking_depth_available": len(child_ids), "scorable": bool(gold)}
    for k in top_ks:
        count = sum(relevance[:k])
        result[f"success_at_{k}"] = float(count > 0) if gold else None
        result[f"gold_parent_recall_at_{k}"] = count / len(gold) if gold else None
        dcg = sum(value / math.log2(rank + 2) for rank, value in enumerate(relevance[:k]))
        ideal = sum(1 / math.log2(rank + 2) for rank in range(min(k, len(gold))))
        first = next((rank for rank, rel in enumerate(relevance[:k], 1) if rel), None)
        result[f"ndcg_at_{k}"] = dcg / ideal if ideal else None
        result[f"mrr_at_{k}"] = (1 / first if first else 0.0) if gold else None
    return result
