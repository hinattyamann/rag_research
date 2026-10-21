"""Certificate control tests use synthetic evidence and explicit validator doubles."""

import json
from copy import deepcopy

import pytest

from rag_research.experiments import bilingual_certification as module
from rag_research.experiments.bilingual_semantics import blank_unit_annotations, make_unit_packet
from rag_research.experiments.frozen_trace import digest
from rag_research.experiments.quality import cost
from rag_research.experiments.storage import checkpoint, read_json, run_lock, write_json
from rag_research.retrieval.common import file_hash


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    state = {"events": [], "sealed": set(), "semantic_pass": True, "bad_cost": False, "change": None}
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "candidate.yaml").write_text("candidate: synthetic\n")
    proof = tmp_path / "data/runs/semantic_diagnostics"
    for name in ("known", "prior"):
        folder = proof / name
        folder.mkdir(parents=True)
        (folder / ".run.lock").write_text("0")
        write_json(folder / "report.json", {"synthetic": True})
    plan = {"source_sha256": {}, "prerequisite": {"report_path": "data/runs/semantic_diagnostics/prior/report.json",
        "sha256": file_hash(proof / "prior/report.json")}}
    write_json(config_dir / "known-plan.json", plan)
    (config_dir / "known.yaml").write_text("diagnostics: configs/known-plan.json\n")
    write_json(proof / "known/manifest.json", {"plan_sha256": file_hash(config_dir / "known-plan.json")})
    write_json(config_dir / "policy.json", {"candidate_config": {
        "path": "configs/candidate.yaml", "sha256": file_hash(config_dir / "candidate.yaml")}})
    rows, inputs = {}, []
    for language in ("en", "ja"):
        run = tmp_path / "data/runs/bilingual_development" / language
        bundle, unit = run / "quality", run / "quality/units"
        unit.mkdir(parents=True)
        (run / ".run.lock").write_text("0")
        case = {"question": "Q?", "answer": "A fact.", "documents": [
            {"passage_id": "p", "title": "T", "text": "A fact."}]}
        packet = {"cases": [{**case, "annotation_id": "anon", "candidate_sha256": digest(case)}], "language": language}
        packet["packet_sha256"] = digest(packet)
        units = make_unit_packet(packet, language)
        labels = blank_unit_annotations(units)
        for label in labels["annotations"]:
            label.update(label="supported", reason="Exact source", evidence=[{"passage_id": "p", "quote": "A fact."}],
                annotator="synthetic-AI", elapsed_seconds=1.25, confirmed_at_utc="2026-10-22T00:00:00+00:00")
        write_json(bundle / "packet.json", packet)
        write_json(bundle / "mapping.private.json", {"synthetic": True})
        write_json(bundle / "annotations.json", {"annotations": [{"annotation_id": "anon", "label": "reliable",
            "annotator": "synthetic-AI", "elapsed_seconds": 2.5}]})
        write_json(unit / "packet.json", units)
        write_json(unit / "annotations.json", labels)
        rows[language] = [{"record_id": language + str(i), "document_group_id": language + "g" + str(i)} for i in range(20)]
        qa = config_dir / (language + ".jsonl")
        qa.write_text("synthetic QA source")
        config = {"language": language, "purpose": "phase11-bilingual-development-candidate", "assets": "configs/assets.json",
            "auxiliary_runtime": {"context_tokens": 24576},
            "execution_scope": "main_development_v1", "main_limits": {"maximum_completion_attempts": 1660},
            "main_execution_policy": {"path": "configs/policy.json", "sha256": file_hash(config_dir / "policy.json")},
            "adopted_known_regression": {"path": "data/runs/semantic_diagnostics/known/report.json",
                "sha256": file_hash(proof / "known/report.json"), "config": {"path": "configs/known.yaml",
                "sha256": file_hash(config_dir / "known.yaml")}}}
        manifest = {"language": language, "config": config, "selection": [{"record_id": r["record_id"]} for r in rows[language]],
            "baseline": {"generation": {"context_tokens": 4096}},
            "qa_path": qa.relative_to(tmp_path).as_posix(), "qa_sha256": file_hash(qa), "source_sha256": {}}
        write_json(run / "manifest.json", manifest)
        write_json(run / "report.private.json", {"selected_qa_count": 20, "failures": [], "records": [
            {"trace": {"record_id": r["record_id"]}, "rewrite": {"status": "ok"}} for r in rows[language]]})
        for row in rows[language]:
            for stage in ("baseline", "internal"):
                path = run / stage / row["record_id"] / ("record.json" if stage == "baseline" else "rewrite.json")
                path.parent.mkdir(parents=True)
                checkpoint(path, {"task": "baseline" if stage == "baseline" else "rewrite_answer", "status": "ok",
                    "completion_attempted": True, "input_tokens": 10, "output_tokens": 2,
                    **({"generation_seconds": .2, "context_seconds": .1} if stage == "baseline" else {"elapsed_seconds": .4})})
        for stage, context in (("baseline", 4096), ("internal", 24576)):
            write_json(run / stage / "session-1.json", {"execution": {"require_full_offload": True},
                "runtime": "synthetic", "server_context_tokens": context, "actual_gpu_offload": True,
                "full_gpu_offload": True, "offloaded_layers": 33, "total_layers": 33})
            (run / stage / "server-1.log").write_text("using device CUDA0\noffloaded 33/33 layers to GPU\n")
        inputs.append({"run": run.relative_to(tmp_path).as_posix(), "quality_bundle": bundle.relative_to(tmp_path).as_posix(),
            "quality_annotations": (bundle / "annotations.json").relative_to(tmp_path).as_posix(),
            "unit_bundle": unit.relative_to(tmp_path).as_posix(), "unit_annotations": (unit / "annotations.json").relative_to(tmp_path).as_posix()})
    path = config_dir / "inputs.json"
    write_json(path, inputs)

    def seal(bundle, annotations):
        packet = read_json(bundle / "packet.json")
        labels = {a["annotation_id"]: a for a in read_json(annotations)["annotations"]}
        if any(a["label"] == "pending" for a in labels.values()):
            raise ValueError("Seal every quality label")
        state["sealed"].add(packet["language"])
        return packet, {}, labels

    def prerequisite(report, candidate):
        assert state["sealed"] == {"en", "ja"} and ".certificate-" in str(report)
        state["events"].append("prerequisite")

    def semantics(specs):
        assert state["sealed"] == {"en", "ja"}
        state["events"].append("semantics")
        if state["change"]:
            target = tmp_path / inputs[0]["run"] / "report.private.json" if state["change"] == "original" else (
                tmp_path / specs[0]["run"] / "report.private.json")
            target.write_text('{"changed":true}')
        return {"main_development_semantic_gate_passed": state["semantic_pass"],
            "main_development_semantic_gate_per_language": {s: state["semantic_pass"] for s in ("en", "ja")},
            "languages": {s: {"complete_comparable_qa": 10} for s in ("en", "ja")}}

    def validate(config, selected, qa):
        assert len(selected) == 20 and ".certificate-" in config["adopted_known_regression"]["path"]
        state["events"].append("adopt:" + config["language"])

    def statistics(specs):
        state["events"].append("statistics")
        collections = []
        for spec in specs:
            manifest = read_json(tmp_path / spec["run"] / "manifest.json")
            language = manifest["language"]
            base = cost([{"completion_attempted": True, "input_tokens": 10, "output_tokens": 2, "elapsed_seconds": .3}] * 20)
            auxiliary = deepcopy(base)
            if state["bad_cost"]:
                auxiliary["input_tokens"] += 1
            collections.append({"language": language, "all_selected_baseline_cost": base,
                "quality_and_costs": {"auxiliary_collection_cost": auxiliary}, "run": spec["run"]})
        return {"condition_sha256": digest({"same": True}), "languages": {s: {
            "selected_qa_count": 20, "selected_document_groups": 20, "comparable_qa_count": 10} for s in ("en", "ja")},
            "all_selected_quality_costs": collections}

    original_hash = module.file_hash
    def checked_hash(p):
        if p.name == "report.private.json":
            assert state["sealed"] == {"en", "ja"}
        return original_hash(p)
    monkeypatch.setattr(module, "file_hash", checked_hash)
    monkeypatch.setattr(module.bilingual_quality, "sealed_annotations", seal)
    monkeypatch.setattr(module.bilingual_semantics, "analyze_semantics", semantics)
    monkeypatch.setattr(module.bilingual_statistics, "analyze_runs", statistics)
    monkeypatch.setattr(module.bilingual_statistics, "condition", lambda manifest: {"same": True})
    monkeypatch.setattr(module, "validate_main", validate)
    monkeypatch.setattr(module, "verify_prerequisite", prerequisite)
    monkeypatch.setattr(module, "execution_identity", lambda c: {"execution": {"require_full_offload": True}, "runtime": "synthetic"})
    monkeypatch.setattr(module, "load_assets", lambda *args, **kwargs: {})
    monkeypatch.setattr(module, "load_rows", lambda assets, language, split, **kwargs: (rows[language], config_dir / (language + ".jsonl")))
    return path, inputs, state, tmp_path


