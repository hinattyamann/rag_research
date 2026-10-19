"""Development-only diagnostics; expected labels never enter model payloads."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.evaluation.tasks import execute_task  # noqa: E402
from rag_research.experiments.frozen_trace import digest  # noqa: E402
from rag_research.experiments.protocol import load_protocol, task_config  # noqa: E402
from rag_research.experiments.storage import read_json, write_json  # noqa: E402
from rag_research.generation.artifacts import model_identity  # noqa: E402
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
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    config, prompts, _ = load_protocol(args.config)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    old = read_json(ROOT / "data/runs/pilot/phase10-twenty-v1/internal/report.private.json")
    records = old["records"]
    suite = read_json(ROOT / "configs/measurement_diagnostics.json")
    binding = {"config": digest(config), "prompts": digest(prompts), "suite": digest(suite)}
    paths = [Path(__file__), args.config, ROOT / "configs/measurement_diagnostics.json",
             *sorted((ROOT / "src/rag_research/evaluation").glob("*.py")),
             ROOT / "src/rag_research/recovery/answer_rewrite.py",
             ROOT / "src/rag_research/generation/auxiliary.py",
             ROOT / "src/rag_research/generation/local.py",
             ROOT / "src/rag_research/experiments/protocol.py"]
    binding["source_sha256"] = {p.resolve().relative_to(ROOT).as_posix(): file_hash(p) for p in paths}
    plan = {"binding": binding, "suite": suite, "model": model_identity(),
            "auxiliary_model": auxiliary_identity(config),
            "known_cases": [1, 2, 4, 6, 10, 11, 17, 19, 20]}
    if (output / "plan.json").exists():
        if read_json(output / "plan.json") != plan:
            raise ValueError("Diagnostic conditions changed; use a new run")
    else:
        write_json(output / "plan.json", plan)
    results = []
    session = len(list(output.glob("server*.log"))) + 1
    with LocalServer(task_config(config, "verify_claims"), output / f"server-{session}.log",
                     **auxiliary_server_kwargs(config)) as server:
        for index in [1, 2, 10, 11, 20]:
            trace = records[index - 1]["trace"]
            result = execute_task(server.client, task_config(config, "extract_claims"), prompts,
                                  "extract_claims", {"answer": trace["answer"]},
                                  output / f"extract-{index:02d}.json", binding,
                                  constraints=config["output_constraints"])
            print(json.dumps({"kind": "extract", "index": index, "status": result["status"],
                              "parsed": result["parsed"]}), flush=True)
        for case in suite["judge"]:
            payload = {"question": case["question"], "answer": case["claim"],
                       "claims": [{"claim_id": "c1", "text": case["claim"]}],
                       "documents": case["documents"]}
            result = execute_task(server.client, task_config(config, "verify_claims"), prompts,
                                  "verify_claims", payload, output / f"judge-{case['id']}.json",
                                  binding, constraints=config["output_constraints"])
            label = result["parsed"]["verdicts"][0]["label"] if result["status"] == "ok" else None
            results.append({"id": case["id"], "expected": case["expected"], "actual": label,
                            "pass": label == case["expected"]})
            print(json.dumps(results[-1]), flush=True)
        for index in [4, 6, 17]:
            old_row = records[index - 1]
            trace = old_row["trace"]
            claims = old_row["evaluation"]["claims"]
            if prompts.get("claim_units") == "verbatim-sentences-v1" and index != 17:
                from rag_research.evaluation.sentence_claims import extract_sentence_units
                claims = extract_sentence_units(trace["answer"])["claims"]
            payload = {"question": trace["question"], "answer": trace["answer"],
                       "claims": claims, "documents": trace["documents"]}
            result = execute_task(server.client, task_config(config, "verify_claims"), prompts,
                                  "verify_claims", payload, output / f"natural-{index:02d}.json",
                                  binding, constraints=config["output_constraints"])
            print(json.dumps({"kind": "natural", "index": index, "status": result["status"],
                              "parsed": result["parsed"]}), flush=True)
        for index in [4, 19]:
            trace = records[index - 1]["trace"]
            result = rewrite_once(server.client, task_config(config, "rewrite_answer"), prompts,
                                  trace, output / f"rewrite-{index:02d}.json", binding)
            print(json.dumps({"kind": "rewrite", "index": index, "status": result["status"],
                              "answer": result["answer"]}), flush=True)
        write_json(output / "summary.json", {"judge": results,
                   "completion_attempts_this_session": server.client.completion_attempts,
                   "raw_completion_attempts_total": sum(read_json(p).get("completion_attempted", False)
                                                        for p in output.glob("*.json")
                                                        if p.name not in {"plan.json", "summary.json"}),
                   "server": server.report()})


if __name__ == "__main__":
    main()
