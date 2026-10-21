"""Literal provenance, missing sources, cited-only Gold and unchanged original splits."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from rag_research.data.japanese_dataset import normalize_answered
from rag_research.data.japanese_evidence import (
    bind_record,
    literal_spans,
    prepare_dataset,
    validate_spec,
)
from rag_research.retrieval.common import file_hash, read_json, write_json

ROOT = Path(__file__).resolve().parents[2]


def original_record(citations=(0,), *, duplicate_parent=False):
    pages = [{"title": title, "url": "https://ja.wikipedia.org/wiki/" + title, **content}
             for title, content in [
                 ("引用記事", {"quote": {"text": "第一文。"}}),
                 ("要約記事", {"summary": {"text": "人手による要約です。"}}),
                 ("欠測記事", {"quote": {"text": "取得できない本文。"}}),
                 ("別名記事", {"quote": {"text": "第一文。"}})]]
    row = {"id": 1, "question": "架空の説明をしてください。", "references": [{"page": p} for p in pages],
           "answer": {"text": "架空の回答です。", "sentences": [{"text": "架空の回答です。", "citations": list(citations)}]}}
    record = normalize_answered(row, raw_line=(json.dumps(row, ensure_ascii=False) + "\n").encode(), line_index=0)
    record.update(research_split="development", document_group_id="group-1")
    body = "第一文。\n続きです。"
    catalog = {"引用記事": {"parent_passage_id": "p1", "body_available": True, "raw_status": "ok", "wikipedia_page_id": 1},
               "要約記事": {"parent_passage_id": "p2", "body_available": True, "raw_status": "ok", "wikipedia_page_id": 2},
               "欠測記事": {"parent_passage_id": None, "body_available": False, "raw_status": "error", "wikipedia_page_id": 3},
               "別名記事": {"parent_passage_id": "p1" if duplicate_parent else "p4", "body_available": True,
                           "raw_status": "ok", "wikipedia_page_id": 1 if duplicate_parent else 4}}
    bodies = {"p1": body, "p2": "元の記事本文です。", "p4": body}
    children = {"p1": [{"passage_id": "1_0-2", "start": 0, "end": 2}, {"passage_id": "1_2-10", "start": 2, "end": len(body)}],
                "p2": [{"passage_id": "2_0-10", "start": 0, "end": 10}],
                "p4": [{"passage_id": "4_0-10", "start": 0, "end": len(body)}]}
    return record, catalog, children, bodies


@pytest.mark.parametrize("body,quote,mode,locations", [
    ("前。引用です。後。", "引用です。", "exact", [(2, 7)]),
    ("博 物\n館です。", "博物館です。", "whitespace_only", [(0, 8)]),
    ("aaa", "aa", "exact", [(0, 2), (1, 3)]),
])
def test_literal_locations_preserve_actual_source_characters(body, quote, mode, locations):
    value = literal_spans(body, quote)
    assert value["status"] == "located" and value["mode"] == mode
    assert [(s["start"], s["end"]) for s in value["spans"]] == locations
    assert value["ambiguous_location"] == (len(locations) > 1)
    assert all(s["source_span_sha256"] == hashlib.sha256(body[s["start"]:s["end"]].encode()).hexdigest()
               for s in value["spans"])


@pytest.mark.parametrize("body,quote", [("Ａです。", "Aです。"), ("違う内容です。", "元の内容です。"),
                                       ("cat.", "Cat."), ("内容。", "内容！")])
def test_literal_audit_does_not_use_fuzzy_case_unicode_or_punctuation_replacement(body, quote):
    assert literal_spans(body, quote)["status"] == "not_located"


def test_missing_body_and_human_summary_remain_distinct():
    assert literal_spans(None, "元の引用。")["status"] == "article_body_unavailable"
    assert literal_spans("同文でも自動で原文扱いにしない。", None)["status"] == "no_literal_quote"
    with pytest.raises(ValueError):
        literal_spans("本文", " \n")


def test_only_cited_parents_and_verified_quote_children_become_gold():
    record, catalog, children, bodies = original_record((0, 1, 2))
    original = deepcopy(record)
    mapped = bind_record(record, catalog, children, bodies)
    assert record == original
    assert mapped["gold_parent_ids"] == ["p1", "p2"]
    assert mapped["gold_passage_ids"] == ["1_0-2", "1_2-10"]  # Quote spans both existing children.
    assert mapped["unavailable_cited_reference_ids"] == ["jawiki-page:3"]
    assert mapped["is_answerable"] is True and mapped["research_split"] == "development"
    assert mapped["reference_corpus_metadata_offline_only"] is True
    assert mapped["reference_corpus_mapping"][1]["has_human_summary_not_literal_source"] is True
    assert mapped["reference_corpus_mapping"][1]["literal_quote_audit"]["status"] == "no_literal_quote"
    assert "p4" not in mapped["gold_parent_ids"]
    assert all(mapped[k] == value for k, value in original.items() if k not in
               {"gold_passage_ids", "gold_passage_mapping_status"})


def test_missing_all_cited_bodies_does_not_drop_or_relabel_qa():
    record, catalog, children, bodies = original_record((2,))
    mapped = bind_record(record, catalog, children, bodies)
    assert mapped["gold_parent_ids"] == mapped["gold_passage_ids"] == []
    assert mapped["unavailable_cited_reference_ids"] == ["jawiki-page:3"]
    assert mapped["is_answerable"] is True


def test_aliases_deduplicate_parent_gold_and_unlocated_quotes_stay_explicit():
    record, catalog, children, bodies = original_record((0, 3), duplicate_parent=True)
    assert bind_record(record, catalog, children, bodies)["gold_parent_ids"] == ["p1"]
    bodies["p1"] = "一致しない過去本文です。"
    mapped = bind_record(record, catalog, children, bodies)
    assert mapped["gold_parent_ids"] == ["p1"] and mapped["gold_passage_ids"] == []
    assert all(m["literal_quote_audit"]["status"] == "not_located" for m in mapped["reference_corpus_mapping"] if m["cited"])


def test_unknown_catalog_title_or_changed_citation_mapping_is_rejected():
    record, catalog, children, bodies = original_record()
    catalog.pop("引用記事")
    with pytest.raises(ValueError, match="exact declared"):
        bind_record(record, catalog, children, bodies)
    record, catalog, children, bodies = original_record()
    record["reference_evidence"][0]["cited_by_answer_sentence_indices"] = []
    with pytest.raises(ValueError, match="correspondence changed"):
        bind_record(record, catalog, children, bodies)


@pytest.mark.parametrize("field,value", [("quote_matching", "fuzzy"), ("uncited_references_are_gold", True),
                                         ("human_summary", "literal_source"), ("per_question_corpus_injection", True)])
def test_unsafe_mapping_policy_is_rejected(field, value):
    spec = read_json(ROOT / "configs/phase11_japanese_evidence_v1.json")
    spec[field] = value
    with pytest.raises(ValueError):
        validate_spec(spec)


def fixture_dataset(tmp_path):
    groups, corpus, snapshot = [tmp_path / name for name in ("groups", "corpus", "snapshot")]
    for directory in (groups, corpus, snapshot / "articles"):
        directory.mkdir(parents=True)
    record, catalog, _, bodies = original_record((0,))
    # Materialize full provenance for all available parents, without reading real QA.
    parent_rows, child_rows, hashes = [], [], {}
    actual_parents = {}
    for i, title in [(1, "引用記事"), (2, "要約記事"), (4, "別名記事")]:
        body = bodies[f"p{i}"]
        text_hash = hashlib.sha256(body.encode()).hexdigest()
        article = {"status": "ok", "page_id": i, "revision_id": 100 + i, "text_sha256": text_hash, "text": body}
        path = snapshot / "articles" / (hashlib.sha256(title.encode()).hexdigest()[:24] + ".json")
        write_json(path, article)
        hashes[title] = file_hash(path)
        parent = f"jawiki:{i}:{100+i}:{text_hash}"
        actual_parents[title] = parent
        catalog[title]["requested_title"] = title
        catalog[title]["parent_passage_id"] = parent
        child_id = f"{i}_0-{len(body)}"
        parent_rows.append({"parent_passage_id": parent, "child_passage_ids": [child_id]})
        child_rows.append({"passage_id": child_id, "parent_passage_id": parent,
                           "source_char_span": {"start": 0, "end": len(body)}})
    catalog["欠測記事"]["requested_title"] = "欠測記事"
    for directory, name, rows in [(groups, "qa.jsonl", [record]), (groups, "groups.json", []),
                                   (corpus, "passages.jsonl", child_rows), (corpus, "parent_map.jsonl", parent_rows),
                                   (corpus, "article_catalog.jsonl", list(catalog.values()))]:
        (directory / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    for directory in (groups, corpus):
        artifacts = {p.name: {"sha256": file_hash(p), "bytes": p.stat().st_size} for p in directory.iterdir()}
        report = {"artifacts": artifacts}
        if directory == corpus:
            report["execution_identity"] = {"article_journal_sha256": hashes}
        write_json(directory / "report.json", report)
    spec = read_json(ROOT / "configs/phase11_japanese_evidence_v1.json")
    spec.update(expected_qa_count=1, source_group_report_sha256=file_hash(groups / "report.json"),
                source_corpus_report_sha256=file_hash(corpus / "report.json"))
    return groups, corpus, snapshot, spec


def test_full_dataset_publish_is_immutable_and_preserves_original_sources(tmp_path):
    groups, corpus, snapshot, spec = fixture_dataset(tmp_path)
    output = tmp_path / "mapped"
    original_hashes = {str(p): file_hash(p) for d in (groups, corpus, snapshot) for p in d.rglob("*") if p.is_file()}
    report = prepare_dataset(groups, corpus, snapshot, output, spec, code_hashes={"fixture": "v1"})
    assert report["statistics"]["qa_count"] == 1
    assert report["statistics"]["split_counts"] == {"development": 1}
    assert report["statistics"]["cited_reference_quote_statuses"] == {"located": 1}
    assert original_hashes == {p: file_hash(Path(p)) for p in original_hashes}
    before = {p.name: file_hash(p) for p in output.iterdir()}
    assert prepare_dataset(groups, corpus, snapshot, output, spec, code_hashes={"fixture": "v1"}) == report
    assert before == {p.name: file_hash(p) for p in output.iterdir()}
    with pytest.raises(ValueError, match="differs"):
        prepare_dataset(groups, corpus, snapshot, output, spec, code_hashes={"fixture": "v2"})


@pytest.mark.parametrize("changed", ["corpus", "raw_article"])
def test_changed_input_cannot_be_accepted_via_existing_output_cache(tmp_path, changed):
    groups, corpus, snapshot, spec = fixture_dataset(tmp_path)
    output = tmp_path / "mapped"
    prepare_dataset(groups, corpus, snapshot, output, spec, code_hashes={})
    path = corpus / "passages.jsonl" if changed == "corpus" else next((snapshot / "articles").glob("*.json"))
    path.write_text("changed")
    with pytest.raises(ValueError, match="changed"):
        prepare_dataset(groups, corpus, snapshot, output, spec, code_hashes={})
