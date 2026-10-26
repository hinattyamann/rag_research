"""Resource version migration keeps scientific gates and historical limits intact."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from rag_research.experiments import bilingual_main, calibration_protocol
from rag_research.experiments.phase11_autonomy import ADOPTION, SCIENTIFIC_RULES, VERSION
from rag_research.experiments.storage import read_json, write_json
from rag_research.retrieval.common import file_hash

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def registered_resources(tmp_path, monkeypatch):
    monkeypatch.setattr(bilingual_main, "ROOT", tmp_path)
    monkeypatch.setattr(calibration_protocol, "ROOT", tmp_path)
    (tmp_path / "configs").mkdir()

    def bind(name, value):
        path = tmp_path / name
        write_json(path, value)
        return {"path": name, "sha256": file_hash(path)}

    authorization = bind("authorization.json", {"user_authorized": True})
    legacy = bind("legacy.json", {"cumulative_recorded_all9b_development_attempts": 909,
        "cumulative_unknown_responses": 3, "known_regression_adopted": False})
    protocol = bind("configs/protocol.json", {"version": VERSION, "semantic_adoption_version": ADOPTION,
        "scientific_rules": SCIENTIFIC_RULES, "global_call_ceiling": None, "global_seconds_ceiling": None,
        "global_candidate_ceiling": None, "authorization": authorization, "legacy_result": legacy,
        "legacy_attempts": 909, "legacy_unknown": 3})
    chain = {"autonomy_protocol_version": VERSION, "autonomy_protocol": protocol,
        "candidate_identity_sha256": "a" * 64, "semantic_adoption_version": ADOPTION}
    limits = {**bilingual_main.LEGACY_LIMITS, "maximum_completion_attempts": 2400}
    budget = {"planned_calls": 2100, "maximum_calls": 2400, "estimated_tokens": 123456,
        "estimated_native_seconds": 5000, "maximum_wall_seconds": 10000,
        "request_timeout_seconds": 1200, "maximum_tokens_per_call": 12288}
    registration = {**chain, "purpose": "phase11-finite-stage-resource-registration", "stage": "main",
        "count_per_language": 20, "limits_per_language": limits, "registered_before_new_outputs": True,
        "call_calculation": "Twenty QA with every fixed unit and all nine planned trials reserved.",
        "token_time_assumptions": "Conservative planning estimates; do not truncate or refill.",
        "stop_method": "Stop on any error, unknown outcome, or finite run budget exhaustion.",
        "resume_method": "Only genuinely unsent journal entries may resume; never resend unknowns.",
        "budget_per_language": {lang: deepcopy(budget) for lang in ("en", "ja")}}
    policy = {**chain, "limits_per_language": deepcopy(limits),
        "resource_budget_registration": bind("configs/resources.json", registration)}

    def save(value):
        policy["resource_budget_registration"] = bind("configs/resources.json", value)

    return policy, registration, save, tmp_path


def test_historical_limits_cannot_be_expanded_without_a_new_version():
    assert bilingual_main.stage_limits({"limits_per_language": bilingual_main.LEGACY_LIMITS}, "main") == bilingual_main.LEGACY_LIMITS
    changed = {**bilingual_main.LEGACY_LIMITS, "maximum_completion_attempts": 1661}
    with pytest.raises(ValueError, match="legacy stage limits"):
        bilingual_main.stage_limits({"limits_per_language": changed}, "main")


def test_v3_accepts_a_finite_pre_output_budget_without_changing_scientific_criteria(registered_resources):
    policy, _, _, _ = registered_resources
    assert bilingual_main.stage_limits(policy, "main")["maximum_completion_attempts"] == 2400
    with pytest.raises(ValueError, match="before new outputs"):
        bilingual_main.stage_limits(policy, "cal")
    policy["semantic_adoption_version"] = "three-label-v1"
    with pytest.raises(ValueError, match="support-binary-v2"):
        bilingual_main.stage_limits(policy, "main")


@pytest.mark.parametrize("fault", ["missing_registration", "changed_registration", "candidate", "stage", "count",
    "after_outputs", "language", "calls", "boolean_calls", "infinite_time", "timeout", "missing_reason", "session", "refill"])
def test_new_hashes_cannot_hide_weakened_or_unbounded_resource_registrations(registered_resources, fault):
    policy, registration, save, root = registered_resources
    if fault == "missing_registration":
        policy.pop("resource_budget_registration")
    elif fault == "changed_registration":
        write_json(root / "configs/resources.json", {"changed": True})
    else:
        if fault == "candidate":
            registration["candidate_identity_sha256"] = "b" * 64
        elif fault == "stage":
            registration["stage"] = "cal"
        elif fault == "count":
            registration["count_per_language"] = 19
        elif fault == "after_outputs":
            registration["registered_before_new_outputs"] = False
        elif fault == "language":
            registration["budget_per_language"].pop("ja")
        elif fault == "calls":
            registration["budget_per_language"]["en"]["planned_calls"] = 2401
        elif fault == "boolean_calls":
            registration["budget_per_language"]["en"]["planned_calls"] = True
        elif fault == "infinite_time":
            registration["budget_per_language"]["ja"]["maximum_wall_seconds"] = float("inf")
        elif fault == "timeout":
            registration["budget_per_language"]["ja"]["maximum_wall_seconds"] = 1200
        elif fault == "missing_reason":
            registration["call_calculation"] = ""
        elif fault == "session":
            policy["limits_per_language"]["maximum_new_qa_per_stage_session"] = 20
        else:
            policy["limits_per_language"]["automatic_refill"] = True
        if fault == "infinite_time":
            path = root / "configs/resources.json"
            path.write_text(json.dumps(registration).replace("Infinity", "1e309"))
            policy["resource_budget_registration"]["sha256"] = file_hash(path)
        else:
            save(registration)
    with pytest.raises(ValueError):
        bilingual_main.stage_limits(policy, "main")


def test_calibration_rules_accept_only_their_own_hashed_v3_finite_registration(registered_resources):
    policy, registration, save, root = registered_resources
    registration["stage"] = "cal"
    save(registration)
    rules = read_json(REPO / "configs/phase11_bilingual_calibration_execution_rules_v2.json")
    rules.update(policy)
    rules["resource_policy"]["total_native_call_ceiling"] = 2400
    path = root / "configs/rules.json"
    write_json(path, rules)
    assert calibration_protocol.rules(path)["limits_per_language"]["maximum_completion_attempts"] == 2400
    rules["resource_policy"]["total_native_call_ceiling"] = 2401
    write_json(path, rules)
    with pytest.raises(ValueError, match="resource/revision"):
        calibration_protocol.rules(path)


def test_calibration_cannot_relabel_main_configuration_as_a_legacy_or_other_candidate(registered_resources):
    policy, registration, save, _ = registered_resources
    registration["stage"] = "cal"
    save(registration)
    config = {**{k: policy[k] for k in ("autonomy_protocol_version", "autonomy_protocol", "candidate_identity_sha256",
        "semantic_adoption_version")}, "execution_scope": "main_development_v1", "language": "en",
        "main_limits": policy["limits_per_language"], "development_selection": {}, "main_execution_policy": {}}
    selected = [{"record_id": str(i)} for i in range(20)]
    actual = calibration_protocol.configuration(config, selected, "en", policy)
    assert actual["calibration_limits"]["maximum_completion_attempts"] == 2400
    with pytest.raises(ValueError, match="separately registered"):
        calibration_protocol.configuration(config, selected, "en")
    changed = {**policy, "candidate_identity_sha256": "b" * 64}
    with pytest.raises(ValueError, match="identity differs"):
        calibration_protocol.configuration(config, selected, "en", changed)
