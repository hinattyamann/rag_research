import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from rag_research.calibration.preparation import (
    QA_PATH,
    baseline_stage,
    immutable_checkpoint,
    load_config,
    prepare,
    progress_report,
    select_calibration,
)
from rag_research.calibration.report import calibration_report
from rag_research.experiments.frozen_trace import digest
from rag_research.experiments.protocol import load_protocol
from rag_research.experiments.storage import checkpoint, read_json, write_json
from rag_research.pilot import baseline
from rag_research.retrieval.common import file_hash

ROOT = Path(__file__).resolve().parents[1]


def qa(identifier, title, *, split="calibration", answerable=True):
    return {"record_id": identifier, "source_title": title, "question": f"Question {identifier}?",
            "research_split": split, "is_answerable": answerable}


def test_calibration_sample_is_outcome_independent_and_groups_unicode_titles():
    rows = [qa("1", "Caf\u00e9"), qa("2", "CAFE\u0301"), qa("3", "Other"),
            qa("4", "Unanswerable", answerable=False)]
    chosen = select_calibration(rows, 2, 42)
    assert len(chosen) == 2 and "3" in {r["record_id"] for r in chosen}
    altered = [dict(r, arbitrary_observed_score=1, label="bad") for r in reversed(rows)]
    assert [r["record_id"] for r in chosen] == [r["record_id"] for r in select_calibration(altered, 2, 42)]
    with pytest.raises(ValueError, match="Not enough"):
        select_calibration(rows, 3, 42)
    for split in ("evaluation", "development"):
        with pytest.raises(ValueError, match="Calibration only"):
            select_calibration([qa("bad", "Wrong", split=split)], 1, 42)
    with pytest.raises(ValueError, match="Duplicate"):
        select_calibration([rows[0], rows[0]], 1, 42)


def test_calibration_protocol_requires_explicit_opt_in_and_cannot_read_evaluation(tmp_path):
    path = ROOT / "configs/order_phase11_calibration.yaml"
    config, _, _ = load_protocol(path, split="calibration")
    assert config["data"]["qa_path"] == QA_PATH
    with pytest.raises(ValueError, match="purpose"):
        load_protocol(path)
    with pytest.raises(ValueError, match="Evaluation"):
        load_protocol(tmp_path / "does-not-exist.yaml", split="evaluation")
    wrong = deepcopy(config)
    wrong["data"]["qa_path"] = QA_PATH.replace("calibration", "evaluation")
    changed = tmp_path / "changed.yaml"
    changed.write_text(yaml.safe_dump(wrong), encoding="utf-8")
    with pytest.raises(ValueError, match="QA path"):
        load_protocol(changed, split="calibration")


@pytest.mark.parametrize("field,value", [("qa_path", "evaluation.jsonl"),
                                         ("phase12_allowed", True),
                                         ("replace_failed_questions", True),
                                         ("human_reviewed", True)])
def test_config_rejects_final_evaluation_and_policy_drift(tmp_path, field, value):
    config = yaml.safe_load((ROOT / "configs/phase11_calibration.yaml").read_text("utf-8"))
    config[field] = value
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)


def test_prepare_binds_calibration_only_and_rejects_changed_conditions(tmp_path, monkeypatch):
    from rag_research.calibration import preparation

    # Minimal local data fixture; real configs, prompts and code remain hash-bound.
    real_local_path = preparation.local_path
    qa_path = tmp_path / "calibration.jsonl"
    rows = [qa("1", "One"), qa("2", "Two")]
    qa_path.write_text("\n".join(map(json.dumps, rows)), encoding="utf-8")
    monkeypatch.setattr(preparation, "local_path", lambda name:
                        qa_path if name == QA_PATH else real_local_path(name))
    original_read = preparation.read_json
    monkeypatch.setattr(preparation, "read_json", lambda path:
                        {"group_assignments": {"one": "calibration", "two": "calibration"}}
                        if path.name == "clapnq_split_manifest.json" else original_read(path))
    config_path = ROOT / "configs/phase11_calibration.yaml"
    config = load_config(config_path)
    config["count"] = 2
    selection_path = tmp_path / "selection.json"
    output = tmp_path / "run"
    selection, candidate = prepare(config_path, config, selection_path, output)
    before = selection_path.read_bytes(), (output / "candidate_manifest.json").read_bytes()
    assert candidate["gate11_passed"] is False and candidate["phase12_allowed"] is False
    assert selection["split"] == "calibration" and selection["replace_failed_questions"] is False
    assert not any(name.endswith("/evaluation.jsonl") for name in candidate["source_sha256"])
    assert prepare(config_path, config, selection_path, output) == (selection, candidate)
    assert before == (selection_path.read_bytes(), (output / "candidate_manifest.json").read_bytes())
    config["annotation_seed"] += 1
    with pytest.raises(ValueError, match="conditions changed"):
        prepare(config_path, config, selection_path, output)
    assert before == (selection_path.read_bytes(), (output / "candidate_manifest.json").read_bytes())