def test_certificate_binds_originals_full_proofs_native_costs_burden_and_never_allows_calibration(evidence):
    path, inputs, state, root = evidence
    before = {str(p): file_hash(p) for p in root.rglob("*") if p.is_file()}
    result = module.certify_main(path)
    assert state["events"] == ["prerequisite", "semantics", "adopt:en", "adopt:ja", "statistics"]
    assert result["status"] == "verified" and not result["calibration_execution_allowed"] and not result["gate11_passed"]
    assert result["new_model_calls"] == result["new_model_servers"] == 0
    assert all(v["recorded_native_attempts"] == v["native_collection_cost"]["completion_attempts"] == 40 for v in result["source_runs"].values())
    assert all(v["quality_annotation_seconds"] == 2.5 and v["unit_annotation_seconds"] == 1.25 for v in result["annotation_burden"].values())
    assert ".certificate-" not in json.dumps(result)
    assert before == {str(p): file_hash(p) for p in root.rglob("*") if p.is_file()}
    assert not list(root.rglob(".certificate-*"))


@pytest.mark.parametrize("kind", ["quality", "unit"])
def test_any_pending_language_stops_before_private_hashes_replays_or_certification(evidence, kind):
    path, inputs, state, root = evidence
    target = root / inputs[1][kind + "_annotations"]
    value = read_json(target)
    value["annotations"][0]["label"] = "pending"
    write_json(target, value)
    with pytest.raises(ValueError, match="Seal"):
        module.certify_main(path)
    assert state["events"] == [] and not list(root.rglob(".certificate-*"))


