"""Freeze guards and projections; positive main/Calibration certification is explicitly doubled."""

from copy import deepcopy
from pathlib import Path

import pytest

from rag_research.experiments import bilingual_finalization as module
from rag_research.experiments.storage import checkpoint, read_json, write_json
from rag_research.retrieval.common import file_hash

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def final_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    for name in ("src/rag_research/fixed.py", "scripts/finalize_bilingual_phase11.py",
                 "docs/order_quality_rubric.md", "docs/phase11_statistical_plan.md"):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("Synthetic fixed source")

    def binding(name, value):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        write_json(p, value)
        return {"path": name, "sha256": file_hash(p)}

    decisions = read_json(REPO / "configs/phase11_bilingual_freeze_decisions_v1.json")
    decisions.update(status="resolved_pending_evidence_reverification", counts={"en": 30, "ja": 25},
        resource_safety_factor=2, resource_limits={lang: {"native_calls": 10000, "summed_native_step_seconds": 10000,
            "annotation_seconds": 10000} for lang in ("en", "ja")})
    main = {"source_runs": {}, "annotation_burden": {}, "condition_sha256": "same-frozen-condition",
        "evidence_files_sha256": {}, "bound_external_files_sha256": {}}
    calibration = {"created_at_utc": "synthetic-first-time", "analysis_elapsed_seconds": 10,
        "calibration_gate_passed": True, "human_reviewed": False, "new_model_calls": 0, "new_model_servers": 0,
        "statistics": {"condition_sha256": main["condition_sha256"], "languages": {}, "qa": [],
            "statistical_plan_sha256": file_hash(tmp_path / "docs/phase11_statistical_plan.md")},
        "native_collection_costs": {}, "annotation_burden": {}, "evidence_files_sha256": {}}
    native = {"completion_attempts": 220, "summed_step_seconds": 200, "incomplete": False}
    burden = {"quality_annotation_seconds": 20, "unit_annotation_seconds": 40}
    for lang in ("en", "ja"):
        run = "data/runs/bilingual_development/synthetic-" + lang
        binding(run + "/manifest.json", {"config": {"assets": decisions["assets"]["path"], "language": lang}})
        main["source_runs"][lang] = {"run": run, "selected": [
            {"record_id": lang + "main" + str(i), "document_group_id": lang + "group" + str(i)} for i in range(20)],
            "native_collection_cost": deepcopy(native)}
        main["annotation_burden"][lang] = deepcopy(burden)
        calibration["statistics"]["languages"][lang] = {"selected_qa_count": 20, "selected_document_groups": 20,
            "comparable_qa_count": 15}
        calibration["statistics"]["qa"].extend({"record_id": lang + "cal" + str(i)} for i in range(20))
        calibration["native_collection_costs"][lang] = deepcopy(native)
        calibration["annotation_burden"][lang] = deepcopy(burden)
    decisions["main_inputs"] = binding("configs/synthetic-main-inputs.json", [])
    decisions["main_certificate"] = binding("data/runs/development_certification/synthetic/certificate.private.json", {"synthetic": True})
    decisions["calibration_inputs"] = binding("configs/synthetic-calibration-inputs.json", [])
    protocol = {"main_inputs": decisions["main_inputs"], "main_certificate": decisions["main_certificate"],
        "condition_sha256": main["condition_sha256"]}
    protocol_path = tmp_path / "data/runs/bilingual_calibration_protocol/synthetic/protocol.json"
    protocol_path.parent.mkdir(parents=True)
    checkpoint(protocol_path, protocol)
    calibration["protocol"] = {"path": protocol_path.relative_to(tmp_path).as_posix(), "sha256": file_hash(protocol_path)}
    saved = tmp_path / "data/runs/bilingual_calibration_analysis/synthetic/analysis.private.json"
    saved.parent.mkdir(parents=True)
    checkpoint(saved, calibration)
    decisions["calibration_analysis"] = {"path": saved.relative_to(tmp_path).as_posix(), "sha256": file_hash(saved)}
    assets = {"datasets": {"ja": {"source_dataset": "baobab-trees/wikipedia-human-retrieval-ja"}}}
    decisions["assets"] = binding(decisions["assets"]["path"], assets)
    comparison = tmp_path / "docs/japanese_dataset_selection.md"
    comparison.write_text("Synthetic source comparison rationale")
    decisions["source_comparison_document"] = {"path": comparison.relative_to(tmp_path).as_posix(), "sha256": file_hash(comparison)}
    decisions["japanese_source_selection"] = binding(decisions["japanese_source_selection"]["path"], {
        "dataset_id": assets["datasets"]["ja"]["source_dataset"], "source_revision": module.REVISION,
        "status": "selected_for_phase11_preparation", "annotation_license_declared": "Apache-2.0",
        "wikipedia_content_rights_retained_separately": True})
    monkeypatch.setattr(module, "SOURCE_SELECTION_SHA256", decisions["japanese_source_selection"]["sha256"])
    state = {"sealed": False, "analyze_calls": 0, "main_calls": 0}

    def analyze(_):
        state["sealed"] = True
        state["analyze_calls"] += 1
        result = deepcopy(calibration)
        result.update(created_at_utc="synthetic-recheck-time", analysis_elapsed_seconds=15)
        return result

    def verify_main(*_):
        assert state["sealed"]
        state["main_calls"] += 1
        return main

    original_hash, original_read = module.file_hash, module.read_json

    def guarded_hash(p):
        if p == tmp_path / decisions["main_certificate"]["path"]:
            assert state["sealed"], "Do not hash a private certificate before both Calibration seals"
        return original_hash(p)

    def guarded_read(p):
        if p == saved or p == protocol_path:
            assert state["sealed"], "Do not open saved private analysis/protocol before seals"
        return original_read(p)

    monkeypatch.setattr(module.calibration_analysis, "analyze", analyze)
    monkeypatch.setattr(module.calibration_protocol, "verify_main", verify_main)
    monkeypatch.setattr(module, "file_hash", guarded_hash)
    monkeypatch.setattr(module, "read_json", guarded_read)
    monkeypatch.setattr(module, "load_assets", lambda *_args, **_kwargs: assets)
    monkeypatch.setattr(module, "retrieval_artifacts", lambda _: {})
    populations = {lang: [lang + "eval" + str(i) for i in range(50)] for lang in ("en", "ja")}
    for key, name in module.METADATA.items():
        decisions["evaluation_metadata"][key] = binding(name, {"synthetic-metadata": key})
    validation = {"purpose": "phase11-bilingual-finalization-validation-not-final-freeze",
        "tests": {"pytest_passed": 1, "ruff": "passed"}, "validation_source_sha256": module.sources(),
        "actual_pending_freeze_rejected": True, "actual_evaluation_qa_rows_parsed": 0, "new_model_calls": 0,
        "gate11_passed": False, "artifacts": {"src/rag_research/fixed.py": {"sha256": file_hash(tmp_path / "src/rag_research/fixed.py")}}}
    vp = tmp_path / "data/manifests/synthetic-validation.json"
    vp.parent.mkdir(parents=True, exist_ok=True)
    checkpoint(vp, validation)
    decisions["validator_validation"] = {"path": vp.relative_to(tmp_path).as_posix(), "sha256": file_hash(vp)}
    monkeypatch.setattr(module, "evaluation_population", lambda _: populations)
    decision_path = tmp_path / "configs/final-decisions.json"
    write_json(decision_path, decisions)
    return tmp_path, decision_path, decisions, main, calibration, state, populations


