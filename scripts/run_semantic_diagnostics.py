"""Run the preregistered known/synthetic bilingual semantic gate."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.experiments.semantic_diagnostics import run  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.config, args.output_dir)
    print(json.dumps({k: v for k, v in report.items() if k not in {"task_result_sha256", "not_attempted_ids"}}, indent=2))
