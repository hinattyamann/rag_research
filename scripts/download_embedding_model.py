"""Prepare the pinned official ONNX files without installing PyTorch."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.retrieval.common import MODEL_ROOT  # noqa: E402
from rag_research.retrieval.dense import prepare_model  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="固定RevisionのCPU用Embedding Modelを取得")
    parser.add_argument("--model-root", type=Path, default=MODEL_ROOT)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    print(prepare_model(args.model_root, offline=args.offline))


if __name__ == "__main__":
    main()