def test_positive_freeze_with_explicit_certification_doubles(final_evidence):
    root, p, _, _, _, state, _ = final_evidence
    result = module.readiness(p.relative_to(root).as_posix())
    assert result["gate11_passed"] and all(result["checks"].values())
    assert state["analyze_calls"] == state["main_calls"] == 1
    conditions = result["conditions"]
    assert {k: len(v) for k, v in conditions["evaluation_record_ids"].items()} == {"en": 30, "ja": 25}
    assert conditions["resource_projection"]["en"]["projected_with_safety_factor"] == {
        "native_calls": 660, "summed_native_step_seconds": 600, "annotation_seconds": 180}
    assert conditions["new_model_calls"] == conditions["evaluation_qa_rows_read"] == 0
    saved = module.save(p.relative_to(root).as_posix(), "data/manifests/phase11_bilingual_final_freeze_v1.json")
    assert saved["schema_version"] == 2 and saved["gate11_passed"]
    assert state["analyze_calls"] == state["main_calls"] == 2  # save rechecks, never accepts a pass flag
    with pytest.raises(ValueError, match="previous final freeze"):
        module.save(p.relative_to(root).as_posix(), "data/manifests/phase11_bilingual_final_freeze_v1.json")


@pytest.mark.parametrize("matching", [False, True])
def test_finalization_requires_same_binary_version_as_main_and_calibration(final_evidence, matching):
    from rag_research.experiments.semantic_adoption import BINARY

    root, path, decisions, main, calibration, _, _ = final_evidence
    decisions["semantic_adoption_version"] = BINARY
    main["semantics"] = {"semantic_adoption_version": BINARY}
    calibration["semantics"] = {"semantic_adoption_version": BINARY if matching else "three-label-v1"}
    saved_path = root / decisions["calibration_analysis"]["path"]
    checkpoint(saved_path, calibration)
    decisions["calibration_analysis"]["sha256"] = file_hash(saved_path)
    write_json(path, decisions)
    result = module.readiness(path.relative_to(root).as_posix())
    assert result["gate11_passed"] is matching
    if not matching:
        assert "semantic adoption versions differ" in str(result["reasons"])


