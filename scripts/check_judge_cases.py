"""Run a frozen additional diagnostic suite without modifying previous runs."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.evaluation.tasks import execute_task  # noqa: E402
from rag_research.experiments.frozen_trace import digest, require  # noqa: E402
from rag_research.experiments.protocol import load_protocol, task_config  # noqa: E402
from rag_research.experiments.storage import read_json, write_json  # noqa: E402
from rag_research.generation.auxiliary import (  # noqa: E402
    auxiliary_identity,
    auxiliary_server_kwargs,
)
from rag_research.generation.local import LocalServer  # noqa: E402
from rag_research.recovery.answer_rewrite import rewrite_once  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    config, prompts, _ = load_protocol(args.config)
    suite = read_json(args.suite)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    plan = {"config": config, "prompts": prompts, "suite": suite,
            "model": auxiliary_identity(config), "script_sha256": file_hash(Path(__file__))}
    if (output / "plan.json").exists():
        require(read_json(output / "plan.json") == plan, "Additional diagnostic conditions changed")
    else:
        write_json(output / "plan.json", plan)
    results = []
    session = len(list(output.glob("server*.log"))) + 1
    with LocalServer(task_config(config, "verify_claims"), output / f"server-{session}.log",
                     **auxiliary_server_kwargs(config)) as server:
        for case in suite["judge"]:
            payload = {"question": case["question"], "answer": case["claim"],
                       "claims": [{"claim_id": "c1", "text": case["claim"]}],
                       "documents": case["documents"]}
            task = execute_task(server.client, task_config(config, "verify_claims"), prompts,
                                "verify_claims", payload, output / f"judge-{case['id']}.json",
                                {"plan_sha256": digest(plan)}, constraints=config["output_constraints"])
            label = task["parsed"]["verdicts"][0]["label"] if task["status"] == "ok" else None
            results.append({"id": case["id"], "expected": case["expected"], "actual": label,
                            "pass": label == case["expected"]})
            print(json.dumps(results[-1]), flush=True)
        for case in suite.get("rewrite", []):
            trace = {k: case[k] for k in ("question", "answer", "documents")}
            task = rewrite_once(server.client, task_config(config, "rewrite_answer"), prompts,
                                trace, output / f"rewrite-{case['id']}.json", {"plan_sha256": digest(plan)})
            print(json.dumps({"kind": "rewrite", "id": case["id"], "status": task["status"],
                              "answer": task["answer"]}), flush=True)
        write_json(output / "summary.json", {"results": results,
                   "completed_at_utc": datetime.now(UTC).isoformat(),
                   "completion_attempts_this_session": server.client.completion_attempts,
                   "server": server.report()})


if __name__ == "__main__":
    main()
