"""Build one common-Corpus Index; finalized artifacts are never overwritten."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.retrieval.bm25 import build_bm25  # noqa: E402
from rag_research.retrieval.common import (  # noqa: E402
    CORPUS_PATH,
    INDEX_ROOT,
    MODEL_ROOT,
    IndexValidationError,
)
from rag_research.retrieval.dense import OnnxEncoder, build_dense  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="全CorpusのBM25/Embedding Indexを構築")
    parser.add_argument("--kind", choices=("bm25", "embedding"), required=True)
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--model-root", type=Path, default=MODEL_ROOT)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--threads", type=int, default=6)
    args = parser.parse_args()
    output = args.output_dir or INDEX_ROOT / args.kind
    try:
        if args.kind == "bm25":
            manifest = build_bm25(args.corpus, output)
        else:
            encoder = OnnxEncoder(args.model_root, threads=args.threads)
            manifest = build_dense(args.corpus, output, encoder, batch_size=args.batch_size)
    except (OSError, IndexValidationError, ValueError) as error:
        parser.exit(1, f"Index build failed: {error}\n")
    print(f"Index: {output}; {manifest['corpus']['record_count']} passages")
    print(f"Corpus SHA-256: {manifest['corpus']['sha256']}")


if __name__ == "__main__":
    main()
