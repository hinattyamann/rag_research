"""Wait for GPU headroom; retry only proved OOM at startup before any native request."""

import re
import subprocess
import time
import uuid
from pathlib import Path

from common import now, progress, read, require, sha, write


def raw_snapshot(folder):
    from rag_research.experiments.bilingual_budget import budget_snapshot

    value = budget_snapshot(folder)
    require(not value["unknown_or_interrupted_paths"], "Never retry an unknown native request")
    return {r["path"]: r["sha256"] for r in value["raw_calls"]}


def free_mib():
    value = subprocess.run(["nvidia-smi", "--id=0", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
        check=True, capture_output=True, text=True, timeout=5)
    return int(value.stdout.strip())


def wait_ready(config, language, phase, maximum_seconds, *, stage_receipt=None):
    policy = config["cal_gpu_policy"]
    required = policy["internal_min_free_mib"] if phase == "internal" else policy["baseline_min_free_mib"]
    receipt = Path(config["state_dir"]) / "cal-sessions" / ("resource-wait-" + uuid.uuid4().hex + ".json")
    started = time.monotonic()
    value = {"kind": "gpu_resource_wait", "language": language, "phase": phase,
             "stage_receipt": stage_receipt,
             "started_at_utc": now(), "elapsed_seconds": 0., "required_free_mib": required}
    stable = 0
    write(receipt, value)
    try:
        while True:
            require(not (Path(config["state_dir"]) / "stop.request").exists(), "Workflow stop requested")
            value.update(elapsed_seconds=time.monotonic() - started, available_free_mib=free_mib())
            write(receipt, value)
            stable = stable + 1 if value["available_free_mib"] >= required else 0
            if stable >= policy["stable_samples"]:
                return
            require(value["elapsed_seconds"] < min(maximum_seconds, policy["maximum_wait_seconds"]),
                    "GPU headroom wait exhausted; release GPU memory without changing inference conditions")
            if not stable:
                progress(config, "waiting_gpu", cohort="cal", language=language, phase=phase,
                    gpu_free_mib=value["available_free_mib"], gpu_required_mib=required, codex_running=False)
            remaining = min(maximum_seconds, policy["maximum_wait_seconds"]) - value["elapsed_seconds"]
            time.sleep(min(policy["poll_seconds"], remaining))
    finally:
        value.update(elapsed_seconds=time.monotonic() - started, finished_at_utc=now())
        write(receipt, value)


def archive_startup_oom(config, receipt, before, language, phase):
    """Never handle an in-flight/unknown, post-request, or non-OOM failure here."""
    run = Path(config["cal_run"])
    value = read(receipt)
    require(value.get("exit_code") == 1 and value.get("finished_at_utc"), "Only a finished startup failure is eligible")
    require(raw_snapshot(run / language) == before, "Native records changed; startup retry forbidden")
    text = receipt.with_suffix(".log").read_text()
    found = re.findall(r"Local server exited; see ([^\n]+)", text)
    require(found, "Failure was not a server startup exit")
    log = Path(found[-1]).resolve()
    require(log.parent == (run / language / phase).resolve() and re.fullmatch(r"server-\d+\.log", log.name),
            "Unexpected server log path")
    native_log = log.read_text()
    require("cudaMalloc failed: out of memory" in native_log and "exiting due to model loading error" in native_log,
            "Only explicit model-loading CUDA OOM is recoverable")
    ledger_path = run / "startup_recovery/ledger.json"
    ledger = read(ledger_path) if ledger_path.exists() else {"failures": []}
    require(not any(r["server_log"] == str(log.relative_to(run)) for r in ledger["failures"]), "Failure already archived")
    prior = sum(r["stage_receipt"] == receipt.name for r in ledger["failures"])
    require(prior < config["cal_gpu_policy"]["maximum_startup_failures"], "Finite startup retry limit exhausted")
    destination = receipt.with_name(receipt.stem + f".startup-failure-{prior + 1}.json")
    require(not destination.exists(), "Preserve previous startup receipt")
    old_hash = sha(receipt)
    receipt.rename(destination)
    receipt.with_suffix(".log").rename(destination.with_suffix(".log"))
    ledger["failures"].append({"language": language, "phase": phase, "stage_receipt": receipt.name,
        "archived_receipt": str(destination), "receipt_sha256": old_hash,
        "server_log": str(log.relative_to(run)), "server_log_sha256": sha(log),
        "recorded_at_utc": now(), "native_snapshot": before, "new_native_calls": 0,
        "elapsed_seconds": value["elapsed_seconds"], "reason": "cuda_oom_before_native_request"})
    write(ledger_path, ledger)
    return value["elapsed_seconds"]


def registered_failures(run, language, phase):
    path = Path(run) / "startup_recovery/ledger.json"
    rows = read(path)["failures"] if path.exists() else []
    selected = [r for r in rows if r["language"] == language and r["phase"] == phase]
    for row in selected:
        require(sha(Path(run) / row["server_log"]) == row["server_log_sha256"]
                and sha(row["archived_receipt"]) == row["receipt_sha256"] and row["new_native_calls"] == 0,
                "Registered startup failure changed")
        require(all(sha(Path(run) / language / name) == expected for name, expected in row["native_snapshot"].items()),
                "A native record preceding startup recovery changed")
    return selected
