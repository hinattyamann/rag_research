"""Main execution needs unchanged preselected IDs and already adopted judge conditions."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from rag_research.experiments import bilingual_main as main
from rag_research.experiments.storage import checkpoint, write_json
from rag_research.retrieval.common import file_hash


@pytest.fixture
def adoption(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    for name in ("qa.jsonl", "assets.json", "usage.json", "ja.yaml", "core.py"):
        (tmp_path / name).write_text("fixed historical artifact")
    core = tmp_path / "src/rag_research/generation/core.py"
    core.parent.mkdir(parents=True)
    core.write_text("fixed core")
    rows = [{"record_id": str(i), "document_group_id": "g" + str(i)} for i in range(20)]
    selection = {"purpose": "phase11-main-development-preselected-ids-not-execution-approval", "split": "development",
        "phase12_allowed": False, "assets_sha256": file_hash(tmp_path / "assets.json"),
        "development_qa_sha256": {"qa.jsonl": file_hash(tmp_path / "qa.jsonl")},
        "used_baseline_input_sha256": {"usage.json": file_hash(tmp_path / "usage.json")},
        "languages": {"ja": {"selected": rows}}}
    checkpoint(tmp_path / "selection.json", selection)
    config = {"language": "ja", "assets": "assets.json", "prompts": "ja.yaml", "auxiliary_runtime": {"context": 12288},
        "sampling": {"seed": 42}, "execution": {"device": "CUDA0"}, "verification_mode": "source-reading-v1",
        "output_constraints": "thinking_json_passage_ids_v2", "model_tag": "adopted",
        "tasks": {k: {"max_output_tokens": 4096 if k == "read_sources" else 3072}
                  for k in ("read_sources", "verify_claims", "rewrite_answer")},
        "decision": {"threshold": .7, "bare_refusal_policy": "rewrite_once"},
        "main_limits": {"maximum_completion_attempts": 1660, "maximum_new_qa_per_stage_session": 5,
                        "stop_on_any_task_error": True, "automatic_refill": False},
        "development_selection": {"path": "selection.json", "sha256": file_hash(tmp_path / "selection.json")},
        "adopted_known_regression": {"path": "known.json", "sha256": "fixed"}}
    prior = {k: deepcopy(v) for k, v in config.items() if k not in {
        "language", "assets", "prompts", "main_limits", "development_selection", "adopted_known_regression"}}
    prior.update(purpose="phase11-bilingual-semantic-candidate", study_version="known-regression", diagnostics="known-plan")
    prior["decision"].pop("bare_refusal_policy")
    prior["prompts"] = {"ja": "ja.yaml"}
    candidate = {**deepcopy(prior), "study_version": "candidate", "diagnostics": "bilingual-diagnostic-plan"}
    (tmp_path / "candidate.yaml").write_text(yaml.safe_dump(candidate))
    policy = yaml.safe_load((Path(__file__).resolve().parents[1] /
        "configs/phase11_main_development_execution_policy_v1.json").read_text())
    policy.update(status="preregistered", selection_manifest=config["development_selection"],
                  limits_per_language=config["main_limits"],
                  candidate_config={"path": "candidate.yaml", "sha256": file_hash(tmp_path / "candidate.yaml")})
    write_json(tmp_path / "policy.json", policy)
    config["main_execution_policy"] = {"path": "policy.json", "sha256": file_hash(tmp_path / "policy.json")}
    manifest = {"model": {"tag": "adopted"}, "source_sha256": {
        "ja.yaml": file_hash(tmp_path / "ja.yaml"),
        "src/rag_research/generation/core.py": file_hash(core)}}
    monkeypatch.setattr(main, "passing_known_regression", lambda binding: (prior, manifest))
    monkeypatch.setattr(main, "auxiliary_identity", lambda c: {"tag": c["model_tag"]})
    return config, rows, tmp_path / "qa.jsonl", tmp_path


def test_unchanged_adoption_is_required_and_selection_cannot_be_reordered_or_refilled(adoption):
    config, rows, qa, _ = adoption
    main.validate_main(config, rows, qa)
    for changed in (rows[::-1], rows[:-1], [{**r, "record_id": "replacement"} if i == 0 else r for i, r in enumerate(rows)]):
        with pytest.raises(ValueError, match="preselected"):
            main.validate_main(config, changed, qa)


@pytest.mark.parametrize("change", ["model", "seed", "tokens", "threshold", "fallback", "limits", "prompt", "core", "usage", "qa", "policy"])
def test_changed_conditions_or_historical_evidence_cannot_enter_main(adoption, change):
    config, rows, qa, root = adoption
    if change == "model":
        config["model_tag"] = "other"
    elif change == "seed":
        config["sampling"]["seed"] = 1
    elif change == "tokens":
        config["tasks"]["verify_claims"]["max_output_tokens"] += 1
    elif change == "threshold":
        config["decision"]["threshold"] = .5
    elif change == "fallback":
        config["decision"]["bare_refusal_policy"] = "keep_initial"
    elif change == "limits":
        config["main_limits"]["maximum_completion_attempts"] += 1
    else:
        name = {"prompt": "ja.yaml", "core": "src/rag_research/generation/core.py", "usage": "usage.json", "qa": "qa.jsonl", "policy": "policy.json"}[change]
        (root / name).write_text("changed")
    with pytest.raises(ValueError):
        main.validate_main(config, rows, qa)


def test_missing_adoption_cannot_be_bypassed_by_a_pending_or_missing_binding(tmp_path):
    with pytest.raises(ValueError, match="Missing preregistered"):
        main.passing_known_regression(None)


@pytest.mark.parametrize("field,value", [("model_tag", "other"), ("sampling", {"seed": 1}),
    ("prompts", {"ja": "other.yaml"}), ("decision", {"threshold": .5}), ("extra_condition", True)])
def test_policy_candidate_cannot_drift_even_when_its_new_file_hash_is_supplied(adoption, field, value):
    config, rows, qa, root = adoption
    path = root / "candidate.yaml"
    candidate = yaml.safe_load(path.read_text())
    candidate[field] = value
    path.write_text(yaml.safe_dump(candidate))
    policy = yaml.safe_load((root / "policy.json").read_text())
    policy["candidate_config"]["sha256"] = file_hash(path)
    write_json(root / "policy.json", policy)
    config["main_execution_policy"]["sha256"] = file_hash(root / "policy.json")
    with pytest.raises(ValueError, match="Policy candidate must match"):
        main.validate_main(config, rows, qa)


@pytest.mark.parametrize("section,field,value", [
    ("semantic_adoption_after_blind_seal", "minimum_exact_label_accuracy_per_language", .5),
    ("semantic_adoption_after_blind_seal", "minimum_supported_label_accuracy_per_language", .5),
    ("semantic_adoption_after_blind_seal", "maximum_definite_negative_false_support", 1),
    ("semantic_adoption_after_blind_seal", "minimum_complete_comparable_qa_per_language", 1),
    ("semantic_adoption_after_blind_seal", "AI_expected_labels_frozen_before_internal_verdict_unblinding", False),
    ("semantic_adoption_after_blind_seal", "ambiguous_units_excluded_only_from_accuracy_not_F", False),
    ("health_gate", "maximum_task_errors", 1), ("health_gate", "maximum_input_overflow", 1),
    ("health_gate", "baseline_requires_actual_used_context", False),
    ("health_gate", "unknown_outcome_stops_without_resampling", False),
    ("quality", "seal_all_candidates_both_languages_before_internal_unblinding", False),
    ("quality", "unknown_quality_not_imputed", False),
    ("decision", "threshold", .5), ("decision", "bare_refusal_policy", "keep_initial"),
    ("decision", "score_for_no_fixed_units", 0),
    ("health_gate", "maximum_task_errors", False),
])
def test_weakened_policy_cannot_start_main_even_with_an_updated_policy_binding(adoption, section, field, value):
    config, rows, qa, root = adoption
    policy = yaml.safe_load((root / "policy.json").read_text())
    policy[section][field] = value
    write_json(root / "policy.json", policy)
    config["main_execution_policy"]["sha256"] = file_hash(root / "policy.json")
    with pytest.raises(ValueError):
        main.validate_main(config, rows, qa)


@pytest.mark.parametrize("section,field", [("decision", "score_for_no_fixed_units"), (None, "candidate_config")])
def test_policy_must_explicitly_bind_the_candidate_and_preserve_null_score(adoption, section, field):
    config, rows, qa, root = adoption
    policy = yaml.safe_load((root / "policy.json").read_text())
    (policy if section is None else policy[section]).pop(field)
    write_json(root / "policy.json", policy)
    config["main_execution_policy"]["sha256"] = file_hash(root / "policy.json")
    with pytest.raises(ValueError):
        main.validate_main(config, rows, qa)
