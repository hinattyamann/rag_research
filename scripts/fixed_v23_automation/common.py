"""Bounded, local orchestration primitives. No model call is made by this module."""

import hashlib
import json
import os
import signal
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import psutil


def require(condition, message):
    if not condition:
        raise ValueError(message)


def now():
    return datetime.now(UTC).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def immutable(path, value):
    if Path(path).exists():
        require(read(path) == value, "Immutable workflow artifact changed: " + str(path))
    else:
        write(path, value)


def identity(pid):
    return {"pid": pid, "created": psutil.Process(pid).create_time()}


def alive(owner):
    try:
        proc = psutil.Process(owner["pid"])
        return proc.create_time() == owner["created"] and proc.status() != psutil.STATUS_ZOMBIE
    except (KeyError, psutil.Error):
        return False


def clean_env():
    # Never switch an unattended review to API-key billing.
    return {k: v for k, v in os.environ.items() if k not in {"OPENAI_API_KEY", "CODEX_API_KEY"}} | {
        "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false", "MPLBACKEND": "Agg"}


def load_config(path):
    config = read(path)
    checksum = Path(path).with_suffix(".sha256")
    if config.get("config_sha256_required"):
        require(checksum.is_file() and checksum.read_text().strip() == sha(path), "Workflow configuration changed")
    require(config["version"] == "fixed-v23-automation-v1" and config["phase12_allowed"] is False
            and config["api_billing_allowed"] is False, "Wrong automation authorization")
    for name, expected in config["sealed_files"].items():
        require(sha(name) == expected, "Frozen automation input changed: " + name)
    return config


def progress(config, stage, **counts):
    require(set(counts) <= {"cohort", "language", "kind", "completed_jobs", "total_jobs", "cli_invocations",
        "baseline_qa", "baseline_failed_qa", "completed_qa", "rewrite_failed_qa", "attempts",
        "failed", "unknown", "processed_qa", "remaining_qa", "codex_running", "phase", "error"},
        "Public progress must contain only allowlisted counters")
    write(Path(config["state_dir"]) / "progress.json", {"updated_at_utc": now(), "stage": stage, **counts})


def terminate_owned(process, owner):
    if process.poll() is None and alive(owner) and os.getpgid(process.pid) == process.pid:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            if alive(owner) and os.getpgid(process.pid) == process.pid:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)


def run_owned(argv, *, cwd, receipt, timeout, heartbeat=None, env=None):
    """An interrupted/failed invocation is durable and never silently resubmitted."""
    receipt = Path(receipt)
    if receipt.exists():
        saved = read(receipt)
        require(saved.get("exit_code") == 0, "Previous invocation failed or has unknown outcome: " + str(receipt))
        return saved
    receipt.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with receipt.with_suffix(".log").open("ab", buffering=0) as log:
        process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                   start_new_session=True, env=clean_env() if env is None else env)
        owner = identity(process.pid)
        saved = {"argv": list(map(str, argv)), "owner": owner, "started_at_utc": now(),
                 "exit_code": None, "timeout_seconds": timeout}
        write(receipt, saved)
        try:
            while process.poll() is None:
                require(time.monotonic() - started < timeout, "Finite subprocess deadline reached")
                if heartbeat:
                    heartbeat()
                time.sleep(.1 if timeout < 10 else 2)
            saved.update(exit_code=process.wait(), finished_at_utc=now(),
                         elapsed_seconds=time.monotonic() - started)
            write(receipt, saved)
            require(saved["exit_code"] == 0, "Subprocess failed; preserve receipt/log: " + str(receipt))
        finally:
            terminate_owned(process, owner)
    return saved


def cohort_run(config, cohort):
    require(cohort in {"main", "cal"}, "Unknown cohort")
    return Path(config[cohort + "_run"])
