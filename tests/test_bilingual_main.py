"""Main execution needs unchanged preselected IDs and already adopted judge conditions."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from rag_research.experiments import bilingual_main as main
from rag_research.experiments import semantic_diagnostics
from rag_research.experiments.frozen_trace import digest
from rag_research.experiments.storage import checkpoint, read_json, write_json
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


def test_binary_main_cannot_adopt_a_legacy_known_report(adoption):
    from rag_research.experiments.semantic_adoption import BINARY, BINARY_RULES

    config, rows, qa, root = adoption
    policy = read_json(root / "policy.json")
    policy["semantic_adoption_version"] = BINARY
    rules = policy["semantic_adoption_after_blind_seal"]
    for key in ("minimum_exact_label_accuracy_per_language", "minimum_supported_label_accuracy_per_language",
                "maximum_definite_negative_false_support"):
        rules.pop(key)
    rules.update(BINARY_RULES)
    write_json(root / "policy.json", policy)
    config["main_execution_policy"]["sha256"] = file_hash(root / "policy.json")
    config["semantic_adoption_version"] = BINARY
    with pytest.raises(ValueError, match="Known/Main semantic adoption versions differ"):
        main.validate_main(config, rows, qa)


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


@pytest.fixture(params=["source-reading-v1", "claimwise-v1"])
def known_evidence(tmp_path, monkeypatch, request):
    """Synthetic full-size plan; configuration loading and model replay are doubles."""
    monkeypatch.setattr(main, "ROOT", tmp_path)
    run = tmp_path / "data/runs/semantic_diagnostics/known"
    (run / "tasks").mkdir(parents=True)
    config = {"verification_mode": request.param, "output_constraints": "synthetic"}
    config_path = tmp_path / "candidate.yaml"
    config_path.write_text(yaml.safe_dump(config))
    cases = []
    for number in range(15):
        claims = [{"claim_id": "c" + str(i + 1), "text": "Fixed sentence."} for i in range(3 if number < 12 else 2)]
        cases.append({"id": "known-" + str(number), "scope": "known_used_development", "language": "en",
            "question": "Q?", "answer": "Full draft", "claims": claims,
            "documents": [{"passage_id": "p1", "text": "One"}, {"passage_id": "p2", "text": "Two"}],
            "expected": {c["claim_id"]: "contradicted" if number < 6 and c["claim_id"] == "c1" else "supported" for c in claims},
            "critical_claim_ids": ["c1"] if number < 6 else []})
    limit = 114 if request.param == "source-reading-v1" else 84
    plan = {"purpose": "phase11-known-trace-semantic-regression", "cases": cases,
        "orders": ["original", "reversed"], "max_completion_attempts": limit}
    plan_path = tmp_path / "plan.json"
    write_json(plan_path, plan)
    manifest = {"config": config, "model": "synthetic", "plan_sha256": file_hash(plan_path)}
    write_json(run / "manifest.json", manifest)
    tasks = {}
    for case, _, key in semantic_diagnostics.specs(plan):
        tasks[key] = checkpoint(run / "tasks" / (key + ".json"), {"status": "ok", "execution_mode": request.param,
            "completion_attempted": True, "subtask_costs": [{"completion_attempted": True}] *
                (len(case["claims"]) + (request.param == "source-reading-v1")),
            "parsed": {"verdicts": [{"claim_id": i, "label": label} for i, label in case["expected"].items()]}})
    report = {**semantic_diagnostics.assess(plan, tasks), "completed_conditions": 30, "planned_conditions": 30,
        "not_attempted_ids": [], "completion_attempts_recorded": limit, "cost_incomplete": False,
        "manifest_sha256": digest(manifest), "task_result_sha256": {k: v["result_sha256"] for k, v in tasks.items()}}
    write_json(run / "report.json", report)
    state = {"calls": []}

    def replay(client, generation, prompts, payload, path, binding, **kwargs):
        assert client is None and kwargs["mode"] == request.param
        assert kwargs["reader_generation"] == ("read_sources" if request.param == "source-reading-v1" else None)
        state["calls"].append(path.stem)
        return read_json(path)

    monkeypatch.setattr(semantic_diagnostics, "load_config", lambda p: (config, plan, {"en": {}}, plan_path))
    monkeypatch.setattr(main, "auxiliary_identity", lambda c: "synthetic")
    monkeypatch.setattr(main, "execution_identity", lambda c: {})
    monkeypatch.setattr(main, "task_config", lambda c, t: t)
    monkeypatch.setattr(main, "verify_once", replay)
    binding = {"path": "data/runs/semantic_diagnostics/known/report.json", "sha256": file_hash(run / "report.json"),
        "config": {"path": "candidate.yaml", "sha256": file_hash(config_path)}}
    return binding, run, plan, plan_path, state


def test_full_known_adoption_uses_all_42_units_in_both_modes(known_evidence):
    binding, _, plan, _, state = known_evidence
    main.passing_known_regression(binding)
    assert len(plan["cases"]) == 15 and sum(len(c["claims"]) for c in plan["cases"]) == 42
    assert len(state["calls"]) == 30


def test_binary_known_adoption_replays_all_raw_and_keeps_legacy_failure(known_evidence):
    from rag_research.experiments.semantic_adoption import BINARY, KNOWN_GATE_V2

    binding, run, plan, plan_path, state = known_evidence
    results = {}
    for case, _, key in semantic_diagnostics.specs(plan):
        path = run / "tasks" / (key + ".json")
        task = read_json(path)
        for verdict in task["parsed"]["verdicts"]:
            if verdict["label"] == "contradicted":
                verdict["label"] = "not_supported"
        task.pop("result_sha256")
        results[key] = checkpoint(path, task)
    assert not semantic_diagnostics.assess(plan, results)["diagnostic_gate_passed"]
    plan["gate"] = deepcopy(KNOWN_GATE_V2)
    write_json(plan_path, plan)
    manifest = read_json(run / "manifest.json")
    manifest.update(semantic_adoption_version=BINARY, plan_sha256=file_hash(plan_path))
    write_json(run / "manifest.json", manifest)
    report = read_json(run / "report.json")
    report.update(semantic_diagnostics.assess(plan, results), manifest_sha256=digest(manifest),
                  task_result_sha256={k: v["result_sha256"] for k, v in results.items()})
    write_json(run / "report.json", report)
    binding["sha256"] = file_hash(run / "report.json")
    assert report["diagnostic_gate_passed"] and not report["critical_passed"]
    main.passing_known_regression(binding)
    assert len(state["calls"]) == 30
    manifest.pop("semantic_adoption_version")
    write_json(run / "manifest.json", manifest)
    report["manifest_sha256"] = digest(manifest)
    write_json(run / "report.json", report)
    binding["sha256"] = file_hash(run / "report.json")
    with pytest.raises(ValueError, match="versions differ"):
        main.passing_known_regression(binding)


@pytest.mark.parametrize("fault", ["count", "plan", "fewer_units", "extra_condition", "false_pass", "native_count"])
def test_full_known_adoption_cannot_reduce_units_or_trust_flags_and_recorded_costs(known_evidence, fault):
    binding, run, plan, plan_path, _ = known_evidence
    report = read_json(run / "report.json")
    if fault == "count":
        report["completion_attempts_recorded"] += 1
    elif fault == "plan":
        plan_path.write_text("different bytes")
    elif fault == "fewer_units":
        plan["cases"][-1]["claims"].pop()
    elif fault == "extra_condition":
        report["task_result_sha256"]["unplanned"] = "fake"
    else:
        raw = run / "tasks/known-0-original.json"
        task = read_json(raw)
        task.pop("result_sha256")
        if fault == "false_pass":
            task["parsed"]["verdicts"][0]["label"] = "supported"
        else:
            task["subtask_costs"] = deepcopy(task["subtask_costs"])
            task["subtask_costs"][0]["completion_attempted"] = False
        task = checkpoint(raw, task)
        report["task_result_sha256"][raw.stem] = task["result_sha256"]
    write_json(run / "report.json", report)
    binding["sha256"] = file_hash(run / "report.json")
    with pytest.raises(ValueError):
        main.passing_known_regression(binding)
