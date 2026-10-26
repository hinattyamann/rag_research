"""Version 3 finite-run supervision; the historical guards and results stay immutable.

This layer records resource use and prevents resending a registered run. Passing a
process is deliberately not an adoption certificate. Scientific gates remain in
the experiment validators and are bound as hashed predecessor evidence.
"""

import json
import math
import os
import re
import signal
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import psutil
import yaml

from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.storage import read_json, run_lock, verify_checkpoint, write_json
from rag_research.retrieval.common import file_hash

VERSION = "phase11-autonomy-v3"
ADOPTION = "support-binary-v2"
COMPONENTS = {"model", "runtime", "prompt", "sampler", "schema", "core"}
STAGES = {"triage", "preflight", "smoke", "format", "semantic", "known", "main", "cal", "freeze"}
PREDECESSOR = {"main": "known", "cal": "main", "freeze": "cal"}
SCIENTIFIC_RULES = {
    "minimum_supported_recall": .9, "minimum_negative_specificity": .9,
    "minimum_unique_supported_units": 10, "minimum_unique_negative_units": 5,
    "minimum_supported_groups": 3, "minimum_negative_groups": 3,
    "threshold": .7, "automatic_retries": 0, "count_per_language": 20,
    "minimum_complete_comparable_qa_per_language": 10,
    "full_text_and_fixed_units": True, "same_order_total_trials": 5,
    "share_original_first_trial": True, "bare_refusal_policy": "rewrite_once",
    "seal_all_quality_and_expected_before_unblinding": True,
    "unknown_outcome": "preserve_and_stop_without_resending",
    "evaluation_outputs_for_tuning": False, "phase12_allowed": False,
}


def now():
    return datetime.now(UTC).isoformat()


def local(root, name):
    root = Path(root).resolve()
    path = (root / name).resolve()
    require(path.is_relative_to(root) and path != root, "Path escapes fixed checkout")
    return path


def verify_binding(root, binding):
    require(set(binding) == {"path", "sha256"}, "File binding needs path and SHA256")
    path = local(root, binding["path"])
    require(path.is_file() and file_hash(path) == binding["sha256"],
            f"Missing or changed bound file: {binding['path']}")
    return path


def load_protocol(root, path):
    protocol = read_json(Path(path))
    require(protocol["version"] == VERSION and protocol["semantic_adoption_version"] == ADOPTION,
            "Wrong autonomy or semantic version")
    require(protocol["scientific_rules"] == SCIENTIFIC_RULES, "Scientific criteria changed")
    require(protocol["global_call_ceiling"] is None and protocol["global_seconds_ceiling"] is None
            and protocol["global_candidate_ceiling"] is None, "No replacement arbitrary global cap")
    verify_binding(root, protocol["authorization"])
    old = read_json(verify_binding(root, protocol["legacy_result"]))
    require(old["cumulative_recorded_all9b_development_attempts"] == 909
            and old["cumulative_unknown_responses"] == 3 and old["known_regression_adopted"] is False,
            "Preserve the 909 attempts, three unknowns and rejected v10")
    require(protocol["legacy_attempts"] == 909 and protocol["legacy_unknown"] == 3,
            "Legacy counters changed")
    return protocol


def validate_chain_identity(*values, root):
    """Legacy chains remain legacy; a v3 chain must agree at every boundary."""
    keys = {"autonomy_protocol_version", "autonomy_protocol", "candidate_identity_sha256"}
    if not any(keys.intersection(value) for value in values):
        return None
    require(values and all(keys <= set(value) for value in values),
            "Mixed legacy/v3 or incomplete autonomy identity")
    identity = {key: values[0][key] for key in keys}
    require(identity["autonomy_protocol_version"] == VERSION
            and re.fullmatch(r"[0-9a-f]{64}", identity["candidate_identity_sha256"]),
            "Invalid v3 chain identity")
    require(all(all(value[key] == expected for key, expected in identity.items()) for value in values),
            "Known/Main/Cal/Freeze autonomy identity differs")
    protocol_path = verify_binding(root, identity["autonomy_protocol"])
    load_protocol(root, protocol_path)
    return identity


