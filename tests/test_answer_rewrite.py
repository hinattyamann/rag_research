"""Phase 9 scientific boundaries and manual-label integrity, using synthetic labels only."""

import json
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from rag_research.experiments import quality
from rag_research.experiments.decisions import decide
from rag_research.experiments.frozen_trace import digest, freeze_record
from rag_research.experiments.protocol import load_protocol, task_config
from rag_research.experiments.quality import (
    blank_annotations,
    cost,
    make_packet,
    reconstruct,
    validate_annotations,
    verify_packet,
)
from rag_research.experiments.quality_form import render_form
from rag_research.experiments.storage import checkpoint, read_json, verify_checkpoint, write_json
from rag_research.generation.local import GenerationError
from rag_research.recovery.answer_rewrite import rewrite_once
from rag_research.retrieval.common import file_hash

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def protocol():
    return load_protocol(ROOT / "configs/order_phase8_v5.yaml")[:2]


@pytest.fixture
def trace():
    return freeze_record({"record_id": "example-only", "question": "When is it closed?",
                          "answer": "It closes on Sundays. [b]", "status": "ok",
                          "used_context": [{"passage_id": "b", "title": "Hours",
                                            "text": "Closed on Sundays."},
                                           {"passage_id": "a", "title": "Location",
                                            "text": "Located downtown."}]})


class Client:
    def __init__(self, response=None, count=10, fail=False):
        self.calls = 0
        self.count = count
        self.fail = fail
        self.response = response if response is not None else {
            "content": "It is closed on Sundays. [b]", "stop_type": "eos", "tokens": [1, 2]}

    def render(self, messages):
        self.messages = deepcopy(messages)
        return json.dumps(messages)

    def tokenize(self, rendered, *, special):
        assert special
        return [1] * self.count

    def complete(self, tokens, config):
        self.calls += 1
        if self.fail:
            raise GenerationError("synthetic transport failure")
        return self.response


def test_rewrite_uses_original_order_without_gold_or_judge_and_resumes(protocol, trace, tmp_path):
    config, prompts = protocol
    trace.update(reference_answers=["MUST_NOT_LEAK"], judge_feedback="MUST_NOT_LEAK")
    client = Client()
    path = tmp_path / "rewrite.json"
    result = rewrite_once(client, task_config(config, "rewrite_answer"), prompts, trace, path, {"run": "x"})
    payload = json.loads(client.messages[1]["content"].removeprefix("Input JSON:\n"))
    assert set(payload) == {"question", "answer", "documents"}
    assert payload["documents"] == trace["documents"]
    assert "MUST_NOT_LEAK" not in json.dumps(client.messages)
    assert result["answer"] == client.response["content"]
    verify_checkpoint(result)
    assert rewrite_once(None, task_config(config, "rewrite_answer"), prompts, trace, path,
                        {"run": "x"}) == result
    assert client.calls == 1
    trace["answer"] = "different"
    with pytest.raises(ValueError, match="input hash"):
        rewrite_once(client, task_config(config, "rewrite_answer"), prompts, trace, path, {"run": "x"})


@pytest.mark.parametrize("response", [
    {"content": "", "stop_type": "eos"}, {"content": "partial", "stop_type": "limit"},
    {"content": "bad", "stop_type": "eos", "truncated": True},
])
def test_invalid_rewrite_is_not_retried(protocol, trace, tmp_path, response):
    config, prompts = protocol
    client = Client(response=response)
    path = tmp_path / "rewrite.json"
    result = rewrite_once(client, task_config(config, "rewrite_answer"), prompts, trace, path, {})
    assert result["status"] == "error" and result["answer"] is None
    assert rewrite_once(client, task_config(config, "rewrite_answer"), prompts, trace, path, {}) == result
    assert client.calls == 1


def test_overflow_never_truncates_or_calls_model(protocol, trace, tmp_path):
    config, prompts = protocol
    client = Client(count=8000)
    result = rewrite_once(client, task_config(config, "rewrite_answer"), prompts, trace,
                          tmp_path / "rewrite.json", {})
    assert result["error_code"] == "input_overflow" and client.calls == 0
    assert result["messages"][1]["content"].endswith(json.dumps(
        {"question": trace["question"], "answer": trace["answer"], "documents": trace["documents"]},
        ensure_ascii=False))