@pytest.mark.parametrize("change", ["semantic_gate", "cost", "raw", "partial"])
def test_unusable_evidence_never_gets_a_certificate(evidence, change):
    path, inputs, state, root = evidence
    if change == "semantic_gate":
        state["semantic_pass"] = False
    elif change == "cost":
        state["bad_cost"] = True
    elif change == "partial":
        report = root / inputs[0]["run"] / "report.private.json"
        value = read_json(report)
        value["records"].pop()
        write_json(report, value)
    else:
        raw = root / inputs[0]["run"] / "internal/en0/rewrite.json"
        write_json(raw, {"task": "rewrite_answer", "status": "started", "completion_attempted": True})
    with pytest.raises(ValueError):
        module.certify_main(path)
    assert not list(root.rglob(".certificate-*"))


def test_connection_scope_even_with_a_passing_flag_is_not_main_evidence(evidence):
    path, inputs, _, root = evidence
    manifest = root / inputs[0]["run"] / "manifest.json"
    value = read_json(manifest)
    value["config"]["execution_scope"] = "connection_smoke_only"
    write_json(manifest, value)
    with pytest.raises(ValueError, match="main20"):
        module.certify_main(path)


def test_run_owned_by_another_process_cannot_be_certified(evidence):
    path, inputs, state, root = evidence
    with run_lock(root / inputs[0]["run"]):
        with pytest.raises((BlockingIOError, ValueError)):
            module.certify_main(path)
    assert state["events"] == []