def _finite(value, *, positive=False):
    return (type(value) in {float, int} and math.isfinite(value)
            and (value > 0 if positive else value >= 0))


def validate_plan(root, plan, protocol_path):
    root = Path(root).resolve()
    protocol_path = Path(protocol_path).resolve()
    protocol = load_protocol(root, protocol_path)
    require(plan["version"] == VERSION and plan["semantic_adoption_version"] == ADOPTION
            and plan["protocol_sha256"] == file_hash(protocol_path), "Run protocol binding differs")
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]+", plan["run_id"]), "Invalid run ID")
    require(plan["stage"] in STAGES and plan["phase12_allowed"] is False,
            "Only Phase11 stages are permitted")
    require(re.fullmatch(r"[0-9a-f]{40}", plan["fixed_commit"]), "Full fixed commit required")
    for field in ("hypothesis", "change", "validation_scope", "stop_method", "resume_method"):
        require(isinstance(plan[field], str) and bool(plan[field].strip()), f"Missing {field}")
    targets = plan["targets"]
    require(isinstance(targets, list) and targets and len(targets) == len(set(targets))
            and all(isinstance(v, str) and v for v in targets), "Register all target IDs")
    counts = plan["target_counts"]
    require(set(counts) == {"qa", "fixed_units", "conditions"}
            and all(type(v) is int and v >= 0 for v in counts.values()), "Register full denominators")
    identity = plan["identity_files"]
    require(set(identity) == COMPONENTS and all(isinstance(v, list) and v for v in identity.values()),
            "Bind Model/Runtime/Prompt/Sampler/Schema/Core files")
    for bindings in identity.values():
        require(len({v["path"] for v in bindings}) == len(bindings), "Duplicate identity file")
        for binding in bindings:
            verify_binding(root, binding)
    identity_sha = digest({k: sorted(v, key=lambda b: b["path"]) for k, v in identity.items()})
    require(plan["candidate_identity_sha256"] == identity_sha, "Candidate identity digest differs")
    require(plan["bindings"], "Bind the executed config and implementation")
    bound = {b["path"]: b["sha256"] for b in plan["bindings"]}
    require(len(bound) == len(plan["bindings"]), "Duplicate input binding")
    for binding in plan["bindings"]:
        verify_binding(root, binding)
    budget = plan["budget"]
    require(type(budget["planned_calls"]) is int and budget["planned_calls"] >= 0
            and type(budget["maximum_calls"]) is int
            and budget["maximum_calls"] >= budget["planned_calls"], "Finite call budget required")
    for key in ("estimated_tokens", "estimated_native_seconds"):
        require(_finite(budget[key]), f"Register finite {key}")
    for key in ("maximum_wall_seconds", "request_timeout_seconds", "maximum_tokens_per_call"):
        require(_finite(budget[key], positive=True), f"Register finite {key}")
    require(budget["maximum_wall_seconds"] > budget["request_timeout_seconds"],
            "Leave time for request timeout and shutdown")
    allowed_timeouts = budget.get("allowed_request_timeout_seconds", [budget["request_timeout_seconds"]])
    require(isinstance(allowed_timeouts, list) and allowed_timeouts
            and all(_finite(v, positive=True) and v <= budget["request_timeout_seconds"] for v in allowed_timeouts),
            "Register finite per-task timeout values no greater than the Run maximum")
    monitor = plan["monitor"]
    require(_finite(monitor["interval_seconds"], positive=True)
            and 1 <= monitor["interval_seconds"] <= 60 and monitor["method"] == "process_journal_resources",
            "Monitor process, journals and resources every 1–60 seconds")
    require(plan["automatic_retries"] == 0, "No request or process automatic retries")
    output = local(root, plan["output_dir"])
    require(output.is_relative_to(root / "data/runs") and output != root / "data/runs",
            "New output must be under data/runs")
    script = local(root, plan["command"][0])
    require(script.is_relative_to(root / "scripts") and script.suffix == ".py"
            and plan["command"][0] in bound, "Run only a hashed repository Python entrypoint")
    require(all(isinstance(v, str) for v in plan["command"]), "Command must be an argv list")
    require("--output-dir" in plan["command"] and
            local(root, plan["command"][plan["command"].index("--output-dir") + 1]) == output,
            "Command output must match the registered fresh directory")
    configs = []
    for flag in ("--config", "--config-ja"):
        if flag not in plan["command"]:
            continue
        config_name = plan["command"][plan["command"].index(flag) + 1]
        require(config_name in bound, "Every executed language config must be bound")
        config = yaml.safe_load(local(root, config_name).read_text("utf-8"))
        configs.append(config)
        runtime = config.get("auxiliary_runtime", config.get("generation", {}))
        require(runtime.get("timeout_seconds") in allowed_timeouts,
                "Registered request timeout must equal executed runtime config")
        require(config.get("errors", {}).get("automatic_retries", 0) == 0, "Retries forbidden")
        if config.get("autonomy_protocol_version") is not None:
            chain = validate_chain_identity(config, root=root)
            require(chain["candidate_identity_sha256"] == identity_sha,
                    "Executed config candidate differs from registered Run")
        if config.get("baseline_config"):
            name = config["baseline_config"]
            require(name in bound, "Baseline config must also be bound")
            baseline = yaml.safe_load(local(root, name).read_text("utf-8"))
            require(baseline["generation"]["timeout_seconds"] in allowed_timeouts,
                    "Register the baseline task timeout before collection")
    if configs and plan["stage"] in {"preflight", "semantic", "known"} and configs[0].get("diagnostics"):
        name = configs[0]["diagnostics"]
        require(name in bound, "Bind the complete executed diagnostic target plan")
        actual_plan = read_json(local(root, name))
        cases = actual_plan["cases"]
        actual_targets = [case["id"] + "/" + order for case in cases for order in actual_plan["orders"]]
        require(set(targets) == set(actual_targets) and counts == {
            "qa": len(cases), "fixed_units": sum(len(c["claims"]) for c in cases),
            "conditions": len(actual_targets)}, "Registered diagnostic targets/denominators differ")
        require(plan["stage"] == "preflight" or budget["planned_calls"] == actual_plan["max_completion_attempts"],
                "Register every planned diagnostic call")
    if plan["stage"] in {"main", "cal"}:
        require(len(configs) == 2 and {c.get("language") for c in configs} == {"en", "ja"},
                "Register and bind both language configs before collection")
        actual_targets = [c["language"] + "/" + identifier for c in configs for identifier in c["data"]["record_ids"]]
        require(all(len(c["data"]["record_ids"]) == 20 for c in configs)
                and set(targets) == set(actual_targets) and counts["qa"] == 40,
                "Main/Cal must retain both complete twenty-QA selections")
    if "--target-plan" in plan["command"]:
        name = plan["command"][plan["command"].index("--target-plan") + 1]
        require(name in bound, "Bind every executed target-plan argument")
        actual_plan = read_json(local(root, name))
        actual_targets = ["/".join(t[k] for k in ("case_id", "order", "claim_id")) for t in actual_plan["targets"]]
        require(set(targets) == set(actual_targets), "Registered smoke targets differ from executed targets")
    if plan["stage"] in {"preflight", "freeze", "triage"}:
        require(budget["maximum_calls"] == 0, "This stage must generate zero completions")
    if plan["stage"] == "known":
        require(counts == {"qa": 15, "fixed_units": 42, "conditions": 30}
                and budget["planned_calls"] == budget["maximum_calls"] == 84,
                "Fresh known regression must preserve all 15/42/30/84")
    if plan["stage"] in PREDECESSOR:
        predecessor = plan["predecessor"]
        certificate = read_json(verify_binding(root, predecessor))
        require(certificate["version"] == VERSION and certificate["semantic_adoption_version"] == ADOPTION
                and certificate["protocol_sha256"] == file_hash(protocol_path)
                and certificate["candidate_identity_sha256"] == identity_sha
                and certificate["stage"] == PREDECESSOR[plan["stage"]]
                and certificate["scientific_gate_passed"] is True,
                "Missing passing same-version/same-candidate predecessor certificate")
        for binding in certificate["evidence"]:
            verify_binding(root, binding)
    return protocol


