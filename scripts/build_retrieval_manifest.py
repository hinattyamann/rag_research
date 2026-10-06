"""Freeze the two verified Index identities without rewriting existing artifacts."""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.retrieval.common import (  # noqa: E402
    CORPUS_PATH,
    INDEX_ROOT,
    file_hash,
    json_bytes,
)
from rag_research.retrieval.validation import build_retrieval_manifest  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="検証済みBM25・Embedding Indexの条件を固定")
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH)
    parser.add_argument("--index-root", type=Path, default=INDEX_ROOT)
    parser.add_argument(
        "--qa", type=Path, default=Path("data/processed/clapnq/c508d78-base-v1/qa.jsonl")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/manifests/clapnq_retrieval_manifest.json")
    )
    args = parser.parse_args()
    content = json_bytes(build_retrieval_manifest(args.corpus, args.index_root, args.qa))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        if args.output.read_bytes() != content:
            parser.exit(1, "Existing Retrieval Manifest differs; use a new output path\n")
    else:
        # Exclusive creation: don't race with or overwrite another research condition.
        temporary = args.output.with_name(args.output.name + ".tmp")
        with temporary.open("xb") as target:
            target.write(content)
            target.flush()
            os.fsync(target.fileno())
        try:
            os.link(temporary, args.output)
        finally:
            temporary.unlink()
    print(f"Verified: {args.output}; SHA-256: {file_hash(args.output)}")


if __name__ == "__main__":
    main()
