"""Check displayed case excerpts against the retained actual evidence and answers."""

import hashlib
import json
from pathlib import Path

PAPER = Path(__file__).resolve().parent.parent


def test_case_quotes_are_exact_saved_input_slices():
    record = json.loads((PAPER / "notes/case_excerpts_v1.json").read_text(encoding="utf-8"))
    path = PAPER / "materials/fixed_v23_v1" / record["source_input"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["source_input_sha256"]
    source = json.loads(path.read_text(encoding="utf-8"))
    assert source["qa_key"] == record["qa_key"]
    assert {q["role"] for q in record["quotes"]} == {"evidence", "A", "B"}
    for quote in record["quotes"]:
        value = source
        for field in quote["field_path"]:
            value = value[field]
        assert value[quote["start"] : quote["stop"]] == quote["original_ja"]
        assert quote["translation_en"]


def test_saved_mismatched_citation_is_retained():
    record = json.loads((PAPER / "notes/case_excerpts_v1.json").read_text(encoding="utf-8"))
    source = json.loads(
        (PAPER / "materials/fixed_v23_v1" / record["source_input"]).read_text(encoding="utf-8")
    )
    phrase = next(q["original_ja"] for q in record["quotes"] if q["role"] == "B")
    support, cited = source["used_documents"][0], source["used_documents"][4]
    assert phrase in support["text"] and phrase not in cited["text"]
    cited_id = cited["passage_id"]
    assert f"[{cited_id}]" in source["B"]["answer"]
    assert source["B"]["quality"]["y"] == 1
