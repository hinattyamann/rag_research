"""Two preregistered Runtime probes; never adopt semantics or retry an old result."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.evaluation.claimwise import atomic_steps, payloads, verify_once  # noqa: E402
from rag_research.experiments.frozen_trace import digest, require  # noqa: E402
from rag_research.experiments.protocol import task_config  # noqa: E402
from rag_research.experiments.semantic_diagnostics import load_config  # noqa: E402
from rag_research.experiments.storage import read_json, run_lock, write_json  # noqa: E402
from rag_research.generation.auxiliary import auxiliary_server_kwargs  # noqa: E402
from rag_research.generation.cuda_runtime import execution_identity  # noqa: E402
from rag_research.generation.local import LocalServer  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def run(config_path, target_plan_path, output):
    config_path, target_plan_path, output = (
        Path(p).resolve() for p in (config_path, target_plan_path, output)
    )
    parent = ROOT / "data/runs/runtime_screening"
    require(Path.cwd().resolve() == ROOT and output.is_relative_to(parent)
            and output != parent and not output.exists(), "Use a fresh fixed-checkout smoke")
    config, _, prompts, _ = load_config(config_path)
    plan = read_json(target_plan_path)
    require(plan["purpose"] == "phase11-runtime-smoke-v3" and plan["maximum_calls"] == 2
            and plan["automatic_retries"] == 0 and plan["phase12_allowed"] is False,
            "Use the registered two-probe plan")
    source_path = (ROOT / plan["source"]["path"]).resolve()
    require(source_path.is_relative_to(ROOT)
            and file_hash(source_path) == plan["source"]["sha256"], "Smoke source changed")
    source = read_json(source_path)
    require(len(plan["targets"]) == 2, "Preserve both registered probes")
    manifest = {
        "purpose": plan["purpose"], "config_sha256": file_hash(config_path),
        "target_plan_sha256": file_hash(target_plan_path), "config": config,
        "fixed_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in
                          [*sorted((ROOT / "src/rag_research").rglob("*.py")), Path(__file__)]},
        "targets": plan["targets"], **execution_identity(config),
        "old_results_replaced": False, "semantic_adoption_claimed": False,
        "gate11_passed": False, "phase12_allowed": False,
    }
    with run_lock(output):
        write_json(output / "manifest.json", manifest)
        results = []
        with LocalServer(task_config(config, "verify_claims"), output / "server.log",
                         **auxiliary_server_kwargs(config)) as server:
            for index, target in enumerate(plan["targets"], 1):
                case = next(c for c in source["cases"] if c["id"] == target["case_id"])
                documents = case["documents"]
                require(target["order"] in {"original", "reversed"}, "Invalid probe order")
                if target["order"] == "reversed":
                    documents = list(reversed(documents))
                full = {"question": case["question"], "answer": case["answer"],
                        "claims": case["claims"], "documents": documents}
                # payloads preserves the whole draft/context and maps the global ID to local c1.
                payload = next(p for claim_id, p in payloads(full, "claimwise-v1")
                               if claim_id == target["claim_id"])
                task = verify_once(server.client, task_config(config, "verify_claims"),
                                   prompts[case["language"]], payload, output / f"probe-{index}.json",
                                   {"manifest_sha256": digest(manifest), **target},
                                   constraints=config["output_constraints"], mode="claimwise-v1")
                results.append(task)
                print(json.dumps({"probe": index, "status": task["status"]}), flush=True)
                if task["status"] != "ok":
                    break
            write_json(output / "session.json", server.report())
        steps = list(atomic_steps(results))
        unknown = any(t.get("cost_incomplete", False) for t in steps)
        report = {
            "purpose": plan["purpose"], "manifest_sha256": digest(manifest),
            "runtime_health_passed": len(results) == 2 and all(t["status"] == "ok" for t in results),
            "planned_completion_limit": 2,
            "completion_attempts_recorded": sum(bool(t["completion_attempted"]) for t in steps),
            "summed_task_seconds": sum(t.get("elapsed_seconds", 0) for t in steps),
            "cost_incomplete": unknown,
            "observed_input_tokens": sum(t.get("input_tokens") or 0 for t in steps),
            "observed_output_tokens": sum(t.get("output_tokens") or 0 for t in steps),
            "total_output_tokens": None if unknown else sum(t.get("output_tokens") or 0 for t in steps),
            "semantic_adoption_claimed": False, "gate11_passed": False, "phase12_allowed": False,
        }
        write_json(output / "report.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--target-plan", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.target_plan, args.output_dir)))
