"""Freeze only Development IDs; never generate answers or read Evaluation QA."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.development_selection import prepare  # noqa: E402
from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.storage import checkpoint  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "data/manifests") and not output.exists(),
            "Write a new selection manifest; preserve any prior selection")
    value = prepare(args.policy)
    value["created_at_utc"] = datetime.now(UTC).isoformat()
    checkpoint(output, value)
    print(json.dumps({"selected": {lang: v["planned_qa"] for lang, v in value["languages"].items()},
                      "used_baseline_inputs": len(value["used_baseline_input_sha256"]),
                      "model_completion_attempts": 0, "candidate_adopted": False}))
