"""Pilot selection is outcome independent; baseline attempts cannot be silently resampled."""

from copy import deepcopy
from pathlib import Path

import pytest

from rag_research.experiments.storage import read_json, verify_checkpoint, write_json
from rag_research.generation.config import GenerationConfig
from rag_research.generation.context import PromptSpec
from rag_research.pilot.baseline import JournalClient, baseline_once
from rag_research.pilot.selection import select_rows


def qa(i, title, answerable=True):
    return {"record_id": str(i), "source_title": title, "question": f"Q{i}?",
            "research_split": "development", "is_answerable": answerable}


def test_selection_excludes_inspected_title_and_is_input_order_invariant():
    rows = [qa(1, "Seen"), qa(2, "SEEN"), qa(3, "A"), qa(4, "A"), qa(5, "B"), qa(6, "C", False)]
    chosen = select_rows(rows, {"1"}, 2, 42)
    assert chosen == select_rows(list(reversed(rows)), {"1"}, 2, 42)
    assert {r["source_title"] for r in chosen} == {"A", "B"}
    changed = deepcopy(rows)
    for row in changed:
        row.update(reference_answers=["altered"], gold_passage_ids=["gold"], quality_y=0)
    assert [r["record_id"] for r in chosen] == [r["record_id"] for r in select_rows(changed, {"1"}, 2, 42)]


def test_selection_unicode_and_wrong_split():
    rows = [qa(1, "é"), qa(2, "e\u0301"), qa(3, "Other")]
    assert [r["record_id"] for r in select_rows(rows, {"1"}, 1, 42)] == ["3"]
    with pytest.raises(ValueError, match="Not enough"):
        select_rows(rows, {"1"}, 2, 42)
    rows[0]["research_split"] = "evaluation"
    with pytest.raises(ValueError, match="Development only"):
        select_rows(rows, set(), 1, 42)


def test_journal_written_before_completion_and_raw_response_preserved(tmp_path):
    path = tmp_path / "record.json"
    journal = {"status": "started", "completion_attempted": False}

    class Client:
        def complete(self, tokens, config):
            assert read_json(path)["completion_attempted"] is True
            return {"content": "Answer", "tokens": [3], "stop_type": "eos"}

    proxy = JournalClient(Client(), journal, path)
    proxy.complete([1, 2], GenerationConfig())
    assert read_json(path)["runtime_response"]["content"] == "Answer"


def test_baseline_resume_never_calls_model_again(tmp_path, monkeypatch):
    from rag_research.pilot import baseline

    class Pipeline:
        def __init__(self, retriever, generator, **kwargs):
            pass

        def run(self, question):
            return {"status": "ok", "answer": "A", "answer_generation_calls": 1}

    monkeypatch.setattr(baseline, "BaselinePipeline", Pipeline)
    spec = {"record_id": "q1", "question": "Q1?"}
    prompt = PromptSpec(**__import__("yaml").safe_load(Path("configs/prompts.yaml").read_text("utf-8")))
    result = baseline_once(None, None, GenerationConfig(), prompt, 10, spec, tmp_path, {"run": "x"})
    verify_checkpoint(result)
    assert baseline_once(None, None, GenerationConfig(), prompt, 10, spec, tmp_path, {"run": "x"}) == result
    saved = read_json(tmp_path / "record.json")
    saved.pop("result_sha256")
    saved.update(status="started", completion_attempted=True)
    write_json(tmp_path / "record.json", saved)
    sealed = baseline_once(None, None, GenerationConfig(), prompt, 10, spec, tmp_path, {"run": "x"})
    assert sealed["status"] == "error" and sealed["cost_incomplete"]
    with pytest.raises(ValueError, match="changed"):
        baseline_once(None, None, GenerationConfig(), prompt, 10, spec, tmp_path, {"run": "other"})


