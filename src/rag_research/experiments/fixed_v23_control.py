"""Local, finite collection supervision; no Codex or external API is called."""

import json
import os
import shlex
import signal
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psutil

from rag_research.experiments.bilingual_budget import budget_snapshot
from rag_research.experiments.fixed_v23 import ROOT, bound, load_study, verify_release
from rag_research.experiments.frozen_trace import require
from rag_research.experiments.storage import read_json, run_lock, write_json
from rag_research.retrieval.common import file_hash


def now():
    return datetime.now(UTC).isoformat()


def alive(identity):
    try:
        process = psutil.Process(identity["pid"])
        return process.create_time() == identity["created"] and process.status() != psutil.STATUS_ZOMBIE
    except (KeyError, psutil.Error):
        return False


def identity(pid):
    return {"pid": pid, "created": psutil.Process(pid).create_time()}


def command(output, action):
    return shlex.join([str(ROOT / "fixed-v23.sh"), action, "--run", str(output)])


def totals(output):
    value = {"attempts": 0, "unknown": 0, "failed": 0, "input_tokens": 0,
             "output_tokens": 0, "observed_task_seconds": 0., "baseline_qa": 0,
             "completed_qa": 0, "planned_qa": 40, "remaining_qa": 40}
    for language in ("en", "ja"):
        snapshot = budget_snapshot(output / language)
        value["attempts"] += snapshot["recorded_native_attempts_upper_bound"]
        value["unknown"] += len(snapshot["unknown_or_interrupted_paths"])
        value["failed"] += len(snapshot["error_paths"])
        for leaf in snapshot["raw_calls"]:
            task = read_json(output / language / leaf["path"])
            for key in ("input_tokens", "output_tokens"):
                value[key] += task.get(key) or 0
            value["observed_task_seconds"] += task.get("elapsed_seconds") or task.get("generation_seconds") or 0
        value["baseline_qa"] += sum(read_json(p).get("status") == "ok"
            for p in (output / language / "baseline").glob("*/record.json"))
        for summary in (output / language / "internal").glob("*/summary.json"):
            rewrite = summary.parent / "rewrite.json"
            data = read_json(summary)
            if rewrite.exists() and read_json(rewrite).get("status") == "ok" and all(
                    t["status"] in {"ok", "not_applicable"} for t in data["trials"]):
                value["completed_qa"] += 1
    value["remaining_qa"] = 40 - value["completed_qa"]
    value["token_totals_complete"] = value["unknown"] == 0
    value["rough_remaining_task_seconds"] = (
        value["observed_task_seconds"] / value["completed_qa"] * value["remaining_qa"]
        if value["completed_qa"] else None)
    value["estimate_scope"] = "observed task-time per finished QA; includes partial work, excludes scoring; not a wall-time guarantee"
    return value


