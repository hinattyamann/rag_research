"""Review or freeze complete bilingual Phase 11 evidence; never run Phase 12."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.bilingual_finalization import readiness, save  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("review", "freeze"))
    parser.add_argument("--decisions", required=True, help="Repository-relative JSON under configs")
    parser.add_argument("--output", help="New data/manifests/phase11_bilingual_final_freeze_vN.json")
    args = parser.parse_args()
    if args.stage == "freeze":
        if args.output is None:
            parser.error("--output is required for freeze")
        result = save(args.decisions, args.output)
    else:
        result = readiness(args.decisions)
    print(json.dumps({k: v for k, v in result.items() if k != "conditions"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