def condition_fingerprint(plan):
    """Renaming output, run, commit or budget cannot permit the same resampling."""
    # These are complete mandatory batteries, each run once per fixed candidate.
    targets = [] if plan["stage"] in {"known", "semantic", "format"} else sorted(plan["targets"])
    return digest({"stage": plan["stage"], "candidate_identity_sha256": plan["candidate_identity_sha256"],
                   "targets": targets})


def journal_snapshot(output):
    """Count atomic completion journals, not claimwise aggregates or copied reports."""
    rows, invalid, unsent_errors = [], [], []
    for path in sorted(Path(output).rglob("*.json")):
        try:
            task = read_json(path)
        except (ValueError, OSError) as error:
            invalid.append({"path": str(path), "error": str(error)})
            continue
        if not isinstance(task, dict) or not ("completion_attempted" in task and "request_sha256" in task):
            continue
        if task.get("execution_mode") in {"claimwise-v1", "source-reading-v1"}:
            continue
        status = task.get("status")
        if status != "started":
            try:
                verify_checkpoint(task)
            except ValueError as error:
                invalid.append({"path": str(path), "error": str(error)})
        if task["completion_attempted"] is False:
            if status == "error":
                unsent_errors.append(path.relative_to(output).as_posix())
            continue
        require(task["completion_attempted"] is True, "Invalid completion attempt flag")
        unknown = (status == "started" or bool(task.get("cost_incomplete"))
                   or task.get("error_code") == "interrupted_unknown_outcome")
        rows.append({"path": path.relative_to(output).as_posix(), "sha256": file_hash(path),
                     "status": status, "unknown": unknown,
                     "prompt_sha256": digest(task["prompt_tokens"]) if isinstance(task.get("prompt_tokens"), list) else None,
                     "input_tokens": task.get("input_tokens"), "output_tokens": task.get("output_tokens"),
                     "elapsed_seconds": task.get("elapsed_seconds")})
    return {"attempts": len(rows), "successful": sum(r["status"] == "ok" and not r["unknown"] for r in rows),
            "failed": sum(r["status"] != "ok" and not r["unknown"] for r in rows),
            "unknown": sum(r["unknown"] for r in rows),
            "observed_input_tokens": sum(r["input_tokens"] or 0 for r in rows),
            "observed_output_tokens": sum(r["output_tokens"] or 0 for r in rows),
            "total_output_tokens": (sum(r["output_tokens"] for r in rows)
                                    if all(r["output_tokens"] is not None and not r["unknown"] for r in rows) else None),
            "known_task_seconds": sum(r["elapsed_seconds"] or 0 for r in rows),
            "cost_incomplete": any(r["unknown"] or r["output_tokens"] is None for r in rows),
            "unsent_errors": unsent_errors, "invalid_journals": invalid, "raw_calls": rows}


