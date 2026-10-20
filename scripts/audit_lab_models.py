"""Compare all active model bytes to tracked pre-transfer identities."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.generation.artifacts import model_identity, verify_model  # noqa: E402
from rag_research.generation.auxiliary import (  # noqa: E402
    auxiliary_identity,
    auxiliary_server_kwargs,
)
from rag_research.retrieval.common import file_hash, read_json, write_json  # noqa: E402
from rag_research.retrieval.dense import prepare_model  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or not args.output.resolve().is_relative_to(ROOT / "data/runs/lab"):
        raise ValueError("Choose a new local model audit output")
    expected = read_json(ROOT / "data/manifests/clapnq_retrieval_manifest.json")["indexes"]["embedding"]["config"]["model"]
    directory = prepare_model(offline=True)
    if read_json(directory / "model_manifest.json") != expected:
        raise ValueError("MiniLM differs from the pre-transfer retrieval manifest")
    baseline = verify_model()
    config = {"auxiliary_model_manifest": "data/manifests/phase10_auxiliary_qwen3_manifest.json"}
    auxiliary_server_kwargs(config)
    result = {"purpose": "fixed-active-models-verified", "minilm": expected,
              "baseline": model_identity(), "auxiliary": auxiliary_identity(config),
              "baseline_actual_sha256": file_hash(baseline), "all_active_hashes_match": True}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, result)
    print("MiniLM ONNX, Qwen2.5-3B Q4_K_M and Qwen3-4B Q4_K_M: all pinned hashes match")