@pytest.mark.parametrize("field,value", [("status", "pending"), ("counts", {"en": 200, "ja": None}),
    ("selection_uses_effect_size_or_significance", True), ("automatic_refill", True),
    ("resource_safety_factor", float("inf")), ("retry_unknown_outcomes", True),
    ("statistics", {"language_contrast": "paired_language_effect"})])
def test_pending_or_weakened_decisions_stop_before_private_analysis(final_evidence, field, value):
    root, p, decisions, _, _, state, _ = final_evidence
    decisions[field] = value
    # JSON does not permit nonfinite input; test this case against the pure validator.
    if field == "resource_safety_factor":
        with pytest.raises(ValueError):
            module.public_decisions(decisions)
        return
    write_json(p, decisions)
    result = module.readiness(p.relative_to(root).as_posix())
    assert not result["gate11_passed"] and not result["phase12_allowed"] and result["conditions"] is None
    assert state["analyze_calls"] == state["main_calls"] == 0


@pytest.mark.parametrize("failure", ["failed_calibration", "pending_labels", "native_cost_change", "condition_change",
    "resource_limit", "unknown_cost", "evaluation_overlap", "population_too_small", "source_changed",
    "prior_evaluation", "late_evidence_change", "validator_source_drift", "validator_artifact_drift"])
def test_incomplete_or_changed_evidence_never_writes_freeze(final_evidence, monkeypatch, failure):
    root, p, decisions, main, cal, _, populations = final_evidence
    if failure == "failed_calibration":
        cal["calibration_gate_passed"] = False
    elif failure == "pending_labels":
        def unsealed(_):
            raise ValueError("Seal every unit label in both languages")
        monkeypatch.setattr(module.calibration_analysis, "analyze", unsealed)
    elif failure == "native_cost_change":
        cal["native_collection_costs"]["en"]["completion_attempts"] += 1
    elif failure == "condition_change":
        main["condition_sha256"] = "changed"
    elif failure == "resource_limit":
        decisions["resource_limits"]["ja"]["native_calls"] = 1
    elif failure == "unknown_cost":
        main["source_runs"]["en"]["native_collection_cost"]["incomplete"] = True
    elif failure == "evaluation_overlap":
        populations["en"] = [main["source_runs"]["en"]["selected"][0]["record_id"]]
        decisions["counts"]["en"] = 1
    elif failure == "population_too_small":
        decisions["counts"]["ja"] = 51
    elif failure == "source_changed":
        original = module.calibration_analysis.analyze
        def changed(path):
            result = original(path)
            (root / "src/rag_research/fixed.py").write_text("changed during recheck")
            return result
        monkeypatch.setattr(module.calibration_analysis, "analyze", changed)
    elif failure == "prior_evaluation":
        prior = root / "data/runs/bilingual_evaluation/started/request.json"
        prior.parent.mkdir(parents=True)
        prior.write_text("Do not parse this Evaluation execution artifact")
    elif failure == "late_evidence_change":
        raw = root / "data/runs/bilingual_development/synthetic-en/raw.json"
        raw.write_text("original raw")
        main["evidence_files_sha256"][raw.relative_to(root).as_posix()] = file_hash(raw)
        original = module.resource_projection
        def changed_projection(*args):
            result = original(*args)
            raw.write_text("changed after full certification")
            return result
        monkeypatch.setattr(module, "resource_projection", changed_projection)
    elif failure == "validator_source_drift":
        (root / "scripts/finalize_bilingual_phase11.py").write_text("changed after test evidence")
    elif failure == "validator_artifact_drift":
        vp = root / decisions["validator_validation"]["path"]
        validation = read_json(vp)
        validation["artifacts"]["src/rag_research/fixed.py"]["sha256"] = "changed"
        checkpoint(vp, {k: v for k, v in validation.items() if k != "result_sha256"})
        decisions["validator_validation"]["sha256"] = file_hash(vp)
    write_json(p, decisions)
    with pytest.raises(ValueError, match="unmet requirements"):
        module.save(p.relative_to(root).as_posix(), "data/manifests/phase11_bilingual_final_freeze_v1.json")
    assert not (root / "data/manifests/phase11_bilingual_final_freeze_v1.json").exists()


