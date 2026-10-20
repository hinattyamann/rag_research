"""Audit known Development false support separately from answer insufficiency."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.evaluation.sentence_claims import extract_sentence_units  # noqa: E402
from rag_research.evaluation.tasks import execute_task  # noqa: E402
from rag_research.experiments.frozen_trace import digest  # noqa: E402
from rag_research.experiments.protocol import load_protocol, task_config  # noqa: E402
from rag_research.experiments.storage import write_json  # noqa: E402
from rag_research.generation.auxiliary import auxiliary_server_kwargs  # noqa: E402
from rag_research.generation.local import LocalServer  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path,
                        default=ROOT / "configs/order_phase11_gpu_diagnostics_v2.yaml")
    args = parser.parse_args()
    if args.output.exists() or not args.output.resolve().is_relative_to(ROOT / "data/runs/lab"):
        raise ValueError("Choose a new Development probe directory")
    args.output.mkdir(parents=True)
    path = args.config.resolve()
    config, prompts, _ = load_protocol(path)
    rows = []
    for name in ("data/runs/pilot/phase10-five-v2/baseline/answers.jsonl",
                 "data/runs/pilot/phase10-five-extra-v2/baseline/answers.jsonl",
                 "data/runs/phase6/development-five-v1/answers.jsonl"):
        for row in map(json.loads, (ROOT / name).read_text().splitlines()):
            if any(word in row["question"] for word in ("warm front", "tar heels", "bernette", "prada")):
                rows.append(row)
    plan = {"purpose": "known-development-semantic-probes", "protocol_sha256": file_hash(path),
            "record_ids": [r["record_id"] for r in rows], "automatic_retries": 0,
            "calibration20_used": False, "source_sha256": file_hash(Path(__file__)),
            "purpose_of_prada": "supported_content_can_still_fail_essential_answer"}
    write_json(args.output / "plan.json", plan)
    results = []
    with LocalServer(task_config(config, "verify_claims"), args.output / "server.log",
                     **auxiliary_server_kwargs(config)) as server:
        for i, row in enumerate(rows):
            payload = {"question": row["question"], "answer": row["answer"],
                       "documents": row["used_context"],
                       "claims": extract_sentence_units(row["answer"])["claims"]}
            result = execute_task(server.client, task_config(config, "verify_claims"), prompts,
                                  "verify_claims", payload, args.output / f"task-{i + 1}.json",
                                  {"plan": digest(plan)}, constraints=config["output_constraints"])
            summary = {"question": row["question"], "answer": row["answer"],
                       "status": result["status"], "parsed": result["parsed"]}
            results.append(summary)
            print(json.dumps(summary), flush=True)
        write_json(args.output / "summary.json", {"results": results, "server": server.report()})
