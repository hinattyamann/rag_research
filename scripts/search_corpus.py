"""Question-only search; no QA labels, references or Gold passages are inputs."""

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.retrieval.bm25 import BM25Retriever  # noqa: E402
from rag_research.retrieval.common import CORPUS_PATH, INDEX_ROOT, MODEL_ROOT  # noqa: E402
from rag_research.retrieval.dense import DenseRetriever, OnnxEncoder  # noqa: E402
from rag_research.retrieval.factory import load_retriever  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="質問文字列から全Corpusを検索")
    parser.add_argument("question")
    parser.add_argument("--kind", choices=("bm25", "embedding", "hybrid"), default="bm25")
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH)
    parser.add_argument("--index-dir", type=Path)
    parser.add_argument("--model-root", type=Path, default=MODEL_ROOT)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--config", type=Path, default=Path("configs/phase6.yaml"))
    args = parser.parse_args()
    index_dir = args.index_dir or INDEX_ROOT / args.kind
    top_k = args.top_k if args.top_k is not None else 5
    if args.kind == "hybrid":
        if args.index_dir is not None:
            parser.error("Hybrid uses both frozen Indexes; --index-dir is for single retrievers")
        config = yaml.safe_load(args.config.read_text(encoding="utf-8"))["retrieval"]
        if config["kind"] != "hybrid":
            parser.error("Hybrid requires a Hybrid config")
        retriever = load_retriever(config, corpus=args.corpus, model_root=args.model_root)
        top_k = args.top_k if args.top_k is not None else config["top_k"]
    elif args.kind == "bm25":
        retriever = BM25Retriever(args.corpus, index_dir)
    else:
        retriever = DenseRetriever(args.corpus, index_dir, OnnxEncoder(args.model_root))
    print(
        json.dumps(
            [hit.to_dict() for hit in retriever.search(args.question, top_k=top_k)],
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