def run_snapshot(output, ledger_dir, run_id):
    tasks = journal_snapshot(output)
    native = native_snapshot(ledger_dir, run_id)
    # A Native reservation is the submission authority. Task journals can mark an
    # attempt just before the guard declines it, and baseline records differ.
    available = Counter(c["prompt_sha256"] for c in native["calls"] if c["state"] == "returned")
    validated_success = validated_failure = 0
    for task in tasks["raw_calls"]:
        key = task["prompt_sha256"]
        if key is None or task["unknown"] or available[key] == 0:
            continue
        available[key] -= 1
        validated_success += task["status"] == "ok"
        validated_failure += task["status"] != "ok"
    tasks.update(attempts=native["attempts"], successful=validated_success,
                 failed=validated_failure, unknown=native["unknown"],
                 unvalidated_returned=native["returned"] - validated_success - validated_failure,
                 native_reservations=native, task_failures=tasks["failed"],
                 observed_input_tokens=native["observed_input_tokens"],
                 known_native_seconds=native["observed_native_seconds"],
                 observed_output_tokens=native["observed_output_tokens"],
                 total_output_tokens=native["total_output_tokens"],
                 cost_incomplete=tasks["cost_incomplete"] or native["cost_incomplete"])
    return tasks


def initial_ledger(protocol_path, protocol):
    return {"version": VERSION, "protocol_sha256": file_hash(protocol_path),
            "legacy_result": protocol["legacy_result"], "legacy_attempts": 909, "legacy_unknown": 3,
            "legacy_unused_calls_not_reallocated": True, "runs": [], "phase12_allowed": False}


