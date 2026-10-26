"""Actual manifest producer and binary consumer; synthetic reviews, zero Native.

Metadata/model/Cal-protocol accesses are doubles. The real producer builds the
manifest, while real quality/unit sealing, v2 rules and binary analysis run.
These software fixtures do not substitute for real Main/Cal evidence.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from rag_research.experiments import bilingual_runner as runner
from rag_research.experiments import bilingual_semantics as semantics
from rag_research.experiments import calibration_protocol
from rag_research.experiments.quality import blank_annotations, make_packet
from rag_research.experiments.storage import checkpoint, write_json
from rag_research.retrieval.common import file_hash

REPO = Path(__file__).resolve().parents[1]


class CapturedManifest(Exception):
    """Stop before any budget reservation, retriever, model or Native call."""


def forbidden_native(*args, **kwargs):
    raise AssertionError("This integration test must perform zero Native calls")


def produce_manifest(root, monkeypatch, scope, language, *, missing_group=False):
    root.mkdir(parents=True)
    calibration = scope == "heldout_calibration_v1"
    rows = [{"record_id": f"synthetic-{language}-{i}", "question": f"Synthetic question {i}?",
             "document_group_id": f"source-group-{language}-{i}", "is_answerable": True,
             "reference_answers": ["GOLD-SECRET"], "gold_passage_ids": ["GOLD-PASSAGE"]}
            for i in range(20)]
    if missing_group:
        rows[7].pop("document_group_id")
    config = {"purpose": "phase11-bilingual-calibration-candidate" if calibration else
              "phase11-bilingual-development-candidate", "execution_scope": scope,
              "language": language, "semantic_adoption_version": "support-binary-v2",
              "assets": "assets.json", "baseline_config": "baseline.yaml",
              "baseline_prompts": "initial.yaml", "prompts": "prompts.yaml",
              "calibration_limits" if calibration else "main_limits": {"maximum_completion_attempts": 1660}}
    if calibration:
        config["calibration_protocol"] = {"path": "protocol.json"}
    elif scope == "main_development_v1":
        config.update(development_selection={"path": "selection.json"},
                      adopted_known_regression={"path": "known.json"},
                      main_execution_policy={"path": "policy.json"})
    for name in ("config.yaml", "assets.json", "baseline.yaml", "initial.yaml", "prompts.yaml",
                 "protocol.json", "selection.json", "known.json", "policy.json",
                 "scripts/run_bilingual_development.py", "scripts/run_bilingual_calibration.py"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic metadata only\n")
    qa_path = root / "synthetic-qa.jsonl"
    qa_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    output = root / "data/runs" / ("bilingual_calibration" if calibration else "bilingual_development") / "test"
    captured = {}

    def immutable(path, manifest):
        assert path == output / "manifest.json"
        captured.update(deepcopy(manifest))
        raise CapturedManifest

    contract = (config, {}, rows, qa_path, {"retrieval": {"top_k": 5}}, None, None, {})
    with monkeypatch.context() as local:
        local.chdir(root)
        local.setattr(runner, "ROOT", root)
        local.setattr(runner, "load_config", lambda *a, **k: contract)
        local.setattr(runner, "auxiliary_identity", lambda *a: {"synthetic": True})
        local.setattr(runner, "execution_identity", lambda *a: {"synthetic_execution": True})
        local.setattr(runner, "validate_chain_identity", lambda *a, **k: None)
        local.setattr(runner, "immutable", immutable)
        for name in ("LocalServer", "load_retriever", "reserve_calls"):
            local.setattr(runner, name, forbidden_native)
        with pytest.raises(CapturedManifest):
            runner._run(root / "config.yaml", output, stage="baseline", calibration=calibration)
    return captured, rows


def sealed_fixture(root, manifest):
    language = manifest["language"]
    records, references, truth = [], {}, {}
    for i, selected in enumerate(manifest["selection"]):
        supported = i < 10
        answer = "The synthetic tower is 42 metres tall." if language == "en" else "架空の塔の高さは42メートルです。"
        text = ("The synthetic tower is 42 metres tall. 架空の塔の高さは42メートルです。" if supported else
                "The synthetic tower is made of stone. 架空の塔は石造りです。")
        documents = [{"passage_id": "synthetic-p1", "title": "Synthetic tower", "text": text}]
        identifier = selected["record_id"]
        records.append({"trace": {"record_id": identifier, "question": selected["question"],
                        "answer": answer, "documents": documents}, "rewrite": {"status": "ok", "answer": answer}})
        references[identifier] = {"reference_answers": [], "selected_sentences_by_reference": [], "gold_passage_ids": []}
        truth[identifier] = "supported" if supported else "not_supported"
    quality, mapping = make_packet(records, references, {}, "Synthetic software rubric", "v1", 42, "synthetic")
    units = semantics.make_unit_packet(quality, language)
    unit_labels = semantics.blank_unit_annotations(units)
    expected = {case["annotation_id"]: truth[mapping["assignments"][case["annotation_id"]][0]["record_id"]]
                for case in units["cases"]}
    for label in unit_labels["annotations"]:
        label.update(label=expected[label["annotation_id"]], reason="Synthetic actual-context comparison",
                     annotator="Synthetic software fixture", elapsed_seconds=1.,
                     confirmed_at_utc="2026-10-26T00:00:00+00:00",
                     evidence=[{"passage_id": "synthetic-p1", "quote": "42"}]
                     if expected[label["annotation_id"]] == "supported" else [])
    quality_labels = blank_annotations(quality)
    for label in quality_labels["annotations"]:
        reliable = expected[label["annotation_id"]] == "supported"
        label.update(label="reliable" if reliable else "unreliable",
                     criteria={"essential_answer": "pass", "no_major_error": "pass",
                               "context_support": "pass" if reliable else "fail"},
                     essential_points="Synthetic tower height", reason="Synthetic context check",
                     annotator="Synthetic software fixture", elapsed_seconds=1.,
                     confirmed_at_utc="2026-10-26T00:00:00+00:00",
                     evidence=[{"passage_id": "synthetic-p1", "quote": "42"}] if reliable else [])
    run = root / "data/runs" / ("bilingual_calibration" if manifest["config"]["execution_scope"] ==
                                 "heldout_calibration_v1" else "bilingual_development") / language
    bundle, unit_dir = run / "quality", run / "quality/units"
    unit_dir.mkdir(parents=True)
    for path, value in ((bundle / "packet.json", quality), (bundle / "annotations.json", quality_labels),
                        (unit_dir / "packet.json", units), (unit_dir / "annotations.json", unit_labels)):
        write_json(path, value)
    checkpoint(bundle / "mapping.private.json", mapping)
    unit_by_id = {mapping["assignments"][c["annotation_id"]][0]["record_id"]: c["unit_audit"]["claims"]
                  for c in units["cases"]}
    trials = ["original", "reversed", "repeat_2"]
    private = []
    for selected in manifest["selection"]:
        identifier = selected["record_id"]
        claims = unit_by_id[identifier]
        private.append({"trace": {"record_id": identifier}, "evaluation": {"claims": claims,
                        "trials": [{"trial_id": t, "status": "ok", "score": float(truth[identifier] == "supported")}
                                   for t in trials], "plan": {"trials": [{"trial_id": t} for t in trials],
                        "order_group": trials[:2], "repeat_group": [trials[0], trials[2]]}}, "tasks": {"judges": {
                        t: {"status": "ok", "parsed": {"verdicts": [{"claim_id": c["claim_id"], "label": truth[identifier]}
                        for c in claims]}} for t in trials}}})
    spec = {"run": run.relative_to(root).as_posix(), "quality_bundle": bundle.relative_to(root).as_posix(),
            "quality_annotations": (bundle / "annotations.json").relative_to(root).as_posix(),
            "unit_bundle": unit_dir.relative_to(root).as_posix(),
            "unit_annotations": (unit_dir / "annotations.json").relative_to(root).as_posix()}
    return spec, run, (manifest, {"records": private, "selected_qa_count": 20, "failures": []}, {})


@pytest.mark.parametrize("scope", ["main_development_v1", "heldout_calibration_v1"])
@pytest.mark.parametrize("first_language", ["en", "ja"])
def test_actual_producer_to_binary_consumer_preserves_twenty_source_groups(tmp_path, monkeypatch, scope, first_language):
    manifests = {}
    for language in ("en", "ja"):
        manifest, rows = produce_manifest(tmp_path / "producer" / language, monkeypatch, scope, language)
        assert manifest["selection"] == [{k: r[k] for k in ("record_id", "question", "document_group_id")} for r in rows]
        assert [r["record_id"] for r in manifest["selection"]] == [r["record_id"] for r in rows]
        assert len({r["document_group_id"] for r in manifest["selection"]}) == 20
        assert "GOLD-SECRET" not in json.dumps(manifest["selection"])
        assert "GOLD-PASSAGE" not in json.dumps(manifest["selection"])
        manifests[language] = manifest
    analysis = tmp_path / "analysis"
    policy_path = analysis / "configs/rules.json"
    policy_path.parent.mkdir(parents=True)
    policy_path.write_bytes((REPO / "configs/phase11_main_development_execution_policy_v2.json").read_bytes())
    binding = {"path": "configs/rules.json", "sha256": file_hash(policy_path)}
    inputs, private = [], {}
    order = [first_language, "ja" if first_language == "en" else "en"]
    for language in order:
        if scope == "main_development_v1":
            manifests[language]["config"]["main_execution_policy"] = binding
        spec, run, value = sealed_fixture(analysis, manifests[language])
        inputs.append(spec)
        private[run] = value
    monkeypatch.setattr(semantics, "ROOT", analysis)
    # Real public quality and unit seals precede this private-results double.
    monkeypatch.setattr(semantics.bilingual_quality, "validated_annotations", lambda run, *a: private[run])
    monkeypatch.setattr(semantics, "condition", lambda manifest: {"synthetic_same_conditions": True})
    monkeypatch.setattr(calibration_protocol, "review_contract", lambda *a, **k: {"rules": binding})
    result = semantics.analyze_semantics(inputs, analysis_split="calibration" if scope == "heldout_calibration_v1" else "development")
    assert result["semantic_adoption_version"] == "support-binary-v2"
    for counts in result["languages"].values():
        binary = counts["binary_adoption"]
        assert counts["complete_comparable_qa"] == 20
        assert binary["supported_groups"] == binary["negative_groups"] == 10
        assert binary["unique_supported_units"] == binary["unique_negative_units"] == 10
        assert binary["supported_denominator"] == binary["negative_denominator"] == 30
        assert binary["supported_recall"] == binary["negative_specificity"] == 1.
    gate = "calibration_semantic_gate_passed" if scope == "heldout_calibration_v1" else "main_development_semantic_gate_passed"
    assert result[gate] and not result["gate11_passed"] and not result["phase12_allowed"]


@pytest.mark.parametrize("scope", ["main_development_v1", "heldout_calibration_v1"])
@pytest.mark.parametrize("language", ["en", "ja"])
def test_missing_source_group_is_rejected_before_native_and_manifest(tmp_path, monkeypatch, scope, language):
    with pytest.raises(KeyError, match="document_group_id"):
        produce_manifest(tmp_path / "producer", monkeypatch, scope, language, missing_group=True)
    assert not list(tmp_path.rglob("manifest.json"))


@pytest.mark.parametrize("language", ["en", "ja"])
def test_connection_keeps_original_id_question_only_and_does_not_require_group(tmp_path, monkeypatch, language):
    manifest, rows = produce_manifest(tmp_path / "producer", monkeypatch, "connection_smoke_only", language, missing_group=True)
    assert manifest["selection"] == [{k: r[k] for k in ("record_id", "question")} for r in rows]
    assert all("document_group_id" not in r for r in manifest["selection"])
