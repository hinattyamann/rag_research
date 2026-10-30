"""One authorized reexecution after a proven monitoring cancellation; preserve every attempt."""

import argparse
import importlib.util
import json
import os
import shlex
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMPORT_ROOT = (Path(sys.argv[sys.argv.index("--checkout") + 1]).resolve()
               if len(sys.argv) > 1 and sys.argv[1] == "prepare" and "--checkout" in sys.argv else ROOT)
sys.path.insert(0, str(IMPORT_ROOT / "src"))

from rag_research.experiments.bilingual_budget import budget_snapshot  # noqa: E402
from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.storage import (  # noqa: E402
    checkpoint,
    read_json,
    run_lock,
    verify_checkpoint,
    write_json,
)
from rag_research.retrieval.common import file_hash  # noqa: E402

VERSION = "fixed-v23-external-interruption-reexecution-v3"
REGISTRATION = "fixed-v23-recovery-v3.json"
PARENT = "fixed-v23-recovery-v2.json"
RUN = "data/runs/bilingual_development/fixed-v23-main-v1"
TARGET = "ja/internal/4c57945331dd21845abdf886/rewrite.json"
TARGET_SHA = "a9197387192b1f488b4dcab03a61a954ee91ff9cd559264672b596834a67f76d"
ARCHIVE = "external_interruptions/monitor-cancellation-v1/request.started.json"
RECEIPT = "external_interruptions/monitor-cancellation-v1/reexecution.json"


