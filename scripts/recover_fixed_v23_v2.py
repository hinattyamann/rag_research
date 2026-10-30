"""Resume fixed-v23 with baseline/rewrite length failures retained, never retried.

This control-only entry is deployed outside src. The original sealed inference
sources, language manifests, successful requests and failed response stay intact.
"""

import argparse
import gc
import json
import math
import os
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments import bilingual_runner as runner  # noqa: E402
from rag_research.experiments import fixed_v23_control as legacy  # noqa: E402
from rag_research.experiments.bilingual_budget import (  # noqa: E402
    DevelopmentStop,
    budget_snapshot,
    pending_trace_calls,
)
from rag_research.experiments.fixed_v23 import bound, verify_release  # noqa: E402
from rag_research.experiments.frozen_trace import digest, require  # noqa: E402
from rag_research.experiments.storage import (  # noqa: E402
    checkpoint,
    next_session,
    read_json,
    run_lock,
    verify_checkpoint,
    write_json,
)
from rag_research.retrieval.common import file_hash, json_bytes  # noqa: E402

VERSION = "fixed-v23-answer-length-recovery-v2"
REGISTRATION = "fixed-v23-recovery-v2.json"
PARENT_REGISTRATION = "fixed-v23-recovery-v1.json"
RUN = "data/runs/bilingual_development/fixed-v23-main-v1"
ORIGINAL_PUBLIC = legacy.public_state


def terminal_limit(value):
    """Accept only a received, checkpointed 512-token baseline length failure."""
    raw = value.get("runtime_response") or {}
    settings = raw.get("generation_settings") or {}
    return (value.get("status") == "error" and value.get("completion_attempted") is True
        and value.get("cost_incomplete") is False and value.get("finish_reason") == "limit"
        and value.get("error") == "Output token limit reached; answer may be incomplete"
        and type(value.get("input_tokens")) is int and 0 < value["input_tokens"] <= 3584
        and value.get("output_tokens") == 512 and raw.get("stop_type") == "limit"
        and raw.get("truncated") is False and len(raw.get("tokens", [])) == 512
        and raw.get("tokens_predicted") == 512 and settings.get("n_predict") == 512
        and settings.get("temperature") == 0. and settings.get("seed") == 42)


def rewrite_limit(value):
    """Only the received, naturally ended rewrite's final-512-token validation error."""
    raw = value.get("runtime_response") or {}
    settings = raw.get("generation_settings") or {}
    predicted = raw.get("tokens_predicted")
    final = value.get("final_answer_tokens")
    return (value.get("task") == "rewrite_answer" and value.get("status") == "error"
        and value.get("completion_attempted") is True and value.get("cost_incomplete") is False
        and value.get("error_code") == "invalid_output"
        and value.get("error") == "Final answer exceeds 512-token candidate budget"
        and type(final) is int and final > 512
        and type(value.get("input_tokens")) is int and 0 < value["input_tokens"] <= 6144
        and type(predicted) is int and 0 < predicted <= 6144
        and value.get("output_tokens") == predicted and len(raw.get("tokens", [])) == predicted
        and raw.get("stop_type") in {"eos", "word"} and raw.get("truncated") is False
        and settings.get("n_predict") == 6144
        and type(settings.get("temperature")) in {float, int}
        and math.isclose(settings["temperature"], .2, rel_tol=1e-6, abs_tol=1e-8)
        and settings.get("seed") == 42)


def reserve(output, ceiling, needed=0):
    snapshot = budget_snapshot(output)
    require(not snapshot["unknown_or_interrupted_paths"], "Unknown/in-flight outcome blocks recovery")
    for name in snapshot["error_paths"]:
        parts = Path(name).parts
        value = read_json(output / name)
        require((len(parts) == 3 and parts[0] == "baseline" and parts[-1] == "record.json"
                 and terminal_limit(value)) or
                (len(parts) == 3 and parts[0] == "internal" and parts[-1] == "rewrite.json"
                 and rewrite_limit(value)),
                "Only confirmed baseline/rewrite answer length failures may remain missing")
    if snapshot["recorded_native_attempts_upper_bound"] + needed > ceiling:
        raise DevelopmentStop("preregistered_call_budget_exhausted", snapshot)
    return snapshot


