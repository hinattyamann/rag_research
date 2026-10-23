"""Two preregistered, fresh runtime requests; preserve the old failed request."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.evaluation.claimwise import atomic_steps, payloads, verify_once  # noqa: E402
from rag_research.experiments.frozen_trace import digest, require  # noqa: E402
from rag_research.experiments.protocol import ROOT, task_config  # noqa: E402
from rag_research.experiments.semantic_diagnostics import load_config  # noqa: E402
from rag_research.experiments.storage import read_json, run_lock, write_json  # noqa: E402
from rag_research.generation.auxiliary import auxiliary_server_kwargs  # noqa: E402
from rag_research.generation.local import LocalServer  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def probe_payload(case, target):
    full = {k: case[k] for k in ("question", "answer", "claims", "documents")}
    require(target["order"] == "original", "Unknown runtime probe order")
    return next(payload for identifier, payload in payloads(full, "claimwise-v1") if identifier == target["claim_id"])


def recovery_proof():
    path = ROOT / "data/manifests/phase11_review_smoke_recovery_v1.json"
    proof = read_json(path)
    for name, sha in proof["preserved_files_sha256"].items():
        require(file_hash(ROOT / name) == sha, "Preserve original software-failed smoke evidence")
    old = ROOT / proof["old_smoke_run"]
    first = read_json(old / "probe-1.claims/c1.json")
    require(first["status"] == "ok" and not first["cost_incomplete"] and first["completion_attempted"] is True and
            not (old / "probe-2.json").exists() and not (old / "probe-2.claims").exists(),
            "Only a proven unsubmitted second probe may continue; never retry an unknown response")
    return proof


def run(output, *, remaining_only=False):
    output = Path(output).resolve()
    parent = ROOT / "data/runs/runtime_screening"
    require(Path.cwd().resolve() == ROOT and output.is_relative_to(parent) and output != parent and not output.exists(),
            "Use a new fixed-checkout runtime smoke; never retry previous requests")
    registration_path = ROOT / "data/manifests/phase11_review_development_preregistration_v1.json"
    registration = read_json(registration_path)
    config_binding = registration["known_config"]
    config_path = ROOT / config_binding["path"]
    require(file_hash(config_path) == config_binding["sha256"], "Registered runtime candidate changed")
    config, plan, prompts, _ = load_config(config_path)
    targets = registration["runtime_smoke_targets"]
    require(len(targets) == registration["allocated_calls"]["runtime_smoke"] == 2, "Only two registered runtime probes")
    if remaining_only:
        recovery_proof()
        targets = targets[1:]
    manifest = {"purpose": "phase11-readonly-triage-fresh-runtime-smoke-not-semantic-adoption",
                "registration_sha256": file_hash(registration_path), "config": config,
                "fixed_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                "targets": targets, "remaining_only": remaining_only, "old_results_replaced": False, "phase12_allowed": False}
    with run_lock(output):
        write_json(output / "manifest.json", manifest)
        results = []
        with LocalServer(task_config(config, "verify_claims"), output / "server.log", **auxiliary_server_kwargs(config)) as server:
            for index, target in enumerate(targets):
                case = next(c for c in plan["cases"] if c["id"] == target["case_id"])
                task = verify_once(server.client, task_config(config, "verify_claims"), prompts[case["language"]],
                    probe_payload(case, target),
                    output / f"probe-{index + 1}.json", {"manifest_sha256": digest(manifest), **target},
                    constraints=config["output_constraints"], mode=config["verification_mode"])
                results.append(task)
                print(json.dumps({"probe": index + 1, "status": task["status"]}), flush=True)
                if task["status"] != "ok":
                    break
            write_json(output / "session.json", server.report())
        steps = list(atomic_steps(results))
        report = {"purpose": manifest["purpose"], "runtime_health_passed": len(results) == len(targets) and all(t["status"] == "ok" for t in results),
            "remaining_only": remaining_only, "earlier_successful_calls_not_repeated": 1 if remaining_only else 0,
            "completion_attempts_recorded": sum(bool(t["completion_attempted"]) for t in steps),
            "summed_task_seconds": sum(t.get("elapsed_seconds", 0) for t in steps),
            "cost_incomplete": any(t.get("cost_incomplete", False) for t in steps),
            "input_tokens": sum(t.get("input_tokens") or 0 for t in steps),
            "output_tokens": sum(t.get("output_tokens") or 0 for t in steps),
            "semantic_adoption_claimed": False, "gate11_passed": False, "phase12_allowed": False}
        write_json(output / "report.json", report)
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--remaining-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir, remaining_only=args.remaining_only)))
