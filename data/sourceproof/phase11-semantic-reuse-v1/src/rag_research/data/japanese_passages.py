"""Contiguous, token-bounded source passages; no QA/reference data is accepted."""

import bisect
import hashlib
import re

from rag_research.data.baobab_source import DATASET_ID, REVISION
from rag_research.experiments.frozen_trace import digest, require

VERSION = "e5-token-bounded-contiguous-char-spans-v1"


def split_spans(text, tokenizer, *, max_tokens=512):
    """Cover original characters exactly, preferring sentence/paragraph boundaries."""
    require(isinstance(text, str), "Passage source must be text")
    require(type(max_tokens) is int and 32 <= max_tokens <= 512, "Invalid passage token budget")
    if not text.strip():
        return []
    encoding = tokenizer.raw.encode(text, add_special_tokens=False)
    ends = [end for _, end in encoding.offsets]
    require(ends == sorted(ends) and all(0 <= end <= len(text) for end in ends),
            "Tokenizer source offsets are invalid")
    spans, start = [], 0
    while start < len(text):
        token_start = bisect.bisect_right(ends, start)
        token_end = min(token_start + max_tokens - 16, len(ends))
        end = len(text) if token_end == len(ends) else ends[token_end - 1]
        require(end > start, "Tokenizer cannot advance a source passage")
        # The prefix and specials are counted on the actual substring, never guessed.
        while end > start and tokenizer.count(text[start:end]) > max_tokens:
            end -= 1
        require(end > start, "One source character exceeds the passage token budget")
        if end < len(text):
            boundaries = [match.end() for match in re.finditer(r"[。！？!?\n]|\.(?=\s)", text[start:end])
                          if match.end() >= (end - start) // 2]
            if boundaries:
                candidate = start + boundaries[-1]
                if text[start:candidate].strip() and tokenizer.count(text[start:candidate]) <= max_tokens:
                    end = candidate
        if not text[end:].strip():
            require(tokenizer.count(text[start:]) <= max_tokens,
                    "Trailing source whitespace exceeds budget; no text discarded")
            end = len(text)
        tokens = tokenizer.count(text[start:end])
        spans.append({"start": start, "end": end, "embedding_input_tokens": tokens})
        start = end
    require("".join(text[s["start"]:s["end"]] for s in spans) == text,
            "Source passage spans lose or duplicate text")
    return spans


def article_passages(article, tokenizer, *, max_tokens=512):
    """Preserve numeric citation grammar with a source-derived 96-bit document ID."""
    require(article.get("status") == "ok" and
            type(article.get("page_id")) is int and article["page_id"] > 0 and
            type(article.get("revision_id")) is int and article["revision_id"] > 0,
            "Passages require a verified historical article identity")
    text = article["text"]
    require(hashlib.sha256(text.encode()).hexdigest() == article["text_sha256"], "Article body hash differs")
    identity = ["ja.wikipedia.org", article["page_id"], article["revision_id"], article["text_version"],
                article["text_sha256"]]
    parent = str(int(digest(identity)[:24], 16))
    result = []
    for span in split_spans(text, tokenizer, max_tokens=max_tokens):
        passage = text[span["start"]:span["end"]]
        result.append({"passage_id": f"{parent}_{span['start']}-{span['end']}",
                       "source_dataset": DATASET_ID, "source_revision": REVISION, "language": "ja",
                       "title": article["canonical_title"], "text": passage,
                       "text_sha256": hashlib.sha256(passage.encode()).hexdigest(),
                       "wikipedia_page_id": article["page_id"], "wikipedia_revision_id": article["revision_id"],
                       "wikipedia_revision_timestamp_utc": article["revision_timestamp_utc"],
                       "source_url": article["source_url"], "article_text_sha256": article["text_sha256"],
                       "passage_version": VERSION, "source_char_span": span,
                       "embedding_token_budget": max_tokens})
    require(bool(result), "Historical article produced no passages")
    return result