def protected_files(output):
    """Seal all old scientific records; mutable supervisory state is kept in a snapshot."""
    result = {}
    for language in ("en", "ja"):
        for path in (output / language).rglob("*"):
            if path.is_file() and path.name not in {"progress.json", ".run.lock"}:
                result[path.relative_to(output).as_posix()] = file_hash(path)
    return result


def validate(output, *, check_budget=True):
    output, study = legacy.collection(output)
    registration = read_json(ROOT / REGISTRATION)
    require(registration["version"] == VERSION and registration["output_dir"] == RUN
            and registration["new_native_calls_at_preparation"] == 0
            and registration["original_release_sha256"] == file_hash(ROOT / "fixed-v23-release.json")
            and registration["maximum_calls_per_language"] == 1660
            and registration["baseline_output_limit_is_missing"] is True
            and registration["rewrite_output_limit_is_missing"] is True
            and registration["rewrite_failure_action"] == "keep_initial_answer_with_rewrite_failed_status"
            and registration["automatic_retries"] == 0 and registration["phase12_allowed"] is False,
            "Recovery registration changed")
    bound(ROOT, registration["entrypoint"])
    bound(ROOT, registration["wrapper"])
    parent = read_json(bound(ROOT, registration["parent_registration"]))
    require(registration["parent_registration"]["path"] == PARENT_REGISTRATION
            and parent["version"] == "fixed-v23-terminal-baseline-recovery-v1",
            "Preserve the baseline recovery protocol")
    bound(ROOT, parent["entrypoint"])
    bound(ROOT, parent["wrapper"])
    for name, sha in registration["protected_original_files"].items():
        require(file_hash(output / name) == sha, "A preserved original result changed: " + name)
    if check_budget:
        for language in ("en", "ja"):
            reserve(output / language, 1660)
    return output, study, registration


def command(output, action):
    return shlex.join([str(ROOT / "fixed-v23-recover-v2.sh"), action, "--run", str(output)])


def missing_count(output):
    return sum(terminal_limit(read_json(path)) for lang in ("en", "ja")
               for path in (output / lang / "baseline").glob("*/record.json"))


def rewrite_missing_count(output):
    count = 0
    for language in ("en", "ja"):
        for path in (output / language / "internal").glob("*/rewrite.json"):
            task = read_json(path)
            verify_checkpoint(task)
            summary = path.parent / "summary.json"
            if rewrite_limit(task) and summary.exists() and all(
                    t["status"] in {"ok", "not_applicable"} for t in read_json(summary)["trials"]):
                count += 1
    return count


def enrich(output, value):
    missing = missing_count(output)
    rewrite_missing = rewrite_missing_count(output)
    state = value["state"]
    value.update(recovery_protocol=VERSION, baseline_failed_qa=missing,
                 baseline_processed_qa=value["baseline_qa"] + missing,
                 baseline_remaining_qa=40 - value["baseline_qa"] - missing,
                 rewrite_failed_qa=rewrite_missing,
                 missing_candidate_qa=missing + rewrite_missing,
                 processed_qa=value["completed_qa"] + missing + rewrite_missing,
                 successful_qa=value["completed_qa"],
                 remaining_qa=40 - value["completed_qa"] - missing - rewrite_missing,
                 collection_has_missing=bool(missing + rewrite_missing),
                 unhandled_failure_records=max(0, value["failed"] - missing - rewrite_missing),
                 failure_counts_are_retained=True)
    if state == "awaiting_scoring":
        require(value["processed_qa"] == 40, "Do not claim full collection from an incomplete selection")
        value["collection_completed"] = True
        value["next_owner"] = "Codex"
    elif state in {"recovery_ready", "stopped"}:
        value.update(next_owner="ユーザー", next_action=command(output, "resume"))
    elif state == "collecting":
        value["next_action"] = command(output, "status")
    value["rough_remaining_task_seconds"] = (value.get("observed_task_seconds", 0) /
        value["completed_qa"] * value["remaining_qa"] if value["completed_qa"] else None)
    return value


