"""Preselect unseen Development questions and run the Phase 10 pilot."""

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.pilot.baseline import run_baseline  # noqa: E402
from rag_research.pilot.internal import run_internal  # noqa: E402
from rag_research.pilot.report import pilot_report  # noqa: E402
from rag_research.pilot.selection import freeze_selection  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["select", "baseline", "internal", "report"])
    parser.add_argument("--config", type=Path, default=ROOT / "configs/phase10.yaml")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/runs/pilot/phase10-twenty-v1")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text("utf-8"))
    require(config["purpose"] == "phase10-development-pilot" and config["automatic_retries"] == 0 and
            config["replace_failed_questions"] is False and config["human_reviewed"] is False,
            "Invalid pilot protocol")
    selection = freeze_selection(config, ROOT / "data/manifests/phase10_selection_manifest.json")
    if args.stage == "select":
        print(f"Selected {len(selection['records'])} unseen titles before model execution")
    else:
        output = args.output_dir.resolve()
        require(output.is_relative_to(ROOT / "data/runs/pilot") and output != ROOT / "data/runs/pilot",
                "Unexpected pilot output directory")
        output.mkdir(parents=True, exist_ok=True)
        if args.stage == "baseline":
            run_baseline(config, selection, output / "baseline")
        elif args.stage == "internal":
            run_internal(args.config.resolve(), config, selection, output)
        else:
            import json

            print(json.dumps(pilot_report(output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
