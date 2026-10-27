"""Two registered synthetic rewrites with an explicit pinned reasoning budget."""

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
sys.path.insert(0, str(ROOT / "src"))

import psutil  # noqa: E402

from rag_research.evaluation.sentence_claims import extract_sentence_units  # noqa: E402
from rag_research.experiments.frozen_trace import digest, require, validate_documents  # noqa: E402
from rag_research.experiments.phase11_autonomy import validate_plan, verify_binding  # noqa: E402
from rag_research.experiments.protocol import task_config  # noqa: E402
from rag_research.experiments.semantic_diagnostics import load_config  # noqa: E402
from rag_research.experiments.storage import read_json, run_lock, write_json  # noqa: E402
from rag_research.generation.auxiliary import auxiliary_server_kwargs  # noqa: E402
from rag_research.generation.local import LocalServer  # noqa: E402
from rag_research.recovery.answer_rewrite import rewrite_once  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402

ENTRY = "scripts/run_phase11_rewrite_smoke_v4.py"
FIELDS = ("question", "answer", "documents")


def git_paths(root):
    marker = root / ".git"
    admin = marker if marker.is_dir() else (root / marker.read_text().strip().removeprefix("gitdir: ")).resolve()
    common = (admin / (admin / "commondir").read_text().strip()).resolve() if (admin / "commondir").exists() else admin
    return admin, common


def fixed_head(root):
    admin, common = git_paths(root)
    value = (admin / "HEAD").read_text().strip()
    if not value.startswith("ref: "):
        return value
    name = value.removeprefix("ref: ")
    for path in (admin / name, common / name):
        if path.is_file():
            return path.read_text().strip()
    for line in (common / "packed-refs").read_text().splitlines():
        if not line.startswith(("#", "^")) and line.split()[1:] == [name]:
            return line.split()[0]
    raise ValueError("Cannot identify actual fixed checkout HEAD")


def live_plan(root, argv, args):
    require(os.environ.get("RAG_PHASE11_AUTONOMY_CONTEXT"), "Rewrite smoke requires its live v3 supervisor")
    context = json.loads(os.environ["RAG_PHASE11_AUTONOMY_CONTEXT"])
    ledger_dir = Path(context["ledger_dir"]).resolve()
    canonical = git_paths(root)[1].parent / "data/runs/development_screening/phase11-autonomy-v3"
    require(ledger_dir == canonical.resolve(), "Use the canonical shared v3 ledger")
    ledger = read_json(ledger_dir / "ledger.json")
    rows = [r for r in ledger["runs"] if r["run_id"] == context["run_id"]]
    require(ledger["version"] == "phase11-autonomy-v3" and len(rows) == 1 and rows[0]["state"] == "running",
            "No unique running registered rewrite smoke")
    row = rows[0]
    plan = row["plan"]
    require(plan["version"] == "phase11-autonomy-v3" and plan["stage"] == "smoke" and
            plan["automatic_retries"] == 0 and plan["phase12_allowed"] is False,
            "Only a preregistered Phase11 v3 smoke may run")
    monitor = read_json(ledger_dir / row["run_id"] / "manifest.json")
    require(digest(plan) == row["plan_content_sha256"] and monitor["plan"] == plan and
            monitor["plan_sha256"] == row["plan_sha256"] and
            monitor["protocol_sha256"] == ledger["protocol_sha256"] == plan["protocol_sha256"],
            "Registered rewrite plan content changed")
    require(plan["command"] == [ENTRY, *argv] and Path(__file__).resolve() == root / ENTRY,
            "Run only the exact registered, published script and arguments")
    require(fixed_head(root) == plan["fixed_commit"], "Fixed checkout HEAD changed")
    for kind in ("supervisor", "child"):
        process = psutil.Process(row[kind + "_pid"])
        require(process.is_running() and process.status() != psutil.STATUS_ZOMBIE and
                process.create_time() == row[kind + "_create_time"], "Stale v3 process handle")
    require(row["child_pid"] == os.getpid() and os.getpgrp() == row["child_pid"], "Not the owned v3 child group")
    elapsed = (datetime.now(UTC) - datetime.fromisoformat(row["started_at_utc"])).total_seconds()
    budget = plan["budget"]
    require(0 <= elapsed < budget["maximum_wall_seconds"] and budget["maximum_wall_seconds"] == 1800 and
            budget["planned_calls"] == budget["maximum_calls"] == 2 and
            budget["request_timeout_seconds"] == 1200 and budget["maximum_tokens_per_call"] == 6144,
            "Finite two-rewrite budget/deadline differs")
    require(plan["monitor"] == {"method": "process_journal_resources", "interval_seconds": 5},
            "Use the preregistered five-second resource monitor")
    # Revalidate the full registered candidate/closure after authenticating the live owner.
    # This is the existing v3 validator, not a new permission or scientific gate.
    validate_plan(root, plan, root / "configs/phase11_autonomy_v3.json")
    bindings = {b["path"]: b for b in plan["bindings"]}
    for b in bindings.values():
        verify_binding(root, b)
    for path in (args.config, args.rewrite_plan):
        name = path.resolve().relative_to(root).as_posix()
        require(name in bindings, "Every config/rewrite-plan argument must be directly bound")
    require(ENTRY in bindings, "Bind the actual rewrite entry source")
    output = args.output_dir.resolve()
    require(output == root / plan["output_dir"] and output.is_relative_to(root / "data/runs/runtime_screening") and
            output != root / "data/runs/runtime_screening" and not output.exists(), "Use the registered fresh smoke output")
    return plan, bindings