def public(output, state, reason=None):
    missing = missing_count(output)
    rewrite_missing = rewrite_missing_count(output)
    if state == "awaiting_scoring":
        require(legacy.totals(output)["completed_qa"] + missing + rewrite_missing == 40,
                "Do not claim full collection from an incomplete selection")
    value = enrich(output, ORIGINAL_PUBLIC(output, state, reason))
    write_json(output / "status.public.json", value)
    if state in {"failed", "awaiting_scoring"}:
        with (output / "report_to_codex.txt").open("a", encoding="utf-8") as stream:
            stream.write(f"\n復旧Protocol：{VERSION}\n処理済み予定QA：{value['processed_qa']}/40\n"
                         f"成功QA：{value['successful_qa']}、初回出力上限の欠測QA：{missing}\n"
                         f"書換え本文上限の失敗QA：{rewrite_missing}（初回保持・書換え候補は欠測）\n"
                         "失敗QAを除いて分母40を縮めず、失敗・未実施・比較可能数を分けて報告してください。\n"
                         "docs/phase11_fixed_v23_recovery_v2.md を確認し、元条件と事後の停止規則変更を区別してください。\n")
    return value


def language_contract(output, language):
    release = verify_release()
    contract = runner.load_config(bound(ROOT, release["configs"][language]))
    manifest = read_json(output / language / "manifest.json")
    require(manifest["config"] == contract[0] and manifest["qa_sha256"] == file_hash(contract[3]),
            "Preserve original config and QA binding")
    for name, sha in manifest["source_sha256"].items():
        require(file_hash(ROOT / name) == sha, "Frozen inference source or input changed")
    return contract, manifest


def baseline_stage(output, contract, manifest):
    config, assets, rows, _, baseline, generation, prompt, _ = contract
    directory = output / "baseline"
    limits = config["main_limits"]
    reserve(output, limits["maximum_completion_attempts"])
    selection = manifest["selection"]
    records = []

    def collect(client, retriever):
        new = 0
        for spec in selection:
            folder = directory / digest(spec["record_id"])[:24]
            if not (folder / "record.json").exists():
                if (output.parent / "stop.request").exists():
                    raise DevelopmentStop("user_stop_requested", budget_snapshot(output))
                if new == limits["maximum_new_qa_per_stage_session"]:
                    break
                reserve(output, limits["maximum_completion_attempts"], 1)
                new += 1
            folder.mkdir(exist_ok=True)
            value = runner.baseline_once(client, retriever, generation, prompt, baseline["retrieval"]["top_k"],
                spec, folder, {"manifest_sha256": digest(manifest)})
            require(value.get("status") == "ok" and value.get("used_context") or terminal_limit(value),
                    "Nonrecoverable baseline failure; preserve and stop")
            records.append(value)
            print(json.dumps({"stage": "baseline", "processed": len(records),
                              "status": value["status"], "phase12_allowed": False}), flush=True)

    pending = any(not (directory / digest(s["record_id"])[:24] / "record.json").exists() for s in selection)
    session = next_session(directory)
    if pending:
        retriever = runner.load_retriever(assets, config["language"])
        with runner.LocalServer(generation, directory / f"server-{session}.log", **runner.execution_kwargs(baseline)) as server:
            collect(server.client, retriever)
            write_json(directory / f"session-{session}.json", server.report())
        del retriever
        gc.collect()
    else:
        collect(None, None)
    temporary = directory / "answers.jsonl.tmp"
    temporary.write_bytes(b"".join(json_bytes(record) for record in records))
    temporary.replace(directory / "answers.jsonl")
    result = {"stage": "baseline", "processed_qa": len(records), "selected_qa": len(rows),
              "baseline_ok": sum(v["status"] == "ok" for v in records),
              "baseline_failures": sum(v["status"] != "ok" for v in records),
              "stage_complete": len(records) == len(rows), "phase12_allowed": False}
    write_json(output / "progress.json", result)
    return result


