"""Open a blinded pilot candidate or save Codex's grounded annotation."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.pilot.assessment import open_candidate, save_candidate  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["open", "save"])
    parser.add_argument("--packet", type=int, required=True)
    parser.add_argument("--decision", type=Path)
    parser.add_argument("--run-dir", type=Path, default=ROOT / "data/runs/pilot/phase10-twenty-v1")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    require(run.is_relative_to(ROOT / "data/runs/pilot") and args.packet > 0, "Unexpected pilot packet")
    bundle = run / "quality" / f"ready-{args.packet:03d}"
    assessment = run / "quality/assessments" / f"packet-{args.packet:03d}"
    result = (open_candidate(bundle, assessment) if args.action == "open" else
              save_candidate(bundle, assessment, args.decision))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
