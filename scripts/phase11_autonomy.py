"""Register, execute or inspect finite Phase11 v3 runs; never launch Phase12."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.phase11_autonomy import (  # noqa: E402
    execute,
    inspect_handle,
    register,
    seal_stopped_run,
    validate_plan,
)
from rag_research.experiments.storage import read_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["validate", "register", "execute", "inspect", "seal-stopped"])
    parser.add_argument("--protocol", type=Path, default=ROOT / "configs/phase11_autonomy_v3.json")
    parser.add_argument("--ledger-dir", type=Path,
                        default=ROOT / "data/runs/development_screening/phase11-autonomy-v3")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--reason")
    args = parser.parse_args()
    if args.action == "inspect":
        result = inspect_handle(args.ledger_dir)
    elif args.action == "seal-stopped":
        if args.run_id is None or args.reason is None:
            parser.error("--run-id and --reason are required for recovery without resending")
        result = seal_stopped_run(ROOT, args.ledger_dir, args.run_id, args.reason)
    elif args.action == "execute":
        parser.error("--run-id is required") if args.run_id is None else None
        result = execute(ROOT, args.protocol, args.ledger_dir, args.run_id)
    else:
        parser.error("--plan is required") if args.plan is None else None
        if args.action == "register":
            result = register(ROOT, args.protocol, args.plan, args.ledger_dir)
        else:
            validate_plan(ROOT, read_json(args.plan), args.protocol)
            result = {"valid": True, "generation_calls": 0, "phase12_allowed": False}
    print(json.dumps(result, ensure_ascii=False))
    if args.action == "execute" and result["state"] != "process_completed":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