def internal_stage(output, contract, manifest):
    config, assets, rows, _, _, _, _, prompts = contract
    limits = config["main_limits"]
    reserve(output, limits["maximum_completion_attempts"])
    records = []
    for spec in manifest["selection"]:
        path = output / "baseline" / digest(spec["record_id"])[:24] / "record.json"
        record = read_json(path)
        verify_checkpoint(record)
        require(record["binding"] == {"manifest_sha256": digest(manifest)} and
                record["question"] == spec["question"], "Original baseline provenance differs")
        require(record["status"] == "ok" and record.get("used_context") or terminal_limit(record),
                "Unclassified baseline failure cannot enter internal collection")
        records.append(record)
    traces = [runner.freeze_record(v) for v in records if v["status"] == "ok"]
    failures = [{"record_id": v["record_id"], "status": v["status"], "error": v["error"],
                 "reason": "baseline_output_limit_missing_without_retry"} for v in records if v["status"] != "ok"]
    mapping = runner.parent_map(assets, config["language"])
    metadata = {r["record_id"]: r for r in rows}
    offline = [{"record_id": v["record_id"], "status": v["status"], "retrieval_metrics": runner.retrieval_metrics(
        [h["passage_id"] for h in v.get("retrieved_context", [])], mapping,
        metadata[v["record_id"]]["gold_parent_ids"],
        missing_source_units=metadata[v["record_id"]]["unavailable_cited_reference_ids"])} for v in records]
    write_json(output / "retrieval.offline.json", {"scope": "offline_only_not_quality_truth", "records": offline})
    internal = output / "internal"
    internal.mkdir(exist_ok=True)
    binding = {"manifest_sha256": digest(manifest), "traces": [
        {"record_id": t["record_id"], "directory": digest(t["record_id"])[:24], "trace_sha256": t["trace_sha256"],
         "plan": runner.trial_plan(t, config)} for t in traces]}
    runner.immutable(internal / "manifest.json", binding)
    assembled = []

    def pending(trace, entry):
        units = runner.extract_sentence_units(trace["answer"], language=config["language"])["claims"]
        return pending_trace_calls(internal / entry["directory"], [t["trial_id"] for t in entry["plan"]["trials"]],
                                   [c["claim_id"] for c in units], mode=config["verification_mode"])

    def notify(message, **kwargs):
        require(json.loads(message).get("status") != "error", "Internal task error; preserve and stop")

    def collect(client):
        new = 0
        for trace, entry in zip(traces, binding["traces"], strict=True):
            needed = pending(trace, entry)
            if needed:
                if (output.parent / "stop.request").exists():
                    raise DevelopmentStop("user_stop_requested", budget_snapshot(output))
                if new == limits["maximum_new_qa_per_stage_session"]:
                    break
                reserve(output, limits["maximum_completion_attempts"], needed)
                new += 1
            folder = internal / entry["directory"]
            per_manifest = {**binding, "traces": [entry]}
            evaluations, _ = runner.evaluate_traces(client, config, prompts, [trace], per_manifest, internal, notify=notify)
            rewritten = runner.rewrite_once(client, runner.task_config(config, "rewrite_answer"), prompts, trace,
                folder / "rewrite.json", {"manifest_sha256": digest(per_manifest), "trace_sha256": trace["trace_sha256"]})
            require(rewritten["status"] == "ok" or rewrite_limit(rewritten),
                    "Unclassified rewrite error; preserve and stop")
            original = next(v for v in records if v["record_id"] == trace["record_id"])
            assembled.append({"trace": trace, "evaluation": evaluations[0], "rewrite": rewritten,
                "tasks": {"extraction": read_json(folder / "claims.json"), "judges": {
                    t["trial_id"]: read_json(internal / t["task_file"]) for t in evaluations[0]["trials"] if "task_file" in t}},
                "baseline_cost": {k: original.get(k) for k in
                    ("input_tokens", "output_tokens", "generation_seconds", "context_seconds", "answer_generation_calls")}})
    needed = [pending(t, e) for t, e in zip(traces, binding["traces"], strict=True)]
    if any(needed):
        reserve(output, limits["maximum_completion_attempts"], next(n for n in needed if n))
        session = next_session(internal)
        with runner.LocalServer(runner.task_config(config, "verify_claims"), internal / f"server-{session}.log",
                               **runner.auxiliary_server_kwargs(config)) as server:
            collect(server.client)
            write_json(internal / f"session-{session}.json", server.report())
    else:
        collect(None)
    complete = len(assembled) == len(traces)
    if complete:
        write_json(output / "report.private.json", {"schema_version": 1, "purpose": config["purpose"],
            "manifest_sha256": digest(manifest), "language": config["language"], "selected_qa_count": len(rows),
            "records": assembled, "failures": failures, "quality_status": "pending_external_blinded_annotation",
            "recovery_protocol": {"path": REGISTRATION, "sha256": file_hash(ROOT / REGISTRATION)},
            "gate11_passed": False, "phase12_allowed": False})
    rewrite_failures = sum(r["rewrite"]["status"] != "ok" for r in assembled)
    result = {"stage": "internal", "processed_qa": len(assembled) + len(failures),
              "successful_qa": len(assembled) - rewrite_failures, "rewrite_failed_qa": rewrite_failures,
              "baseline_failures": len(failures), "selected_qa": len(rows), "stage_complete": complete,
              "quality_status": "pending_external_blinded_annotation", "phase12_allowed": False}
    write_json(output / "progress.json", result)
    return result