def totals(ledger):
    snapshots = [r["snapshot"] for r in ledger["runs"] if "snapshot" in r]
    summed = {key: sum(s[key] for s in snapshots) for key in (
        "attempts", "successful", "failed", "unknown", "observed_input_tokens", "observed_output_tokens",
        "known_task_seconds", "known_native_seconds", "task_failures", "unvalidated_returned")}
    summed.update(cumulative_attempts=ledger["legacy_attempts"] + summed["attempts"],
                  cumulative_unknown=ledger["legacy_unknown"] + summed["unknown"],
                  new_wall_seconds=sum(r.get("wall_seconds", 0) for r in ledger["runs"]),
                  cost_incomplete=any(s["cost_incomplete"] for s in snapshots),
                  external_paid_api_calls=0,
                  electricity_cost_currency=None,
                  legacy_success_failure_and_cost_not_reconstructed=True)
    return summed


def register(root, protocol_path, plan_path, ledger_dir):
    """Freeze a plan in the persistent ledger before creating the Native output."""
    plan_path, protocol_path, ledger_dir = map(Path, (plan_path, protocol_path, ledger_dir))
    plan = read_json(plan_path)
    protocol = validate_plan(root, plan, protocol_path)
    require(not local(root, plan["output_dir"]).exists(), "Preserve existing Native output")
    with run_lock(ledger_dir):
        ledger_path = ledger_dir / "ledger.json"
        ledger = read_json(ledger_path) if ledger_path.exists() else initial_ledger(protocol_path, protocol)
        require(ledger["protocol_sha256"] == file_hash(protocol_path), "Keep one cumulative v3 ledger")
        require(not any(r["state"] == "running" for r in ledger["runs"]),
                "Audit existing handle before registering another run")
        fingerprint = condition_fingerprint(plan)
        require(not any(r["run_id"] == plan["run_id"] or r["condition_sha256"] == fingerprint
                        for r in ledger["runs"]), "No duplicate run or unchanged-condition resampling")
        record = {"run_id": plan["run_id"], "state": "registered", "registered_at_utc": now(),
                  "plan_sha256": file_hash(plan_path), "plan_content_sha256": digest(plan), "plan": plan,
                  "condition_sha256": fingerprint}
        ledger["runs"].append(record)
        ledger["totals"] = totals(ledger)
        write_json(ledger_path, ledger)
    return record


def _fixed_checkout(root, expected):
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip() == expected,
            "Execute from the registered fixed commit")
    require(not subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip(),
            "Commit code/configuration before Native execution")


def _resource_sample(pid):
    sample = {"at_utc": now(), "available_memory_bytes": psutil.virtual_memory().available,
              "processes": [], "gpu": None, "errors": []}
    try:
        parent = psutil.Process(pid)
        for process in [parent, *parent.children(recursive=True)]:
            try:
                sample["processes"].append({"pid": process.pid, "create_time": process.create_time(),
                                            "rss_bytes": process.memory_info().rss})
            except psutil.Error:
                pass
    except psutil.Error as error:
        sample["errors"].append(str(error))
    try:
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=uuid,memory.used,memory.total,utilization.gpu",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True,
                             timeout=5, check=False)
        sample["gpu"] = gpu.stdout.strip() if gpu.returncode == 0 else None
        if gpu.returncode:
            sample["errors"].append(gpu.stderr.strip())
    except (OSError, subprocess.TimeoutExpired) as error:
        sample["errors"].append(str(error))
    return sample