def load_rewrite_inputs(root, plan, bindings, args):
    """Called only after the complete live registration/ownership check."""
    config, _, prompts, _ = load_config(args.config.resolve())
    require(config["candidate_identity_sha256"] == plan["candidate_identity_sha256"] and
            "semantic_evidence_reuse" not in config, "Run/current candidate differs")
    generation = task_config(config, "rewrite_answer")
    require(args.reasoning_budget_tokens in (1024, 2048, 4096) and
            generation.reasoning_budget_tokens == args.reasoning_budget_tokens and generation.max_output_tokens == 6144 and
            generation.context_tokens == 12288 and generation.timeout_seconds == 1200,
            "Rewrite registered reasoning/6144/12288/1200 contract differs")
    target = read_json(args.rewrite_plan.resolve())
    require(target["purpose"] == "phase11-synthetic-rewrite-smoke-v4" and target["maximum_calls"] == 2 and
            target["automatic_retries"] == 0 and target["phase12_allowed"] is False,
            "Wrong preregistered rewrite target contract")
    source_binding = target["source"]
    require(bindings.get(source_binding["path"]) == source_binding, "Directly bind the complete synthetic source/Expected file")
    source = read_json(verify_binding(root, source_binding))
    cases = source["cases"]
    require(len(cases) == 2 and {c["language"] for c in cases} == {"en", "ja"} and
            len({c["id"] for c in cases}) == 2 and target["targets"] == [c["id"] for c in cases] and
            plan["targets"] == ["rewrite/" + c["id"] for c in cases] and
            plan["target_counts"] == {"qa": 2, "fixed_units": 2, "conditions": 2},
            "Keep both complete synthetic inputs and their two initial fixed sentences")
    require(source["human_reviewed"] is False and source["phase12_allowed"] is False and
            all(c["scope"] == "synthetic_development" and set(c) == {"id", "language", "scope", *FIELDS, "offline_expected"}
                for c in cases), "Only the preregistered invented input set is allowed")
    for case in cases:
        require(len(case["documents"]) == 2 and isinstance(case["question"], str) and case["question"].strip(),
                "Keep both complete synthetic source passages and the original question")
        validate_documents(case["documents"])
        require(len(extract_sentence_units(case["answer"], language=case["language"])["claims"]) == 1,
                "Each complete original synthetic draft has one fixed sentence")
    return config, prompts, generation, target, cases


def run(args, argv):
    require(Path.cwd().resolve() == ROOT, "Run from the fixed checkout root")
    plan, bindings = live_plan(ROOT, argv, args)
    config, prompts, generation, target, cases = load_rewrite_inputs(ROOT, plan, bindings, args)
    output = args.output_dir.resolve()
    manifest = {"purpose": target["purpose"], "run_plan_sha256": digest(plan),
        "candidate_identity_sha256": plan["candidate_identity_sha256"], "config": config,
        "config_sha256": file_hash(args.config.resolve()), "rewrite_plan_sha256": file_hash(args.rewrite_plan.resolve()),
        "source": target["source"], "fixed_commit": plan["fixed_commit"], "targets": target["targets"],
        "source_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p)
            for p in [*sorted((ROOT / "src/rag_research").rglob("*.py")), Path(__file__).resolve()]},
        "expected_passed_to_inference": False, "semantic_adoption_claimed": False, "phase12_allowed": False}
    with run_lock(output):
        write_json(output / "manifest.json", manifest)
        tasks = []
        with LocalServer(generation, output / "server.log", **auxiliary_server_kwargs(config)) as server:
            for case in cases:
                # Gold/Expected remain offline: only these three original fields are passed.
                trace = {key: case[key] for key in FIELDS}
                task = rewrite_once(server.client, generation, prompts[case["language"]], trace,
                    output / (case["id"] + ".json"), {"manifest_sha256": digest(manifest), "case_id": case["id"]})
                tasks.append(task)
                print(json.dumps({"case_id": case["id"], "status": task["status"]}), flush=True)
                if task["status"] != "ok":
                    break
            write_json(output / "session.json", server.report())
        unknown = any(t["cost_incomplete"] for t in tasks)
        report = {"purpose": target["purpose"], "manifest_sha256": digest(manifest),
            "runtime_health_passed": len(tasks) == 2 and all(t["status"] == "ok" for t in tasks),
            "completion_attempts_recorded": sum(t["completion_attempted"] for t in tasks),
            "cost_incomplete": unknown, "observed_input_tokens": sum(t.get("input_tokens") or 0 for t in tasks),
            "observed_output_tokens": sum(t.get("output_tokens") or 0 for t in tasks),
            "total_output_tokens": None if unknown else sum(t.get("output_tokens") or 0 for t in tasks),
            "summed_task_seconds": sum(t["elapsed_seconds"] for t in tasks),
            "offline_quality_review_passed": None, "human_reviewed": False,
            "semantic_adoption_claimed": False, "gate11_passed": False, "phase12_allowed": False}
        write_json(output / "report.json", report)
    require(report["runtime_health_passed"], "Preserve failed/partial rewrites; never retry this run")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--rewrite-plan", type=Path, required=True)
    parser.add_argument("--reasoning-budget-tokens", type=int, choices=(1024, 2048, 4096), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args, sys.argv[1:])))


if __name__ == "__main__":
    main()