def child(output, language, stage):
    output, _, _ = validate(output)
    deadline = time.monotonic() + 5
    while True:
        owner = read_json(output / "control.json")
        if owner.get("child", {}).get("pid") == os.getpid() or time.monotonic() >= deadline:
            break
        time.sleep(.02)
    require(owner.get("launch_token") == os.environ.get("RAG_FIXED_V23_OWNER_TOKEN")
            and legacy.alive(owner.get("supervisor", {})) and legacy.alive(owner.get("child", {}))
            and owner["child"]["pid"] == os.getpid() == os.getpgrp()
            and owner["active_stage"] == {"language": language, "stage": stage, "recovery": VERSION},
            "Use the owned recovery supervisor, never invoke the child directly")
    require(language == "ja", "English is complete and must not be regenerated")
    contract, manifest = language_contract(output, language)
    with run_lock(output / language):
        result = (baseline_stage if stage == "baseline" else internal_stage)(output / language, contract, manifest)
        write_json(output / f"recovery-result-{language}-{stage}.json", result)
    return 0


def export_packets(output):
    from rag_research.experiments.bilingual_quality import export, read_run
    from rag_research.experiments.bilingual_semantics import export_units

    inventory = []
    for language in ("en", "ja"):
        manifest, report = read_run(output / language)
        require(len(report["records"]) + len(report["failures"]) == report["selected_qa_count"] == 20,
                "Every selected QA must be accounted for, including failures")
        for failure in report["failures"]:
            path = output / language / "baseline" / digest(failure["record_id"])[:24] / "record.json"
            require(terminal_limit(read_json(path)), "Only registered terminal baseline failures may remain missing")
            inventory.append({"language": language, "record_id": failure["record_id"],
                "raw_path": path.relative_to(output).as_posix(), "sha256": file_hash(path),
                "reason": "baseline_output_limit", "replacement_or_retry": False})
        for row in report["records"]:
            if row["rewrite"]["status"] == "ok":
                continue
            path = output / language / "internal" / digest(row["trace"]["record_id"])[:24] / "rewrite.json"
            require(rewrite_limit(read_json(path)), "Only registered rewrite length failures may remain missing")
            inventory.append({"language": language, "record_id": row["trace"]["record_id"],
                "raw_path": path.relative_to(output).as_posix(), "sha256": file_hash(path),
                "reason": "rewrite_final_answer_token_limit", "replacement_or_retry": False,
                "initial_answer_and_evaluation_retained": True,
                "failure_action": "keep_initial_answer_with_rewrite_failed_status"})
    for language in ("en", "ja"):
        bundle = output / language / "quality"
        if not bundle.exists():
            export(output / language, bundle)
        require(all((bundle / name).exists() for name in
                    ("packet.json", "mapping.private.json", "annotations.blank.json", "export_manifest.json")),
                "Partial annotation export needs explicit repair")
        if not (bundle / "units").exists():
            export_units(bundle, bundle / "units", language)
        require((bundle / "units/packet.json").exists() and (bundle / "units/annotations.blank.json").exists(),
                "Partial unit packet export needs explicit repair")
    checkpoint(output / "failure_inventory.json", {"selected_qa": 40, "failures": inventory,
        "failed_qa_retained_in_selected_denominator": True, "phase12_allowed": False})


