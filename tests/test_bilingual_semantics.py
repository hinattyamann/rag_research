"""Stage blindness, context-only truth, all-label sealing, and unchanged F denominators."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from rag_research.experiments import bilingual_semantics as sem
from rag_research.experiments.quality import make_packet
from rag_research.experiments.storage import checkpoint, write_json


def public_packet(language="en", *, identical=False, bare=False):
    answer = "The tower is 42 metres tall.[p1]" if language == "en" else "塔の高さは42メートルです。[p1]"
    if bare:
        answer = ("The provided context does not contain enough information to answer this question."
                  if language == "en" else "提示された根拠には、この質問に答えるための十分な情報がありません。")
    other = answer if identical else answer.replace("42", "24")
    document = {"passage_id": "p1", "title": "Tower", "text": "The tower is 42 metres tall. 塔の高さは42メートルです。"}
    row = {"trace": {"record_id": language + "-id", "question": "How tall?", "answer": answer, "documents": [document]},
           "rewrite": {"status": "ok", "answer": other}}
    qa = {language + "-id": {"reference_answers": ["GOLD-SECRET"], "selected_sentences_by_reference": [], "gold_passage_ids": ["g1"]}}
    gold = {"g1": {"passage_id": "g1", "title": "Gold", "text": "REFERENCE-SECRET"}}
    packet, mapping = make_packet([row], qa, gold, "quality rubric", "v1", 42, "run")
    return packet, mapping


def completed(packet):
    labels = sem.blank_unit_annotations(packet)
    for row in labels["annotations"]:
        row.update(label="supported", reason="Synthetic source support", annotator="Codex AI test fixture",
                   evidence=[{"passage_id": "p1", "quote": "42"}], elapsed_seconds=1., confirmed_at_utc="2026-10-21T13:00:00+00:00")
    return labels


def test_public_units_hide_stage_gold_and_internal_results_and_keep_identical_candidates_once():
    original, mapping = public_packet(identical=True)
    packet = sem.make_unit_packet(original, "en")
    assert len(packet["cases"]) == 1 and len(mapping["assignments"][packet["cases"][0]["annotation_id"]]) == 2
    assert len(sem.blank_unit_annotations(packet)["annotations"]) == 1
    text = str(packet)
    assert "GOLD-SECRET" not in text and "REFERENCE-SECRET" not in text
    assert all(k not in packet["cases"][0] for k in ("stage", "score", "decision", "reference_answers", "gold_documents", "record_id"))
    tampered = deepcopy(packet)
    tampered["cases"][0]["unit_audit"]["claims"][0]["text"] = "altered"
    with pytest.raises(ValueError, match="hash"):
        sem.verify_unit_packet(tampered)


def test_annotation_requires_all_units_provenance_and_only_verbatim_used_evidence():
    quality, _ = public_packet()
    packet = sem.make_unit_packet(quality, "en")
    value = completed(packet)
    assert len(sem.validate_unit_annotations(packet, value, sealed=True)) == 2
    blank = sem.blank_unit_annotations(packet)
    with pytest.raises(ValueError, match="Seal every"):
        sem.validate_unit_annotations(packet, blank, sealed=True)
    changes = [lambda v: v["annotations"].pop(),
               lambda v: v["annotations"][0].update(human_reviewed=True),
               lambda v: v["annotations"][0].update(evidence=[{"passage_id": "g1", "quote": "REFERENCE-SECRET"}]),
               lambda v: v["annotations"][0].update(evidence=[{"passage_id": "p1", "quote": "paraphrase"}]),
               lambda v: v["annotations"][0].update(elapsed_seconds=0)]
    for change in changes:
        bad = deepcopy(value)
        change(bad)
        with pytest.raises(ValueError):
            sem.validate_unit_annotations(packet, bad, sealed=True)


def test_bare_refusal_is_present_with_empty_units_and_no_fictitious_semantic_label():
    quality, _ = public_packet("ja", identical=True, bare=True)
    packet = sem.make_unit_packet(quality, "ja")
    assert len(packet["cases"]) == 1 and packet["cases"][0]["unit_audit"]["exclusion"] == "standalone_refusal"
    blank = sem.blank_unit_annotations(packet)
    assert blank["annotations"] == [] and sem.validate_unit_annotations(packet, blank, sealed=True) == {}


def record_for(packet, identifier, *, predicted=("supported", "supported", "contradicted")):
    case = packet["cases"][0]
    ids = ["original", "reversed", "repeat_2"]
    trials = [{"trial_id": i, "status": "ok", "score": int(label == "supported")} for i, label in zip(ids, predicted, strict=True)]
    return {"trace": {"record_id": identifier},
            "evaluation": {"claims": case["unit_audit"]["claims"], "trials": trials,
                           "plan": {"trials": [{"trial_id": i} for i in ids], "order_group": ids[:2], "repeat_group": [ids[0], ids[2]]}},
            "tasks": {"judges": {i: {"status": "ok", "parsed": {"verdicts": [{"claim_id": "c1", "label": label}]}}
                                  for i, label in zip(ids, predicted, strict=True)}}}


def test_accuracy_keeps_all_planned_units_ambiguity_and_failures_without_changing_F():
    quality, _ = public_packet(identical=True)
    packet = sem.make_unit_packet(quality, "en")
    record = record_for(packet, "id")
    original = deepcopy(record)
    counts = sem.semantic_counts([record], {("id", "c1"): "supported"})
    assert counts["exact_label_accuracy"] == counts["supported_label_accuracy"] == pytest.approx(2/3)
    assert counts["complete_comparable_qa"] == 1
    ambiguous = sem.semantic_counts([record], {("id", "c1"): "ambiguous"})
    assert ambiguous["ambiguous_unit_conditions_retained_in_F"] == 3 and ambiguous["exact_label_accuracy"] is None
    assert record == original
    record["tasks"]["judges"]["reversed"]["status"] = "error"
    record["evaluation"]["trials"][1].update(status="error", score=None)
    failed = sem.semantic_counts([record], {("id", "c1"): "supported"})
    assert failed["planned_definite_unit_conditions"] == 3 and failed["exact_label_accuracy"] == pytest.approx(1/3)
    assert failed["complete_comparable_qa"] == 0 and failed["invalid_trial_conditions"] == 1


@pytest.fixture
def sealed_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(sem, "ROOT", tmp_path)
    inputs, public, private = [], {}, {}
    for language in ("en", "ja"):
        run = tmp_path / "data/runs/bilingual_development" / language
        quality, mapping = public_packet(language, identical=True)
        unit = sem.make_unit_packet(quality, language)
        bundle, units = run / "quality", run / "quality/units"
        units.mkdir(parents=True)
        write_json(bundle / "packet.json", quality)
        checkpoint(bundle / "mapping.private.json", mapping)
        write_json(bundle / "labels.json", {"test_only_sealed": True})
        write_json(units / "packet.json", unit)
        write_json(units / "labels.json", completed(unit))
        inputs.append({"run": str(run), "quality_bundle": str(bundle), "quality_annotations": str(bundle / "labels.json"),
                       "unit_bundle": str(units), "unit_annotations": str(units / "labels.json")})
        public[bundle] = quality, mapping, {}
        identifier = language + "-id"
        private[run] = ({"language": language, "config": {}}, {"records": [record_for(unit, identifier)]}, {})
    accesses = []
    monkeypatch.setattr(sem.bilingual_quality, "sealed_annotations", lambda b, a: public[b])
    def validate(run, bundle, labels):
        accesses.append(run.name)
        return private[run]
    monkeypatch.setattr(sem.bilingual_quality, "validated_annotations", validate)
    monkeypatch.setattr(sem, "condition", lambda manifest: {"same": True})
    return inputs, accesses


@pytest.mark.parametrize("pending", ["unit", "quality"])
def test_both_languages_quality_and_unit_labels_seal_before_any_internal_access(sealed_inputs, monkeypatch, pending):
    inputs, accesses = sealed_inputs
    if pending == "unit":
        path = Path(inputs[1]["unit_annotations"])
        value = json.loads(path.read_text())
        value["annotations"][0]["label"] = "pending"
        write_json(path, value)
    else:
        original = sem.bilingual_quality.sealed_annotations
        def check(bundle, labels):
            if bundle.parent.name == "ja":
                raise ValueError("Seal all quality labels")
            return original(bundle, labels)
        monkeypatch.setattr(sem.bilingual_quality, "sealed_annotations", check)
    with pytest.raises(ValueError, match="Seal"):
        sem.analyze_semantics(inputs)
    assert accesses == []


def test_sealed_source_candidate_labels_produce_metrics_without_promoting_connection_to_main(sealed_inputs):
    inputs, accesses = sealed_inputs
    result = sem.analyze_semantics(inputs)
    assert accesses == ["en", "ja"]
    assert result["languages"]["en"]["exact_label_accuracy"] == pytest.approx(2/3)
    assert result["languages"]["ja"]["planned_definite_unit_conditions"] == 3
    assert not result["main_development_semantic_gate_passed"] and not result["gate11_passed"]


def test_changed_seal_during_internal_validation_is_rejected(sealed_inputs, monkeypatch):
    inputs, accesses = sealed_inputs
    original = sem.bilingual_quality.validated_annotations
    def change(run, bundle, labels):
        result = original(run, bundle, labels)
        path = Path(inputs[1]["unit_annotations"])
        value = json.loads(path.read_text())
        value["annotations"][0]["reason"] = "changed after seal"
        write_json(path, value)
        return result
    monkeypatch.setattr(sem.bilingual_quality, "validated_annotations", change)
    with pytest.raises(ValueError, match="Sealed review changed"):
        sem.analyze_semantics(inputs)
    assert accesses == ["en"]


def test_preregistered_main_semantic_gate_requires_twenty_qa_and_ten_complete_comparisons(sealed_inputs, monkeypatch):
    inputs, _ = sealed_inputs
    original = sem.bilingual_quality.validated_annotations
    originals = {}
    for spec in inputs:
        run, bundle, labels = (Path(spec[k]) for k in ("run", "quality_bundle", "quality_annotations"))
        manifest, report, assigned = original(run, bundle, labels)
        manifest, report = deepcopy(manifest), deepcopy(report)
        mapping = json.loads((bundle / "mapping.private.json").read_text())
        anonymous = next(iter(mapping["assignments"]))
        mapping.pop("result_sha256")
        mapping["assignments"][anonymous] = [{"record_id": run.name + str(i), "stage": "initial"} for i in range(20)]
        checkpoint(bundle / "mapping.private.json", mapping)
        record = report["records"][0]
        report["records"] = []
        for i in range(20):
            row = deepcopy(record)
            row["trace"]["record_id"] = run.name + str(i)
            for trial in row["evaluation"]["trials"]:
                trial["score"] = 1
                row["tasks"]["judges"][trial["trial_id"]]["parsed"]["verdicts"][0]["label"] = "supported"
            report["records"].append(row)
        report.update(selected_qa_count=20, failures=[])
        policy = json.loads((Path(__file__).resolve().parents[1] /
            "configs/phase11_main_development_execution_policy_v1.json").read_text())
        policy_path = run / "policy.json"
        write_json(policy_path, policy)
        from rag_research.retrieval.common import file_hash

        manifest["config"].update(execution_scope="main_development_v1", main_execution_policy={
            "path": str(policy_path.relative_to(sem.ROOT)), "sha256": file_hash(policy_path)})
        originals[run] = manifest, report, assigned
    # Public sealing still uses its original same anonymous case, with 20 private initial slots.
    def seal(bundle, labels):
        packet = json.loads((bundle / "packet.json").read_text())
        mapping = json.loads((bundle / "mapping.private.json").read_text())
        return packet, mapping, {}
    monkeypatch.setattr(sem.bilingual_quality, "sealed_annotations", seal)
    monkeypatch.setattr(sem.bilingual_quality, "validated_annotations", lambda run, bundle, labels: originals[run])
    assert sem.analyze_semantics(inputs)["main_development_semantic_gate_passed"]
    for _, report, _ in originals.values():
        for row in report["records"][9:]:
            row["evaluation"]["plan"]["order_group"] = ["original"]
    result = sem.analyze_semantics(inputs)
    assert result["languages"]["en"]["exact_label_accuracy"] == 1
    assert result["languages"]["en"]["complete_comparable_qa"] == 9
    assert not result["main_development_semantic_gate_passed"]
    # The sealed analysis must reject weaker rules, even if the metadata is
    # rebound to the new policy hash. It must not merely report a softer gate.
    run = Path(inputs[0]["run"])
    manifest, _, _ = originals[run]
    path = run / "policy.json"
    weakened = json.loads(path.read_text())
    weakened["semantic_adoption_after_blind_seal"]["minimum_exact_label_accuracy_per_language"] = .5
    write_json(path, weakened)
    manifest["config"]["main_execution_policy"]["sha256"] = file_hash(path)
    with pytest.raises(ValueError, match="preregistered main policy rules"):
        sem.analyze_semantics(inputs)
