"""Analyze source-verified Development runs only after all bilingual labels are sealed."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.experiments.bilingual_statistics import analyze_runs  # noqa: E402
from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.protocol import ROOT  # noqa: E402
from rag_research.experiments.storage import read_json, run_lock, write_json  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True, help="JSON list of run/bundle/annotations paths")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    require(Path.cwd().resolve() == ROOT and output.is_relative_to(ROOT / "data/runs/statistics_validation") and
            output != ROOT / "data/runs/statistics_validation", "Unexpected Development statistics output")
    value = analyze_runs(read_json(args.inputs))
    with run_lock(output):
        require({p.name for p in output.iterdir()} == {".run.lock"}, "Preserve previous statistical output")
        write_json(output / "report.private.json", value)
    print(json.dumps({"languages": value["languages"], "ja_minus_en": value["ja_minus_en"], "gate11_passed": False}))
