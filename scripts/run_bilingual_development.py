"""Run selected bilingual Development QA; public output excludes scores/answers."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.experiments.bilingual_runner import run  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--stage", choices=("baseline", "internal", "all"), default="all")
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.output_dir, stage=args.stage), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
