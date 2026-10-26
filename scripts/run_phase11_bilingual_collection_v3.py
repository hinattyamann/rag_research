"""Run all scheduled Main or Cal sessions; leave internal values sealed for scoring."""

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.bilingual_runner import run, run_calibration  # noqa: E402
from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.phase11_collection import collect_language  # noqa: E402
from rag_research.experiments.storage import run_lock, write_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="English config")
    parser.add_argument("--config-ja", type=Path, required=True)
    parser.add_argument("--mode", choices=("main", "cal"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    parent = ROOT / "data/runs" / ("bilingual_development" if args.mode == "main" else "bilingual_calibration")
    require(Path.cwd().resolve() == ROOT and output.is_relative_to(parent)
            and output != parent and not output.exists(), "Use a new registered collection directory")
    configs = {"en": args.config.resolve(), "ja": args.config_ja.resolve()}
    for language, path in configs.items():
        config = yaml.safe_load(path.read_text("utf-8"))
        require(config["language"] == language and len(config["data"]["record_ids"]) == 20
                and config["phase12_allowed"] is False, "Collect both original twenty-QA selections")
    results = {}
    with run_lock(output):
        for language, config_path in configs.items():
            def record(stage, session, result):
                path = output / f"{language}-{stage}-session-{session}.json"
                require(not path.exists(), "Preserve the original session receipt")
                write_json(path, {"language": language, "stage": stage, "session": session,
                                  "public_progress": result, "phase12_allowed": False})
                print(json.dumps({"language": language, "stage": stage, "session": session,
                                  "session_finished": True}), flush=True)

            results[language] = collect_language(run if args.mode == "main" else run_calibration,
                                                 config_path, output / language, record)
            if not results[language]["collection_completed"]:
                break
        report = {"mode": args.mode, "languages": results,
                  "collection_completed": len(results) == 2 and all(
                      r["collection_completed"] for r in results.values()),
                  "quality_and_expected_sealed": False, "scientific_adoption_claimed": False,
                  "gate11_passed": False, "phase12_allowed": False}
        write_json(output / "collection.json", report)
    return 0 if report["collection_completed"] else 1


if __name__ == "__main__":
    sys.exit(main())