def test_changed_replay_is_rejected_and_original_research_stays_untouched(evidence):
    path, _, state, root = evidence
    before = {str(p): file_hash(p) for p in root.rglob("*") if p.is_file()}
    state["change"] = "copy"
    with pytest.raises((ValueError, KeyError)):
        module.certify_main(path)
    assert before == {str(p): file_hash(p) for p in root.rglob("*") if p.is_file()}
    assert not list(root.rglob(".certificate-*"))


def test_original_change_during_certification_is_detected(evidence):
    path, _, state, _ = evidence
    state["change"] = "original"
    with pytest.raises(ValueError, match="evidence changed"):
        module.certify_main(path)


def test_evaluation_source_file_and_duplicate_or_absolute_paths_are_rejected(evidence):
    path, inputs, _, root = evidence
    evaluation = root / "data/processed/evaluation.jsonl"
    evaluation.parent.mkdir(parents=True)
    evaluation.write_text("DO NOT OPEN")
    with pytest.raises(ValueError, match="not Evaluation"):
        module.certify_main(evaluation)
    write_json(path, [inputs[0], inputs[0]])
    with pytest.raises(ValueError, match="Duplicate"):
        module.certify_main(path)
    inputs[0]["run"] = str(root / inputs[0]["run"])
    write_json(path, inputs)
    with pytest.raises(ValueError, match="portable"):
        module.certify_main(path)


@pytest.fixture
def prerequisite(tmp_path, monkeypatch):
    """Exercise real assessment/checkpoints; model replay is an explicit double."""
    monkeypatch.setattr(module, "ROOT", tmp_path)
    run = tmp_path / "data/runs/semantic_diagnostics/prior"
    (run / "tasks").mkdir(parents=True)
    plan_path = tmp_path / "plan.json"
    cases = []
    for case_id, scope, language, label in (
            ("known", "known_used_development", "en", "contradicted"),
            ("positive", "synthetic_development", "en", "supported"),
            ("negative", "synthetic_development", "ja", "not_supported")):
        cases.append({"id": case_id, "scope": scope, "language": language, "question": "Q?", "answer": "A.",
            "claims": [{"claim_id": "c1", "text": "A."}], "expected": {"c1": label},
            "critical_claim_ids": ["c1"] if case_id == "known" else [],
            "documents": [{"passage_id": "p1", "text": "One."}, {"passage_id": "p2", "text": "Two."}]})
    plan = {"purpose": "phase11-known-bilingual-semantic-diagnostics", "cases": cases,
        "orders": ["original", "reversed"], "max_completion_attempts": 6}
    write_json(plan_path, plan)
    config = {"verification_mode": "claimwise-v1", "output_constraints": {}}
    manifest = {"config": config, "plan_sha256": file_hash(plan_path), "model": {"synthetic": True},
        "runtime": "synthetic", "source_sha256": {}}
    write_json(run / "manifest.json", manifest)
    tasks = {}
    for case, _, key in module.semantic_diagnostics.specs(plan):
        tasks[key] = checkpoint(run / "tasks" / (key + ".json"), {"status": "ok", "completion_attempted": True,
            "parsed": {"verdicts": [{"claim_id": "c1", "label": case["expected"]["c1"]}]}})
    report = {**module.semantic_diagnostics.assess(plan, tasks), "manifest_sha256": digest(manifest),
        "planned_conditions": 6, "completed_conditions": 6, "completion_attempts_recorded": 6,
        "cost_incomplete": False, "task_result_sha256": {k: v["result_sha256"] for k, v in tasks.items()}}
    write_json(run / "report.json", report)
    state = {"calls": [], "alter_replay": False}

    def replay(client, generation, prompts, payload, path, binding, **kwargs):
        assert client is None and kwargs["mode"] == "claimwise-v1" and kwargs["reader_generation"] is None
        expected = cases[0]["documents"]
        assert payload["documents"] == (expected if binding["order"] == "original" else list(reversed(expected)))
        state["calls"].append(path.stem)
        result = read_json(path)
        if state["alter_replay"]:
            result["input_tokens"] = 99
        return result

    monkeypatch.setattr(module.semantic_diagnostics, "load_config", lambda p: (
        config, plan, {"en": {}, "ja": {}}, plan_path))
    monkeypatch.setattr(module, "auxiliary_identity", lambda c: {"synthetic": True})
    monkeypatch.setattr(module, "execution_identity", lambda c: {"runtime": "synthetic"})
    monkeypatch.setattr(module, "task_config", lambda c, name: name)
    monkeypatch.setattr(module, "verify_once", replay)
    return run / "report.json", plan_path, state