def parent_module(root):
    spec = importlib.util.spec_from_file_location("original_recovery_v2_for_v3", root / "scripts/recover_fixed_v23_v2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def registration(root):
    value = read_json(root / REGISTRATION)
    require(value["version"] == VERSION and value["run"] == RUN and value["target"] == TARGET
            and value["archived_request"]["sha256"] == TARGET_SHA
            and value["maximum_external_reexecutions"] == 1 and value["phase12_allowed"] is False
            and value["user_authorized_reexecution"] is True, "External reexecution registration changed")
    for spec in (value["entrypoint"], value["wrapper"], value["parent_registration"], value["parent_entrypoint"]):
        require(file_hash(root / spec["path"]) == spec["sha256"], "Registered recovery source changed")
    require(value["parent_registration"]["path"] == PARENT, "Wrong recovery parent")
    run = root / RUN
    require(value["archived_request"]["path"] == ARCHIVE and file_hash(run / ARCHIVE) == TARGET_SHA,
            "Original interrupted request changed")
    require(file_hash(run / value["server_log"]["path"]) == value["server_log"]["sha256"], "Cancellation log changed")
    for name, expected in value["protected_scientific_files"].items():
        require(file_hash(run / name) == expected, "Preserved pre-reexecution result changed: " + name)
    old = read_json(run / ARCHIVE)
    require(old["status"] == "started" and old["task"] == "rewrite_answer"
            and old["completion_attempted"] is True and old.get("output_tokens") is None
            and not old.get("runtime_response"), "Only the interrupted, unreceived rewrite may be reexecuted")
    return value


def external_attempts(language_run):
    """Historical uncertainty is separate from active task outcomes, never erased."""
    language_run = Path(language_run).resolve()
    root = next((p for p in language_run.parents if (p / REGISTRATION).is_file()), None)
    require(root is not None, "Missing registered external attempt")
    value = registration(root)
    require(language_run.parent == root / RUN and language_run.name in {"en", "ja"}, "Wrong external attempt scope")
    if language_run.name == "en":
        return []
    old = read_json(language_run.parent / ARCHIVE)
    return [{"language": "ja", "stage": "internal", "archive": ARCHIVE, "sha256": TARGET_SHA,
        "request_sha256": old["request_sha256"], "completion_attempted": True,
        "input_tokens": old["input_tokens"], "output_tokens": None, "elapsed_seconds": None,
        "cost_incomplete": True, "response_unknown": True,
        "server_log": str(Path(value["server_log"]["path"]).relative_to("ja")),
        "server_log_sha256": value["server_log"]["sha256"]}]


def configure(base):
    """Change control callbacks only; use the unchanged sealed inference implementation."""
    root = base.ROOT
    original_validate, original_reserve = base.validate, base.reserve
    original_public, original_enrich = base.public, base.enrich
    original_rewrite = base.runner.rewrite_once

    def validate(output, *, check_budget=True):
        result = original_validate(output, check_budget=False)
        registration(root)
        if check_budget:
            for language in ("en", "ja"):
                reserve(result[0] / language, 1660)
        return result

    def reserve(language_run, ceiling, needed=0):
        overhead = len(external_attempts(language_run))
        result = original_reserve(language_run, ceiling, needed + overhead)
        return {**result, "historical_external_attempts": overhead,
            "total_attempts_including_external": result["recorded_native_attempts_upper_bound"] + overhead}

    def missing(output):
        # A live journal has no completed-checkpoint hash yet.
        count = 0
        for language in ("en", "ja"):
            for path in (output / language / "internal").glob("*/rewrite.json"):
                task = read_json(path)
                if task.get("status") == "started":
                    continue
                verify_checkpoint(task)
                summary = path.parent / "summary.json"
                count += bool(base.rewrite_limit(task) and summary.exists() and all(
                    t["status"] in {"ok", "not_applicable"} for t in read_json(summary)["trials"]))
        return count

    def enrich(output, value):
        value = original_enrich(output, value)
        old = read_json(output / ARCHIVE)
        value.update(recovery_protocol=VERSION, active_attempts=value["attempts"],
            attempts=value["attempts"] + 1, archived_external_attempts=1,
            historical_unknown_responses=1, external_reexecutions_started=int((output / RECEIPT).exists()),
            input_tokens=value["input_tokens"] + old["input_tokens"], token_totals_complete=False,
            total_output_tokens=None, external_interruption_is_candidate_missing=False)
        if value["state"] in {"collecting", "recovery_ready", "stopped"}:
            action = "status" if value["state"] == "collecting" else "resume"
            value["next_action"] = shlex.join([str(root / "fixed-v23-recover-v3.sh"), action, "--run", str(output)])
        return value

    def public(output, state, reason=None):
        value = original_public(output, state, reason)
        # original_public dispatches the installed enrich, including the historical cost.
        value["external_reexecution_registration"] = {"path": REGISTRATION, "sha256": file_hash(root / REGISTRATION)}
        write_json(output / "status.public.json", value)
        return value

    class ReexecutionClient:
        def __init__(self, client, path):
            self.client, self.path = client, path

        def __getattr__(self, name):
            return getattr(self.client, name)

        def complete(self, *args, **kwargs):
            registration(root)
            run = root / RUN
            old, new = read_json(run / ARCHIVE), read_json(self.path)
            require(all(new.get(k) == old.get(k) for k in ("request_sha256", "binding", "messages", "settings",
                "prompt_tokens", "rendered_prompt_sha256", "input_tokens")), "Reexecution input differs from interrupted request")
            require(not (run / RECEIPT).exists(), "The single external reexecution has already been reserved")
            checkpoint(run / RECEIPT, {"version": VERSION, "original_request_sha256": TARGET_SHA,
                "new_request_sha256": new["request_sha256"], "state": "reexecution_reserved",
                "started_at_utc": new["started_at_utc"], "pid": os.getpid(), "maximum_reexecutions": 1})
            return self.client.complete(*args, **kwargs)

    def rewrite(client, config, prompts, trace, path, binding):
        if Path(path).resolve() == (root / RUN / TARGET).resolve() and not path.exists():
            require(not (root / RUN / RECEIPT).exists(), "Do not resubmit the external reexecution")
            client = ReexecutionClient(client, path)
        return original_rewrite(client, config, prompts, trace, path, binding)

    base.validate, base.reserve = validate, reserve
    base.rewrite_missing_count, base.enrich, base.public = missing, enrich, public
    base.runner.rewrite_once = rewrite
    base.command = lambda output, action: shlex.join([str(root / "fixed-v23-recover-v3.sh"), action, "--run", str(output)])
    base.__file__ = str(root / "scripts/recover_fixed_v23_v3.py")
    return base


def prepare(root, incident_path):
    root = root.resolve()
    run = root / RUN
    base = parent_module(root)
    base.validate(run, check_budget=False)
    require(not (root / REGISTRATION).exists(), "Preserve an existing reexecution registration")
    with run_lock(run):
        control = read_json(run / "control.json")
        require(not base.legacy.alive(control.get("supervisor", {})) and not base.legacy.alive(control.get("child", {})),
                "Do not prepare while collection is running")
        snapshots = {lang: budget_snapshot(run / lang) for lang in ("en", "ja")}
        unknown = [(lang, name) for lang, value in snapshots.items() for name in value["unknown_or_interrupted_paths"]]
        require(unknown == [("ja", str(Path(TARGET).relative_to("ja")))], "Only the registered interruption is eligible")
        incident = read_json(incident_path)
        require(incident["unknown_outcomes"] == [{"language": "ja", "path": str(Path(TARGET).relative_to("ja")),
            "sha256": TARGET_SHA}] and incident["last_child_exit_code"] == -15
            and incident["original_835_scientific_files_unchanged"] is True
            and incident["supervisor_log_sha256"] == file_hash(run / "supervisor.log"), "Cancellation evidence changed")
        require(file_hash(run / TARGET) == TARGET_SHA, "The interrupted request differs")
        old = read_json(run / TARGET)
        folder = (run / TARGET).parent
        summary, trace = read_json(folder / "summary.json"), read_json(folder / "trace.json")
        require(summary["trace_sha256"] == old["binding"]["trace_sha256"] == trace["trace_sha256"]
                and len(summary["trials"]) == 9 and all(t["status"] == "ok" for t in summary["trials"]),
                "Resume only the rewrite after all saved internal evaluations")
        audit = run / "external_interruptions/monitor-cancellation-v1"
        require(not audit.exists(), "Preserve any partial preparation for explicit inspection")
        snapshot_dir = root / "data/runs/recovery_audits/fixed-v23-external-reexecution-v3"
        require(not snapshot_dir.exists(), "Preserve the pre-reexecution snapshot")
        shutil.copytree(run, snapshot_dir)
        hashes = {str(p.relative_to(run)): file_hash(p) for p in run.rglob("*") if p.is_file()}
        require(all(file_hash(snapshot_dir / name) == value for name, value in hashes.items()), "Snapshot differs")
        audit.mkdir(parents=True)
        shutil.copy2(run / TARGET, run / ARCHIVE)
        require(file_hash(run / ARCHIVE) == TARGET_SHA, "Interrupted request was not archived exactly")
        entry = root / "scripts/recover_fixed_v23_v3.py"
        require(not entry.exists(), "Preserve the registered entrypoint")
        shutil.copy2(Path(__file__), entry)
        wrapper = root / "fixed-v23-recover-v3.sh"
        wrapper.write_text((root / "fixed-v23-recover-v2.sh").read_text().replace(
            "scripts/recover_fixed_v23_v2.py", "scripts/recover_fixed_v23_v3.py"))
        wrapper.chmod(0o755)
        protected = {name: value for name, value in hashes.items()
            if Path(name).parts[0] in {"en", "ja"} and name != TARGET
            and Path(name).name not in {"progress.json", ".run.lock"}}
        def spec(path):
            return {"path": str(path.relative_to(root)), "sha256": file_hash(path)}
        value = {"version": VERSION, "run": RUN, "target": TARGET,
            "user_authorized_reexecution": True, "maximum_external_reexecutions": 1,
            "automatic_retries_after_this_exception": 0, "phase12_allowed": False,
            "entrypoint": spec(entry), "wrapper": spec(wrapper), "parent_registration": spec(root / PARENT),
            "parent_entrypoint": spec(root / "scripts/recover_fixed_v23_v2.py"),
            "archived_request": {"path": ARCHIVE, "sha256": TARGET_SHA},
            "server_log": {"path": "ja/internal/server-2.log", "sha256": file_hash(run / "ja/internal/server-2.log")},
            "protected_scientific_files": protected, "snapshot_file_count": len(hashes),
            "snapshot_manifest_sha256": base.digest(hashes), "snapshot_directory": str(snapshot_dir),
            "native_attempts_before": sum(v["recorded_native_attempts_upper_bound"] for v in snapshots.values()),
            "historical_unknown_response_cost_retained": True, "same_request_hash_required_before_send": True,
            "interrupted_request_not_a_missing_candidate": True, "new_native_calls_at_preparation": 0}
        write_json(root / REGISTRATION, value)
        write_json(audit / "snapshot_manifest.json", hashes)
        (run / TARGET).unlink()  # Sole authorized journal move; its exact bytes remain archived and snapshotted.
        fixed = configure(base)
        fixed.validate(run)
        fixed.public(run, "recovery_ready", "one_authorized_external_reexecution_same_input_no_new_candidate_missing")
    return value


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "prepare":
        parser = argparse.ArgumentParser()
        parser.add_argument("action")
        parser.add_argument("--checkout", type=Path, required=True)
        parser.add_argument("--incident", type=Path, required=True)
        args = parser.parse_args()
        value = prepare(args.checkout, args.incident)
        print(json.dumps({"prepared": True, "snapshot_files": value["snapshot_file_count"], "new_native_calls": 0}))
        return 0
    base = configure(parent_module(ROOT))
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        parser = argparse.ArgumentParser()
        parser.add_argument("action")
        parser.add_argument("--run", type=Path, required=True)
        args = parser.parse_args()
        output, study, _ = base.validate(args.run)
        with run_lock(output / "launch-lock"):
            control = read_json(output / "control.json")
            require(not base.legacy.alive(control.get("supervisor", {})) and not base.legacy.alive(control.get("child", {})),
                    "Another collector still owns this run")
            require(control["spent_wall_seconds"] < study["total_wall_seconds"], "Original wall budget exhausted")
            require(not (output / "stop.request").exists(), "Preserve an explicit stop request")
            token = uuid.uuid4().hex
            control.update(launch_token=token, recovery_protocol=VERSION)
            write_json(output / "control.json", control)
        return int(base.worker(output, token)["state"] == "failed")
    return base.main()


if __name__ == "__main__":
    sys.exit(main())