def _terminate_owned_group(child):
    """The child was created in a fresh session; never signal unrelated processes."""
    if child.poll() is not None:
        return
    os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait(timeout=10)


def execute(root, protocol_path, ledger_dir, run_id):
    """Supervise exactly one pre-registered run, retaining unknown work on interruption."""
    root, protocol_path, ledger_dir = map(lambda p: Path(p).resolve(), (root, protocol_path, ledger_dir))
    with run_lock(ledger_dir):
        ledger_path = ledger_dir / "ledger.json"
        ledger = read_json(ledger_path)
        record = next(r for r in ledger["runs"] if r["run_id"] == run_id)
        require(record["state"] == "registered", "Never relaunch a started/finished run")
        require(not any(r["state"] == "running" for r in ledger["runs"]), "Another handle is active")
        plan = record["plan"]
        require(digest(plan) == record["plan_content_sha256"], "Registered plan content changed")
        validate_plan(root, plan, protocol_path)
        _fixed_checkout(root, plan["fixed_commit"])
        output = local(root, plan["output_dir"])
        require(not output.exists(), "Never resume or overwrite Native requests")
        monitor = ledger_dir / run_id
        monitor.mkdir(exist_ok=False)
        write_json(monitor / "manifest.json", {"version": VERSION,
                   "protocol_sha256": ledger["protocol_sha256"], "plan": plan,
                   "plan_sha256": record["plan_sha256"], "phase12_allowed": False})
        record.update(state="running", started_at_utc=now(), supervisor_pid=os.getpid(),
                      supervisor_create_time=psutil.Process().create_time())
        write_json(ledger_path, ledger)
        started, child, reason, result = time.monotonic(), None, None, None
        try:
            with (monitor / "stdout.log").open("x") as stdout, (monitor / "monitor.jsonl").open("x") as samples:
                environment = dict(os.environ)
                environment[CONTEXT_ENV] = json.dumps({"ledger_dir": str(ledger_dir), "run_id": run_id})
                child = subprocess.Popen([sys.executable, *plan["command"]], cwd=root,
                                         stdout=stdout, stderr=subprocess.STDOUT, start_new_session=True,
                                         env=environment)
                record.update(child_pid=child.pid, child_create_time=psutil.Process(child.pid).create_time())
                write_json(ledger_path, ledger)
                while True:
                    snapshot = run_snapshot(output, ledger_dir, run_id)
                    sample = {**_resource_sample(child.pid), "snapshot": snapshot}
                    samples.write(json.dumps(sample, ensure_ascii=False) + "\n")
                    samples.flush()
                    record.update(last_monitor_at_utc=sample["at_utc"], snapshot=snapshot,
                                  wall_seconds=time.monotonic() - started)
                    ledger["totals"] = totals(ledger)
                    write_json(ledger_path, ledger)
                    result = child.poll()
                    if result is not None:
                        break
                    if snapshot["task_failures"] or snapshot["unsent_errors"] or snapshot["invalid_journals"]:
                        reason = "task_or_journal_error"
                    # A started journal is an in-flight request, not yet a timeout. The
                    # bound runtime enforces per-request timeout; only terminal unknowns stop here.
                    if snapshot["native_reservations"]["terminal_unknown"]:
                        reason = "terminal_unknown_outcome"
                    if snapshot["attempts"] > plan["budget"]["maximum_calls"]:
                        reason = "call_budget_violation"
                    if time.monotonic() - started >= plan["budget"]["maximum_wall_seconds"]:
                        reason = "finite_run_wall_timeout"
                    if reason:
                        _terminate_owned_group(child)
                        result = child.returncode
                        break
                    time.sleep(plan["monitor"]["interval_seconds"])
        except BaseException as error:
            reason = f"supervisor_interrupted:{type(error).__name__}:{error}"
            if child is not None:
                _terminate_owned_group(child)
                result = child.returncode
            raise
        finally:
            snapshot = run_snapshot(output, ledger_dir, run_id)
            passed = (result == 0 and reason is None and not snapshot["unknown"]
                      and not snapshot["task_failures"] and not snapshot["unsent_errors"]
                      and not snapshot["invalid_journals"]
                      and snapshot["attempts"] <= plan["budget"]["maximum_calls"])
            record.update(state="process_completed" if passed else "failed_or_unknown",
                          finished_at_utc=now(), returncode=result, stop_reason=reason,
                          wall_seconds=time.monotonic() - started, snapshot=snapshot,
                          scientific_gate_passed_not_asserted=True)
            ledger["totals"] = totals(ledger)
            write_json(ledger_path, ledger)
        return record


