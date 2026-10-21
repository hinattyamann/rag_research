"""All-language sealing precedes private analysis; missing selected QA and group IDs survive."""

import json

import pytest

from rag_research.experiments import bilingual_statistics as module
from rag_research.experiments.frozen_trace import digest


def evaluation():
    orders = ["original", "reversed", "shuffle_1", "shuffle_2", "shuffle_3"]
    repeats = ["original", "repeat_2", "repeat_3", "repeat_4", "repeat_5"]
    documents = [["a", "b", "c"], ["c", "b", "a"], ["b", "a", "c"], ["a", "c", "b"], ["b", "c", "a"]]
    definitions = {i: docs for i, docs in zip(orders, documents, strict=True)}
    definitions.update({i: documents[0] for i in repeats})
    return {"threshold": .7, "plan": {"order_group": orders, "repeat_group": repeats,
            "trials": [{"trial_id": i, "document_ids": docs} for i, docs in definitions.items()]},
            "trials": [{"trial_id": i, "status": "ok", "score": 1., "decision": "accept"} for i in definitions]}


@pytest.fixture
def cohorts(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    state = {"sealed": [], "private": [], "pending": False, "conditions_differ": False, "evaluation_path": False}
    inputs = []
    for lang in ("en", "ja"):
        run = tmp_path / "data/runs/bilingual_development" / lang
        bundle = run / "quality"
        bundle.mkdir(parents=True)
        for name in ("packet.json", "mapping.private.json", "export_manifest.json", "annotations.json"):
            (bundle / name).write_text("{}")
        for name in ("manifest.json", "report.private.json"):
            (run / name).write_text("{}")
        for identifier in ("success", "failed"):
            path = run / "baseline" / digest(identifier)[:24] / "record.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"completion_attempted": True, "input_tokens": 10, "output_tokens": 2 if identifier == "success" else None,
                "error_code": None if identifier == "success" else "interrupted_unknown_outcome", "cost_incomplete": identifier == "failed"}))
        inputs.append({"run": str(run), "bundle": str(bundle), "annotations": str(bundle / "annotations.json")})
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/phase11_statistical_plan.md").write_text("preregistered")
    (tmp_path / "prompts.yaml").write_text("tasks:\n  verify_claims:\n    system: Shared judge\n")

    def seal(bundle, annotations):
        state["sealed"].append(bundle.parent.name)
        if state["pending"] and bundle.parent.name == "ja":
            raise ValueError("Seal all external labels")

    def verified(run, bundle, annotations):
        assert set(state["sealed"]) == {"en", "ja"}
        language = run.name
        state["private"].append(language)
        manifest = {"language": language, "baseline_model": {"id": "baseline"}, "auxiliary_model": {"id": "judge"},
                    "baseline": {"retrieval": "shared"}, "qa_path": "evaluation" if state["evaluation_path"] else language + "/development",
                    "qa_sha256": "test-source", "config": {"assets": "assets", "prompts": "prompts.yaml", "decision": {"threshold": .8 if
                    state["conditions_differ"] and language == "ja" else .7}},
                    "selection": [{"record_id": "success"}, {"record_id": "failed"}]}
        report = {"selected_qa_count": 2, "records": [{"trace": {"record_id": "success"}, "evaluation": evaluation()}],
                  "failures": [{"record_id": "failed", "status": "error", "reason": "baseline_not_freezable"}]}
        return manifest, report, {("success", "initial"): "indeterminate"}

    assets = {"datasets": {lang: {"qa": {s: {"path": lang + "/" + s} for s in ("development", "calibration", "evaluation")}}
                           for lang in ("en", "ja")}}
    monkeypatch.setattr(module.bilingual_quality, "sealed_annotations", seal)
    monkeypatch.setattr(module.bilingual_quality, "validated_annotations", verified)
    monkeypatch.setattr(module, "load_assets", lambda p: assets)
    monkeypatch.setattr(module, "load_rows", lambda *args, **kwargs: ([
        {"record_id": "success", "document_group_id": "actual-group"},
        {"record_id": "failed", "document_group_id": "missing-group"}], None))
    monkeypatch.setattr(module, "reconstruct", lambda rows, labels: {"labels": list(labels.values()), "cost_preserved": True})
    return inputs, state


def test_all_selected_ids_failures_groups_unknown_quality_and_hashes_survive(cohorts):
    inputs, state = cohorts
    result = module.analyze_runs(inputs)
    assert state["private"] == ["en", "ja"] and state["sealed"] == ["en", "ja"]
    for lang in ("en", "ja"):
        counts = result["languages"][lang]
        assert counts["selected_qa_count"] == 2 and counts["comparable_qa_count"] == counts["missing_qa_count"] == 1
        assert counts["selected_document_groups"] == 2 and counts["ci95"] is None
    assert result["ja_minus_en"] == {"mean": 0., "ci95": None}
    assert len(result["source_runs"]) == 2 and all(len(r["files_sha256"]) == 8 for r in result["source_runs"])
    assert all(c["quality_and_costs"]["labels"] == ["indeterminate"] for c in result["all_selected_quality_costs"])
    assert all(c["all_selected_baseline_cost"]["completion_attempts"] is None and
               c["all_selected_baseline_cost"]["recorded_completion_attempts"] == 2 and
               c["all_selected_baseline_cost"]["unknown_outcome_steps"] == 1 for c in result["all_selected_quality_costs"])
    assert "baseline_unavailable" in json.dumps(result) and not result["gate11_passed"]


def test_one_pending_language_prevents_every_private_read(cohorts):
    inputs, state = cohorts
    state["pending"] = True
    with pytest.raises(ValueError, match="Seal all external labels"):
        module.analyze_runs(inputs)
    assert not state["private"]


def test_conditions_cannot_be_mixed_between_languages(cohorts):
    inputs, state = cohorts
    state["conditions_differ"] = True
    with pytest.raises(ValueError, match="conditions differ"):
        module.analyze_runs(inputs)


def test_evaluation_and_duplicate_runs_are_rejected(cohorts):
    inputs, state = cohorts
    with pytest.raises(ValueError, match="Duplicate"):
        module.analyze_runs([inputs[0], inputs[0]])
    state["evaluation_path"] = True
    with pytest.raises(ValueError, match="Development runs"):
        module.analyze_runs(inputs)