@pytest.mark.parametrize("split", ["development", "calibration"])
def test_internal_end_to_end_reuses_all_raw_calls_and_publishes_blind_materials(tmp_path, monkeypatch, split):
    import json

    from rag_research.evaluation.order import trial_plan
    from rag_research.experiments.frozen_trace import digest, freeze_record
    from rag_research.experiments.protocol import load_protocol
    from rag_research.pilot import internal

    repository = Path.cwd()
    config = {"internal_protocol": str(repository / "configs/order_phase8_v5.yaml"),
              "quality_rubric_version": "order-quality-ai-pilot-v1", "annotation_seed": 44,
              "health_gate": {"after_questions": 5, "minimum_complete_scorable_questions": 3,
                              "maximum_judge_error_fraction": 0.25, "stop_on_input_overflow": True}}
    protocol, prompts, prompt_path = load_protocol(repository / "configs/order_phase8_v5.yaml")
    if split == "calibration":
        config["purpose"] = "phase11-calibration"
        # Reuse a simple synthetic decoder here; real Phase 11 protocol validation
        # and final-only Qwen3 grammar are tested separately.
        monkeypatch.setattr(internal, "load_protocol", lambda *a, **kw: (protocol, prompts, prompt_path))
    trace = freeze_record({"record_id": "q1", "question": "Q?", "answer": "A.", "status": "ok",
                           "used_context": [{"passage_id": str(i), "title": "T", "text": "A."}
                                            for i in range(10)]})
    selection = {"records": [{"record_id": "q1"}, {"record_id": "failed"}]}
    if split == "calibration":
        selection["split"] = split
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    write_json(baseline / "run_manifest.json", {"status": "completed"})
    rows = [{"record_id": "q1", "status": "ok", "input_tokens": 5, "output_tokens": 2,
             "generation_seconds": 1, "context_seconds": 0.1, "answer_generation_calls": 1},
            {"record_id": "failed", "status": "error"}]
    (baseline / "answers.jsonl").write_text("\n".join(map(json.dumps, rows)), encoding="utf-8")
    monkeypatch.setattr(internal, "ROOT", tmp_path)
    monkeypatch.setattr(internal, "load_traces", lambda *a, **kw: ([trace], None))
    manifest = {"purpose": "phase10-test", "traces": [{"record_id": "q1", "directory": digest("q1")[:24],
                 "plan": trial_plan(trace, protocol)}]}
    if split == "calibration":
        manifest["purpose"] = "phase11-calibration-not-final-evaluation"
    monkeypatch.setattr(internal, "pilot_identity", lambda *a: manifest)
    qa_row = {"reference_answers": ["A."], "gold_passage_ids": ["0"], "selected_sentences_by_reference": [["A."]]}
    monkeypatch.setattr(internal, "load_offline", lambda *a: ({"q1": qa_row}, {"0": trace["documents"][0]}))

    class Client:
        completion_attempts = 0

        def render(self, messages):
            self.messages = messages
            return json.dumps(messages)

        def tokenize(self, prompt, *, special):
            return [1] * 10

        def complete(self, tokens, config, **kwargs):
            self.completion_attempts += 1
            payload = json.loads(self.messages[1]["content"].removeprefix("Input JSON:\n"))
            if set(payload) == {"answer"}:
                content = json.dumps({"claims": [{"claim_id": "c1", "text": "A."}]})
            elif "claims" in payload:
                content = json.dumps({"verdicts": [{"claim_id": "c1", "label": "supported", "reason": "A",
                                                    "evidence": [{"passage_id": "0", "quote": "A."}]}]})
            else:
                content = "A revised answer. [0]"
            return {"content": content, "stop_type": "eos", "tokens": [1], "truncated": False}

    client = Client()

    class Server:
        def __init__(self, *args):
            self.client = client

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def report(self):
            return {}

    monkeypatch.setattr(internal, "LocalServer", Server)
    internal.run_internal(None, config, selection, tmp_path, split=split)
    assert client.completion_attempts == 11
    folder = tmp_path / "internal" / digest("q1")[:24]
    before = {p.name: p.read_bytes() for p in folder.glob("*.json")}
    packet = read_json(tmp_path / "quality/final/packet.json")
    assert len(packet["cases"]) == 2
    assert "q1" not in json.dumps(packet)
    assert all("score" not in c and "stage" not in c for c in packet["cases"])
    internal.run_internal(None, config, selection, tmp_path, split=split)
    assert client.completion_attempts == 11
    assert before == {p.name: p.read_bytes() for p in folder.glob("*.json")}
    assert read_json(tmp_path / "progress.json")["baseline_failed"] == 1
    from rag_research.pilot.assessment import open_candidate, save_candidate
    from rag_research.pilot.report import pilot_report

    bundle = tmp_path / "quality/ready-001"
    assessment = tmp_path / "quality/assessments/packet-001"
    for _ in range(2):
        opened = open_candidate(bundle, assessment)
        case = opened["case"]
        decision_path = tmp_path / "synthetic-decision.json"
        write_json(decision_path, {"annotation_id": case["annotation_id"], "label": "unreliable",
                   "criteria": {"essential_answer": "fail", "no_major_error": "uncertain", "context_support": "uncertain"},
                   "essential_points": "Synthetic test only", "reason": "AI代行 synthetic fixture, not an empirical label",
                   "evidence": [{"passage_id": "0", "quote": "A."}]})
        save_candidate(bundle, assessment, decision_path)
    with pytest.raises(ValueError, match="assessed"):
        open_candidate(bundle, assessment)
    if split == "calibration":
        from rag_research.calibration.report import calibration_report

        report = calibration_report(tmp_path)
        result = {**report, **report["analysis"]}
        assert report["gate11_passed"] is False and report["phase12_allowed"] is False
    else:
        result = pilot_report(tmp_path)
    assert result["comparable_questions"] == 1
    assert result["quality_transitions"]["0->0"] == 1
    assert read_json(tmp_path / "quality/assessment_manifest.json")["human_reviewed"] is False


