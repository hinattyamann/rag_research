"""Refusal, omission, provenance and semantic-tamper tests on the actual export."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


verifier = module("verify_materials")
builder = module("build_materials")


@pytest.fixture
def material_copy(tmp_path):
    target = tmp_path / "standalone"
    shutil.copytree(HERE, target, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache"))
    return target


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_full_pack_verifies_without_original_repository_paths(material_copy):
    result = verifier.verify(material_copy)
    assert result["qa"] == 80 and result["planned_trials"] == 706
    assert result["candidate_stage_assignments"] == 156 and result["policy_slots"] == 880
    assert result["observed_policy_outcomes"] == 864 and result["cases"] == 4
    assert result["original_run_access_required"] is False


@pytest.mark.parametrize("bad", ["missing", "extra", "changed", "escaping_manifest"])
def test_file_inventory_and_hashes_reject_missing_extra_changed_or_escaping_files(material_copy, bad):
    path = material_copy / "qa_summary.csv"
    if bad == "missing":
        path.unlink()
    elif bad == "extra":
        (material_copy / "unregistered.txt").write_text("not part of the export")
    elif bad == "changed":
        path.write_text(path.read_text() + "altered")
    else:
        value = json.loads((material_copy / "artifact_manifest.json").read_text())
        value["files"]["../outside.json"] = {"bytes": 1, "sha256": "fake"}
        write_json(material_copy / "artifact_manifest.json", value)
    with pytest.raises(ValueError):
        verifier.verify(material_copy)


@pytest.mark.parametrize("bad", ["trial_F", "null_quality", "alias_omission", "source_QA", "used_context", "case_cost"])
def test_semantic_checks_reject_tampering_even_after_rehashing_derived_files(material_copy, bad):
    if bad == "trial_F":
        path = material_copy / "trials.jsonl"
        values = verifier.rows(path)
        row = next(t for t in values if t["score"] is not None)
        row["score"] = 0.123456
        builder.jsonl(path, values)
    elif bad in {"null_quality", "alias_omission"}:
        path = material_copy / "policy_outcomes.csv"
        values = verifier.csv_rows(path)
        if bad == "null_quality":
            row = next(r for r in values if r["quality_status"] == "indeterminate")
            row["quality_y"] = "0"
        else:
            row = next(r for r in values if r["policy_state"] == "omitted_duplicate_order_alias")
            row["policy_state"] = "observed"
        builder.table(path, values)
    elif bad in {"source_QA", "used_context"}:
        path = next((material_copy / "inputs").glob("*.json"))
        value = json.loads(path.read_text())
        if bad == "source_QA":
            value["qa_source"]["reference_answers"] = ["invented answer"]
        else:
            value["used_documents"][0]["text"] = "invented source text"
        write_json(path, value)
    else:
        path = material_copy / "cases/index.json"
        value = json.loads(path.read_text())
        value["cases"][0]["policy_outcomes"][0]["input_tokens"] = 999999
        write_json(path, value)
        write_json(material_copy / "cases" / (value["cases"][0]["case_id"] + ".json"), value["cases"][0])
    builder.artifact_manifest(material_copy)
    with pytest.raises(ValueError):
        verifier.verify(material_copy)


def test_verifier_relative_path_guard_rejects_absolute_and_parent_paths(tmp_path):
    for value in ("../secret", "/etc/passwd"):
        with pytest.raises(ValueError):
            verifier.path_in(tmp_path, value)