def test_baseline_limit_preserves_pending_questions_and_resume_never_retries_failures(tmp_path, monkeypatch):
    real_load = baseline.load_config
    monkeypatch.setattr(baseline, "load_config", lambda *a: real_load(ROOT / "configs/phase6.yaml"))
    # Real QA hash is read, while model execution and retrieval are synthetic.
    config = load_config(ROOT / "configs/phase11_calibration.yaml")
    qa_path = tmp_path / "calibration.jsonl"
    qa_path.write_text("synthetic QA hash fixture", encoding="utf-8")
    config["qa_path"] = str(qa_path)
    selection = {"split": "calibration", "records": [qa("1", "One"), qa("2", "Two")]}
    calls = []

    class Server:
        def __init__(self, *a):
            self.client = type("Client", (), {"completion_attempts": 1})()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def report(self):
            return {}

    def once(client, retriever, generation, prompt, top_k, spec, folder, binding):
        path = folder / "record.json"
        if path.exists():
            return read_json(path)
        calls.append(spec["record_id"])
        return checkpoint(path, {"record_id": spec["record_id"], "status": "error" if
                          spec["record_id"] == "1" else "ok", "answer_generation_calls": 1})

    monkeypatch.setattr(baseline, "LocalServer", Server)
    monkeypatch.setattr(baseline, "load_retriever", lambda *a, **kw: None)
    monkeypatch.setattr(baseline, "baseline_once", once)
    output = tmp_path / "baseline"
    first = baseline.run_baseline(config, selection, output, split="calibration", max_new_questions=1)
    assert first["status"] == "in_progress" and first["completed_questions"] == 1
    assert len((output / "answers.jsonl").read_text("utf-8").splitlines()) == 1
    second = baseline.run_baseline(config, selection, output, split="calibration", max_new_questions=1)
    assert second["status"] == "completed" and second["successful_questions"] == 1
    assert calls == ["1", "2"]  # failed question 1 is neither retried nor replaced
    assert second["split"] == "calibration" and "development_sha256" not in second


def test_baseline_cannot_rewrite_provenance_after_internal_binding(tmp_path, monkeypatch):
    monkeypatch.setattr(baseline, "run_baseline", lambda *a, **kw: pytest.fail("Unexpected model call"))
    folder = tmp_path / "baseline"
    folder.mkdir()
    (tmp_path / "internal").mkdir()
    selection = {"split": "calibration", "records": []}
    write_json(folder / "run_manifest.json", {"status": "completed"})
    (folder / "answers.jsonl").write_text("fixed", encoding="utf-8")
    write_json(tmp_path / "internal/manifest.json", {"selection_sha256": digest(selection),
               "baseline_answers_sha256": file_hash(folder / "answers.jsonl"),
               "baseline_provenance_sha256": file_hash(folder / "run_manifest.json")})
    before = (folder / "run_manifest.json").read_bytes()
    assert baseline_stage({}, selection, tmp_path)["additional_completion_attempts"] == 0
    assert (folder / "run_manifest.json").read_bytes() == before
    (folder / "answers.jsonl").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        baseline_stage({}, selection, tmp_path)


def test_status_is_public_and_does_not_claim_freeze_or_read_private_scores(tmp_path):
    (tmp_path / "internal").mkdir()
    (tmp_path / "internal/report.private.json").write_text("not-readable-json", encoding="utf-8")
    candidate = {"result_sha256": "x", "open_items": {"semantic_validity": "pending"}}
    result = progress_report(tmp_path, candidate)
    assert result["gate11_passed"] is False and result["baseline_status"] == "not_started"
    assert "score" not in result and "decision" not in result
    with pytest.raises(FileNotFoundError):
        calibration_report(tmp_path)  # no quality packet: no private results are disclosed


def test_immutable_manifest_detects_tampering(tmp_path):
    path = tmp_path / "candidate.json"
    immutable_checkpoint(path, {"status": "candidate"})
    value = read_json(path)
    value["status"] = "frozen"
    write_json(path, value)
    with pytest.raises(ValueError, match="hash mismatch"):
        immutable_checkpoint(path, {"status": "candidate"})
