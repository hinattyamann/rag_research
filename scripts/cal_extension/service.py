"""Detached extension workflow. Heartbeats cannot abort an in-flight request."""

import argparse
import ctypes
import importlib.util
import json
import os
import subprocess
import sys
import time
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def modules(config):
    sys.path.insert(0, str(Path(config["helper_dir"]) / "legacy"))
    import common
    import gpu_guard
    return common, gpu_guard


def utc_now():
    return datetime.now(UTC).isoformat()


def safe_counts(run):
    counts = {"baseline_ok": 0, "baseline_failed": 0, "internal_complete": 0,
              "rewrite_ok": 0, "rewrite_failed": 0, "in_flight_or_unreadable": 0}
    for language in ["en", "ja"]:
        for folder, pattern, kind in [("baseline", "*/record.json", "baseline"),
                                       ("internal", "*/rewrite.json", "rewrite")]:
            for path in (Path(run) / language / folder).glob(pattern):
                try:
                    status = read(path).get("status")
                    if status in ["ok", "error"]:
                        counts[kind + ("_ok" if status == "ok" else "_failed")] += 1
                    else:
                        counts["in_flight_or_unreadable"] += 1
                except (OSError, ValueError):
                    counts["in_flight_or_unreadable"] += 1
        for path in (Path(run) / language / "internal").glob("*/summary.json"):
            try:
                if read(path).get("trials") is not None:
                    counts["internal_complete"] += 1
            except (OSError, ValueError):
                pass
    return counts


def close_vscode_window(*, perform=True):
    """Send normal WM_DELETE_WINDOW only to windows whose WM_CLASS is Code.

    X11 requests are intentionally limited to the explicitly authorized application.
    This is called by the detached service, after it owns its execution context.
    """
    library = ctypes.cdll.LoadLibrary("libX11.so.6")
    ptr = ctypes.c_void_p
    ulong = ctypes.c_ulong
    library.XOpenDisplay.restype = ptr
    library.XDefaultRootWindow.argtypes = [ptr]
    library.XDefaultRootWindow.restype = ulong
    library.XInternAtom.argtypes = [ptr, ctypes.c_char_p, ctypes.c_int]
    library.XInternAtom.restype = ulong
    library.XGetWindowProperty.argtypes = [ptr, ulong, ulong, ctypes.c_long, ctypes.c_long, ctypes.c_int,
        ulong, ctypes.POINTER(ulong), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ulong),
        ctypes.POINTER(ulong), ctypes.POINTER(ptr)]
    library.XGetClassHint.argtypes = [ptr, ulong, ptr]
    library.XFree.argtypes = [ptr]
    library.XSendEvent.argtypes = [ptr, ulong, ctypes.c_int, ctypes.c_long, ptr]
    library.XFlush.argtypes = [ptr]
    library.XCloseDisplay.argtypes = [ptr]
    error_callback_type = ctypes.CFUNCTYPE(ctypes.c_int, ptr, ptr)
    error_callback = error_callback_type(lambda display, error: 0)
    library.XSetErrorHandler.argtypes = [ptr]
    library.XSetErrorHandler.restype = ptr
    previous_error_handler = library.XSetErrorHandler(error_callback)
    display = library.XOpenDisplay(None)
    if not display:
        library.XSetErrorHandler(previous_error_handler)
        return {"closed_windows": 0, "reason": "X11 display unavailable"}
    class Hint(ctypes.Structure):
        _fields_ = [("name", ptr), ("cls", ptr)]
    class Message(ctypes.Structure):
        _fields_ = [("type", ctypes.c_int), ("serial", ulong), ("send_event", ctypes.c_int),
                    ("display", ptr), ("window", ulong), ("message_type", ulong),
                    ("format", ctypes.c_int), ("data", ctypes.c_long * 5)]
    class Event(ctypes.Union):
        _fields_ = [("message", Message), ("pad", ctypes.c_long * 24)]
    closed = []
    try:
        root = library.XDefaultRootWindow(display)
        atom = library.XInternAtom(display, b"_NET_CLIENT_LIST", 0)
        actual, count, after = ulong(), ulong(), ulong()
        form, data = ctypes.c_int(), ptr()
        library.XGetWindowProperty(display, root, atom, 0, 4096, 0, 33,
                                  ctypes.byref(actual), ctypes.byref(form), ctypes.byref(count),
                                  ctypes.byref(after), ctypes.byref(data))
        if not data:
            return {"closed_windows": 0, "reason": "No X11 client list"}
        windows = list(ctypes.cast(data, ctypes.POINTER(ulong))[:count.value])
        library.XFree(data)
        for window in windows:
            hint = Hint()
            if not library.XGetClassHint(display, window, ctypes.byref(hint)):
                continue
            names = [ctypes.string_at(value).decode(errors="replace") for value in [hint.name, hint.cls] if value]
            for value in [hint.name, hint.cls]:
                if value:
                    library.XFree(value)
            if not any(name.casefold() in {"code", "com.microsoft.vscode"} for name in names):
                continue
            event = Event()
            event.message = Message(33, 0, 1, display, window,
                library.XInternAtom(display, b"WM_PROTOCOLS", 0), 32,
                (ctypes.c_long * 5)(library.XInternAtom(display, b"WM_DELETE_WINDOW", 0), 0, 0, 0, 0))
            if perform:
                library.XSendEvent(display, window, 0, 0, ctypes.byref(event))
            closed.append(window)
        library.XFlush(display)
    finally:
        library.XCloseDisplay(display)
        library.XSetErrorHandler(previous_error_handler)
    return {"close_requests": len(closed) if perform else 0, "eligible_windows": len(closed),
            "method": "WM_DELETE_WINDOW", "application": "Code", "dry_run": not perform}


