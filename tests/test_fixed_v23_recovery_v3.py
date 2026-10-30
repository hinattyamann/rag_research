"""External cancellation: one identical-input reexecution, no lost costs or repeated completed work."""

import importlib.util
from pathlib import Path

import pytest
from test_bilingual_pipeline import connection, registry  # noqa: F401

from rag_research.experiments.bilingual_budget import budget_snapshot
from rag_research.experiments.frozen_trace import digest
from rag_research.experiments.storage import read_json, write_json
from rag_research.retrieval.common import file_hash

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("external_recovery_v3", REPO / "scripts/recover_fixed_v23_v3.py")
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


@pytest.mark.parametrize("drift", [False, True])
def test_real_saved_trials_reused_and_only_interrupted_rewrite_reexecuted(connection, monkeypatch, drift):  # noqa: F811
    config_path, output, state = connection
    root, run = config_path.parent, output.parent
    base = recovery.parent_module(REPO)
    monkeypatch.setattr(base, "ROOT", root)
    monkeypatch.setattr(recovery, "RUN", str(run.relative_to(root)))
    runner = base.runner
    # Restore the shared runner when this test's installed adapter is torn down.
    monkeypatch.setattr(runner, "rewrite_once", runner.rewrite_once)
    contract = runner.load_config(config_path)
    config, _, rows, _, _, _, _, _ = contract
    config.update(verification_mode="claimwise-v1", main_limits={
        "maximum_completion_attempts": 1660, "maximum_new_qa_per_stage_session": 5})
    runner.run(config_path, output, stage="baseline")
    manifest = read_json(output / "manifest.json")
    folder = output / "internal" / digest(rows[0]["record_id"])[:24]
    target = folder / "rewrite.json"
    monkeypatch.setattr(recovery, "TARGET", str(target.relative_to(run)))
    original_server = runner.LocalServer
    cancelled = []

    class Server:
        def __init__(self, *a, **kw):
            self.server = original_server(*a, **kw)

        def __enter__(self):
            self.server.__enter__()
            self.client = self.server.client
            complete = self.client.complete

            def call(*a, **kw):
                if self.client.messages[0]["content"] == "rewrite_answer" and not cancelled:
                    cancelled.append(True)
                    raise KeyboardInterrupt("Synthetic external monitoring cancellation")
                return complete(*a, **kw)

            self.client.complete = call
            return self

        def __exit__(self, *a):
            return self.server.__exit__(*a)

        def report(self):
            return self.server.report()

    monkeypatch.setattr(runner, "LocalServer", Server)
    with pytest.raises(KeyboardInterrupt):
        base.internal_stage(output, contract, manifest)
    old = read_json(target)
    assert old["status"] == "started" and old["completion_attempted"]
    assert all(t["status"] == "ok" for t in read_json(folder / "summary.json")["trials"])
    assert len(budget_snapshot(output)["unknown_or_interrupted_paths"]) == 1
    protected = {p: file_hash(p) for p in output.rglob("*.json")
                 if p != target and p.name != "progress.json"}
    archived = run / recovery.ARCHIVE
    archived.parent.mkdir(parents=True)
    target.rename(archived)
    old_bytes = archived.read_bytes()
    write_json(root / base.REGISTRATION, {"synthetic_parent_only": True})
    monkeypatch.setattr(recovery, "registration", lambda root: {})
    monkeypatch.setattr(recovery, "external_attempts", lambda path: [{"synthetic_cancelled": True}] if path.name == "ja" else [])
    base = recovery.configure(base)
    assert not base.reserve(output, 1660)["unknown_or_interrupted_paths"]
    with pytest.raises(Exception, match="budget"):
        base.reserve(output, budget_snapshot(output)["recorded_native_attempts_upper_bound"], 1)
    if drift:
        changed = read_json(archived)
        changed["settings"]["seed"] = 99
        write_json(archived, changed)
    before = len(state["calls"])
    if drift:
        with pytest.raises(ValueError, match="Unclassified rewrite"):
            base.internal_stage(output, contract, manifest)
        assert "input differs" in read_json(target)["error"]
        assert len(state["calls"]) == before and not (run / recovery.RECEIPT).exists()
        return
    result = base.internal_stage(output, contract, manifest)
    assert result["stage_complete"] and result["rewrite_failed_qa"] == 0
    assert len(state["calls"]) == before + 1
    new = read_json(target)
    assert new["status"] == "ok" and new["request_sha256"] == old["request_sha256"]
    assert archived.read_bytes() == old_bytes
    assert all(file_hash(p) == value for p, value in protected.items())
    assert read_json(run / recovery.RECEIPT)["state"] == "reexecution_reserved"
    assert base.internal_stage(output, contract, manifest) == result
    assert len(state["calls"]) == before + 1
    # A removed active journal still cannot authorize a second replacement call.
    target.unlink()
    with pytest.raises(ValueError, match="Do not resubmit"):
        base.internal_stage(output, contract, manifest)
    assert len(state["calls"]) == before + 1


def test_registration_preserves_archive_source_log_and_completed_results(tmp_path, monkeypatch):
    run = tmp_path / recovery.RUN
    run.mkdir(parents=True)

    def spec(name, value):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, value)
        return {"path": name, "sha256": file_hash(path)}

    archived = run / recovery.ARCHIVE
    archived.parent.mkdir(parents=True)
    write_json(archived, {"status": "started", "task": "rewrite_answer", "completion_attempted": True,
        "output_tokens": None, "request_sha256": "same-input", "input_tokens": 3211})
    monkeypatch.setattr(recovery, "TARGET_SHA", file_hash(archived))
    log = run / "ja/internal/server-2.log"
    log.parent.mkdir(parents=True)
    write_json(log, {"synthetic_cancelled_session": True})
    saved = run / "ja/internal/completed.json"
    write_json(saved, {"preserved": True})
    value = {"version": recovery.VERSION, "run": recovery.RUN, "target": recovery.TARGET,
        "maximum_external_reexecutions": 1, "phase12_allowed": False, "user_authorized_reexecution": True,
        "entrypoint": spec("scripts/new.py", {}), "wrapper": spec("new.sh", {}),
        "parent_registration": spec(recovery.PARENT, {}), "parent_entrypoint": spec("scripts/old.py", {}),
        "archived_request": {"path": recovery.ARCHIVE, "sha256": file_hash(archived)},
        "server_log": {"path": str(log.relative_to(run)), "sha256": file_hash(log)},
        "protected_scientific_files": {str(saved.relative_to(run)): file_hash(saved)}}
    write_json(tmp_path / recovery.REGISTRATION, value)
    assert recovery.registration(tmp_path) == value
    attempt = recovery.external_attempts(run / "ja")[0]
    assert attempt["cost_incomplete"] and attempt["response_unknown"] and attempt["output_tokens"] is None
    assert recovery.external_attempts(run / "en") == []
    saved.write_text("changed")
    with pytest.raises(ValueError, match="Preserved"):
        recovery.registration(tmp_path)