def worker(output, token):
    output, study, _ = validate(output)
    with run_lock(output / "launch-lock"):
        control = read_json(output / "control.json")
        require(control["launch_token"] == token, "Stale recovery launch token")
    with run_lock(output):
        control["supervisor"] = legacy.identity(os.getpid())
        write_json(output / "control.json", control)
        old_public = legacy.public_state
        legacy.public_state = public  # Monitoring callback only; original inference modules remain unchanged.
        try:
            public(output, "collecting")
            for stage in ("baseline", "internal"):
                for _ in range(5):
                    if (output / "stop.request").exists():
                        return public(output, "stopped", "user_stop_requested")
                    remaining = study["total_wall_seconds"] - control["spent_wall_seconds"]
                    require(remaining > 0, "Original total wall budget exhausted")
                    argv = [sys.executable, str(Path(__file__).resolve()), "child", "--run", str(output),
                            "--language", "ja", "--stage", stage]
                    control["active_stage"] = {"language": "ja", "stage": stage, "recovery": VERSION}
                    code, reason = legacy.supervise(argv, output, control, min(remaining, study["session_wall_seconds"]))
                    require(code == 0 and reason is None, reason or "recovery_child_failed")
                    result = read_json(output / f"recovery-result-ja-{stage}.json")
                    if result["stage_complete"]:
                        break
                else:
                    raise ValueError("Finite recovery schedule did not finish")
            export_packets(output)
            validate(output)
            return public(output, "awaiting_scoring")
        except BaseException as error:
            safe_stop = False
            if (output / "stop.request").exists():
                try:
                    reserve(output / "ja", 1660)
                    safe_stop = True
                except (ValueError, DevelopmentStop):
                    pass
            state = "stopped" if safe_stop else "failed"
            public(output, state, f"{type(error).__name__}: {error}")
            if not isinstance(error, Exception):
                raise
            return read_json(output / "status.public.json")
        finally:
            legacy.public_state = old_public


def launch(output):
    output, study, _ = validate(output)
    with run_lock(output / "launch-lock"):
        control = read_json(output / "control.json")
        require(not legacy.alive(control.get("supervisor", {})) and not legacy.alive(control.get("child", {})),
                "An owned process is still running")
        require(read_json(output / "status.public.json")["state"] in {"recovery_ready", "stopped", "failed", "collecting"},
                "Collection state does not permit recovery launch")
        require(control["spent_wall_seconds"] < study["total_wall_seconds"], "Original total wall budget exhausted")
        (output / "stop.request").unlink(missing_ok=True)
        token = uuid.uuid4().hex
        control.update(launch_token=token, recovery_protocol=VERSION)
        write_json(output / "control.json", control)
        with (output / "supervisor.log").open("ab", buffering=0) as log:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "worker", "--run", str(output),
                "--token", token], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        control["supervisor"] = legacy.identity(process.pid)
        write_json(output / "control.json", control)
    return {"started": True, "supervisor_pid": process.pid, "next_action": command(output, "status")}