def test_transport_unknown_journal_and_unknown_citation(protocol, trace, tmp_path):
    config, prompts = protocol
    cfg = task_config(config, "rewrite_answer")
    path = tmp_path / "rewrite.json"
    result = rewrite_once(Client(fail=True), cfg, prompts, trace, path, {})
    assert result["status"] == "error" and result["cost_incomplete"]
    saved = read_json(path)
    saved.pop("result_sha256")
    saved["status"] = "started"
    write_json(path, saved)
    sealed = rewrite_once(None, cfg, prompts, trace, path, {})
    assert sealed["error_code"] == "interrupted_unknown_outcome"
    assert rewrite_once(None, cfg, prompts, trace, path, {}) == sealed
    other = rewrite_once(Client(response={"content": "Claim [unknown]", "stop_type": "eos"}),
                         cfg, prompts, trace, tmp_path / "other.json", {})
    assert other["status"] == "ok" and other["unknown_citation_ids"] == ["unknown"]
    assert other["audit_warnings"]


@pytest.fixture
def row(trace):
    measured = {"completion_attempted": True, "input_tokens": 10, "output_tokens": 2,
                "elapsed_seconds": 3, "cost_incomplete": False}
    trials = [{"trial_id": name, **decide(score, 0.7)} for name, score in
              [("original", 1), ("reversed", 0), ("repeat_2", None)]]
    return {"trace": trace, "rewrite": {**measured, "status": "ok", "answer": "A rewrite. [b]"},
            "baseline_cost": {"input_tokens": 20, "output_tokens": 4, "answer_generation_calls": 1,
                              "generation_seconds": 5, "context_seconds": 1},
            "evaluation": {"trials": trials},
            "tasks": {"extraction": measured,
                      "judges": {"original": measured, "reversed": measured}}}


@pytest.fixture
def packet(row):
    qa = {row["trace"]["record_id"]: {"reference_answers": ["Closed on Sunday."],
                                       "selected_sentences_by_reference": [["Closed on Sundays."]],
                                       "gold_passage_ids": ["b"]}}
    gold = {"b": row["trace"]["documents"][0]}
    return make_packet([row], qa, gold, "Synthetic rubric", "synthetic-v1", 44, "run-hash")


def test_blind_packet_no_stage_judge_or_condition_and_candidate_dedup(packet, row):
    public, mapping = packet
    assert len(public["cases"]) == 2
    serialized = json.dumps(public)
    for forbidden in ("example-only", '"rewritten"', '"initial"', '"score"', '"decision"', '"trials"'):
        assert forbidden not in serialized
    assert mapping["assignments"]
    qa = {row["trace"]["record_id"]: {"reference_answers": [], "selected_sentences_by_reference": [],
                                       "gold_passage_ids": []}}
    row["rewrite"]["answer"] = row["trace"]["answer"]
    result, private = make_packet([row], qa, {}, "rubric", "v1", 44, "run")
    assert len(result["cases"]) == 1
    assert len(next(iter(private["assignments"].values()))) == 2


def test_pending_preserved_and_packet_tamper_rejected(packet, tmp_path):
    public, mapping = packet
    mapping = checkpoint(tmp_path / "mapping.json", mapping)
    verify_packet(public, mapping)
    annotations = blank_annotations(public)
    result = validate_annotations(public, annotations)
    assert all(a["label"] == "pending" for a in result.values())
    public["cases"][0]["answer"] = "tampered"
    with pytest.raises(ValueError, match="Packet hash"):
        verify_packet(public, mapping)


def completed(packet, label="reliable"):
    value = blank_annotations(packet)
    for a in value["annotations"]:
        a.update(label=label, essential_points="State closing day", reason="Synthetic test label only",
                 annotator="test-fixture", elapsed_seconds=15, confirmed_at_utc="2026-10-19T00:00:00+00:00",
                 evidence=[{"passage_id": "b", "quote": "Closed on Sundays."}])
        a["criteria"] = dict.fromkeys(quality.CRITERIA, "pass")
        if label == "unreliable":
            a["criteria"] = dict.fromkeys(quality.CRITERIA, "pending")
            a["criteria"]["essential_answer"] = "fail"
        elif label == "indeterminate":
            a["criteria"]["essential_answer"] = "uncertain"
    return value