def public_state(output, state, reason=None):
    """Only allowlisted progress reaches the console or user report."""
    owner = "プログラム" if state == "collecting" else "Codex" if state in {
        "awaiting_scoring", "failed", "interrupted"} else "ユーザー"
    next_action = (str(output / "report_to_codex.txt") if owner == "Codex" else
                   command(output, "status") if state == "collecting" else
                   command(output, "continue") if state == "pilot_complete" else
                   command(output, "resume") if state == "stopped" else command(output, "pilot"))
    value = {"state": state, "next_owner": owner, "next_action": next_action,
             "updated_at_utc": now(), "reason": reason, "run": str(output),
             "status_file": str(output / "status.public.json"), **totals(output),
             "collection_completed": state == "awaiting_scoring",
             "quality_and_expected_sealed": False, "old_gate11_passed": False,
             "phase12_allowed": False}
    write_json(output / "status.public.json", value)
    if owner == "Codex":
        complete = state == "awaiting_scoring"
        packets = {lang: str(output / lang / "quality/packet.json") for lang in ("en", "ja")
                   if (output / lang / "quality/packet.json").exists()}
        text = ("v23固定実験のMain収集が終了したので採点・解析をお願いします。" if complete else
                "v23固定実験が停止・失敗・状態不明になりました。まず保存状態を確認してください。")
        text += "\ndocs/phase11_v23_user_runbook_2026-10-28.md に従ってください。\n"
        text += f"作業ディレクトリ：{ROOT}\nRun：{output}\n公開状態：{output / 'status.public.json'}\n"
        text += f"状態：{state}\n停止理由：{reason}\n匿名Packet：{json.dumps(packets, ensure_ascii=False) or '未生成'}\n"
        text += ("全日英品質Labelと全文Expectedを匿名Packetで採点・封印するまで、内部F・判断・候補対応を閲覧しないでください。\n"
                 "文Expectedは専用の実使用根拠だけのPacketで判定し、Goldで支持を補わないでください。\n"
                 "AI採点の来歴・履歴分離の限界を記録し、封印後に順序変更対反復・品質・費用・欠測を解析してください。\n"
                 "固定v23の別ProtocolでCalへ進めるか確認し、可能なら実設定と単独実行コマンドを渡してください。Calはユーザーが起動します。\n"
                 if complete else "実プロセス・Raw・Journal・費用を保全し、未知を再送せず、同じ固定条件での再開可否を確認してください。\n")
        text += "v23・Prompt・閾値0.7を再調整せず、旧90%基準未達を合格へ変更しないでください。Phase12は開始しません。\n"
        (output / "report_to_codex.txt").write_text(text, encoding="utf-8")
    return value


def collection(output):
    output = Path(output).resolve()
    parent = ROOT / "data/runs/bilingual_development"
    require(output.is_relative_to(parent) and output != parent, "Run stays in the fixed checkout")
    release = verify_release()
    readiness = read_json(ROOT / "fixed-v23-readiness.json")
    report = read_json(bound(ROOT, readiness["preflight"]))
    require(readiness["release_sha256"] == file_hash(ROOT / "fixed-v23-release.json") == report["release_sha256"]
            and report["status"] == "passed" and report["completion_attempts"] == 0
            and report["actual_qa_inference_tested"] is False and report["main_started"] is False,
            "Complete zero-generation preflight for this exact source release before collection")
    study_path = bound(ROOT, release["study"])
    study, _, _ = load_study(study_path)
    require(output == ROOT / study["output_dir"], "Use the registered collection path")
    require(not os.environ.get("RAG_PHASE11_AUTONOMY_CONTEXT"), "Do not mix historical supervisor contexts")
    return output, study


def initialize(output):
    output, study = collection(output)
    require(not output.exists(), "Preserve the existing collection")
    output.mkdir(parents=True)
    write_json(output / "control.json", {"study_sha256": read_json(ROOT / "fixed-v23-release.json")["study"]["sha256"],
               "spent_wall_seconds": 0., "resume_action": "pilot", "sessions": []})
    return public_state(output, "ready")


def status(output):
    output, _ = collection(output)
    value = read_json(output / "status.public.json")
    control = read_json(output / "control.json")
    value.update(totals(output))
    if value["state"] == "collecting" and not alive(control.get("supervisor", {})):
        # Read-only status: never send signals or replace the authoritative state.
        value.update(state="interrupted", next_owner="Codex", reason="supervisor_not_alive",
                     next_action=f"{output / 'report_to_codex.txt'}（未生成なら公開状態とRunを報告）")
    value["supervisor_alive"] = alive(control.get("supervisor", {}))
    value["child_alive"] = alive(control.get("child", {}))
    value["stop_requested"] = (output / "stop.request").exists()
    return value


