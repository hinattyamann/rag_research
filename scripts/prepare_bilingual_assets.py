"""Freeze only candidate asset identities; never load QA text or run a model."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.retrieval.common import file_hash, write_json  # noqa: E402


def prepare(output):
    def bind(path):
        value = ROOT / path
        return {"path": str(path), "sha256": file_hash(value)}
    files = ["configs/phase11_multilingual_embedding_v1.json", "environments/embedding_gpu/pyproject.toml",
             "environments/embedding_gpu/uv.lock", "src/rag_research/data/study_assets.py",
             "src/rag_research/retrieval/bilingual.py", "src/rag_research/retrieval/multilingual.py",
             "src/rag_research/retrieval/common.py", "src/rag_research/retrieval/bm25.py",
             "src/rag_research/retrieval/dense.py", "src/rag_research/retrieval/hybrid.py",
             "data/manifests/phase11_japanese_reference_projection_v2.json",
             "data/manifests/phase11_bilingual_dense_index_manifest.json",
             "data/manifests/phase11_bilingual_bm25_hybrid_preflight.json"]
    datasets = {}
    specs = [("en", "CLAPNQ", "clapnq/c508d78-split-v1", "clapnq/c508d78-e5-passages-v1",
              "clapnq/c508d78-e5-cuda-v1", "original_source_parent_passage"),
             ("ja", "baobab-trees/wikipedia-human-retrieval-ja", "wikipedia_human_retrieval_ja/02e85c8-qa-corpus-v2",
              "wikipedia_human_retrieval_ja/02e85c8-e5-passages-v1", "wikipedia_human_retrieval_ja/02e85c8-e5-cuda-v1",
              "available_cited_source_article")]
    for language, source, qa, corpus, index, unit in specs:
        datasets[language] = {"language": language, "source_dataset": source, "gold_parent_unit": unit,
                              "qa": {s: bind(f"data/processed/{qa}/{s}.jsonl")
                                     for s in ("development", "calibration", "evaluation")},
                              "corpus": bind(f"data/processed/{corpus}/passages.jsonl"),
                              "parent_map": bind(f"data/processed/{corpus}/parent_map.jsonl"),
                              "indexes": {k: bind(f"data/indexes/{index}/{k}/manifest.json")
                                          for k in ("bm25", "embedding")}}
    value = {"schema_version": 1, "purpose": "phase11-bilingual-assets-candidate",
             "status": "candidate_not_frozen", "phase12_allowed": False,
             "embedding": {"model_root": "data/models/multilingual-e5-small", "provider": "cuda",
                           "device_id": 0, "use_tf32": 0, "threads": 6},
             "retrieval": {"kind": "hybrid", "candidate_count": 50, "rrf_constant": 60, "top_k": 5},
             "datasets": datasets, "fixed_files": [bind(p) for p in files]}
    require(not output.exists(), "Asset registry exists; preserve it and use a new version")
    write_json(output, value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    path = args.output.resolve()
    require(path.is_relative_to(ROOT / "configs"), "Store the candidate asset registry in configs")
    prepare(path)
    print(f"Saved candidate asset bindings: {path}")


if __name__ == "__main__":
    main()