@pytest.mark.parametrize("label", ["reliable", "unreliable", "indeterminate"])
def test_manual_completed_labels_and_single_definite_failure(packet, label):
    value = completed(packet[0], label)
    validated = validate_annotations(packet[0], value)
    assert all(a["label"] == label for a in validated.values())


@pytest.mark.parametrize("change", ["duplicate", "missing", "hash", "rubric", "quote", "label",
                                     "time", "nan", "reason", "essential", "annotator", "date"])
def test_invalid_annotation_rejected(packet, change):
    public = packet[0]
    value = completed(public)
    a = value["annotations"][0]
    if change == "duplicate":
        value["annotations"][1] = deepcopy(a)
    elif change == "missing":
        value["annotations"].pop()
    elif change == "hash":
        a["candidate_sha256"] = "bad"
    elif change == "rubric":
        value["rubric_version"] = "other"
    elif change == "quote":
        a["evidence"][0]["quote"] = "invented"
    elif change == "label":
        a["criteria"]["essential_answer"] = "fail"
    elif change == "time":
        a["elapsed_seconds"] = 0
    elif change == "nan":
        a["elapsed_seconds"] = float("nan")
    elif change == "reason":
        a["reason"] = ""
    elif change == "essential":
        a["essential_points"] = ""
    elif change == "annotator":
        a["annotator"] = ""
    else:
        a["confirmed_at_utc"] = "2026-10-19T00:00:00"
    with pytest.raises(ValueError):
        validate_annotations(public, value)


@pytest.mark.parametrize("initial,revised", [(0, 0), (0, 1), (1, 0), (1, 1)])
def test_four_transitions_common_candidate_routes_and_costs(row, initial, revised):
    names = {0: "unreliable", 1: "reliable"}
    identifier = row["trace"]["record_id"]
    result = reconstruct([row], {(identifier, "initial"): names[initial],
                                 (identifier, "rewritten"): names[revised]})
    assert result["quality_transitions"][f"{initial}->{revised}"] == 1
    routes = {r["route"]: r for r in result["routes"]}
    assert routes["reversed"]["selected_answer_sha256"] == routes["always_rewrite"]["selected_answer_sha256"]
    assert routes["original"]["selected_answer_sha256"] == routes["no_repair"]["selected_answer_sha256"]
    assert routes["original"]["missed_improvement"] == (initial == 0 and revised == 1)
    assert routes["reversed"]["harmful_rewrite"] == (initial == 1 and revised == 0)
    assert routes["repeat_2"]["fallback"] == "unscorable"
    assert [routes[r]["operational_cost"]["completion_attempts"] for r in
            ("no_repair", "always_rewrite", "original", "reversed", "repeat_2")] == [1, 2, 3, 4, 2]
    assert result["auxiliary_collection_cost"]["completion_attempts"] == 4


def test_rewrite_failure_fallback_unknown_quality_and_unknown_cost(row):
    row["rewrite"].update(status="error", answer=None)
    result = reconstruct([row], {})
    assert result["quality_transitions"]["unknown"] == 1
    assert all(r["selected_stage"] == "initial" and r["quality_y"] is None and
               r["harmful_rewrite"] is None for r in result["routes"])
    assert next(r for r in result["routes"] if r["route"] == "reversed")["fallback"] == "rewrite_failed"
    unknown = cost([{"completion_attempted": True, "error_code": "interrupted_unknown_outcome"}])
    assert unknown["completion_attempts"] is None and unknown["incomplete"]


