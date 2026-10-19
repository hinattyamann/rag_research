"""Preselect unseen Development questions and run the Phase 10 pilot."""

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.frozen_trace import digest, require  # noqa: E402
from rag_research.experiments.storage import read_json  # noqa: E402
from rag_research.pilot.baseline import run_baseline  # noqa: E402
from rag_research.pilot.internal import run_internal  # noqa: E402
from rag_research.pilot.report import pilot_report  # noqa: E402
from rag_research.pilot.selection import freeze_selection  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def baseline_stage(config, selection, output):
    # Once internal inference binds this provenance, even a cached baseline run
    # must not append a session and change its hash. This guard is read-only.
    path = output / "internal/manifest.json"
    if not path.exists():
        return run_baseline(config, selection, output / "baseline")
    binding = read_json(path)
    require(binding["selection_sha256"] == digest(selection), "Frozen baseline selection differs")
    answers = output / "baseline/answers.jsonl"
    provenance = output / "baseline/run_manifest.json"
    require(file_hash(answers) == binding["baseline_answers_sha256"] and
            file_hash(provenance) == binding["baseline_provenance_sha256"],
            "Frozen baseline artifacts changed; never overwrite the existing run")
    baseline = read_json(provenance)
    require(baseline["status"] == "completed", "Frozen baseline is not completed")
    return {"stage": "baseline", "status": "frozen_baseline_reused",
            "completed_questions": baseline["completed_questions"],
            "additional_completion_attempts": 0, "provenance_changed": False}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["select", "baseline", "internal", "report"])
    parser.add_argument("--config", type=Path, default=ROOT / "configs/phase10.yaml")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/runs/pilot/phase10-twenty-v1")
    parser.add_argument("--selection-manifest", type=Path,
                        default=ROOT / "data/manifests/phase10_selection_manifest.json")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text("utf-8"))
    require(config["purpose"] == "phase10-development-pilot" and config["automatic_retries"] == 0 and
            config["replace_failed_questions"] is False and config["human_reviewed"] is False,
            "Invalid pilot protocol")
    selection_path = args.selection_manifest.resolve()
    require(selection_path.is_relative_to(ROOT / "data/manifests"), "Unexpected selection manifest")
    selection = freeze_selection(config, selection_path)
    if args.stage == "select":
        print(f"Selected {len(selection['records'])} unseen titles before model execution")
    else:
        output = args.output_dir.resolve()
        require(output.is_relative_to(ROOT / "data/runs/pilot") and output != ROOT / "data/runs/pilot",
                "Unexpected pilot output directory")
        output.mkdir(parents=True, exist_ok=True)
        if args.stage == "baseline":
            result = baseline_stage(config, selection, output)
            if result["status"] == "frozen_baseline_reused":
                print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.stage == "internal":
            run_internal(args.config.resolve(), config, selection, output)
        else:
            print(json.dumps(pilot_report(output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