def launch(output, action):
    output, study = collection(output)
    with run_lock(output / "launch-lock"):
        control = read_json(output / "control.json")
        require(not alive(control.get("supervisor", {})) and not alive(control.get("child", {})),
                "An owned supervisor or child is still running")
        current = read_json(output / "status.public.json")["state"]
        expected = {"pilot": {"ready"}, "continue": {"pilot_complete"},
                    "resume": {"stopped", "failed", "interrupted", "collecting"}}
        require(action in expected and current in expected[action], "Action does not match collection state")
        for lang in ("en", "ja"):
            snap = budget_snapshot(output / lang)
            require(not snap["error_paths"] and not snap["unknown_or_interrupted_paths"],
                    "Existing task error/unknown needs Codex review; never resend")
        require(control["spent_wall_seconds"] < study["total_wall_seconds"], "Total wall budget exhausted")
        if action != "resume":
            control["resume_action"] = action
        (output / "stop.request").unlink(missing_ok=True)
        token = uuid.uuid4().hex
        control["launch_token"] = token
        write_json(output / "control.json", control)
        with (output / "supervisor.log").open("ab", buffering=0) as log:
            process = subprocess.Popen([sys.executable, str(ROOT / "scripts/fixed_v23.py"), "worker",
                "--run", str(output), "--token", token], cwd=ROOT, stdin=subprocess.DEVNULL,
                stdout=log, stderr=log, start_new_session=True)
        # A durable launch receipt closes the window before the worker takes its run lock.
        control["supervisor"] = identity(process.pid)
        write_json(output / "control.json", control)
    return {"started": True, "supervisor_pid": process.pid, "next_action": command(output, "status")}


def stop(output):
    output, _ = collection(output)
    write_json(output / "stop.request", {"requested_at_utc": now(), "policy": "stop_before_next_new_qa"})
    return {"stop_requested": True, "policy": "現在のQAを保存して次の新規QAの前で停止",
            "next_action": command(output, "status")}


def terminate_owned(process, owned):
    if process.poll() is None and alive(owned) and os.getpgid(process.pid) == process.pid:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if alive(owned) and os.getpgid(process.pid) == process.pid:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)