def test_prerequisite_recomputes_every_order_and_both_language_gates(prerequisite):
    report, plan, state = prerequisite
    module.verify_prerequisite(report, plan)
    assert len(state["calls"]) == 6


@pytest.mark.parametrize("fault", ["incomplete", "plan", "missing_raw", "checkpoint", "replay", "false_pass", "calls"])
def test_prerequisite_cannot_trust_a_forged_pass_flag(prerequisite, fault):
    report_path, plan_path, state = prerequisite
    report = read_json(report_path)
    raw = report_path.parent / "tasks/negative-original.json"
    if fault == "incomplete":
        report["completed_conditions"] = 5
    elif fault == "plan":
        plan_path.write_text("Changed plan bytes")
    elif fault == "missing_raw":
        raw.unlink()
    elif fault in {"checkpoint", "false_pass", "calls"}:
        task = read_json(raw)
        if fault in {"checkpoint", "false_pass"}:
            task["parsed"]["verdicts"][0]["label"] = "supported"
        else:
            task["completion_attempted"] = False
        if fault == "checkpoint":
            write_json(raw, task)
        else:
            task.pop("result_sha256")
            task = checkpoint(raw, task)
            report["task_result_sha256"][raw.stem] = task["result_sha256"]
    else:
        state["alter_replay"] = True
    write_json(report_path, report)
    with pytest.raises((ValueError, FileNotFoundError)):
        module.verify_prerequisite(report_path, plan_path)


def test_interrupted_replay_leaves_originals_and_locks_usable(evidence, monkeypatch):
    path, inputs, _, root = evidence
    before = {str(p): file_hash(p) for p in root.rglob("*") if p.is_file()}

    def interrupt(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(module, "verify_prerequisite", interrupt)
    with pytest.raises(KeyboardInterrupt):
        module.certify_main(path)
    assert before == {str(p): file_hash(p) for p in root.rglob("*") if p.is_file()}
    assert not list(root.rglob(".certificate-*"))
    with run_lock(root / inputs[0]["run"]):
        pass


@pytest.mark.parametrize("fault", ["missing", "orphan", "cpu", "context", "runtime", "partial_layers"])
def test_main_certificate_needs_all_actual_gpu_session_evidence(evidence, fault):
    path, inputs, _, root = evidence
    run = root / inputs[0]["run"]
    session = run / "internal/session-1.json"
    saved = read_json(session)
    if fault == "missing":
        session.unlink()
    elif fault == "orphan":
        (run / "internal/server-2.log").write_text("Interrupted startup")
    elif fault in {"cpu", "partial_layers"}:
        (run / "internal/server-1.log").write_text("CPU model buffer\noffloaded 33/33 layers to GPU\n" if fault == "cpu"
            else "using device CUDA0\noffloaded 12/33 layers to GPU\n")
    else:
        saved["server_context_tokens" if fault == "context" else "runtime"] = 1024 if fault == "context" else "different"
        write_json(session, saved)
    with pytest.raises(ValueError, match="session|stage"):
        module.certify_main(path)
    assert not list(root.rglob(".certificate-*"))