def inspect_handle(ledger_dir):
    """Read-only recovery audit: PID reuse is checked with process create time."""
    ledger = read_json(Path(ledger_dir) / "ledger.json")
    handles = []
    for run in ledger["runs"]:
        if run["state"] != "running":
            continue
        row = {"run_id": run["run_id"], "last_monitor_at_utc": run.get("last_monitor_at_utc")}
        for kind in ("supervisor", "child"):
            pid, created = run.get(kind + "_pid"), run.get(kind + "_create_time")
            try:
                row[kind + "_alive"] = pid is not None and psutil.Process(pid).create_time() == created
            except psutil.Error:
                row[kind + "_alive"] = False
        handles.append(row)
    return {"handles": handles, "totals": totals(ledger), "requests_resent": False}


def seal_stopped_run(root, ledger_dir, run_id, reason):
    """Recover the ledger after a dead supervisor without relaunching any request."""
    require(isinstance(reason, str) and reason.strip(), "Record the interruption evidence/reason")
    ledger_dir = Path(ledger_dir)
    with run_lock(ledger_dir):
        ledger_path = ledger_dir / "ledger.json"
        ledger = read_json(ledger_path)
        record = next(r for r in ledger["runs"] if r["run_id"] == run_id)
        require(record["state"] == "running", "Only an abandoned running handle can be sealed")
        handle = next(h for h in inspect_handle(ledger_dir)["handles"] if h["run_id"] == run_id)
        require(not handle["supervisor_alive"] and not handle["child_alive"],
                "Do not seal while the registered supervisor or child is alive")
        group = record.get("child_pid")
        for process in psutil.process_iter(["pid"]):
            try:
                require(group is None or os.getpgid(process.pid) != group,
                        "Owned process group still exists; preserve and inspect it")
            except ProcessLookupError:
                continue
        record.update(state="failed_or_unknown", finished_at_utc=now(),
                      stop_reason="abandoned_supervisor:" + reason, returncode=None,
                      snapshot=run_snapshot(local(root, record["plan"]["output_dir"]), ledger_dir, run_id),
                      wall_seconds=(datetime.now(UTC) - datetime.fromisoformat(record["started_at_utc"])).total_seconds(),
                      wall_seconds_is_conservative_upper_bound_including_downtime=True,
                      requests_resent=False, scientific_gate_passed_not_asserted=True)
        ledger["totals"] = totals(ledger)
        write_json(ledger_path, ledger)
    return record


CONTEXT_ENV = "RAG_PHASE11_AUTONOMY_CONTEXT"