def publish(config):
    repo = Path(config["repo"])
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=repo, text=True, stderr=subprocess.PIPE, timeout=90).strip()
    if git("branch", "--show-current") != config["branch"] or git("remote", "get-url", "origin") != config["remote_url"]:
        raise ValueError("Publication branch/remote changed")
    if git("diff", "--cached", "--name-only"):
        raise ValueError("Unrelated staged changes; leave them untouched")
    git("fetch", "origin")
    behind = int(git("rev-list", "--left-right", "--count", "HEAD...@{upstream}").split()[1])
    if behind:
        raise ValueError("Remote advanced; preserve local commits without merge/rebase")
    paths = ["docs/cal_extension_status.md", "data/manifests/cal_extension_status_v1.json",
             "reports/cal_extension_v1", "papers/iciae2027/materials/cal_extension_v1"]
    present = [p for p in paths if (repo / p).exists()]
    git("add", "--", *present)
    staged = git("diff", "--cached", "--name-only").splitlines()
    if not all(any(p == allowed or p.startswith(allowed + "/") for allowed in paths) for p in staged):
        raise ValueError("Unexpected staged file")
    if staged:
        git("diff", "--cached", "--check")
        git("commit", "-m", "Cal追加収集の工程と確定資料を共有", "--", *staged)
    git("push", "origin", config["branch"])
    commit = git("rev-parse", "HEAD")
    if commit != git("rev-parse", "@{upstream}"):
        raise ValueError("Remote tip mismatch")
    return {"at_utc": utc_now(), "commit": commit, "pushed": True}


