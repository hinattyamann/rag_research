"""Full source coverage, actual prefix budgets and stable historical passage identity."""

import hashlib
from types import SimpleNamespace

import pytest

from rag_research.data.japanese_passages import article_passages, split_spans
from rag_research.evaluation.sentence_claims import extract_sentence_units


class CharacterTokenizer:
    raw = SimpleNamespace(encode=lambda text, add_special_tokens=False:
                          SimpleNamespace(offsets=[(i, i + 1) for i in range(len(text))]))

    def count(self, text):
        return len(text) + 5  # Prefix plus specials really consume budget.


@pytest.mark.parametrize("text", [
    "架空の市です。資料は三つあります。" * 10,
    "Sentence one. Sentence two.\n" * 10,
    "無句点の説明と絵文字🌸" * 12,
    " leading whitespace. 次の文。\n" * 10,
])
def test_spans_cover_every_original_character_with_no_overlap_or_truncation(text):
    tokenizer = CharacterTokenizer()
    spans = split_spans(text, tokenizer, max_tokens=32)
    assert len(spans) > 1 and spans[0]["start"] == 0 and spans[-1]["end"] == len(text)
    assert all(a["end"] == b["start"] for a, b in zip(spans, spans[1:]))
    assert "".join(text[s["start"]:s["end"]] for s in spans) == text
    assert all(tokenizer.count(text[s["start"]:s["end"]]) == s["embedding_input_tokens"] <= 32 for s in spans)


def test_invalid_budgets_and_empty_text_are_explicit():
    assert split_spans(" \n", CharacterTokenizer()) == []
    for budget in (True, 10, 513):
        with pytest.raises(ValueError, match="budget"):
            split_spans("架空。", CharacterTokenizer(), max_tokens=budget)
    with pytest.raises(ValueError, match="text"):
        split_spans({"question": "秘密"}, CharacterTokenizer())


def article(text):
    return {"status": "ok", "page_id": 1, "revision_id": 2,
            "canonical_title": "架空の記事", "text": text,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "text_version": "synthetic-article-v1", "revision_timestamp_utc": "2023-12-01T00:00:00Z",
            "source_url": "https://ja.wikipedia.org/w/index.php?oldid=2"}


def test_passage_ids_include_actual_rendered_body_and_preserve_numeric_citation_grammar():
    source = article("架空の本文です。" * 10)
    rows = article_passages(source, CharacterTokenizer(), max_tokens=32)
    assert article_passages(source, CharacterTokenizer(), max_tokens=32) == rows
    assert "".join(r["text"] for r in rows) == source["text"]
    assert len({r["passage_id"] for r in rows}) == len(rows)
    for row in rows:
        assert row["wikipedia_page_id"] == 1 and row["wikipedia_revision_id"] == 2
        assert row["text_sha256"] == hashlib.sha256(row["text"].encode()).hexdigest()
        units = extract_sentence_units(f"[{row['passage_id']}] 架空の説明です。", language="ja")
        assert units["normalized_prose"] == "架空の説明です。"
    changed = article("別の描画本文です。" * 10)
    new_ids = {r["passage_id"] for r in article_passages(changed, CharacterTokenizer(), max_tokens=32)}
    assert not new_ids.intersection(r["passage_id"] for r in rows)
    source["text"] += "改変"
    with pytest.raises(ValueError, match="body hash"):
        article_passages(source, CharacterTokenizer(), max_tokens=32)