def supervise(argv, output, control, deadline, *, interval=5):
    """Persist resources and child identity; on deadline terminate only this owned group."""
    index = len(control["sessions"])
    with (output / f"session-{index:03d}.log").open("ab", buffering=0) as log:
        child = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                 start_new_session=True, env={**os.environ,
                                     "RAG_FIXED_V23_OWNER_TOKEN": control.get("launch_token", "synthetic")})
        owned = identity(child.pid)
        control["child"] = owned
        write_json(output / "control.json", control)
        started = time.monotonic()
        prior = control["spent_wall_seconds"]
        reason = None
        try:
            while child.poll() is None:
                elapsed = time.monotonic() - started
                control["spent_wall_seconds"] = prior + elapsed
                write_json(output / "control.json", control)
                sample = {"at_utc": now(), "session": index, "elapsed_seconds": elapsed,
                          "rss_bytes": None, "gpu": None}
                try:
                    processes = [psutil.Process(child.pid), *psutil.Process(child.pid).children(recursive=True)]
                    sample["rss_bytes"] = sum(p.memory_info().rss for p in processes if p.is_running())
                except psutil.Error:
                    pass
                try:
                    gpu = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
                        "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=3)
                    sample["gpu"] = gpu.stdout.strip() if gpu.returncode == 0 else None
                except (OSError, subprocess.TimeoutExpired):
                    pass
                with (output / "resources.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(sample) + "\n")
                if elapsed >= deadline:
                    reason = "finite_wall_deadline"
                    terminate_owned(child, owned)
                    break
                public_state(output, "collecting")
                time.sleep(min(interval, max(.01, deadline - elapsed)))
            returncode = child.wait()
        finally:
            terminate_owned(child, owned)
            control["spent_wall_seconds"] = prior + time.monotonic() - started
            control["sessions"].append({"argv": argv, "exit_code": child.returncode,
                "elapsed_seconds": time.monotonic() - started, "reason": reason})
            control.pop("child", None)
            write_json(output / "control.json", control)
    return returncode, reason


def child_stage(output, language, stage, pilot=False):
    """Use the unchanged collector and never print its private return values."""
    from rag_research.experiments.bilingual_runner import run

    output, _ = collection(output)
    deadline = time.monotonic() + 5
    while True:
        owner = read_json(output / "control.json")
        if owner.get("child", {}).get("pid") == os.getpid() or time.monotonic() >= deadline:
            break
        time.sleep(.02)
    require(owner.get("launch_token") == os.environ.get("RAG_FIXED_V23_OWNER_TOKEN") and
            alive(owner.get("supervisor", {})) and alive(owner.get("child", {})) and
            owner["child"]["pid"] == os.getpid() == os.getpgrp() and
            owner.get("active_stage") == {"language": language, "stage": stage, "pilot": pilot},
            "Collection child requires its live finite supervisor; use the public launch commands")
    release = verify_release()
    config = bound(ROOT, release["configs"][language])
    result = run(config, output / language, stage=stage, qa_limit=1 if pilot else None)
    destination = output / f"result-{language}-{stage}.json"
    write_json(destination, result)
    return 1 if result.get("stage", "").endswith("_stopped") else 0


def export_packets(output):
    from rag_research.experiments.bilingual_quality import export
    from rag_research.experiments.bilingual_semantics import export_units

    for lang in ("en", "ja"):
        report = read_json(output / lang / "report.private.json")
        require(report["selected_qa_count"] == len(report["records"]) == 20 and not report["failures"],
                "Both full selections must be collected before scoring")
    for lang in ("en", "ja"):
        bundle = output / lang / "quality"
        # Incomplete export is retained for explicit repair; never overwrite it.
        if not bundle.exists():
            export(output / lang, bundle)
        require(all((bundle / name).is_file() for name in
                    ("packet.json", "mapping.private.json", "export_manifest.json", "annotations.blank.json")),
                "Incomplete quality export needs review")
        if not (bundle / "units").exists():
            export_units(bundle, bundle / "units", lang)
        require((bundle / "units/packet.json").is_file() and
                (bundle / "units/annotations.blank.json").is_file(), "Incomplete unit export needs review")


def worker(output, token):
    output, study = collection(output)
    # Wait on the launch lock so the parent publishes its PID receipt first.
    with run_lock(output / "launch-lock"):
        control = read_json(output / "control.json")
        require(control["launch_token"] == token, "Stale worker token")
    with run_lock(output):
        control["supervisor"] = identity(os.getpid())
        write_json(output / "control.json", control)
        pilot = control["resume_action"] == "pilot"
        try:
            public_state(output, "collecting")
            for lang in (("en",) if pilot else ("en", "ja")):
                for stage in ("baseline", "internal"):
                    # Four five-QA stages; one extra handles the retained pilot prefix.
                    for _ in range(5):
                        if (output / "stop.request").exists():
                            return public_state(output, "stopped", "user_stop_requested")
                        remaining = study["total_wall_seconds"] - control["spent_wall_seconds"]
                        require(remaining > 0, "Total wall budget exhausted")
                        argv = [sys.executable, str(ROOT / "scripts/fixed_v23.py"), "child", "--run",
                                str(output), "--language", lang, "--stage", stage]
                        if pilot:
                            argv.append("--first-qa")
                        control["active_stage"] = {"language": lang, "stage": stage, "pilot": pilot}
                        code, reason = supervise(argv, output, control,
                            min(remaining, study["pilot_wall_seconds"] if pilot else study["session_wall_seconds"]))
                        require(code == 0 and reason is None, reason or "collection_child_failed")
                        result = read_json(output / f"result-{lang}-{stage}.json")
                        if pilot:
                            require((stage == "baseline" and result.get("processed_qa") == 1) or
                                    (stage == "internal" and result.get("stage") == "pilot_complete"),
                                    "First-QA stage incomplete")
                            break
                        if (stage == "baseline" and result.get("baseline_count") == 20) or (
                                stage == "internal" and result.get("trace_count") == 20):
                            break
                    else:
                        raise ValueError("Finite stage schedule did not complete")
            if pilot:
                return public_state(output, "pilot_complete")
            export_packets(output)
            return public_state(output, "awaiting_scoring")
        except BaseException as error:
            state = "stopped" if (output / "stop.request").exists() and totals(output)["unknown"] == 0 and totals(output)["failed"] == 0 else "failed"
            public_state(output, state, f"{type(error).__name__}: {error}")
            if not isinstance(error, Exception):
                raise
            return read_json(output / "status.public.json")
