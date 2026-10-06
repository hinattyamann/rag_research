"""Check all Gold-ID coverage and optional Development-only retrieval metrics."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.retrieval.bm25 import BM25Retriever  # noqa: E402
from rag_research.retrieval.common import (  # noqa: E402
    CORPUS_PATH,
    DEVELOPMENT_PATH,
    INDEX_ROOT,
    MODEL_ROOT,
    ResourceMonitor,
    write_json,
)
from rag_research.retrieval.dense import DenseRetriever, OnnxEncoder  # noqa: E402
from rag_research.retrieval.validation import (  # noqa: E402
    development_smoke,
    validate_gold_mapping,
)


def main():
    parser = argparse.ArgumentParser(description="Gold対応とDevelopment検索を検証")
    parser.add_argument("--kind", choices=("bm25", "embedding"), required=True)
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH)
    parser.add_argument("--index-dir", type=Path)
    parser.add_argument("--model-root", type=Path, default=MODEL_ROOT)
    parser.add_argument("--qa", type=Path, default=DEVELOPMENT_PATH)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    index_dir = args.index_dir or INDEX_ROOT / args.kind
    with ResourceMonitor() as monitor:
        if args.kind == "bm25":
            retriever = BM25Retriever(args.corpus, index_dir)
        else:
            retriever = DenseRetriever(args.corpus, index_dir, OnnxEncoder(args.model_root))
        report = development_smoke(retriever, args.qa, limit=args.limit)
        report["gold_coverage"] = validate_gold_mapping(
            Path("data/processed/clapnq/c508d78-base-v1/qa.jsonl"), retriever.store.ids
        )
    report["resources"] = monitor.report()
    output = args.output or Path(f"data/processed/retrieval/{args.kind}_development_smoke.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, report)
    print(f"Development-only ({report['sample_count']} queries): {report['metrics']}")
    print(f"Resources: {report['resources']}; report: {output}")


if __name__ == "__main__":
    main()