def prepare(checkout):
    checkout = checkout.resolve()
    require(checkout.is_relative_to(ROOT / ".tools/worktrees"), "Use the existing dedicated fixed-v23 checkout")
    output = checkout / RUN
    require(not (checkout / REGISTRATION).exists(), "Preserve the previous recovery registration")
    release = read_json(checkout / "fixed-v23-release.json")
    for name, sha in release["files"].items():
        require(file_hash(checkout / name) == sha, "Original sealed source changed")
    control = read_json(output / "control.json")
    require(not legacy.alive(control.get("supervisor", {})) and not legacy.alive(control.get("child", {})),
            "Stop and preserve the existing owner before recovery preparation")
    require(read_json(output / "status.public.json")["state"] == "failed", "Prepare only the existing failed Main")
    parent = read_json(checkout / PARENT_REGISTRATION)
    require(parent["version"] == "fixed-v23-terminal-baseline-recovery-v1"
            and parent["original_release_sha256"] == file_hash(checkout / "fixed-v23-release.json"),
            "Preserve the original recovery registration and inference release")
    bound(checkout, parent["entrypoint"])
    bound(checkout, parent["wrapper"])
    for name, sha in parent["protected_original_files"].items():
        require(file_hash(output / name) == sha, "A parent-protected result changed: " + name)
    errors = reserve(output / "ja", 1660)["error_paths"]
    require(len(errors) == 2,
            "Prepare against the observed two Japanese length failures")
    require(sum(terminal_limit(read_json(output / "ja" / p)) for p in errors) == 1
            and sum(rewrite_limit(read_json(output / "ja" / p)) for p in errors) == 1
            and not reserve(output / "en", 1660)["error_paths"], "Observed failure types changed")
    archive = checkout / "data/runs/recovery_audits/fixed-v23-answer-length-v2"
    require(not archive.exists(), "Preserve the existing audit snapshot")
    before = {p.relative_to(output).as_posix(): file_hash(p) for p in output.rglob("*") if p.is_file()}
    shutil.copytree(output, archive / "before")
    require(before == {p.relative_to(archive / "before").as_posix(): file_hash(p)
                       for p in (archive / "before").rglob("*") if p.is_file()}, "Snapshot differs from the stopped Run")
    entrypoint = checkout / "scripts/recover_fixed_v23_v2.py"
    require(not entrypoint.exists(), "Preserve the previous entrypoint")
    shutil.copy2(Path(__file__), entrypoint)
    wrapper = checkout / "fixed-v23-recover-v2.sh"
    require(not wrapper.exists(), "Preserve the previous wrapper")
    old_wrapper = (checkout / "fixed-v23.sh").read_text()
    require("scripts/fixed_v23.py" in old_wrapper, "Original wrapper contract changed")
    wrapper.write_text(old_wrapper.replace("scripts/fixed_v23.py", "scripts/recover_fixed_v23_v2.py"), encoding="utf-8")
    wrapper.chmod(0o755)
    value = {"version": VERSION, "recorded_at_utc": legacy.now(), "output_dir": RUN,
        "original_release_sha256": file_hash(checkout / "fixed-v23-release.json"),
        "parent_registration": {"path": PARENT_REGISTRATION, "sha256": file_hash(checkout / PARENT_REGISTRATION)},
        "entrypoint": {"path": "scripts/recover_fixed_v23_v2.py", "sha256": file_hash(entrypoint)},
        "wrapper": {"path": wrapper.name, "sha256": file_hash(wrapper)},
        "protected_original_files": protected_files(output), "snapshot_files": before,
        "snapshot_directory": archive.relative_to(checkout).as_posix(), "maximum_calls_per_language": 1660,
        "new_native_calls_at_preparation": 0, "baseline_output_limit_is_missing": True,
        "rewrite_output_limit_is_missing": True,
        "rewrite_failure_action": "keep_initial_answer_with_rewrite_failed_status",
        "automatic_retries": 0, "replacement_qa": False, "phase12_allowed": False,
        "post_outcome_stop_rule_amendment": True, "inference_conditions_changed": False,
        "change_reason": "Extend the baseline-only recovery to received rewrite responses whose final answer "
            "exceeds 512 tokens. Keep the failed rewrite missing and initial answer/evaluation intact; never retry. "
            "Unknown/transport/GPU/input/other internal errors still stop the whole collection.",
        "selection_denominator": 40, "new_model_calls": 0}
    write_json(checkout / REGISTRATION, value)
    print(json.dumps({"prepared": True, "snapshot_file_count": len(before),
                      "protected_file_count": len(value["protected_original_files"]), "new_model_calls": 0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check", "arm", "resume", "status", "stop", "worker", "child"))
    parser.add_argument("--checkout", type=Path)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--token")
    parser.add_argument("--language", choices=("ja",))
    parser.add_argument("--stage", choices=("baseline", "internal"))
    args = parser.parse_args()
    if args.action == "prepare":
        require(args.checkout is not None, "Specify the stopped checkout")
        prepare(args.checkout)
        return 0
    require(args.run is not None, "Specify the original Run")
    output = args.run.resolve()
    if args.action == "child":
        return child(output, args.language, args.stage)
    if args.action == "worker":
        result = worker(output, args.token)
        return int(result["state"] == "failed")
    if args.action == "resume":
        result = launch(output)
    elif args.action == "stop":
        validate(output, check_budget=False)
        result = legacy.stop(output)
    elif args.action == "status":
        validate(output, check_budget=False)
        result = enrich(output, legacy.status(output))
    else:
        output, _, registration = validate(output)
        for language in ("en", "ja"):
            language_contract(output, language)
        from rag_research.experiments.bilingual_quality import read_run

        _, report = read_run(output / "en")
        require(len(report["records"]) == report["selected_qa_count"] == 20 and not report["failures"],
                "Preserve and verify the completed English collection")
        if args.action == "arm":
            control = read_json(output / "control.json")
            require(not legacy.alive(control.get("supervisor", {})) and not legacy.alive(control.get("child", {})),
                    "Do not arm a running collection")
            public(output, "recovery_ready", "confirmed_answer_length_failures_retained_without_retry")
        result = {"recovery_verified": True, "protected_files": len(registration["protected_original_files"]),
                  "english_completed_qa_verified": 20, "new_model_calls": 0, "run": str(output)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
