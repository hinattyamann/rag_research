"""Prepare and run Phase 11 Calibration without opening final Evaluation outcomes."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.calibration.preparation import (  # noqa: E402
    baseline_stage,
    load_config,
    prepare,
    progress_report,
)
from rag_research.calibration.report import calibration_report  # noqa: E402
from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.storage import run_lock  # noqa: E402
from rag_research.pilot.assessment import open_candidate, save_candidate  # noqa: E402
from rag_research.pilot.internal import run_internal  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "status", "baseline", "internal",
                                          "open-quality", "save-quality", "report"])
    parser.add_argument("--config", type=Path, default=ROOT / "configs/phase11_calibration.yaml")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "data/runs/calibration/phase11-cpu-five-v1")
    parser.add_argument("--selection-manifest", type=Path,
                        default=ROOT / "data/manifests/phase11_calibration_selection_manifest.json")
    parser.add_argument("--max-new-questions", type=int, default=None,
                        help="Baseline only; bounded execution preserves the full fixed selection")
    parser.add_argument("--packet", type=int, help="One-based anonymous per-question packet")
    parser.add_argument("--decision", type=Path)
    args = parser.parse_args()
    require(Path.cwd().resolve() == ROOT, "Run from repository root")
    require(args.max_new_questions is None or (args.stage == "baseline" and args.max_new_questions > 0),
            "Execution limit is available for baseline only")
    output = args.output_dir.resolve()
    selection_path = args.selection_manifest.resolve()
    require(output.is_relative_to(ROOT / "data/runs/calibration") and
            output != ROOT / "data/runs/calibration", "Unexpected Calibration output directory")
    require(selection_path.is_relative_to(ROOT / "data/manifests"), "Unexpected selection path")
    config = load_config(args.config.resolve())
    with run_lock(output):
        selection, candidate = prepare(args.config.resolve(), config, selection_path, output)
        if args.stage in {"prepare", "status"}:
            result = progress_report(output, candidate)
        elif args.stage == "baseline":
            report = baseline_stage(config, selection, output, args.max_new_questions)
            result = {key: report[key] for key in ("status", "completed_questions",
                      "successful_questions", "answer_generation_calls", "additional_completion_attempts")
                      if key in report}
        elif args.stage == "internal":
            result = run_internal(args.config.resolve(), config, selection, output, split="calibration")
        elif args.stage in {"open-quality", "save-quality"}:
            require(args.packet is not None and 0 < args.packet <= config["count"], "Select a quality packet")
            bundle = output / "quality" / f"ready-{args.packet:03d}"
            assessment = output / "quality/assessments" / f"packet-{args.packet:03d}"
            if args.stage == "open-quality":
                result = open_candidate(bundle, assessment)
            else:
                require(args.decision is not None, "A saved AI quality decision is required")
                result = save_candidate(bundle, assessment, args.decision.resolve())
        else:
            report = calibration_report(output)
            result = {key: report[key] for key in ("planned_questions", "processed_questions",
                      "comparable_questions", "judge_status_counts", "gate11_passed", "phase12_allowed")}
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