def begin_native_call(route, payload, timeout):
    """Durably reserve one completion *before* HTTP submission; old clients are unchanged."""
    context = os.environ.get(CONTEXT_ENV)
    if route != "/completion" or context is None:
        return None
    context = json.loads(context)
    ledger_dir = Path(context["ledger_dir"])
    ledger = read_json(ledger_dir / "ledger.json")
    require(ledger["version"] == VERSION, "Native call requires v3 cumulative ledger")
    run = next(r for r in ledger["runs"] if r["run_id"] == context["run_id"])
    require(run["state"] == "running", "Native calls require a live registered run")
    plan = run["plan"]
    require(plan["version"] == VERSION and plan["automatic_retries"] == 0
            and plan["protocol_sha256"] == ledger["protocol_sha256"], "Native run identity changed")
    require(digest(plan) == run["plan_content_sha256"], "Native registered plan changed")
    require(timeout in plan["budget"].get("allowed_request_timeout_seconds",
                                          [plan["budget"]["request_timeout_seconds"]]),
            "Native timeout differs from preregistered task values")
    require(type(payload.get("n_predict")) is int and
            0 < payload["n_predict"] <= plan["budget"]["maximum_tokens_per_call"],
            "Native output reservation exceeds registered maximum")
    require((datetime.now(UTC) - datetime.fromisoformat(run["started_at_utc"])).total_seconds()
            < plan["budget"]["maximum_wall_seconds"], "Finite run deadline reached")
    guard_dir = ledger_dir / plan["run_id"] / "native_guard"
    with run_lock(guard_dir):
        path = guard_dir / "calls.json"
        guard = read_json(path) if path.exists() else {"version": VERSION,
            "run_id": plan["run_id"], "plan_sha256": run["plan_sha256"], "calls": []}
        require(guard["plan_sha256"] == run["plan_sha256"], "Native reservation plan changed")
        require(all(c["state"] == "returned" for c in guard["calls"]),
                "Never resend or continue after an in-flight/unknown/failed native call")
        require(len(guard["calls"]) < plan["budget"]["maximum_calls"],
                "Finite completion budget exhausted before HTTP submission")
        ticket = {"sequence": len(guard["calls"]) + 1, "state": "started",
                  "started_at_utc": now(), "payload_sha256": digest(payload),
                  "prompt_sha256": digest(payload.get("prompt")),
                  "input_tokens": len(payload["prompt"]) if isinstance(payload.get("prompt"), list) else None,
                  "requested_output_tokens": payload["n_predict"],
                  "timeout_seconds": timeout, "caller_pid": os.getpid(),
                  "output_tokens": None, "native_response_sha256": None}
        guard["calls"].append(ticket)
        write_json(path, guard)
    return {"guard_dir": str(guard_dir), "sequence": ticket["sequence"],
            "payload_sha256": ticket["payload_sha256"]}


def finish_native_call(ticket, *, response=None, error=None):
    if ticket is None:
        return
    guard_dir = Path(ticket["guard_dir"])
    with run_lock(guard_dir):
        path = guard_dir / "calls.json"
        guard = read_json(path)
        row = guard["calls"][ticket["sequence"] - 1]
        require(row["state"] == "started" and row["payload_sha256"] == ticket["payload_sha256"],
                "Native completion reservation changed")
        row.update(state="unknown" if error is not None else "returned", finished_at_utc=now(),
                   error=error, native_response_sha256=digest(response) if response is not None else None,
                   output_tokens=(len(response["tokens"]) if isinstance(response, dict)
                                  and isinstance(response.get("tokens"), list) else None))
        row["elapsed_seconds"] = (datetime.fromisoformat(row["finished_at_utc"])
                                  - datetime.fromisoformat(row["started_at_utc"])).total_seconds()
        write_json(path, guard)


def native_snapshot(ledger_dir, run_id):
    """The pre-submit reservation also covers baseline calls without task request hashes."""
    path = Path(ledger_dir) / run_id / "native_guard/calls.json"
    calls = read_json(path)["calls"] if path.exists() else []
    return {"attempts": len(calls), "returned": sum(c["state"] == "returned" for c in calls),
            "unknown": sum(c["state"] != "returned" for c in calls),
            "terminal_unknown": sum(c["state"] == "unknown" for c in calls),
            "observed_input_tokens": sum(c["input_tokens"] or 0 for c in calls),
            "observed_native_seconds": sum(c.get("elapsed_seconds", 0) for c in calls),
            "observed_output_tokens": sum(c["output_tokens"] or 0 for c in calls),
            "total_output_tokens": (sum(c["output_tokens"] for c in calls) if
                                    all(c["state"] == "returned" and c["output_tokens"] is not None
                                        for c in calls) else None),
            "cost_incomplete": any(c["state"] != "returned" or c["output_tokens"] is None for c in calls),
            "calls": calls}
