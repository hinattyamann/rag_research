"""Supervise the single registered Phase11 validation with a shared conservative time cap."""

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.storage import read_json, run_lock, write_json  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402

NAMES = {"preflight": "data/runs/model_screening/phase11-binary-v10-preflight",
         "smoke": "data/runs/runtime_screening/phase11-binary-v10-smoke",
         "known": "data/runs/semantic_diagnostics/phase11-binary-v10-known"}


def run(stage):
    require(Path.cwd().resolve() == ROOT, "Run from the fixed checkout")
    require(not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip(),
            "Commit all code/configuration changes before Native execution")
    registration_path = ROOT / "data/manifests/phase11_review_development_preregistration_v1.json"
    registration = read_json(registration_path)
    for field in ("known_config", "candidate", "known_plan"):
        binding = registration[field]
        require(file_hash(ROOT / binding["path"]) == binding["sha256"], "Registered final candidate changed")
    ledger_root = ROOT / "data/runs/development_screening/phase11-review-budget-v1"
    with run_lock(ledger_root):
        ledger_path = ledger_root / "ledger.json"
        ledger = read_json(ledger_path) if ledger_path.exists() else {
            "purpose": "phase11-single-final-development-shared-budget",
            "registration_sha256": file_hash(registration_path), "stages": [],
            "fixed_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "previous_all9b_calls": 851, "previous_unknown": 2,
            "hard_call_ceiling": 188, "allocated_call_ceiling": 86, "hard_seconds_ceiling": 14400,
            "wall_time_conservatively_includes_non_native_overhead": True}
        require(ledger["registration_sha256"] == file_hash(registration_path) and
                ledger["fixed_commit"] == subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                "Keep the same registration and fixed commit across all three stages")
        require([s["stage"] for s in ledger["stages"]] == list(NAMES)[:list(NAMES).index(stage)] and
                all(s["status"] == "passed" for s in ledger["stages"]),
                "No retries, duplicate stages or expansion after a failure/unknown stage")
        remaining = ledger["hard_seconds_ceiling"] - sum(s["wall_seconds"] for s in ledger["stages"])
        require(remaining > 15, "Shared four-hour budget exhausted")
        config = registration["known_config"]["path"]
        if stage == "smoke":
            native = [sys.executable, str(ROOT / "scripts/run_review_runtime_smoke.py"), "--output-dir", NAMES[stage]]
        else:
            native = [sys.executable, str(ROOT / "scripts/observe_native_resources.py"), "--kind",
                "preflight" if stage == "preflight" else "semantic", "--config", config,
                "--output-dir", NAMES[stage], "--observations", "data/runs/resource_observation/phase11-binary-v10-" + stage]
        command = ["timeout", "--signal=TERM", "--kill-after=10s", f"{remaining - 15:.3f}s", *native]
        require(not (ROOT / NAMES[stage]).exists(), "Preserve all previous Native outputs")
        entry = {"stage": stage, "status": "started", "started_at_utc": datetime.now(UTC).isoformat(),
                 "remaining_seconds_before": remaining, "command": command}
        ledger["stages"].append(entry)
        write_json(ledger_path, ledger)
        started = time.perf_counter()
        with (ledger_root / (stage + ".stdout.log")).open("x") as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True, check=False)
        entry.update(wall_seconds=time.perf_counter() - started, returncode=result.returncode,
                     finished_at_utc=datetime.now(UTC).isoformat(), status="failed_or_unknown")
        report_path = ROOT / NAMES[stage] / "report.json"
        if result.returncode == 0 and report_path.is_file():
            report = read_json(report_path)
            passed = report.get({"preflight": "status", "smoke": "runtime_health_passed",
                                 "known": "diagnostic_gate_passed"}[stage])
            if passed is True or stage == "preflight" and passed == "passed":
                entry["status"] = "passed"
            entry["report_sha256"] = file_hash(report_path)
        ledger["wall_seconds_used"] = sum(s["wall_seconds"] for s in ledger["stages"])
        ledger["no_request_retry"] = True
        ledger["gate11_passed"] = ledger["phase12_allowed"] = False
        write_json(ledger_path, ledger)
        print(json.dumps({"stage": stage, "status": entry["status"], "wall_seconds_used": ledger["wall_seconds_used"]}), flush=True)
        return 0 if entry["status"] == "passed" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=NAMES)
    sys.exit(run(parser.parse_args().stage))
