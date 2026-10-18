"""Generate one original-order rewrite per saved Phase 8 Development question."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.repair_runner import run_rewrites  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/phase9.yaml")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_rewrites(args.config, args.output_dir)
    print(json.dumps({k: report[k] for k in ("record_count", "rewrite_attempts", "quality_status")}))


if __name__ == "__main__":
    main()
