"""Synthetic offline contracts for Japanese QA, source identities and frozen splits."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from rag_research.data.baobab_source import DATASET_ID, REVISION, SOURCE_FILES
from rag_research.data.japanese_dataset import (
    assign_splits,
    connected_groups,
    group_statistics,
    normalize_answered,
    publish_immutable,
    read_complete_snapshot,
    validate_assignments,
    validate_spec,
)
from rag_research.data.wikipedia_snapshot import fetch_article
from rag_research.experiments.frozen_trace import digest
from rag_research.experiments.protocol import build_messages
from rag_research.experiments.storage import checkpoint, read_json

ROOT = Path(__file__).resolve().parents[2]


def spec():
    return read_json(ROOT / "configs/phase11_japanese_dataset_v1.json")


def row(identifier, *titles):
    return {"id": identifier, "question": f"架空の質問{identifier}ですか？",
            "references": [{"page": {"title": title, "url": "https://ja.wikipedia.org/wiki/Test",
                                      "quote": {"text": f"架空の原文{title}。"}}} for title in titles],
            "answer": {"text": f"架空の回答{identifier}です。", "sentences": [
                {"text": f"架空の回答{identifier}です。", "citations": [0]}]}}


def article(title, *, page_id=None, canonical=None, text_hash=None, redirects=()):
    return {"requested_title": title, "canonical_title": canonical or title,
            "page_id": page_id, "status": "ok" if text_hash else "unavailable",
            "text_sha256": text_hash, "normalized_titles": [], "current_redirects": list(redirects)}


def test_adapter_preserves_literal_quotes_summary_citations_and_raw_line_hash():
    raw = row(1, "引用先", "要約先", "未引用の資料")
    raw["references"][1]["page"].pop("quote")
    raw["references"][1]["page"]["summary"] = {"text": "人が書いた要約。"}
    raw["answer"]["sentences"][0]["citations"] = [0, 1]
    line = (json.dumps(raw, ensure_ascii=False) + "\n").encode()
    record = normalize_answered(raw, raw_line=line, line_index=7)
    assert record["record_id"] == f"whrja:{REVISION[:7]}:answered:1"
    assert record["source_line_index"] == 7
    assert record["source_record_sha256"] == hashlib.sha256(line).hexdigest()
    assert record["reference_answers"] == [raw["answer"]["text"]]
    assert record["selected_sentences_by_reference"] == [["架空の原文引用先。"]]
    assert record["reference_evidence"][1]["quote"] is None
    assert record["reference_evidence"][1]["human_summary_not_literal_source"] == "人が書いた要約。"
    assert record["reference_evidence"][2]["cited_by_answer_sentence_indices"] == []
    assert record["is_answerable"] is True and record["gold_passage_ids"] == []
    assert record["gold_passage_mapping_status"] == "pending_passage_build"
    assert record["provided_passage"] is None and record["language"] == "ja"
    record["reference_answer_sentences"][0]["citations"].append(2)
    assert raw["answer"]["sentences"][0]["citations"] == [0, 1]
    with pytest.raises(ValueError, match="forbidden model input"):
        build_messages({}, "extract_claims", record)


def test_adapter_rejects_source_row_line_mismatch_and_unsuccessful_search_label():
    original = row(1, "資料")
    with pytest.raises(ValueError, match="line/record"):
        normalize_answered(original, raw_line=b"{}\n", line_index=0)
    failed = {"id": 1, "question": "架空？", "references": []}
    with pytest.raises(ValueError, match="reference answer"):
        normalize_answered(failed, raw_line=json.dumps(failed).encode(), line_index=0)


def test_all_references_and_transitive_links_extend_development_reservation():
    # B/C are not cited in row 1/2, but still connect all three QA.
    rows = [row(1, "A", "B"), row(2, "B", "C"), row(3, "C"), row(4, "D")]
    groups = connected_groups(rows, reserved_source_ids=[1])
    assert sorted(g["source_ids"] for g in groups) == [[1, 2, 3], [4]]
    assert group_statistics(groups)["reserved_development_qa"] == 3
    assert connected_groups(rows[::-1], reserved_source_ids=[1]) == groups


@pytest.mark.parametrize("articles", [
    [article("A", page_id=1), article("B", page_id=1)],
    [article("A", canonical="B"), article("B")],
    [article("A", redirects=[{"from": "A", "to": "B"}]), article("B")],
    [article("A", text_hash="0" * 64), article("B", text_hash="0" * 64)],
])
def test_alias_pageid_redirect_and_identical_article_bodies_are_indivisible(articles):
    groups = connected_groups([row(1, "A"), row(2, "B")], reserved_source_ids=[1], articles=articles)
    assert len(groups) == 1 and groups[0]["source_ids"] == [1, 2]
    assert groups[0]["development_reserved"] is True
    assert connected_groups([row(2, "B"), row(1, "A")], reserved_source_ids=[1],
                            articles=articles[::-1]) == groups


def test_title_normalization_and_exact_question_answer_duplicates_are_grouped():
    rows = [row(1, "Ａ_Ｂ"), row(2, "Ａ Ｂ"), row(3, "C"), row(4, "D"), row(5, "E")]
    rows[2]["question"] = rows[0]["question"] + " \n"
    rows[3]["answer"] = deepcopy(rows[0]["answer"])
    groups = connected_groups(rows, reserved_source_ids=[1])
    assert sorted(g["source_ids"] for g in groups) == [[1, 2, 3, 4], [5]]
    with pytest.raises(ValueError, match="reserved"):
        connected_groups(rows, reserved_source_ids=[6])


def test_greedy_split_preserves_all_qa_groups_and_targets_independent_of_input_order():
    rows = [row(i, f"文書{i}") for i in range(1, 101)]
    groups = connected_groups(rows, reserved_source_ids=list(range(1, 11)))
    assignments = assign_splits(groups, spec())
    assert group_statistics(groups, assignments)["split_qa_counts"] == {
        "development": 65, "calibration": 10, "evaluation": 25}
    assert assign_splits(groups[::-1], spec()) == assignments
    assert validate_assignments(groups, assignments)["cross_group_identity_overlap"] == 0
    assert all(assignments[g["group_id"]] == "development" for g in groups if g["development_reserved"])


def test_group_validation_rejects_reserved_escape_and_shared_identity():
    groups = connected_groups([row(i, str(i)) for i in range(1, 11)], reserved_source_ids=[1])
    assignments = assign_splits(groups, spec())
    reserved = next(g for g in groups if g["development_reserved"])
    corrupted = {**assignments, reserved["group_id"]: "evaluation"}
    with pytest.raises(ValueError, match="Reserved"):
        validate_assignments(groups, corrupted)
    groups[0]["identity_keys"].append(groups[1]["identity_keys"][0])
    with pytest.raises(ValueError, match="multiple Groups"):
        validate_assignments(groups, assignments)


def test_indivisible_groups_do_not_get_split_or_replaced_to_fill_a_target():
    groups = connected_groups([row(i, "同じ資料") for i in range(1, 6)], reserved_source_ids=[1])
    with pytest.raises(ValueError, match="empty split"):
        assign_splits(groups, spec())


@pytest.mark.parametrize("field,value", [
    ("seed", True), ("split_percentages", {"development": 65, "calibration": 10, "evaluation": 24}),
    ("unsuccessful_searches_are_unanswerable_qa", True), ("grouping", "cited_pages_only"),
    ("source_revision", "0" * 40),
])
def test_population_grouping_and_split_policy_changes_fail_closed(field, value):
    config = spec()
    config[field] = value
    with pytest.raises(ValueError):
        validate_spec(config)


def complete_snapshot(tmp_path):
    config = read_json(ROOT / "configs/phase11_japanese_corpus_v1.json")
    archive = tmp_path / "source_snapshot/probe.py"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"synthetic archived acquisition source, never executed")
    plan = checkpoint(tmp_path / "plan.json", {
        "purpose": "phase11-historical-japanese-corpus-plan", "source_dataset": DATASET_ID,
        "source_revision": REVISION, "source_files_sha256": SOURCE_FILES, "spec": config,
        "titles": ["架空資料"], "source_code_sha256": {"probe.py": hashlib.sha256(archive.read_bytes()).hexdigest()}})
    checkpoint(tmp_path / "execution.json", {"plan_sha256": digest(plan), "repository_commit": "0" * 40})

    def get(parameters, path):
        if parameters["action"] == "query":
            response = {"query": {"pages": [{"title": "架空資料", "pageid": 1, "ns": 0,
                        "revisions": [{"revid": 2, "timestamp": "2023-12-01T00:00:00Z"}]}]}}
        else:
            response = {"parse": {"revid": 2, "pageid": 1, "text": "<p>架空資料の本文。</p>"}}
        checkpoint(path, {"status": "ok", "parameters": parameters, "response": response})
        return response

    fetch_article(SimpleNamespace(get=get), config, "架空資料", tmp_path, digest(plan))
    checkpoint(tmp_path / "progress-001.json", {"plan_sha256": digest(plan), "status": "finished",
               "articles_seen_this_session": 1, "expected_articles": 1, "statuses": {"ok": 1}})
    return tmp_path


def test_complete_snapshot_checks_raw_response_revision_body_and_source_archive(tmp_path):
    directory = complete_snapshot(tmp_path)
    _, articles = read_complete_snapshot(directory, expected_titles=["架空資料"])
    assert len(articles) == 1 and articles[0]["text"] == "架空資料の本文。"
    (directory / "source_snapshot/probe.py").write_bytes(b"changed")
    with pytest.raises(ValueError, match="source archive"):
        read_complete_snapshot(directory, expected_titles=["架空資料"])


@pytest.mark.parametrize("mutation,expected", [
    ("missing_progress", "incomplete"), ("body_changed", "body changed"),
    ("raw_request_changed", "request archive"), ("progress_counts", "counts differ"),
])
def test_snapshot_cannot_silently_be_partial_or_disconnected_from_raw(tmp_path, mutation, expected):
    directory = complete_snapshot(tmp_path)
    if mutation == "missing_progress":
        (directory / "progress-001.json").unlink()
    elif mutation == "body_changed":
        path = next((directory / "articles").glob("*.json"))
        body = read_json(path)
        body.pop("result_sha256")
        body["text"] = "変更した本文。"
        checkpoint(path, body)
    elif mutation == "raw_request_changed":
        next((directory / "requests").glob("*-parse.json")).write_text("{}")
    else:
        path = directory / "progress-001.json"
        progress = read_json(path)
        progress.pop("result_sha256")
        progress["statuses"] = {"unavailable": 1}
        checkpoint(path, progress)
    with pytest.raises(ValueError, match=expected):
        read_complete_snapshot(directory, expected_titles=["架空資料"])


def test_immutable_multi_file_publish_is_idempotent_and_preflights_all_conflicts(tmp_path):
    first, second = tmp_path / "qa.jsonl", tmp_path / "report.json"
    publish_immutable({first: b"original", second: b"report"})
    publish_immutable({first: b"original", second: b"report"})
    third = tmp_path / "third.json"
    with pytest.raises(ValueError, match="new output version"):
        publish_immutable({third: b"new", first: b"changed"})
    assert not third.exists() and first.read_bytes() == b"original"
