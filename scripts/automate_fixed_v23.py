"""Prepare/start/inspect the fixed-v23 Main→Cal→figures workflow; no implicit AI launch."""

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts/fixed_v23_automation"))

from common import (  # noqa: E402
    alive,
    clean_env,
    identity,
    load_config,
    now,
    read,
    require,
    sha,
    write,
)

STATE = REPO / ".tools/fixed-v23-automation-v1"
CONFIG = STATE / "config.json"


def prepare():
    require(not CONFIG.exists(), "Preserve the existing workflow registration")
    checkout = REPO / ".tools/worktrees/fixed-v23-study-v1"
    require(checkout.exists(), "The original inference checkout is required")
    spec = importlib.util.spec_from_file_location("recovery_setup", checkout / "scripts/recover_fixed_v23_v2.py")
    recovery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recovery)
    recovery.validate(checkout / recovery.RUN, check_budget=False)
    codex = shutil.which("codex")
    require(codex, "Codex CLI is required")
    login = subprocess.run([codex, "-c", 'forced_login_method="chatgpt"', "login", "status"],
        capture_output=True, text=True, env=clean_env(), timeout=30)
    require(login.returncode == 0 and "Logged in using ChatGPT" in login.stdout + login.stderr,
            "Use saved ChatGPT authentication, never API-key billing")
    source = REPO / "scripts/fixed_v23_automation"
    destination = checkout / "scripts/fixed_v23_automation_v1"
    require(not destination.exists(), "Preserve the frozen controller source")
    destination.mkdir()
    files = {}
    for path in sorted(source.glob("*.py")):
        target = destination / path.name
        shutil.copy2(path, target)
        require(sha(path) == sha(target), "Frozen controller copy differs")
        files[str(target)] = sha(target)
    for path in [REPO / "pyproject.toml", REPO / "uv.lock", REPO / "docs/order_quality_rubric.md",
            REPO / "docs/phase11_statistical_plan.md", REPO / "docs/ai_quality_protocol.md",
            REPO / "data/manifests/phase11_bilingual_calibration_selection_v1.json",
            REPO / "configs/phase11_bilingual_calibration_selection_policy_v1.json",
            checkout / "fixed-v23-release.json", checkout / "fixed-v23-recovery-v2.json"]:
        files[str(path)] = sha(path)
    settings_path = Path.home() / ".codex/config.toml"
    settings = tomllib.loads(settings_path.read_text()) if settings_path.exists() else {}
    require(settings.get("model"), "Preserve the user's configured Codex model explicitly")
    config = {"version": "fixed-v23-automation-v1", "recorded_at_utc": now(), "repo": str(REPO),
        "checkout": str(checkout), "state_dir": str(STATE), "frozen_scripts": str(destination),
        "main_run": str(checkout / recovery.RUN),
        "cal_run": str(checkout / "data/runs/bilingual_calibration/fixed-v23-cal-v1"),
        "public_dir": str(REPO / "reports/fixed_v23_order_study_v1"),
        "public_status_json": "data/manifests/fixed_v23_automation_status_v1.json",
        "public_status_markdown": "docs/fixed_v23_automation_status.md",
        "uv": str(REPO / ".tools/bin/uv"), "codex": codex,
        "configured_codex_model": settings["model"],
        "configured_codex_reasoning_effort": settings.get("model_reasoning_effort", "high"),
        "poll_seconds": 30, "git_publish_interval_seconds": 3600,
        "annotation_cases_per_job": 4, "maximum_cli_invocations": 192,
        "maximum_format_repairs": 1, "maximum_cli_job_seconds": 2400,
        "deadline_utc": "2026-11-05T15:00:00+00:00", "sealed_files": files,
        "remote": "origin", "remote_url": subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=REPO, text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=REPO, text=True).strip(),
        "api_billing_allowed": False, "cal_launch_authorized": True, "phase12_allowed": False,
        "config_sha256_required": True,
        "scope": "existing Main completion, anonymous AI grading, analysis, fixed reserved Cal collection, grading, tables/figures/brief; no manuscript or submission"}
    require(config["branch"] == "main", "Use the verified main tracking branch")
    write(CONFIG, config)
    CONFIG.with_suffix(".sha256").write_text(sha(CONFIG) + "\n", encoding="utf-8")
    write(REPO / "data/manifests/fixed_v23_automation_setup_v1.json", {
        "version": config["version"], "recorded_at_utc": now(), "config_sha256": sha(CONFIG),
        "sealed_files": files, "main_run": config["main_run"], "cal_run": config["cal_run"],
        "scope": config["scope"], "cal_launch_authorized": True, "api_billing_allowed": False,
        "configured_codex_model": config["configured_codex_model"],
        "maximum_cli_invocations": 192, "maximum_format_repairs": 1, "maximum_cli_job_seconds": 2400,
        "deadline_utc": config["deadline_utc"], "git_publish_interval_seconds": 3600,
        "new_native_calls_at_setup": 0, "new_cli_model_calls_at_setup": 0,
        "all_execution_conditions_and_raw_preserved": True, "phase12_allowed": False})
    print(json.dumps({"prepared": True, "config": str(CONFIG), "new_model_calls": 0}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "start", "status", "stop"))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
        return
    config = load_config(CONFIG)
    if args.action == "status":
        owner = read(STATE / "owner.json") if (STATE / "owner.json").exists() else {}
        result = read(STATE / "status.json") if (STATE / "status.json").exists() else {"stage": "prepared"}
        result.update(service_alive=alive(owner),
            git=read(STATE / "git_publication.json") if (STATE / "git_publication.json").exists() else None)
    elif args.action == "stop":
        write(STATE / "stop.request", {"requested_at_utc": now(), "policy": "Cal stops at a new-QA boundary; Main collector is independent"})
        result = {"stop_requested": True}
    else:
        from rag_research.experiments.storage import run_lock

        with run_lock(STATE / "launch-lock"):
            owner = read(STATE / "owner.json") if (STATE / "owner.json").exists() else {}
            require(not alive(owner), "An automation service is already running")
            require(not (STATE / "stop.request").exists(), "Preserve explicit stop; inspect before resuming")
            with (STATE / "service.log").open("ab", buffering=0) as log:
                process = subprocess.Popen([config["uv"], "run", "--offline", "--frozen", "--project", str(REPO),
                    "python", str(Path(config["frozen_scripts"]) / "service.py"), "--config", str(CONFIG)],
                    cwd=REPO, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True,
                    env=clean_env() | {"UV_CACHE_DIR": str(REPO / ".tools/uv-cache")})
            owner = identity(process.pid)
            write(STATE / "owner.json", owner)
            result = {"started": True, "owner": owner, "status_command": "uv run python scripts/automate_fixed_v23.py status"}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.path.insert(0, str(REPO / "src"))
    main()
