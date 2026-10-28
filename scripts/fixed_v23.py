"""Operate the separately registered fixed-v23 local collection."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments import fixed_v23_control as control  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("init", "pilot", "continue", "resume", "status", "stop", "worker", "child"))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--token")
    parser.add_argument("--language", choices=("en", "ja"))
    parser.add_argument("--stage", choices=("baseline", "internal"))
    parser.add_argument("--first-qa", action="store_true")
    args = parser.parse_args()
    if args.action == "child":
        if not args.language or not args.stage:
            parser.error("Child needs --language and --stage")
        return control.child_stage(args.run.resolve(), args.language, args.stage, args.first_qa)
    if args.action == "worker":
        if not args.token:
            parser.error("Worker needs its launch token")
        value = control.worker(args.run, args.token)
        return 1 if value["state"] == "failed" else 0
    if args.action in {"pilot", "continue", "resume"}:
        value = control.launch(args.run, args.action)
    else:
        function = {"init": control.initialize, "status": control.status, "stop": control.stop}[args.action]
        value = function(args.run)
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
