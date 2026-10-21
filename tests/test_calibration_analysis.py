"""Real seals, semantic counts, statistics and native costs; explicit protocol/raw/GPU doubles."""

import json
from pathlib import Path

import pytest

from rag_research.experiments import bilingual_quality as quality
from rag_research.experiments import bilingual_semantics as semantics
from rag_research.experiments import bilingual_statistics as statistics
from rag_research.experiments import calibration_analysis as module
from rag_research.experiments import calibration_protocol
from rag_research.experiments.frozen_trace import digest
from rag_research.experiments.quality import blank_annotations, make_packet
from rag_research.experiments.storage import checkpoint, read_json, run_lock, write_json
from rag_research.retrieval.common import file_hash

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    for target in (module, quality, semantics, statistics):
        monkeypatch.setattr(target, "ROOT", tmp_path)
    state = {"sealed": set(), "units": set(), "private": [], "bad_resource": False, "change": None}
    for name in ["src/rag_research/fixed.py", "scripts/analyze_bilingual_calibration.py",
            "scripts/prepare_bilingual_calibration.py", "scripts/run_bilingual_calibration.py",
            "scripts/bilingual_quality.py", "scripts/review_bilingual_units.py", "docs/order_quality_rubric.md",
            "configs/prompts.yaml", "configs/assets.json", "docs/phase11_statistical_plan.md"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("tasks:\n  verify_claims:\n    system: Shared fixture\n")
    rule_path = tmp_path / "configs/rules.json"
    rule_path.write_bytes((REPO / "configs/phase11_bilingual_calibration_execution_rules_v1.json").read_bytes())
    rule_binding = {"path": "configs/rules.json", "sha256": file_hash(rule_path)}
    assets = {"datasets": {}}
    inputs, source_rows, language_by_packet = [], {}, {}
    orders = ["original", "reversed", "shuffle_1", "shuffle_2", "shuffle_3"]
    repeats = ["original", "repeat_2", "repeat_3", "repeat_4", "repeat_5"]
    doc_orders = [["p1", "p2", "p3"], ["p3", "p2", "p1"], ["p2", "p1", "p3"], ["p1", "p3", "p2"], ["p2", "p3", "p1"]]
    definitions = dict(zip(orders, doc_orders, strict=True))
    definitions.update({i: doc_orders[0] for i in repeats})
    documents = [{"passage_id": "p1", "title": "Tower", "text": "The tower is 42 metres tall. 塔の高さは42メートルです。"},
        {"passage_id": "p2", "title": "Other", "text": "Noise."}, {"passage_id": "p3", "title": "Third", "text": "More noise."}]
    for language in ("en", "ja"):
        run = tmp_path / "data/runs/bilingual_calibration" / language
        run.mkdir(parents=True)
        (run / ".run.lock").write_text("0")
        split = "development" if language == "en" else "calibration"
        qa_path = tmp_path / "data/processed" / language / (split + ".jsonl")
        qa_path.parent.mkdir(parents=True)
        rows = [{"record_id": language + str(n), "document_group_id": language + "g" + str(n)} for n in range(20)]
        qa_path.write_text("".join(json.dumps(r) + "\n" for r in rows))
        source_rows[language] = rows
        assets["datasets"][language] = {"qa": {s: {"path": str(qa_path.relative_to(tmp_path)) if s == split else language + "/" + s}
            for s in ("development", "calibration", "evaluation")}}
        config = {"purpose": "phase11-bilingual-calibration-candidate", "execution_scope": "heldout_calibration_v1",
            "analysis_split": "calibration", "language": language, "data": {"split": split},
            "assets": "configs/assets.json", "prompts": "configs/prompts.yaml", "calibration_limits": {"maximum_completion_attempts": 1660},
            "calibration_protocol": {"path": "configs/synthetic-protocol.json", "sha256": "test-double"},
            "decision": {"threshold": .7}, "verification_mode": "claimwise-v1"}
        manifest = {"language": language, "config": config, "baseline_model": {"id": "synthetic-base"},
            "auxiliary_model": {"id": "synthetic-judge"}, "baseline": {"generation": {}},
            "qa_path": qa_path.relative_to(tmp_path).as_posix(), "qa_sha256": file_hash(qa_path),
            "selection": [{"record_id": r["record_id"]} for r in rows]}
        records = []
        references = {}
        for number, row in enumerate(rows):
            identifier = row["record_id"]
            answer = "The tower is 42 metres tall." if language == "en" else "塔の高さは42メートルです。"
            question = language + " question " + str(number)
            trace = {"record_id": identifier, "question": question, "answer": answer, "documents": documents}
            claims = semantics.extract_sentence_units(answer, language=language)["claims"]
            folder = run / "internal" / digest(identifier)[:24]
            folder.mkdir(parents=True)
            base = run / "baseline" / digest(identifier)[:24] / "record.json"
            base.parent.mkdir(parents=True)
            baseline = checkpoint(base, {"task": "baseline", "status": "ok", "completion_attempted": True,
                "input_tokens": 10, "output_tokens": 2, "generation_seconds": .2, "context_seconds": .1, "answer_generation_calls": 1})
            extraction = checkpoint(folder / "claims.json", {"task": "extract_claims", "status": "ok", "completion_attempted": False,
                "input_tokens": 0, "output_tokens": 0, "elapsed_seconds": 0, "parsed": {"claims": claims}})
            rewrite = checkpoint(folder / "rewrite.json", {"task": "rewrite_answer", "status": "ok", "answer": answer,
                "completion_attempted": True, "input_tokens": 10, "output_tokens": 2, "elapsed_seconds": .4})
            judges = {i: checkpoint(folder / (i + ".json"), {"task": "verify_claims", "status": "ok", "completion_attempted": True,
                "input_tokens": 10, "output_tokens": 2, "elapsed_seconds": .1,
                "parsed": {"verdicts": [{"claim_id": "c1", "label": "supported"}], "score": 1.}}) for i in definitions}
            evaluation = {"claims": claims, "threshold": .7,
                "plan": {"order_group": orders, "repeat_group": repeats,
                    "trials": [{"trial_id": i, "document_ids": d} for i, d in definitions.items()]},
                "trials": [{"trial_id": i, "status": "ok", "score": 1., "decision": "accept", "action": "accepted"} for i in definitions]}
            records.append({"trace": trace, "rewrite": rewrite, "evaluation": evaluation,
                "tasks": {"extraction": extraction, "judges": judges}, "baseline_cost": {k: baseline[k] for k in
                ("input_tokens", "output_tokens", "generation_seconds", "context_seconds", "answer_generation_calls")}})
            references[identifier] = {"reference_answers": [answer], "selected_sentences_by_reference": [], "gold_passage_ids": []}
        report = {"selected_qa_count": 20, "records": records, "failures": []}
        write_json(run / "manifest.json", manifest)
        write_json(run / "report.private.json", report)
        packet, mapping = make_packet(records, references, {}, "Synthetic rubric", "v1", 42, digest(manifest))
        bundle, units = run / "quality", run / "quality/units"
        units.mkdir(parents=True)
        write_json(bundle / "packet.json", packet)
        checkpoint(bundle / "mapping.private.json", mapping)
        write_json(bundle / "export_manifest.json", {"synthetic": True})
        labels = blank_annotations(packet)
        for label in labels["annotations"]:
            label.update(label="reliable", criteria=dict.fromkeys(label["criteria"], "pass"), essential_points="Tower height",
                reason="Synthetic exact support", annotator="Synthetic-AI", elapsed_seconds=.5,
                confirmed_at_utc="2026-10-22T00:00:00+00:00", evidence=[{"passage_id": "p1", "quote": "42"}])
        write_json(bundle / "annotations.json", labels)
        unit_packet = semantics.make_unit_packet(packet, language)
        write_json(units / "packet.json", unit_packet)
        unit_labels = semantics.blank_unit_annotations(unit_packet)
        for label in unit_labels["annotations"]:
            label.update(label="supported", reason="Exact synthetic source", annotator="Synthetic-AI", elapsed_seconds=.25,
                confirmed_at_utc="2026-10-22T00:00:00+00:00", evidence=[{"passage_id": "p1", "quote": "42"}])
        write_json(units / "annotations.json", unit_labels)
        inputs.append({"run": run.relative_to(tmp_path).as_posix(), "quality_bundle": bundle.relative_to(tmp_path).as_posix(),
            "quality_annotations": (bundle / "annotations.json").relative_to(tmp_path).as_posix(),
            "unit_bundle": units.relative_to(tmp_path).as_posix(), "unit_annotations": (units / "annotations.json").relative_to(tmp_path).as_posix()})
        language_by_packet[packet["packet_sha256"]] = language
    input_path = tmp_path / "configs/inputs.json"
    write_json(input_path, inputs)
    (tmp_path / "data/runs/bilingual_calibration/.run.lock").write_text("0")
    original_seal, original_units, original_hash = quality.sealed_annotations, semantics.validate_unit_annotations, module.file_hash

    def seal(bundle, labels):
        value = original_seal(bundle, labels)
        state["sealed"].add(language_by_packet[value[0]["packet_sha256"]])
        return value

    def seal_units(packet, labels, *, sealed=False):
        value = original_units(packet, labels, sealed=sealed)
        if sealed:
            state["units"].add(packet["language"])
        return value

    def verified(run, bundle, labels):
        assert state["sealed"] == state["units"] == {"en", "ja"}
        state["private"].append(run)
        manifest, report = read_json(run / "manifest.json"), read_json(run / "report.private.json")
        packet, mapping, assigned = original_seal(bundle, labels)
        slots = {(s["record_id"], s["stage"]): assigned[i]["label"] for i, group in mapping["assignments"].items() for s in group}
        if state["change"]:
            target = (tmp_path / inputs[0]["run"]) if state["change"] == "original" else run
            (target / "report.private.json").write_text('{"changed":true}')
        return manifest, report, slots

    def proof(run, manifest, *, canonical_runs=None):
        assert canonical_runs is not None and run in canonical_runs and len(canonical_runs) == 2
        assert state["sealed"] == state["units"] == {"en", "ja"}
        return {"rules": rule_binding}

    def resources(run, manifest):
        if state["bad_resource"]:
            raise ValueError("Synthetic missing GPU evidence")
        return []

    def checked_hash(path):
        if path.name in {"manifest.json", "report.private.json"}:
            assert state["sealed"] == state["units"] == {"en", "ja"}
        return original_hash(path)

    monkeypatch.setattr(quality, "sealed_annotations", seal)
    monkeypatch.setattr(semantics, "validate_unit_annotations", seal_units)
    monkeypatch.setattr(quality, "validated_annotations", verified)
    monkeypatch.setattr(calibration_protocol, "review_contract", proof)
    monkeypatch.setattr(statistics, "load_assets", lambda *args, **kwargs: assets)
    monkeypatch.setattr(statistics, "load_rows", lambda assets, language, split, **kwargs: (
        source_rows[language], tmp_path / assets["datasets"][language]["qa"][split]["path"]))
    monkeypatch.setattr(module, "resource_sessions", resources)
    monkeypatch.setattr(module, "file_hash", checked_hash)
    return input_path, inputs, state, tmp_path


def test_isolated_calibration_keeps_all20_actual_counts_costs_and_zero_effect_is_acceptable(evidence):
    path, _, state, root = evidence
    before = {str(p): file_hash(p) for p in root.rglob("*") if p.is_file()}
    result = module.analyze(path)
    assert result["calibration_gate_passed"] and not result["gate11_passed"] and not result["phase12_allowed"]
    assert result["new_model_calls"] == result["new_model_servers"] == 0
    assert all(v["completion_attempts"] == 220 and v["input_tokens"] == 2200 for v in result["native_collection_costs"].values())
    assert all(v["selected_qa_count"] == v["comparable_qa_count"] == v["selected_document_groups"] == 20
        for v in result["statistics"]["languages"].values())
    assert result["statistics"]["ja_minus_en"] == {"mean": 0., "ci95": [0., 0.]}
    assert all(v["quality_labels"] == v["unit_labels"] == 20 for v in result["annotation_burden"].values())
    assert state["private"] and "bilingual_calibration_replay" not in json.dumps(result)
    assert before == {str(p): file_hash(p) for p in root.rglob("*") if p.is_file()}
    assert not list(root.rglob(".analysis-*"))


@pytest.mark.parametrize("kind", ["quality", "unit"])
def test_pending_either_kind_in_last_language_prevents_all_private_hashes_and_reads(evidence, kind):
    path, inputs, state, root = evidence
    target = root / inputs[1][kind + "_annotations"]
    value = read_json(target)
    value["annotations"][-1]["label"] = "pending"
    if kind == "quality":
        value["annotations"][-1]["criteria"] = dict.fromkeys(value["annotations"][-1]["criteria"], "pending")
    write_json(target, value)
    with pytest.raises(ValueError, match="Seal"):
        module.analyze(path)
    assert state["private"] == [] and not list(root.rglob(".analysis-*"))


def test_missing_resource_proof_fails_health_but_preserves_known_native_costs(evidence):
    path, _, state, _ = evidence
    state["bad_resource"] = True
    result = module.analyze(path)
    assert not result["calibration_gate_passed"] and all(v is False for v in result["health_gate_per_language"].values())
    assert all(v["completion_attempts"] == 220 for v in result["native_collection_costs"].values())


def test_missing_native_call_cannot_disappear_from_collection_cost(evidence):
    path, inputs, _, root = evidence
    (root / inputs[0]["run"] / "internal" / digest("en0")[:24] / "original.json").unlink()
    with pytest.raises(ValueError, match="native cost differs"):
        module.analyze(path)


@pytest.mark.parametrize("change", ["copy", "original"])
def test_changed_copy_or_original_is_rejected_and_copies_are_cleaned(evidence, change):
    path, _, state, root = evidence
    state["change"] = change
    with pytest.raises((ValueError, KeyError)):
        module.analyze(path)
    assert not list(root.rglob(".analysis-*"))


def test_exception_during_private_replay_releases_locks_and_preserves_originals(evidence, monkeypatch):
    path, inputs, _, root = evidence
    before = {str(p): file_hash(p) for p in root.rglob("*") if p.is_file()}

    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(semantics, "analyze_semantics", interrupt)
    with pytest.raises(KeyboardInterrupt):
        module.analyze(path)
    assert before == {str(p): file_hash(p) for p in root.rglob("*") if p.is_file()}
    with run_lock(root / inputs[0]["run"]):
        pass


def test_input_evaluation_and_duplicate_paths_are_rejected_without_opening_them(evidence):
    path, inputs, _, root = evidence
    evaluation = root / "data/processed/evaluation.jsonl"
    evaluation.parent.mkdir(parents=True, exist_ok=True)
    evaluation.write_text("Never parse")
    with pytest.raises(ValueError, match="Evaluation"):
        module.analyze(evaluation)
    write_json(path, [inputs[0], inputs[0]])
    with pytest.raises(ValueError, match="Duplicate"):
        module.analyze(path)


def test_direct_calibration_statistics_requires_both_kinds_of_sealed_review(evidence):
    _, inputs, state, _ = evidence
    projected = [{"run": r["run"], "bundle": r["quality_bundle"], "annotations": r["quality_annotations"]} for r in inputs]
    with pytest.raises(ValueError, match="One sealed"):
        statistics.analyze_runs(projected, analysis_split="calibration")
    assert state["private"] == []


def test_incomparable_qa_are_retained_and_nine_comparisons_do_not_pass_calibration(evidence):
    path, inputs, _, root = evidence
    for spec in inputs:
        run = root / spec["run"]
        report = read_json(run / "report.private.json")
        for record in report["records"][9:]:
            evaluation = record["evaluation"]
            extra = set(evaluation["plan"]["order_group"]) - {"original"}
            evaluation["plan"]["order_group"] = ["original"]
            evaluation["plan"]["trials"] = [r for r in evaluation["plan"]["trials"] if r["trial_id"] not in extra]
            evaluation["trials"] = [r for r in evaluation["trials"] if r["trial_id"] not in extra]
            for trial in extra:
                record["tasks"]["judges"].pop(trial)
                (run / "internal" / digest(record["trace"]["record_id"])[:24] / (trial + ".json")).unlink()
        write_json(run / "report.private.json", report)
    result = module.analyze(path)
    assert not result["calibration_gate_passed"] and all(result["health_gate_per_language"].values())
    for lang in ("en", "ja"):
        assert result["statistics"]["languages"][lang]["selected_qa_count"] == 20
        assert result["statistics"]["languages"][lang]["comparable_qa_count"] == 9
        assert result["semantics"]["languages"][lang]["complete_comparable_qa"] == 9
        assert result["native_collection_costs"][lang]["completion_attempts"] == 176


def test_statistical_and_semantic_counts_must_agree_before_calibration_can_pass(evidence, monkeypatch):
    path, _, _, _ = evidence
    original = statistics.analyze_runs

    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        result["languages"]["en"]["comparable_qa_count"] -= 1
        return result

    monkeypatch.setattr(statistics, "analyze_runs", changed)
    with pytest.raises(ValueError, match="comparison counts differ"):
        module.analyze(path)


def test_statistical_plan_change_during_analysis_is_detected_after_the_last_replay(evidence, monkeypatch):
    path, _, _, root = evidence
    original = statistics.analyze_runs

    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        (root / "docs/phase11_statistical_plan.md").write_text("Changed after computing estimates")
        return result

    monkeypatch.setattr(statistics, "analyze_runs", changed)
    with pytest.raises(ValueError, match="evidence/source changed"):
        module.analyze(path)
