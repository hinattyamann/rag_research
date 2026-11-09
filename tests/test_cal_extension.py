"""Regression checks for unattended collection boundaries and export integrity."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location("extension_test_" + name, ROOT / "scripts/cal_extension" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_counts_tolerate_in_flight_partial_json_without_validation(tmp_path):
    service = module("service")
    folder = tmp_path / "en/baseline/q1"
    folder.mkdir(parents=True)
    (folder / "record.json").write_text('{"status":')
    value = service.safe_counts(tmp_path)
    assert value["in_flight_or_unreadable"] == 1
    assert value["baseline_ok"] == value["baseline_failed"] == 0


def test_live_record_is_not_a_confirmed_unknown_outcome(tmp_path):
    service = module("service")
    folder = tmp_path / "ja/baseline/q1"
    folder.mkdir(parents=True)
    (folder / "record.json").write_text(json.dumps({"status": "started"}))
    assert service.safe_counts(tmp_path)["in_flight_or_unreadable"] == 1


def test_monitor_log_failure_cannot_escape_heartbeat(tmp_path):
    service = module("service")
    flow = service.Workflow.__new__(service.Workflow)
    flow.state = tmp_path / "nonexistent"
    flow.stage, flow.batch, flow.last_status = "collect_internal", "batch_01", 0
    flow.config = {"batches": [str(tmp_path / "missing.json")]}
    flow.heartbeat(event=True)


def test_heartbeat_exception_does_not_abort_owned_child(tmp_path, monkeypatch):
    service = module("service")
    sys.path.insert(0, str(ROOT / "scripts/fixed_v23_automation"))
    import common

    flow = service.Workflow.__new__(service.Workflow)
    flow.state = tmp_path
    flow.stage, flow.batch, flow.last_status = "collect_internal", "batch_01", 0
    flow.config = {"batches": [str(tmp_path / "missing-config.json")]}
    flow.common = common
    result = common.run_owned([sys.executable, "-c", "print('finished')"], cwd=tmp_path,
        receipt=tmp_path / "receipt.json", timeout=3, heartbeat=flow.heartbeat)
    assert result["exit_code"] == 0
    assert (tmp_path / "monitor-errors.log").exists()


def test_git_publication_failure_preserves_collection(tmp_path, monkeypatch):
    service = module("service")
    sys.path.insert(0, str(ROOT / "scripts/fixed_v23_automation"))
    import common

    (tmp_path / "docs").mkdir()
    path = tmp_path / "batch.json"
    common.write(path, {"batch_id": "batch_01", "cal_run": str(tmp_path / "run")})
    flow = service.Workflow.__new__(service.Workflow)
    flow.state, flow.common = tmp_path, common
    flow.config = {"batches": [str(path)], "repo": str(tmp_path), "collection_cutoff_utc": "2099-01-01T00:00:00+00:00"}
    flow.stage, flow.batch, flow.last_status = "collect_baseline", "batch_01", 0
    monkeypatch.setattr(service, "publish", lambda c: (_ for _ in ()).throw(ValueError("synthetic remote failure")))
    flow.heartbeat(event=True)
    assert common.read(tmp_path / "git_publication.json")["pushed"] is False
    assert common.read(tmp_path / "status.json")["stage"] == "collect_baseline"


def test_verifier_adaptation_keeps_scientific_checks_and_only_cal(tmp_path):
    materials = module("materials")
    original = ROOT / "papers/iciae2027/materials/fixed_v23_v1/verify_materials.py"
    adapted = materials.verifier_text(original)
    compile(adapted, "adapted-verifier", "exec")
    assert 'len(qa) == 40' in adapted and '== 440' in adapted
    assert 'for cohort in ("main", "cal")' not in adapted
    for check in ["F from fixed labels", "Quality Y differs", "Route cost ", "Unit quote is not actual verbatim context",
                  "Bootstrap/original statistics differ", "Unknown value was imputed"]:
        assert check in adapted


def test_verifier_refuses_changed_template(tmp_path):
    materials = module("materials")
    path = tmp_path / "changed.py"
    path.write_text("print('changed upstream')")
    with pytest.raises(ValueError, match="contract changed"):
        materials.verifier_text(path)


def test_selection_plan_balanced_unique_and_disjoint():
    path = ROOT / "data/manifests/cal_extension_plan_v1.json"
    if not path.exists():
        pytest.skip("Lab registration has not been generated")
    plan = json.loads(path.read_text())
    assert plan["planned_qa"] == 120 and plan["planned_per_language"] == 60
    assert plan["source_splits"] == {"en": "development", "ja": "calibration"}
    old = set(plan["old_main_cal_selected_ids"])
    for language in ["en", "ja"]:
        rows = plan["source_selection"][language]["selected"]
        assert len(rows) == len({r["record_id"] for r in rows}) == len({r["document_group_id"] for r in rows}) == 60
        assert not old.intersection(r["record_id"] for r in rows)
        assert plan["source_selection"][language]["selected_group_overlap_with_used_or_reserved"] == 0


def test_native_oom_retry_policy_is_finite_and_no_request_retries():
    path = ROOT / "data/manifests/cal_extension_plan_v1.json"
    if not path.exists():
        pytest.skip("Lab registration has not been generated")
    plan = json.loads(path.read_text())
    assert plan["startup_oom_retries_only_before_native_request"] == 2
    assert plan["native_request_retries"] == 0 and plan["maximum_native_calls"] == 9960
    assert plan["maximum_cli_invocations"] == 288 and plan["api_billing_allowed"] is False


def test_cutoff_prevents_starting_another_batch(tmp_path):
    service = module("service")
    flow = service.Workflow.__new__(service.Workflow)
    flow.config = {"collection_cutoff_utc": "2000-01-01T00:00:00+00:00"}
    assert flow.remaining() < 0


def test_wait_gpu_records_cost_even_when_cutoff_reached(tmp_path):
    service = module("service")
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
    flow = service.Workflow.__new__(service.Workflow)
    flow.common = SimpleNamespace(write=write)
    flow.state = tmp_path
    flow.config = {"collection_cutoff_utc": "2000-01-01T00:00:00+00:00"}
    config = {"state_dir": str(tmp_path), "cal_gpu_policy": {"internal_min_free_mib": 7100}}
    assert flow.wait_gpu(config, "en", "internal", tmp_path / "stage.json", 10) is False
    receipt = next((tmp_path / "cal-sessions").glob("resource-wait-*.json"))
    value = json.loads(receipt.read_text())
    assert value["elapsed_seconds"] >= 0 and value["finished_at_utc"]


def test_deployment_refuses_any_existing_research_record(tmp_path):
    deploy = module("deploy")
    run = tmp_path / "run"
    folder = run / "en/baseline/q1"
    folder.mkdir(parents=True)
    (folder / "record.json").write_text('{}')
    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps({"cal_run": str(run)}))
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"batches": [str(batch)]}))
    with pytest.raises(ValueError, match="after any research record"):
        deploy.deploy(config)


def parent_fixture(tmp_path):
    provenance = module("provenance")
    body = "first part second part"
    parent_hash = provenance.digest(body)
    rows = []
    for pid, text, start in [("child-1", "first part ", 0), ("child-2", "second part", 11)]:
        rows.append({"passage_id": pid, "text": text, "text_sha256": provenance.digest(text),
            "parent_passage_id": "original-parent", "parent_text_sha256": parent_hash,
            "title": "Example source", "language": "en", "source_char_span": {"start": start, "end": start + len(text)}})
    parent = {"parent_passage_id": "original-parent", "parent_text_sha256": parent_hash,
              "child_passage_ids": ["child-1", "child-2"]}
    def asset(name, values):
        path = tmp_path / name
        path.write_text("".join(json.dumps(v) + "\n" for v in values))
        return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    spec = {"corpus": asset("corpus.jsonl", rows), "parent_map": asset("parents.jsonl", [parent])}
    empty = {"corpus": asset("empty.jsonl", []), "parent_map": asset("empty-parents.jsonl", [])}
    return provenance, rows, parent, {"datasets": {"en": spec, "ja": empty}}


def test_split_gold_parent_reconstructed_without_aliasing_child_ids(tmp_path):
    provenance, rows, parent, assets = parent_fixture(tmp_path)
    metadata, bodies = provenance.selected_sources(tmp_path, assets,
        {"en": {"original-parent", "child-1"}, "ja": set()}, lambda p, role: {"role": role})
    assert bodies["en", "original-parent"] == "first part second part"
    assert metadata["en", "original-parent"]["child_passage_ids"] == ["child-1", "child-2"]
    assert metadata["en", "child-1"]["passage_id"] == "child-1"
    qa = {"corpus_documents": [{"passage_id": pid, "text": text, "source_metadata": metadata[lang, pid]}
                               for (lang, pid), text in bodies.items()]}
    provenance.verify_parent_sources(qa)
    qa["corpus_documents"][0]["text"] += "tampered"
    with pytest.raises(ValueError, match="provenance differs|checksum differs"):
        provenance.verify_parent_sources(qa)


@pytest.mark.parametrize("fault", ["gap", "checksum", "missing-child", "wrong-parent"])
def test_invalid_parent_provenance_is_not_silently_filled(tmp_path, fault):
    provenance, rows, parent, assets = parent_fixture(tmp_path)
    if fault == "gap":
        rows[1]["source_char_span"]["start"] += 1
    elif fault == "checksum":
        parent["parent_text_sha256"] = "0" * 64
    elif fault == "wrong-parent":
        rows[1]["parent_passage_id"] = "different-parent"
    else:
        rows.pop()
    for key, values in [("corpus", rows), ("parent_map", [parent])]:
        spec = assets["datasets"]["en"][key]
        path = tmp_path / spec["path"]
        path.write_text("".join(json.dumps(v) + "\n" for v in values))
        spec["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="Parent|parent"):
        provenance.selected_sources(tmp_path, assets, {"en": {"original-parent"}, "ja": set()}, lambda p, role: {})


def test_missing_id_does_not_fabricate_provenance(tmp_path):
    provenance, rows, parent, assets = parent_fixture(tmp_path)
    with pytest.raises(ValueError, match="Missing selected passage provenance"):
        provenance.selected_sources(tmp_path, assets, {"en": {"unknown"}, "ja": set()}, lambda p, role: {})
