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
from rag_research.retrieval.multilingual import (  # noqa: E402
    MODEL_ROOT as E5_MODEL_ROOT,
)
from rag_research.retrieval.multilingual import E5Tokenizer, MultilingualE5Encoder  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="全CorpusのBM25/Embedding Indexを構築")
    parser.add_argument("--kind", choices=("bm25", "embedding"), required=True)
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--model-root", type=Path)
    parser.add_argument("--encoder", choices=("minilm", "multilingual-e5"), default="minilm")
    parser.add_argument("--source-dataset", default="CLAPNQ")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--provider", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--device-id", type=int, default=0)
    args = parser.parse_args()
    if args.encoder == "multilingual-e5" and args.output_dir is None:
        parser.error("Multilingual E5 requires an explicit new --output-dir")
    if (args.provider != "cpu" or args.device_id != 0) and (
            args.encoder != "multilingual-e5" or args.kind != "embedding"):
        parser.error("CUDA/device options apply only to multilingual E5 embedding builds")
    output = args.output_dir or INDEX_ROOT / args.kind
    try:
        if args.kind == "bm25":
            tokenizer = (E5Tokenizer(args.model_root or E5_MODEL_ROOT)
                         if args.encoder == "multilingual-e5" else None)
            manifest = build_bm25(args.corpus, output, tokenizer=tokenizer,
                                  source_dataset=args.source_dataset)
        else:
            encoder = (MultilingualE5Encoder(args.model_root or E5_MODEL_ROOT, threads=args.threads,
                                             provider=args.provider, device_id=args.device_id)
                       if args.encoder == "multilingual-e5" else
                       OnnxEncoder(args.model_root or MODEL_ROOT, threads=args.threads))
            manifest = build_dense(args.corpus, output, encoder, batch_size=args.batch_size,
                                   source_dataset=args.source_dataset)
    except (OSError, IndexValidationError, ValueError) as error:
        parser.exit(1, f"Index build failed: {error}\n")
    print(f"Index: {output}; {manifest['corpus']['record_count']} passages")
    print(f"Corpus SHA-256: {manifest['corpus']['sha256']}")


if __name__ == "__main__":
    main()
