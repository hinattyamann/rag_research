"""Calibration prerequisites use explicit synthetic main/configuration doubles."""

import shutil
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from rag_research.experiments import bilingual_statistics
from rag_research.experiments import calibration_protocol as module
from rag_research.experiments.frozen_trace import digest
from rag_research.experiments.storage import checkpoint, read_json, write_json

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def prerequisite(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    for name in ["src/rag_research/fixed.py", "scripts/prepare_bilingual_calibration.py", "scripts/run_bilingual_calibration.py",
            "scripts/analyze_bilingual_calibration.py", "scripts/bilingual_quality.py", "scripts/review_bilingual_units.py",
            "docs/order_quality_rubric.md", "docs/phase11_statistical_plan.md"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic fixed source")
    configs = tmp_path / "configs"
    configs.mkdir()
    inputs = configs / "main-inputs.json"
    write_json(inputs, [{"synthetic": True}])
    policy = configs / "reservation-policy.json"
    write_json(policy, {"synthetic": True})
    rule_path = configs / "rules.json"
    rule_path.write_bytes((REPO / "configs/phase11_bilingual_calibration_execution_rules_v1.json").read_bytes())
    main = {key: {} for key in module.MAIN_FIELDS}
    main.update(status="verified", canonical_inputs=[{"synthetic": True}], condition_sha256=digest({"synthetic": True}), source_runs={})
    fresh = {key: "synthetic" for key in ["purpose", "method", "analysis_split", "seed", "policy_sha256", "source_qa_sha256"]}
    fresh.update(source_splits=module.SOURCE_SPLITS, inputs={"assets": {"path": "configs/assets.json"}}, languages={})
    configs_by_language = {}
    for language in ("en", "ja"):
        selected = [{"record_id": language + str(n), "document_group_id": language + "-reserved-" + str(n)} for n in range(20)]
        fresh["languages"][language] = {"selected": selected, "planned_qa": 20}
        main["source_runs"][language] = {"run": "data/runs/bilingual_development/main-" + language,
            "selected": [{"record_id": "main-" + language + str(n), "document_group_id": "main-" + language + str(n)} for n in range(20)],
            "native_collection_cost": {"completion_attempts": 200, "input_tokens": 20000, "output_tokens": 10000,
                "summed_step_seconds": 20.5}}
        config = {"purpose": "phase11-bilingual-development-candidate", "status": "candidate_not_frozen", "language": language,
            "phase12_allowed": False, "execution_scope": "main_development_v1", "assets": "configs/assets.json",
            "main_limits": module.LIMITS, "development_selection": {"synthetic": True}, "main_execution_policy": {},
            "data": {"split": "development", "record_ids": [r["record_id"] for r in main["source_runs"][language]["selected"]]},
            "verification_mode": "claimwise-v1", "auxiliary_runtime": {"context_tokens": 24576, "timeout_seconds": 1200},
            "tasks": {"verify_claims": {"max_output_tokens": 6144}, "rewrite_answer": {"max_output_tokens": 6144}}}
        run = tmp_path / main["source_runs"][language]["run"]
        run.mkdir(parents=True)
        write_json(run / "manifest.json", {"config": config, "baseline": {"generation": {
            "context_tokens": 4096, "max_output_tokens": 512, "timeout_seconds": 300}}})
        configs_by_language[language] = config
    reservation = configs / "reservation.json"
    checkpoint(reservation, fresh)
    certificate = tmp_path / "data/runs/development_certification/main/certificate.private.json"
    certificate.parent.mkdir(parents=True)
    checkpoint(certificate, {**main, "purpose": "phase11-main-development-evidence-certificate", "inputs": module.binding(inputs)})
    state = {"calls": 0, "reject_main": False, "excluded": [], "fresh": fresh, "main": main}

    def certify(path):
        state["calls"] += 1
        assert path == inputs
        if state["reject_main"]:
            raise ValueError("Complete main evidence required")
        return deepcopy(main)

    def prepare(path, *, root, excluded_resume_runs=()):
        assert path == policy and root == tmp_path
        state["excluded"].append(list(excluded_resume_runs))
        return deepcopy(state["fresh"])

    monkeypatch.setattr(module, "certify_main", certify)
    monkeypatch.setattr(module, "prepare", prepare)
    monkeypatch.setattr(bilingual_statistics, "condition", lambda manifest: {"synthetic": manifest.get("condition", True)})
    original_read = module.read_json

    def checked_read(path):
        if Path(path) == certificate:
            assert state["calls"] > 0, "Recompute/seal before opening the private certificate"
        return original_read(path)

    monkeypatch.setattr(module, "read_json", checked_read)
    output = tmp_path / "data/runs/bilingual_calibration_protocol/heldout-v1"
    return (inputs, certificate, reservation, policy, rule_path, output), state, tmp_path


def test_protocol_binds_complete_main_exact_reserved_groups_and_source_split_without_model_calls(prerequisite):
    args, state, root = prerequisite
    result = module.create(*args)
    assert result["new_model_calls"] == 0 and not result["gate11_passed"] and not result["phase12_allowed"]
    protocol = read_json(args[-1] / "protocol.json")
    for language in ("en", "ja"):
        config = yaml.safe_load((args[-1] / ("config-" + language + ".yaml")).read_text())
        assert config["data"]["split"] == module.SOURCE_SPLITS[language] and config["analysis_split"] == "calibration"
        assert len(config["data"]["record_ids"]) == 20 and config["calibration_limits"] == module.LIMITS
        assert config["verification_mode"] == "claimwise-v1" and "main_execution_policy" not in config
        checked, _, _ = module.validate(config, root / protocol["runs"][language])
        assert checked == protocol
    assert state["calls"] == 3 and len(state["excluded"][-1]) == 2
    with pytest.raises(ValueError, match="new Calibration protocol"):
        module.create(*args)


def test_binary_calibration_rules_reject_legacy_main_even_before_inference(prerequisite):
    from rag_research.experiments.semantic_adoption import BINARY, BINARY_RULES

    args, _, _ = prerequisite
    rules = read_json(args[4])
    rules["semantic_adoption_version"] = BINARY
    semantic = rules["semantic_adoption_after_blind_seal"]
    for key in ("minimum_exact_label_accuracy_per_language", "minimum_supported_label_accuracy_per_language",
                "maximum_definite_negative_false_support"):
        semantic.pop(key)
    semantic.update(BINARY_RULES)
    write_json(args[4], rules)
    with pytest.raises(ValueError, match="Main/Calibration adoption versions differ"):
        module.create(*args)
    assert not args[-1].exists()


def test_binary_calibration_preserves_actual_main_version_in_both_language_configs(prerequisite):
    from rag_research.experiments.semantic_adoption import BINARY, BINARY_RULES

    args, state, root = prerequisite
    rules = read_json(args[4])
    rules["semantic_adoption_version"] = BINARY
    semantic = rules["semantic_adoption_after_blind_seal"]
    for key in ("minimum_exact_label_accuracy_per_language", "minimum_supported_label_accuracy_per_language",
                "maximum_definite_negative_false_support"):
        semantic.pop(key)
    semantic.update(BINARY_RULES)
    write_json(args[4], rules)
    for run in state["main"]["source_runs"].values():
        path = root / run["run"] / "manifest.json"
        manifest = read_json(path)
        manifest["config"]["semantic_adoption_version"] = BINARY
        write_json(path, manifest)
    module.create(*args)
    protocol = read_json(args[-1] / "protocol.json")
    for language in ("en", "ja"):
        config = yaml.safe_load((args[-1] / ("config-" + language + ".yaml")).read_text())
        assert config["semantic_adoption_version"] == BINARY
        module.validate(config, root / protocol["runs"][language])


@pytest.mark.parametrize("fault", ["main", "certificate", "selection", "rules", "overlap"])
def test_failed_or_changed_prerequisites_never_create_an_execution_protocol(prerequisite, fault):
    args, state, root = prerequisite
    if fault == "main":
        state["reject_main"] = True
    elif fault == "certificate":
        saved = read_json(args[1])
        saved["condition_sha256"] = "changed"
        saved.pop("result_sha256")
        checkpoint(args[1], saved)
    elif fault == "selection":
        state["fresh"]["languages"]["ja"]["selected"][0]["record_id"] = "replacement"
    elif fault == "rules":
        rules = read_json(args[4])
        rules["semantic_adoption_after_blind_seal"]["maximum_definite_negative_false_support"] = 1
        write_json(args[4], rules)
    else:
        # Both saved reservation and fresh selection agree, but still overlap main.
        state["fresh"]["languages"]["en"]["selected"][0]["document_group_id"] = "main-en0"
        checkpoint(args[2], state["fresh"])
    with pytest.raises(ValueError):
        module.create(*args)
    assert not args[-1].exists()


@pytest.mark.parametrize("fault", ["config", "output", "source", "external_usage", "unowned_journal"])
def test_execution_rechecks_conditions_sources_usage_and_exact_resume_identity(prerequisite, fault):
    args, state, root = prerequisite
    module.create(*args)
    protocol = read_json(args[-1] / "protocol.json")
    config = yaml.safe_load((args[-1] / "config-en.yaml").read_text())
    output = root / protocol["runs"]["en"]
    if fault == "config":
        config["calibration_limits"]["maximum_completion_attempts"] += 1
    elif fault == "output":
        output = output.with_name("different")
    elif fault == "source":
        (root / "src/rag_research/fixed.py").write_text("changed")
    elif fault == "external_usage":
        state["fresh"]["languages"]["en"]["selected"][0]["record_id"] = "different unused ID"
    else:
        output.mkdir(parents=True)
        write_json(output / "record.json", {"record_id": "en0", "status": "started"})
    with pytest.raises(ValueError):
        module.validate(config, output)


def test_only_original_both_language_runs_can_be_excluded_for_resume(prerequisite):
    args, state, root = prerequisite
    module.create(*args)
    protocol = read_json(args[-1] / "protocol.json")
    for lang in ("en", "ja"):
        config = yaml.safe_load((args[-1] / ("config-" + lang + ".yaml")).read_text())
        run = root / protocol["runs"][lang]
        run.mkdir(parents=True)
        write_json(run / "manifest.json", {"config": config, "language": lang,
            "selection": [{"record_id": r["record_id"]} for r in protocol["selected"][lang]]})
    config = yaml.safe_load((args[-1] / "config-en.yaml").read_text())
    module.validate(config, root / protocol["runs"]["en"])
    assert state["excluded"][-1] == [protocol["runs"][lang] for lang in ("en", "ja")]
    manifest_path = root / protocol["runs"]["ja"] / "manifest.json"
    manifest = read_json(manifest_path)
    manifest["selection"].pop()
    write_json(manifest_path, manifest)
    with pytest.raises(ValueError, match="original runs"):
        module.validate(config, root / protocol["runs"]["en"])


def test_changed_pending_main_stops_before_even_hashing_its_private_certificate(prerequisite, monkeypatch):
    args, state, root = prerequisite
    module.create(*args)
    protocol = read_json(args[-1] / "protocol.json")
    config = yaml.safe_load((args[-1] / "config-en.yaml").read_text())
    state["reject_main"] = True
    original = Path.open

    def guarded(path, *positional, **keywords):
        assert path != args[1], "No private certificate read/hash before all main labels are sealed"
        return original(path, *positional, **keywords)

    monkeypatch.setattr(Path, "open", guarded)
    with pytest.raises(ValueError, match="Complete main"):
        module.validate(config, root / protocol["runs"]["en"])


def test_evaluation_cannot_be_read_as_a_reservation_or_execution_policy(prerequisite, monkeypatch):
    args, _, root = prerequisite
    evaluation = root / "data/processed/evaluation.jsonl"
    evaluation.parent.mkdir(parents=True)
    evaluation.write_text("DO NOT READ")
    original = Path.open

    def guarded(path, *positional, **keywords):
        assert path != evaluation
        return original(path, *positional, **keywords)

    monkeypatch.setattr(Path, "open", guarded)
    for index in [2, 3, 4]:
        changed = list(args)
        changed[index] = evaluation
        with pytest.raises(ValueError, match="Evaluation"):
            module.create(*changed)


def test_new_payload_and_protocol_hashes_cannot_hide_drift_from_actual_adopted_conditions(prerequisite):
    args, _, root = prerequisite
    module.create(*args)
    config = yaml.safe_load((args[-1] / "config-en.yaml").read_text())
    config["auxiliary_runtime"]["context_tokens"] = 1024
    protocol_path = args[-1] / "protocol.json"
    protocol = read_json(protocol_path)
    protocol.pop("result_sha256")
    protocol["config_payload_sha256"]["en"] = digest({k: v for k, v in config.items() if k != "calibration_protocol"})
    checkpoint(protocol_path, protocol)
    config["calibration_protocol"] = module.binding(protocol_path)
    with pytest.raises(ValueError, match="actual adopted main"):
        module.validate(config, root / protocol["runs"]["en"])


def test_review_replay_requires_exact_original_bytes_and_never_counts_replays_as_fresh_usage(prerequisite):
    args, _, root = prerequisite
    module.create(*args)
    protocol = read_json(args[-1] / "protocol.json")
    aliases = {}
    for lang in ("en", "ja"):
        config = yaml.safe_load((args[-1] / ("config-" + lang + ".yaml")).read_text())
        original = root / protocol["runs"][lang]
        original.mkdir(parents=True)
        write_json(original / "manifest.json", {"language": lang, "config": config,
            "selection": [{"record_id": r["record_id"]} for r in protocol["selected"][lang]]})
        write_json(original / "raw.json", {"synthetic": True})
        copied = root / "data/runs/bilingual_calibration_replay/test" / lang
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(original, copied)
        aliases[copied] = original
    copied = next(iter(aliases))
    manifest = read_json(copied / "manifest.json")
    assert module.review_contract(copied, manifest, canonical_runs=aliases) == protocol
    write_json(copied / "raw.json", {"altered": True})
    with pytest.raises(ValueError, match="differs from original"):
        module.review_contract(copied, manifest, canonical_runs=aliases)


def test_review_checks_actual_condition_digest_instead_of_trusting_calibration_model_metadata(prerequisite):
    args, _, root = prerequisite
    module.create(*args)
    protocol = read_json(args[-1] / "protocol.json")
    for lang in ("en", "ja"):
        config = yaml.safe_load((args[-1] / ("config-" + lang + ".yaml")).read_text())
        original = root / protocol["runs"][lang]
        original.mkdir(parents=True)
        write_json(original / "manifest.json", {"language": lang, "config": config,
            "selection": [{"record_id": r["record_id"]} for r in protocol["selected"][lang]]})
    run = root / protocol["runs"]["en"]
    manifest = read_json(run / "manifest.json")
    manifest["condition"] = False
    with pytest.raises(ValueError, match="conditions differ from"):
        module.review_contract(run, manifest)


@pytest.mark.parametrize("name", ["docs/order_quality_rubric.md", "docs/phase11_statistical_plan.md", "scripts/analyze_bilingual_calibration.py"])
def test_review_and_statistical_definitions_cannot_change_after_protocol_creation(prerequisite, name):
    args, _, root = prerequisite
    module.create(*args)
    protocol = read_json(args[-1] / "protocol.json")
    config = yaml.safe_load((args[-1] / "config-en.yaml").read_text())
    (root / name).write_text("changed after protocol")
    with pytest.raises(ValueError, match="source changed"):
        module.validate(config, root / protocol["runs"]["en"])
