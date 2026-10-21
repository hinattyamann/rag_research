"""Raw-source audit, alias deduplication, full text and immutable Japanese corpus."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rag_research.data.baobab_source import DATASET_ID, REVISION, SOURCE_FILES
from rag_research.data.japanese_token_corpus import article_children, prepare_corpus, validate_spec
from rag_research.data.wikipedia_snapshot import fetch_article
from rag_research.experiments.frozen_trace import digest
from rag_research.experiments.storage import checkpoint
from rag_research.retrieval.common import file_hash, read_json

ROOT = Path(__file__).resolve().parents[2]


class Tokenizer:
    model_manifest = {"model_id": "synthetic-character-tokenizer"}
    raw = SimpleNamespace(encode=lambda text, add_special_tokens=False:
                          SimpleNamespace(offsets=[(i, i + 1) for i in range(len(text))]))

    def count(self, text):
        return len(text) + 5


def fixture_snapshot(directory):
    directory.mkdir()
    config = read_json(ROOT / "configs/phase11_japanese_corpus_v1.json")
    archive = directory / "source_snapshot/probe.py"
    archive.parent.mkdir()
    archive.write_bytes(b"synthetic acquisition source archive")
    titles = sorted(["架空資料", "別名", "取得不能資料"])
    plan = checkpoint(directory / "plan.json", {
        "purpose": "phase11-historical-japanese-corpus-plan", "source_dataset": DATASET_ID,
        "source_revision": REVISION, "source_files_sha256": SOURCE_FILES, "spec": config,
        "titles": titles, "source_code_sha256": {"probe.py": file_hash(archive)}})
    checkpoint(directory / "execution.json", {"plan_sha256": digest(plan), "repository_commit": "0" * 40})

    def get(parameters, path):
        if parameters["action"] == "query":
            page = ({"title": "取得不能資料", "missing": True} if parameters["titles"] == "取得不能資料" else
                    {"title": "架空資料", "pageid": 1, "ns": 0,
                     "revisions": [{"revid": 2, "timestamp": "2023-12-01T00:00:00Z"}]})
            response = {"query": {"pages": [page]}}
        else:
            response = {"parse": {"revid": 2, "pageid": 1, "text": "<p>架空資料の長い本文です。" * 10 + "</p>"}}
        checkpoint(path, {"status": "ok", "parameters": parameters, "response": response})
        return response

    for title in titles:
        fetch_article(SimpleNamespace(get=get), config, title, directory, digest(plan))
    checkpoint(directory / "progress-001.json", {"plan_sha256": digest(plan), "status": "finished",
               "articles_seen_this_session": 3, "expected_articles": 3,
               "statuses": {"ok": 2, "unavailable": 1}})
    spec = read_json(ROOT / "configs/phase11_japanese_token_corpus_v1.json")
    spec.update(snapshot_plan_sha256=file_hash(directory / "plan.json"), expected_titles=3,
                expected_status_counts={"ok": 2, "unavailable": 1, "error": 0},
                expected_unique_articles=1, max_input_tokens=32)
    return spec


def test_source_only_full_corpus_deduplicates_aliases_and_retains_absence(tmp_path):
    snapshot, output = tmp_path / "snapshot", tmp_path / "corpus"
    spec = fixture_snapshot(snapshot)
    raw_hashes = {str(p): file_hash(p) for p in snapshot.rglob("*") if p.is_file()}
    report = prepare_corpus(snapshot, output, spec, Tokenizer(), code_hashes={"fixture": "v1"})
    passages = [json.loads(line) for line in (output / "passages.jsonl").read_text().splitlines()]
    parent = json.loads((output / "parent_map.jsonl").read_text())
    catalog = [json.loads(line) for line in (output / "article_catalog.jsonl").read_text().splitlines()]
    article = next(json.loads(p.read_text()) for p in (snapshot / "articles").glob("*.json")
                   if json.loads(p.read_text())["status"] == "ok")
    assert report["source_unique_article_count"] == 1 and report["output_passage_count"] > 1
    assert report["source_status_counts"] == {"ok": 2, "unavailable": 1}
    assert "".join(p["text"] for p in passages) == article["text"]
    assert report["maximum_embedding_input_tokens"] <= 32
    assert report["qa_or_reference_read"] is False
    assert parent["requested_titles"] == sorted(["架空資料", "別名"])
    assert parent["child_passage_ids"] == [p["passage_id"] for p in passages]
    assert all(p["parent_passage_id"] == parent["parent_passage_id"] for p in passages)
    assert len(catalog) == 3
    assert [c for c in catalog if not c["body_available"]][0]["parent_passage_id"] is None
    assert raw_hashes == {str(p): file_hash(p) for p in snapshot.rglob("*") if p.is_file()}
    assert prepare_corpus(snapshot, output, spec, Tokenizer(), code_hashes={"fixture": "v1"}) == report
    with pytest.raises(ValueError, match="conditions changed"):
        prepare_corpus(snapshot, output, spec, Tokenizer(), code_hashes={"fixture": "v2"})
    (output / "passages.jsonl").write_text("changed")
    with pytest.raises(ValueError, match="artifact changed"):
        prepare_corpus(snapshot, output, spec, Tokenizer(), code_hashes={"fixture": "v1"})


@pytest.mark.parametrize("failure", ["qa_field", "raw_parse", "incomplete", "wrong_plan", "wrong_count"])
def test_corpus_rejects_injected_qa_or_changed_incomplete_snapshot(tmp_path, failure):
    snapshot, output = tmp_path / "snapshot", tmp_path / "corpus"
    spec = fixture_snapshot(snapshot)
    if failure == "qa_field":
        path = next((snapshot / "articles").glob("*.json"))
        row = read_json(path)
        row.pop("result_sha256")
        row["reference_answers"] = ["secret"]
        checkpoint(path, row)
    elif failure == "raw_parse":
        next((snapshot / "requests").glob("*-parse.json")).write_text("{}")
    elif failure == "incomplete":
        (snapshot / "progress-001.json").unlink()
    elif failure == "wrong_plan":
        spec["snapshot_plan_sha256"] = "0" * 64
    else:
        spec["expected_unique_articles"] = 2
    with pytest.raises(ValueError):
        prepare_corpus(snapshot, output, spec, Tokenizer(), code_hashes={})
    assert not output.exists()


@pytest.mark.parametrize("field,value", [("qa_or_reference_input", True), ("max_input_tokens", 513),
                                         ("parent_relevance_unit", "every_child_is_gold"),
                                         ("terminal_source_unavailability_policy", "all_errors")])
def test_unsafe_corpus_policy_is_rejected(field, value):
    spec = read_json(ROOT / "configs/phase11_japanese_token_corpus_v1.json")
    spec[field] = value
    with pytest.raises(ValueError):
        validate_spec(spec)


def test_article_children_reject_reference_injection_and_unavailable_article():
    with pytest.raises(ValueError, match="QA/Reference"):
        article_children({"reference_answers": ["secret"]}, Tokenizer())
    with pytest.raises(ValueError, match="verified historical"):
        article_children({"status": "unavailable"}, Tokenizer())


def test_interrupted_staging_is_preserved(tmp_path):
    snapshot, output = tmp_path / "snapshot", tmp_path / "corpus"
    spec = fixture_snapshot(snapshot)
    stage = output.with_name(output.name + ".building")
    stage.mkdir()
    (stage / "previous.txt").write_bytes(b"preserve previous failure")
    with pytest.raises(ValueError, match="Incomplete Japanese corpus"):
        prepare_corpus(snapshot, output, spec, Tokenizer(), code_hashes={})
    assert (stage / "previous.txt").read_bytes() == b"preserve previous failure"
    assert not output.exists()