def test_import_roundtrip_preserves_history_and_pending_labels(packet, row, tmp_path, monkeypatch):
    monkeypatch.setattr(quality, "ROOT", tmp_path)
    run = tmp_path / "data/runs/answer_rewrite/synthetic"
    bundle = run / "quality"
    bundle.mkdir(parents=True)
    manifest = {"synthetic": True}
    monkeypatch.setattr(quality, "read_run", lambda _: (manifest, {"records": [row]}))
    public, mapping = packet
    mapping["run_manifest_sha256"] = digest(manifest)
    write_json(run / "report.json", {"synthetic": True})
    write_json(bundle / "packet.json", public)
    checkpoint(bundle / "mapping.private.json", mapping)
    checkpoint(bundle / "export_manifest.json", {"packet_sha256": public["packet_sha256"],
               "run_manifest_sha256": digest(manifest),
               "mapping_sha256": file_hash(bundle / "mapping.private.json")})
    path = bundle / "test-only.json"
    write_json(path, blank_annotations(public))
    first = quality.import_quality(run, bundle, path)
    assert first["manual_annotation_status_counts"] == {"pending": 2}
    assert first["quality_transitions"]["unknown"] == 1
    write_json(path, completed(public))
    second = quality.import_quality(run, bundle, path)
    assert second["quality_transitions"]["1->1"] == 1
    assert first["output"] != second["output"]
    assert Path(first["output"]).exists()
    assert read_json(Path(first["output"]) / "annotations.json")["annotations"][0]["label"] == "pending"


def test_form_safe_literal_and_javascript_syntax(packet, tmp_path):
    public = packet[0]
    public["cases"][0]["answer"] = '</script><img src=x onerror="alert(1)">'
    html = render_form(public)
    assert '</script><img' not in html
    assert "mapping.private" not in html and "example-only" not in html
    assert "connect-src 'none'" in html
    script = html.split('<script>')[1].split('</script>')[0]
    path = tmp_path / "form.js"
    path.write_text(script, encoding="utf-8")
    # Syntax check is local development validation; Node is not a runtime dependency of the form.
    import shutil

    node = shutil.which("node")
    if node:
        subprocess.run([node, "--check", str(path)], check=True, capture_output=True)


@pytest.mark.parametrize("changed", ["source", "rewrite", "cost", "evaluation"])
def test_read_run_rejects_changed_source_results_or_costs(row, tmp_path, monkeypatch, changed):
    monkeypatch.setattr(quality, "ROOT", tmp_path)
    source = tmp_path / "data/runs/order_sensitivity/synthetic"
    run = tmp_path / "data/runs/answer_rewrite/synthetic"
    directory = digest(row["trace"]["record_id"])[:24]
    (source / directory).mkdir(parents=True)
    (run / directory).mkdir(parents=True)
    baseline = tmp_path / "data/runs/answers.jsonl"
    baseline.write_text(json.dumps({"record_id": row["trace"]["record_id"],
                                    **row["baseline_cost"]}) + "\n", encoding="utf-8")
    write_json(source / "manifest.json", {"baseline_answers_sha256": file_hash(baseline)})
    write_json(source / directory / "trace.json", row["trace"])
    write_json(source / directory / "claims.json", row["tasks"]["extraction"])
    source_report = {"records": [{"record_id": row["trace"]["record_id"], **row["evaluation"]}]}
    row["evaluation"] = source_report["records"][0]
    write_json(source / "report.json", source_report)
    manifest = {"source_order_run": str(source.relative_to(tmp_path)),
                "source_artifacts": {"report.json": file_hash(source / "report.json")},
                "config": {"baseline_answers": str(baseline.relative_to(tmp_path))}}
    write_json(run / "manifest.json", manifest)
    row["rewrite"]["binding"] = {"manifest_sha256": digest(manifest),
                                   "trace_sha256": row["trace"]["trace_sha256"]}
    row["rewrite"] = checkpoint(run / directory / "rewrite.json", row["rewrite"])
    report = {"manifest_sha256": digest(manifest), "records": [row]}
    write_json(run / "report.json", report)
    quality.read_run(run)
    if changed == "source":
        write_json(source / "report.json", {"records": []})
    elif changed == "rewrite":
        report["records"][0]["rewrite"]["answer"] = "tampered answer"
        write_json(run / "report.json", report)
    elif changed == "cost":
        report["records"][0]["baseline_cost"]["input_tokens"] += 1
        write_json(run / "report.json", report)
    else:
        report["records"][0]["evaluation"]["trials"][0]["score"] = 0
        write_json(run / "report.json", report)
    with pytest.raises(ValueError):
        quality.read_run(run)
