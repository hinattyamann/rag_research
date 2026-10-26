"""Main configuration preparation must fail before new QA or Native work is touched."""

import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from rag_research.experiments.storage import checkpoint, write_json
from rag_research.retrieval.common import file_hash

SPEC = importlib.util.spec_from_file_location(
    "main_preparation", Path(__file__).resolve().parents[1] / "scripts/prepare_bilingual_main.py")
preparation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preparation)
PROJECT = Path(__file__).resolve().parents[1]


def invoke(root):
    return preparation.prepare(root / "data/runs/semantic_diagnostics/known/report.json",
        root / "configs/known.yaml", root / "configs/policy.json", root / "configs/selection-policy.json",
        root / "configs/assets.json", {lang: root / f"configs/{lang}.yaml" for lang in ("en", "ja")},
        root / "data/runs/bilingual_main_protocol/new")


@pytest.mark.parametrize("failure", ["missing", "partial", "failed", "unknown_cost", "missing_audit"])
def test_pending_known_never_reads_main_policy_templates_or_qa(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(preparation, "ROOT", tmp_path)
    run = tmp_path / "data/runs/semantic_diagnostics/known"
    run.mkdir(parents=True)
    report = {"diagnostic_gate_passed": True, "planned_conditions": 30, "completed_conditions": 30,
        "completion_attempts_recorded": 84, "not_attempted_ids": [], "cost_incomplete": False}
    if failure == "partial":
        report.update(completed_conditions=12, completion_attempts_recorded=42)
    elif failure == "failed":
        report["diagnostic_gate_passed"] = False
    elif failure == "unknown_cost":
        report["cost_incomplete"] = True
    if failure != "missing":
        write_json(run / "report.json", report)
    preserved = preparation.snapshot(run)
    original_read = preparation.read_json

    def read_only_terminal(path):
        assert path == run / "report.json", "must reject before reading any other input"
        return original_read(path)

    monkeypatch.setattr(preparation, "read_json", read_only_terminal)
    monkeypatch.setattr(preparation, "passing_known_regression", lambda *a: pytest.fail("must not replay"))
    monkeypatch.setattr(preparation, "select", lambda *a: pytest.fail("must not read unused QA"))
    monkeypatch.setattr(preparation, "load_config", lambda *a: pytest.fail("must not load Main"))
    with pytest.raises(ValueError, match="known|audit"):
        invoke(tmp_path)
    assert preparation.snapshot(run) == preserved
    assert not (tmp_path / "data/runs/bilingual_main_protocol").exists()


@pytest.mark.parametrize("versioned", [False, True])
def test_copied_adopted_conditions_replace_old_templates_without_changing_baseline_or_blind_review(versioned):
    prior = yaml.safe_load((PROJECT / "configs/phase11_semantic_candidate_v18.yaml").read_text())
    chain = {"autonomy_protocol_version": "phase11-autonomy-v3",
        "autonomy_protocol": {"path": "configs/protocol.json", "sha256": "a" * 64},
        "candidate_identity_sha256": "b" * 64}
    if versioned:
        prior.update(chain)
    original = deepcopy(prior)
    for language, name in (("en", "v2"), ("ja", "v1")):
        template = yaml.safe_load((PROJECT / f"configs/phase11_bilingual_connection_{language}_{name}.yaml").read_text())
        selected = [{"record_id": f"{language}-{i}"} for i in range(20)]
        config = preparation.configuration(template, prior, selected, language, "new-assets.json",
            {"path": "policy"}, {"path": "selection"}, {"path": "adoption"}, "test-main")
        for key in ("auxiliary_runtime", "tasks", "sampling", "execution", "verification_mode",
                    "output_constraints", "auxiliary_model_manifest", "trials", "errors"):
            assert config[key] == prior[key]
        for key in ("baseline_config", "baseline_prompts", "identity_manifest", "rewrite", "quality", "costs"):
            assert config[key] == template[key]
        assert config["prompts"] == prior["prompts"][language]
        assert config["assets"] == "new-assets.json"
        assert config["data"]["record_ids"] == [row["record_id"] for row in selected]
        assert config["decision"] == {**prior["decision"], "bare_refusal_policy": "rewrite_once"}
        if versioned:
            assert all(config[key] == value for key, value in chain.items())
            config["autonomy_protocol"]["sha256"] = "c" * 64
        assert config["purpose"] == template["purpose"] and "diagnostics" not in config
        config["sampling"]["top_k"] = 1
        assert prior == original


@pytest.fixture
def staged_inputs(tmp_path, monkeypatch):
    """Orchestration doubles only: never evidence that actual known or Main passed."""
    monkeypatch.setattr(preparation, "ROOT", tmp_path)
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    for name in ("known.yaml", "selection-policy.json", "assets.json"):
        (config_dir / name).write_text("synthetic fixed input")
    script = tmp_path / "scripts/prepare_bilingual_main.py"
    script.parent.mkdir()
    script.write_bytes(Path(preparation.__file__).read_bytes())
    monkeypatch.setattr(preparation, "__file__", str(script))
    prior = yaml.safe_load((PROJECT / "configs/phase11_semantic_candidate_v18.yaml").read_text())
    (config_dir / "candidate.yaml").write_text(yaml.safe_dump(prior))
    for language, name in (("en", "v2"), ("ja", "v1")):
        (config_dir / f"{language}.yaml").write_bytes(
            (PROJECT / f"configs/phase11_bilingual_connection_{language}_{name}.yaml").read_bytes())
    run = tmp_path / "data/runs/semantic_diagnostics/known"
    run.mkdir(parents=True)
    (run / ".run.lock").write_text("0")
    write_json(run / "report.json", {"diagnostic_gate_passed": True, "planned_conditions": 30,
        "completed_conditions": 30, "completion_attempts_recorded": 84,
        "not_attempted_ids": [], "cost_incomplete": False})
    write_json(run / "audit_check.json", {"aggregate_conditions": 30, "actual_leaf_calls": 84})
    sha = {"report.json": file_hash(run / "report.json")}
    write_json(run / "resume_check.json", {"new_calls": 0, "new_server_files": 0,
        "unchanged_files": 1, "sha256": sha})
    selection = checkpoint(tmp_path / "selection.json", {
        "policy_sha256": file_hash(config_dir / "selection-policy.json"),
        "assets_sha256": file_hash(config_dir / "assets.json"), "used_baseline_input_sha256": {},
        "languages": {lang: {"selected": [{"record_id": f"{lang}-{i}"} for i in range(20)]}
                      for lang in ("en", "ja")}})
    manifests = tmp_path / "data/manifests"
    manifests.mkdir()
    (tmp_path / "selection.json").rename(manifests / "selection.json")
    policy = yaml.safe_load((PROJECT / "configs/phase11_main_development_execution_policy_v1.json").read_text())
    policy.update(status="preregistered", candidate_config=preparation.binding(config_dir / "candidate.yaml"),
                  selection_manifest=preparation.binding(manifests / "selection.json"))
    write_json(config_dir / "policy.json", policy)
    calls = []

    def adoption(binding):
        copied = tmp_path / binding["path"]
        assert copied.parent != run and preparation.snapshot(copied.parent) == preparation.snapshot(run)
        calls.append("adoption-copy")
        return deepcopy(prior), {}

    def load(path):
        config = yaml.safe_load(path.read_text())
        assert config["adopted_known_regression"]["path"] != "data/runs/semantic_diagnostics/known/report.json"
        assert not (tmp_path / "data/runs/bilingual_main_protocol/new").exists()
        calls.append(config["language"])
        return config, None, [None] * 20

    monkeypatch.setattr(preparation, "passing_known_regression", adoption)
    monkeypatch.setattr(preparation, "select", lambda p: deepcopy(selection))
    monkeypatch.setattr(preparation, "load_config", load)
    return tmp_path, run, calls, selection


def test_publish_only_after_both_contracts_and_preserve_original_evidence(staged_inputs):
    root, run, calls, _ = staged_inputs
    before = preparation.snapshot(run)
    receipt = invoke(root)
    assert calls == ["adoption-copy", "en", "ja"]
    assert preparation.snapshot(run) == before
    assert receipt["new_model_calls"] == receipt["new_servers"] == 0
    for language, item in receipt["configs"].items():
        config = yaml.safe_load((root / item["path"]).read_text())
        assert config["adopted_known_regression"]["path"] == "data/runs/semantic_diagnostics/known/report.json"
        assert config["language"] == language and config["execution_scope"] == "main_development_v1"
    preserved = preparation.snapshot(root / "data/runs/bilingual_main_protocol/new")
    with pytest.raises(ValueError, match="preserve existing"):
        invoke(root)
    assert preparation.snapshot(root / "data/runs/bilingual_main_protocol/new") == preserved


def test_second_language_failure_publishes_neither_configuration(staged_inputs, monkeypatch):
    root, run, _, _ = staged_inputs
    before = preparation.snapshot(run)

    def fail_japanese(path):
        value = yaml.safe_load(path.read_text())
        if value["language"] == "ja":
            raise ValueError("Japanese contract rejected")
        return value, None, [None] * 20

    monkeypatch.setattr(preparation, "load_config", fail_japanese)
    with pytest.raises(ValueError, match="Japanese"):
        invoke(root)
    assert preparation.snapshot(run) == before
    assert not (root / "data/runs/bilingual_main_protocol/new").exists()


def test_changed_usage_cannot_reselect_or_refill(staged_inputs, monkeypatch):
    root, _, _, selection = staged_inputs
    fresh = deepcopy(selection)
    fresh["languages"]["en"]["selected"][0]["record_id"] = "replacement"
    monkeypatch.setattr(preparation, "select", lambda p: fresh)
    with pytest.raises(ValueError, match="never refill"):
        invoke(root)
    assert not (root / "data/runs/bilingual_main_protocol/new").exists()


def test_raw_adoption_failure_stops_before_qa_and_preserves_the_original(staged_inputs, monkeypatch):
    root, run, _, _ = staged_inputs
    before = preparation.snapshot(run)

    def rejected_raw(binding):
        copied = root / binding["path"]
        copied.write_text("copy altered by failed replay")
        raise ValueError("Raw known adoption rejected")

    monkeypatch.setattr(preparation, "passing_known_regression", rejected_raw)
    monkeypatch.setattr(preparation, "select", lambda *a: pytest.fail("must not read QA"))
    with pytest.raises(ValueError, match="Raw known adoption"):
        invoke(root)
    assert preparation.snapshot(run) == before
    assert not (root / "data/runs/bilingual_main_protocol/new").exists()


def test_old_candidate_or_weakened_policy_reject_before_unused_qa(staged_inputs, monkeypatch):
    root, _, _, _ = staged_inputs
    policy_path = root / "configs/policy.json"
    policy = preparation.read_json(policy_path)
    policy["semantic_adoption_after_blind_seal"]["maximum_definite_negative_false_support"] = 1
    write_json(policy_path, policy)
    monkeypatch.setattr(preparation, "select", lambda *a: pytest.fail("must not read QA"))
    with pytest.raises(ValueError, match="Preserve preregistered"):
        invoke(root)
    policy["semantic_adoption_after_blind_seal"]["maximum_definite_negative_false_support"] = 0
    candidate_path = root / "configs/candidate.yaml"
    candidate = yaml.safe_load(candidate_path.read_text())
    candidate["auxiliary_runtime"]["context_tokens"] = 24576
    candidate_path.write_text(yaml.safe_dump(candidate))
    policy["candidate_config"] = preparation.binding(candidate_path)
    write_json(policy_path, policy)
    with pytest.raises(ValueError, match="Main policy candidate must match"):
        invoke(root)
    assert not (root / "data/runs/bilingual_main_protocol/new").exists()