def test_health_stop_uses_validity_not_scores_or_flips():
    from rag_research.pilot.internal import health_gate

    rules = {"after_questions": 5, "minimum_complete_scorable_questions": 3,
             "maximum_judge_error_fraction": 0.25, "stop_on_input_overflow": True}
    group = {"valid_trials": 5, "planned_trials": 5, "valid_pairs": 10}
    row = {"tasks": {"extraction": {"status": "ok"}, "judges": {"a": {"status": "ok"}}},
           "rewrite": {"status": "ok"},
           "evaluation": {"order_group": group, "repeat_group": group}}
    assert health_gate([row] * 4, rules)["status"] == "pending"
    assert health_gate([row] * 5, rules)["status"] == "passed"
    failed = deepcopy(row)
    failed["tasks"]["judges"]["a"]["status"] = "error"
    assert health_gate([failed] * 2 + [row] * 3, rules)["status"] == "stopped"
    overflow = deepcopy(row)
    overflow["rewrite"]["error_code"] = "input_overflow"
    assert health_gate([overflow], rules)["status"] == "stopped"


def test_cli_baseline_reuses_bound_provenance_without_rewriting(tmp_path, monkeypatch):
    import importlib.util
    from pathlib import Path

    from rag_research.experiments.frozen_trace import digest
    from rag_research.retrieval.common import file_hash

    script = Path(__file__).resolve().parents[1] / "scripts/run_pilot.py"
    spec = importlib.util.spec_from_file_location("pilot_cli_under_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    monkeypatch.setattr(module, "run_baseline", lambda *args: calls.append(args) or {"status": "completed"})
    selection = {"fixed": ["q1"]}
    assert module.baseline_stage({}, selection, tmp_path)["status"] == "completed"
    assert len(calls) == 1
    (tmp_path / "baseline").mkdir()
    (tmp_path / "internal").mkdir()
    answers = tmp_path / "baseline/answers.jsonl"
    provenance = tmp_path / "baseline/run_manifest.json"
    answers.write_text('{"record_id":"q1","answer":"A"}\n', encoding="utf-8")
    write_json(provenance, {"status": "completed", "completed_questions": 1})
    write_json(tmp_path / "internal/manifest.json", {
        "selection_sha256": digest(selection), "baseline_answers_sha256": file_hash(answers),
        "baseline_provenance_sha256": file_hash(provenance)})
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    reused = module.baseline_stage({}, selection, tmp_path)
    assert reused["status"] == "frozen_baseline_reused"
    assert reused["additional_completion_attempts"] == 0 and reused["provenance_changed"] is False
    assert len(calls) == 1
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    answers.write_text("corrupted", encoding="utf-8")
    with pytest.raises(ValueError, match="artifacts changed"):
        module.baseline_stage({}, selection, tmp_path)
    assert answers.read_text("utf-8") == "corrupted" and len(calls) == 1
