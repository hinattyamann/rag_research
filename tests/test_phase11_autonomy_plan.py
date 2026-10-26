"""Identity and run planning do not infer, modify prior runs, or consume QA."""

import copy
import importlib.util
from pathlib import Path

import pytest

from rag_research.experiments.frozen_trace import digest
from rag_research.experiments.storage import read_json, write_json
from rag_research.retrieval.common import file_hash

SPEC = importlib.util.spec_from_file_location(
    "autonomy_plans", Path(__file__).resolve().parents[1] / "scripts/prepare_phase11_autonomy_plan.py")
plans = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plans)


@pytest.fixture
def identity_fixture(tmp_path):
    root = tmp_path
    for name in ("src/rag_research/evaluation", "configs", "data/models", "data/runtimes/native",
                 "data/manifests"):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / "src/rag_research/evaluation/schema.py").write_text("SCHEMA = 1\n")
    (root / "data/models/model.gguf").write_bytes(b"fixed model")
    model_file = plans.binding(root, root / "data/models/model.gguf")
    model_file["bytes"] = len(b"fixed model")
    write_json(root / "data/manifests/model.json", {"files": [model_file]})
    (root / "data/runtimes/native/server").write_bytes(b"fixed executable")
    spec_path = root / "configs/runtime.json"
    write_json(spec_path, {"directory": "data/runtimes/native"})
    write_json(root / "data/runtimes/native/runtime_manifest.json", {
        "specification_sha256": file_hash(spec_path),
        "files": {"server": file_hash(root / "data/runtimes/native/server")}})
    for language in ("en", "ja"):
        (root / f"configs/prompt-{language}.yaml").write_text("instructions: Fixed shared Judge\n")
    config = {"auxiliary_model_manifest": "data/manifests/model.json",
              "execution": {"runtime_spec": "configs/runtime.json", "gpu_layers": 99},
              "auxiliary_runtime": {"timeout_seconds": 10, "temperature": .2},
              "sampling": {"seed": 42}, "tasks": {"verify_claims": {"max_output_tokens": 32}},
              "trials": {}, "errors": {"automatic_retries": 0},
              "output_constraints": "thinking_json_passage_ids_v3", "verification_mode": "claimwise-v1",
              "prompts": {lang: f"configs/prompt-{lang}.yaml" for lang in ("en", "ja")}}
    return root, config, root / "data/manifests/identity"


def test_identity_has_no_config_hash_cycle_and_reuses_sampler(identity_fixture):
    root, config, folder = identity_fixture
    first = plans.build_identity(root, config, folder)
    changed = {**config, "study_version": "different-stage", "purpose": "main",
               "diagnostics": "different-plan", "candidate_identity_sha256": digest(first)}
    second = plans.build_identity(root, changed, folder)
    assert first == second
    assert len(list(folder.glob("sampler-*.json"))) == 1
    assert all(not b["path"].endswith("candidate.yaml") for rows in first.values() for b in rows)


def test_sampler_change_requires_different_identity(identity_fixture):
    root, config, folder = identity_fixture
    first = plans.build_identity(root, config, folder)
    changed = copy.deepcopy(config)
    changed["auxiliary_runtime"]["temperature"] = .3
    second = plans.build_identity(root, changed, folder)
    assert digest(first) != digest(second)
    assert first["model"] == second["model"] and first["runtime"] == second["runtime"]


def test_actual_core_change_changes_candidate(identity_fixture):
    root, config, folder = identity_fixture
    first = plans.build_identity(root, config, folder)
    (root / "src/rag_research/evaluation/schema.py").write_text("SCHEMA = 2\n")
    assert digest(plans.build_identity(root, config, folder)) != digest(first)


@pytest.mark.parametrize("asset", ["data/models/model.gguf", "data/runtimes/native/server"])
def test_missing_or_changed_binary_rejected(identity_fixture, asset):
    root, config, folder = identity_fixture
    (root / asset).write_bytes(b"different binary")
    with pytest.raises(ValueError, match="differs"):
        plans.build_identity(root, config, folder)


def test_target_scope_counts_full_70_and_zero_generation_preflight(identity_fixture):
    root, config, _ = identity_fixture
    diagnostic = {"cases": [{"id": "case-" + str(i), "claims": [{"claim_id": "c1"}]} for i in range(35)],
                  "orders": ["original", "reversed"], "max_completion_attempts": 70}
    write_json(root / "configs/diagnostics.json", diagnostic)
    config["diagnostics"] = "configs/diagnostics.json"
    targets, counts, calls = plans.target_scope(root, "semantic", config, None)
    assert len(targets) == calls == 70 and counts == {"qa": 35, "fixed_units": 35, "conditions": 70}
    assert plans.target_scope(root, "preflight", config, None)[-1] == 0


def test_smoke_keeps_original_full_draft_denominator(identity_fixture):
    root, config, _ = identity_fixture
    source = {"cases": [{"id": "one", "claims": [1, 2, 3, 4]}, {"id": "two", "claims": [1, 2]}]}
    write_json(root / "configs/source.json", source)
    plan = {"maximum_calls": 2, "source": plans.binding(root, root / "configs/source.json"),
            "targets": [{"case_id": "one", "order": "reversed", "claim_id": "c4"},
                        {"case_id": "two", "order": "original", "claim_id": "c2"}]}
    write_json(root / "configs/smoke.json", plan)
    targets, counts, calls = plans.target_scope(root, "smoke", config, root / "configs/smoke.json")
    assert targets == ["one/reversed/c4", "two/original/c2"]
    assert counts == {"qa": 2, "fixed_units": 6, "conditions": 2} and calls == 2
    assert read_json(root / "configs/source.json") == source


def test_native_format_plan_retains_all_ten_states(identity_fixture):
    root, config, _ = identity_fixture
    targets, counts, calls = plans.target_scope(root, "format", config, None)
    assert len(set(targets)) == calls == 10
    assert counts == {"qa": 0, "fixed_units": 0, "conditions": 10}
