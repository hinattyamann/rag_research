"""Run Phase 8 on saved Development answers; never rewrite or regenerate answers."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.order_runner import run_evaluation  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/order_phase8_v5.yaml")
    parser.add_argument("--baseline-answers", type=Path,
                        default=ROOT / "data/runs/phase6/development-five-v1/answers.jsonl")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--record-id", action="append", help="Optional Development Answerable IDs")
    args = parser.parse_args()
    report = run_evaluation(args.config, args.baseline_answers, args.output_dir, args.record_id)
    print(json.dumps({k: report[k] for k in ("record_count", "actual_completion_attempts",
                                           "task_status_counts", "judge_status_counts")}), flush=True)


if __name__ == "__main__":
    main()