class Workflow:
    def __init__(self, config):
        self.config = config
        self.common, self.gpu = modules(config)
        self.state = Path(config["state_dir"])
        self.stage, self.batch = "starting", None
        self.last_status = 0

    def heartbeat(self, event=False, error=None):
        """Never propagate a monitor/Git failure into run_owned's active child."""
        try:
            publication_request = self.state / "publication.request"
            if publication_request.exists() and time.monotonic() - self.last_status >= 30:
                event = True
            if not event and time.monotonic() - self.last_status < 30:
                return
            self.last_status = time.monotonic()
            batches = []
            for path in self.config["batches"]:
                cfg = read(path)
                batches.append({"batch": cfg["batch_id"], **safe_counts(cfg["cal_run"]),
                    "collection_complete": (Path(cfg["cal_run"]) / "collection_completed.json").exists(),
                    "annotations_sealed": (Path(cfg["cal_run"]) / "all_annotations.seal.json").exists(),
                    "materials_complete": (Path(self.config["repo"]) / "papers/iciae2027/materials/cal_extension_v1" /
                                           cfg["batch_id"] / "artifact_manifest.json").exists()})
            value = {"updated_at_utc": utc_now(), "workflow": "fixed-v23-cal-extension-v1", "stage": self.stage,
                "current_batch": self.batch, "planned_qa": 120, "planned_per_language": 60, "batches": batches,
                "collection_cutoff_utc": self.config["collection_cutoff_utc"], "error": error,
                "api_billing_allowed": False, "git_publish_policy": "events_only", "paper_written": False,
                "in_flight_is_not_a_confirmed_unknown_response": True}
            repo = Path(self.config["repo"])
            self.common.write(self.state / "status.json", value)
            self.common.write(repo / "data/manifests/cal_extension_status_v1.json", value)
            lines = ["# Cal追加収集の自動実行状況", "", "更新: " + value["updated_at_utc"], "",
                f"工程: **{self.stage}** / Batch: {self.batch}", "", "予定: 英語60問・日本語60問、計120問。20問ずつの日英Batchを3回。",
                "収集終了目安: 2026-11-14 23:59 JST。結果の向き/有意差による追加・停止はしない。", "",
                "| Batch | 初回成功 | 初回失敗 | 書換え成功 | 書換え失敗 | 処理中等 | 採点封印 | 資料 |",
                "|---|---:|---:|---:|---:|---:|---|---|"]
            lines += [f"| {b['batch']} | {b['baseline_ok']} | {b['baseline_failed']} | {b['rewrite_ok']} | {b['rewrite_failed']} | {b['in_flight_or_unreadable']} | {b['annotations_sealed']} | {b['materials_complete']} |" for b in batches]
            lines += ["", "選定数、生成成功数、完全比較数は別。拒否/Token超過を0や成功へ補完しない。",
                "Git反映は開始・5問ずつの日英処理完了・工程切替・停止・確定資料保存時。定時送信なし。",
                "CLIは匿名採点のときだけ使用。収集/集計/描画/Git反映では起動しない。",
                "実データ・図表・説明・検証入口: papers/iciae2027/materials/cal_extension_v1/。",
                "既存Main/Cal/原稿は別管理で保持。ノートPCはこのBranchをFetchして確認し、収集を二重起動しない。"]
            if error:
                lines += ["", "停止理由: " + error]
            (repo / "docs/cal_extension_status.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
            if event:
                try:
                    self.common.write(self.state / "git_publication.json", publish(self.config))
                    publication_request.unlink(missing_ok=True)
                except Exception as failure:
                    self.common.write(self.state / "git_publication.json", {"at_utc": utc_now(), "pushed": False,
                        "error": type(failure).__name__ + ": " + str(failure)[:500]})
        except Exception:
            try:
                with (self.state / "monitor-errors.log").open("a") as stream:
                    stream.write(traceback.format_exc())
            except Exception:
                # Even a monitoring-log write failure must not cancel a native request.
                pass

    def remaining(self):
        return datetime.fromisoformat(self.config["collection_cutoff_utc"]).timestamp() - time.time()

    def child(self, cfg_path, action, *, receipt, timeout=43200, language=None, phase=None, cpu=False):
        cfg = read(cfg_path)
        remaining_workflow = datetime.fromisoformat(self.config["deadline_utc"]).timestamp() - time.time()
        if remaining_workflow <= 0:
            raise ValueError("Preregistered workflow deadline reached")
        timeout = min(timeout, remaining_workflow)
        command = [self.config["cpu_python"] if cpu else self.config["gpu_python"],
                   str(Path(self.config["helper_dir"]) / "execute.py"), "--config", str(cfg_path), "--action", action]
        if language:
            command += ["--language", language, "--phase", phase]
        def heartbeat():
            if self.remaining() <= 0 or (self.state / "stop.request").exists():
                self.common.write(Path(cfg["cal_run"]) / "stop.request", {"requested_at_utc": utc_now(),
                    "reason": "collection_cutoff_or_user_stop; finish active QA, no new QA"})
            self.heartbeat()
        return self.common.run_owned(command, cwd=self.config["checkout"], receipt=receipt,
                                     timeout=timeout, heartbeat=heartbeat)

    def wait_gpu(self, cfg, language, phase, stage_receipt, maximum):
        policy = cfg["cal_gpu_policy"]
        required = policy["internal_min_free_mib"] if phase == "internal" else policy["baseline_min_free_mib"]
        path = Path(cfg["state_dir"]) / "cal-sessions" / ("resource-wait-" + uuid.uuid4().hex + ".json")
        start = time.monotonic()
        value = {"stage_receipt": stage_receipt.name, "started_at_utc": utc_now(), "elapsed_seconds": 0,
                 "language": language, "phase": phase, "required_free_mib": required}
        stable = 0
        try:
            while True:
                if self.remaining() <= 0 or (self.state / "stop.request").exists():
                    return False
                free = self.gpu.free_mib()
                value.update(available_free_mib=free, elapsed_seconds=time.monotonic() - start)
                self.common.write(path, value)
                stable = stable + 1 if free >= required else 0
                if stable >= policy["stable_samples"]:
                    return True
                if free < required:
                    self.stage = "waiting_gpu"
                    authorization = read(self.config["plan"])["close_vscode_authorized"]
                    close_after = datetime.fromisoformat(self.config.get("vscode_close_not_before_utc", "2000-01-01T00:00:00+00:00")).timestamp()
                    if authorization and time.time() >= close_after and not (self.state / "vscode_close.json").exists():
                        try:
                            result = close_vscode_window()
                        except Exception as failure:
                            result = {"error": type(failure).__name__ + ": " + str(failure)}
                        self.common.write(self.state / "vscode_close.json", {"at_utc": utc_now(), **result})
                        self.heartbeat(event=True)
                self.heartbeat()
                if time.monotonic() - start >= min(maximum, policy["maximum_wait_seconds"]):
                    raise ValueError("GPU wait exhausted; no model/runtime condition was changed")
                time.sleep(policy["poll_seconds"])
        finally:
            value.update(finished_at_utc=utc_now(), elapsed_seconds=time.monotonic() - start)
            self.common.write(path, value)

    def collect(self, cfg_path):
        cfg = read(cfg_path)
        run = Path(cfg["cal_run"])
        receipts = Path(cfg["state_dir"]) / "cal-sessions"
        receipts.mkdir(parents=True, exist_ok=True)
        for phase in ["baseline", "internal"]:
            for index in range(4):
                for language in ["en", "ja"]:
                    if self.remaining() <= 0 or (self.state / "stop.request").exists():
                        return False
                    receipt = receipts / f"{language}-{phase}-{index}.json"
                    while True:
                        spent = sum(read(p).get("elapsed_seconds", 0) for p in receipts.glob("*.json"))
                        stage_spent = sum(read(p).get("elapsed_seconds", 0) for p in receipts.glob("*.json")
                                          if read(p).get("stage_receipt") == receipt.name or
                                          p.name.startswith(receipt.stem + ".startup-failure-"))
                        limit = min(43200 - stage_spent, 259200 - spent)
                        if limit <= 0:
                            raise ValueError("Preregistered stage/batch wall budget exhausted")
                        fresh = not receipt.exists()
                        if fresh:
                            before = self.gpu.raw_snapshot(run / language)
                            wait_started = time.monotonic()
                            if not self.wait_gpu(cfg, language, phase, receipt, limit):
                                return False
                            limit -= time.monotonic() - wait_started
                            if limit <= 0:
                                raise ValueError("GPU wait exhausted the stage wall budget")
                        self.stage = "collect_" + phase
                        try:
                            self.child(cfg_path, "stage", receipt=receipt, timeout=limit,
                                       language=language, phase=phase)
                            break
                        except ValueError:
                            if self.remaining() <= 0 or (self.state / "stop.request").exists():
                                self.gpu.raw_snapshot(run / language)
                                return False
                            if not fresh:
                                raise
                            # This function rejects changed/unknown native outcomes and all
                            # failures except explicit CUDA model-loading OOM before requests.
                            self.gpu.archive_startup_oom(cfg, receipt, before, language, phase)
                    # Integrity checks are performed only after the child exited.
                    self.gpu.raw_snapshot(run / language)
                self.heartbeat(event=True)
        self.child(cfg_path, "finish-collection", receipt=Path(cfg["state_dir"]) / "steps/finish.json", timeout=3600)
        return True

    def serve(self):
        from rag_research.experiments.storage import run_lock
        with run_lock(self.state / "workflow-lock"):
            self.common.write(self.state / "owner.json", self.common.identity(os.getpid()))
            self.heartbeat(event=True)
            try:
                for cfg_path in map(Path, self.config["batches"]):
                    cfg = read(cfg_path)
                    self.batch = cfg["batch_id"]
                    self.stage = "preflight"
                    self.heartbeat(event=True)
                    self.child(cfg_path, "preflight", receipt=Path(cfg["state_dir"]) / "steps/preflight.json", timeout=3600)
                    if not self.collect(cfg_path):
                        self.stage = "collection_cutoff"
                        self.heartbeat(event=True)
                        break
                    for action, timeout, cpu in [("review", 86400, False), ("analyze", 3600, False), ("export", 3600, True)]:
                        self.stage = action
                        self.heartbeat(event=True)
                        self.child(cfg_path, action, receipt=Path(cfg["state_dir"]) / "steps" / (action + ".json"),
                                   timeout=timeout, cpu=cpu)
                        self.heartbeat(event=True)
                    self.stage = "verify_git_copy"
                    self.heartbeat(event=True)
                    self.verify_git_copy(cfg)
                    self.heartbeat(event=True)
                self.stage = "finalizing"
                self.heartbeat(event=True)
                command = [self.config["cpu_python"], str(Path(self.config["helper_dir"]) / "materials.py"),
                           "--finish", str(self.state / "config.json")]
                self.common.run_owned(command, cwd=self.config["checkout"], receipt=self.state / "finalize.json",
                                      timeout=3600, heartbeat=self.heartbeat)
                complete = all((Path(p).parent / "steps/export.json").exists() and
                    read(Path(p).parent / "steps/export.json").get("exit_code") == 0 for p in self.config["batches"])
                self.stage = "complete" if complete else "complete_with_uncollected_batches"
                self.heartbeat(event=True)
                self.verify_final_git_copy()
            except BaseException as failure:
                self.stage = "failed"
                (self.state / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
                self.heartbeat(event=True, error=type(failure).__name__ + ": " + str(failure)[:700])
                raise

    def verify_git_copy(self, cfg):
        spec = importlib.util.spec_from_file_location("extension_materials", Path(self.config["helper_dir"]) / "materials.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.verify_remote(self.config, [cfg["batch_id"]])
        self.common.write(Path(self.config["repo"]) / "reports/cal_extension_v1" / cfg["batch_id"] / "git_verification.json", result)

    def verify_final_git_copy(self):
        spec = importlib.util.spec_from_file_location("extension_materials", Path(self.config["helper_dir"]) / "materials.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        ids = [read(p)["batch_id"] for p in self.config["batches"] if (Path(p).parent / "steps/export.json").exists()]
        self.common.write(self.state / "final_git_verification.json", module.verify_remote(self.config, ids, final=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--post-stop", action="store_true")
    args = parser.parse_args()
    config = read(args.config)
    if args.status:
        print(json.dumps(read(Path(config["state_dir"]) / "status.json"), ensure_ascii=False, indent=2))
        return
    common, _ = modules(config)
    if args.config.with_suffix(".sha256").read_text().strip() != common.sha(args.config):
        raise ValueError("Extension config changed")
    for path, expected in config["sealed_files"].items():
        if common.sha(path) != expected:
            raise ValueError("Frozen controller changed: " + path)
    for path, expected in config["batch_config_hashes"].items():
        if common.sha(path) != expected:
            raise ValueError("Frozen batch configuration changed")
    sys.path.insert(0, str(Path(config["checkout"]) / "src"))
    flow = Workflow(config)
    if args.post_stop:
        status = read(Path(config["state_dir"]) / "status.json")
        if status["stage"] not in ["complete", "complete_with_uncollected_batches", "failed"]:
            flow.stage = "unexpected_service_exit"
            flow.heartbeat(event=True, error="Service exited before completion; inspect durable receipts; no request was automatically resubmitted")
    else:
        flow.serve()


if __name__ == "__main__":
    main()