def test_actual_pending_template_rejects_without_new_inference():
    result = module.readiness("configs/phase11_bilingual_freeze_decisions_v1.json")
    assert not result["gate11_passed"] and not result["phase12_allowed"] and result["conditions"] is None
    assert result["checks"] == dict.fromkeys(module.CHECKS, False)


def test_actual_metadata_selection_never_parses_evaluation_qa(monkeypatch):
    if not all((REPO / name).is_file() for name in module.METADATA.values()):
        pytest.skip("Locally acquired dataset group metadata is not installed")
    seen, original = [], module.read_json
    def only_metadata(p):
        assert p in {REPO / name for name in module.METADATA.values()}
        seen.append(p)
        return original(p)
    monkeypatch.setattr(module, "read_json", only_metadata)
    decisions = original(REPO / "configs/phase11_bilingual_freeze_decisions_v1.json")
    populations = module.evaluation_population(decisions["evaluation_metadata"])
    assert {k: len(v) for k, v in populations.items()} == {"en": 564, "ja": 209}
    selected = module.choose(populations, {"en": 20, "ja": 15})
    assert selected == module.choose({k: list(reversed(v)) for k, v in populations.items()}, {"en": 20, "ja": 15})
    assert len(seen) == 3
    decisions["evaluation_metadata"]["en"]["sha256"] = "updated-but-unapproved"
    with pytest.raises(ValueError, match="immutable"):
        module.evaluation_population(decisions["evaluation_metadata"])


@pytest.mark.parametrize("name", ["../escape.json", "/tmp/external.json", "data/processed/evaluation.jsonl"])
def test_decisions_scope_cannot_parse_evaluation_rows(name):
    result = module.readiness(name)
    assert not result["gate11_passed"] and "decisions" in result["reasons"]


def test_index_and_embedding_payloads_checked_without_gpu(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    corpus = tmp_path / "data/processed/synthetic/corpus.jsonl"
    corpus.parent.mkdir(parents=True)
    corpus.write_text("Synthetic corpus; no Evaluation QA")
    index = tmp_path / "data/indexes/synthetic/embedding"
    index.mkdir(parents=True)
    (index / "vectors.npy").write_bytes(b"synthetic-vector-payload")
    model_root = tmp_path / "data/models/synthetic"
    revision = "a" * 40
    model = model_root / revision
    model.mkdir(parents=True)
    (model / "model.onnx").write_bytes(b"synthetic-model-payload")
    manifest = {"schema_version": 1, "corpus": {"sha256": file_hash(corpus)},
        "files": {"vectors.npy": {"sha256": file_hash(index / "vectors.npy"), "bytes": (index / "vectors.npy").stat().st_size}},
        "config": {"model": {"revision": revision, "files": {"model.onnx": {"sha256": file_hash(model / "model.onnx")}}}}}
    write_json(model / "model_manifest.json", manifest["config"]["model"])
    write_json(index / "manifest.json", manifest)
    assets = {"embedding": {"model_root": model_root.relative_to(tmp_path).as_posix()}, "datasets": {"synthetic": {
        "corpus": {"path": corpus.relative_to(tmp_path).as_posix(), "sha256": file_hash(corpus)},
        "indexes": {"embedding": {"path": (index / "manifest.json").relative_to(tmp_path).as_posix(),
                                   "sha256": file_hash(index / "manifest.json")}}}}}
    assert len(module.retrieval_artifacts(assets)) == 3
    (model / "model.onnx").write_bytes(b"changed-model")
    with pytest.raises(ValueError, match="Embedding model payload changed"):
        module.retrieval_artifacts(assets)
    (model / "model.onnx").write_bytes(b"synthetic-model-payload")
    (index / "vectors.npy").write_bytes(b"changed-vector")
    with pytest.raises(ValueError, match="Index artifact hash mismatch"):
        module.retrieval_artifacts(assets)
