"""Preserve source text and original Gold relevance units during subdivision."""

import hashlib
import json
from types import SimpleNamespace

import pytest

from rag_research.data.clapnq_source import CLAPNQ_REVISION
from rag_research.data.token_bounded_corpus import (
    normalize_corpus,
    parent_relevance,
    source_passages,
)
from rag_research.retrieval.common import file_hash


class Tokenizer:
    model_manifest = {"model_id": "synthetic-token-count-fixture"}
    raw = SimpleNamespace(encode=lambda text, add_special_tokens=False:
                          SimpleNamespace(offsets=[(i, i + 1) for i in range(len(text))]))

    def count(self, text):
        return len(text) + 5


def row(identifier, text):
    return {"source_dataset": "CLAPNQ", "source_revision": CLAPNQ_REVISION, "passage_id": identifier,
            "title": "Synthetic source", "text": text, "text_sha256": hashlib.sha256(text.encode()).hexdigest()}


def test_short_passages_keep_id_and_text_while_long_passages_keep_parent_and_span():
    short = row("42_0-10", "Short.")
    assert source_passages(short, Tokenizer(), max_tokens=32)[0]["passage_id"] == "42_0-10"
    source = row("99_0-200", "A sentence. Another sentence. " * 10)
    children = source_passages(source, Tokenizer(), max_tokens=32)
    assert len(children) > 1 and "".join(c["text"] for c in children) == source["text"]
    assert len({c["passage_id"] for c in children}) == len(children)
    assert all(c["parent_passage_id"] == source["passage_id"] for c in children)
    assert all(c["source_char_span"]["embedding_input_tokens"] <= 32 for c in children)
    assert source_passages(source, Tokenizer(), max_tokens=32) == children
    with pytest.raises(ValueError, match="QA/Reference"):
        source_passages({**short, "reference_answers": ["secret"]}, Tokenizer())


def test_parent_gold_relevance_is_not_counted_again_for_duplicate_children():
    assert parent_relevance(["a", "b", "c"], {"a": "gold", "b": "gold", "c": "other"}, ["gold"]) == [1, 0, 0]
    with pytest.raises(ValueError, match="Unknown child"):
        parent_relevance(["missing"], {}, ["gold"])
    with pytest.raises(ValueError, match="Duplicate"):
        parent_relevance(["a", "a"], {"a": "gold"}, ["gold"])


def test_corpus_parent_map_frozen_resume_and_tamper_detection(tmp_path):
    rows = [row("1", "Short."), row("2", "A sentence. Another sentence. " * 5)]
    source = tmp_path / "source.jsonl"
    source.write_text("".join(json.dumps(r) + "\n" for r in rows))
    original_hash = file_hash(source)
    spec = {"schema_version": 1, "purpose": "phase11-token-bounded-english-corpus",
            "dataset_version": "c508d78-e5-passages-v1", "source_dataset": "CLAPNQ",
            "source_revision": CLAPNQ_REVISION, "expected_parent_passages": 2, "max_input_tokens": 32,
            "source_corpus_sha256": original_hash, "preserve_within_budget_ids": True,
            "gold_relevance_unit": "original_source_parent_passage", "quality_or_question_filtering": False,
            "phase12_allowed": False}
    output = tmp_path / "new-version"
    report = normalize_corpus(source, output, spec, Tokenizer(), code_hashes={"fixture": "test"})
    assert report["source_parent_count"] == 2 and report["subdivided_parent_count"] == 1
    assert report["unchanged_parent_id_count"] == 1 and file_hash(source) == original_hash
    children = [json.loads(s) for s in (output / "passages.jsonl").read_text().splitlines()]
    mapping = [json.loads(s) for s in (output / "parent_map.jsonl").read_text().splitlines()]
    assert len(mapping) == 2 and sum(len(m["child_passage_ids"]) for m in mapping) == len(children)
    for parent in rows:
        assert "".join(c["text"] for c in children if c["parent_passage_id"] == parent["passage_id"]) == parent["text"]
    assert normalize_corpus(source, output, spec, Tokenizer(), code_hashes={"fixture": "test"}) == report
    with pytest.raises(ValueError, match="conditions changed"):
        normalize_corpus(source, output, spec, Tokenizer(), code_hashes={"fixture": "changed"})
    (output / "passages.jsonl").write_text("changed")
    with pytest.raises(ValueError, match="artifact changed"):
        normalize_corpus(source, output, spec, Tokenizer(), code_hashes={"fixture": "test"})
