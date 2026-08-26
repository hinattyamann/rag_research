"""Tests for the CLAPNQ Retrieval Corpus Loader and Document schema."""

import hashlib
import json
import re
import zipfile
from pathlib import Path

import pytest

from rag_research.data.clapnq_corpus import (
    CorpusValidationError,
    InternalRetrievalDocument,
    iter_clapnq_corpus,
    iter_corpus_file,
    serialize_retrieval_document,
    write_corpus_jsonl,
)
from rag_research.data.clapnq_records import load_clapnq_qa_records
from rag_research.data.clapnq_source import (
    CLAPNQ_CORPUS_PASSAGE_COUNT,
    CLAPNQ_REVISION,
    SourceFileRole,
    SourceFileSpec,
)

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def _spec(expected_count: int = 2) -> SourceFileSpec:
    return SourceFileSpec(
        "retrieval/passages.tsv.zip",
        SourceFileRole.RETRIEVAL_CORPUS,
        expected_record_count=expected_count,
    )


def _write_corpus_zip(root: Path, content: str, *, entry: str = "passages.tsv") -> None:
    path = root / "retrieval/passages.tsv.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(entry, content)


def _document(passage_id: str, *, title: str = "Fixture title") -> InternalRetrievalDocument:
    text = f"Text for {passage_id}."
    return InternalRetrievalDocument(
        passage_id=passage_id,
        source_dataset="CLAPNQ",
        source_revision=CLAPNQ_REVISION,
        title=title,
        text=text,
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def test_iter_corpus_file_normalizes_document_and_multiline_text(tmp_path: Path) -> None:
    _write_corpus_zip(
        tmp_path,
        'id\ttext\ttitle\npassage-1\t"line 1\nline 2"\tTitle 1\n'
        "passage-2\tSecond text.\tTitle 2\n",
    )

    documents = list(iter_corpus_file(tmp_path, _spec()))

    assert [document.passage_id for document in documents] == ["passage-1", "passage-2"]
    assert documents[0].text == "line 1\nline 2"
    assert documents[0].title == "Title 1"
    assert documents[0].text_sha256 == hashlib.sha256(
        b"line 1\nline 2"
    ).hexdigest()
    assert json.loads(serialize_retrieval_document(documents[0])) == documents[0].to_dict()


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("wrong\ttext\ttitle\np1\tText.\tTitle\n", "schema mismatch"),
        ("id\ttext\ttitle\np1\tText.\tTitle\np1\tOther.\tTitle\n", "Duplicate"),
        ("id\ttext\ttitle\np1\t\tTitle\np2\tText.\tTitle\n", "Blank passage text"),
    ],
)
def test_iter_corpus_file_rejects_invalid_source(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    _write_corpus_zip(tmp_path, content)

    with pytest.raises(CorpusValidationError, match=message):
        list(iter_corpus_file(tmp_path, _spec()))


def test_iter_corpus_file_enforces_archive_entry_and_record_count(tmp_path: Path) -> None:
    _write_corpus_zip(
        tmp_path,
        "id\ttext\ttitle\np1\tText.\tTitle\n",
        entry="unexpected.tsv",
    )
    with pytest.raises(CorpusValidationError, match="Unexpected Corpus ZIP entries"):
        list(iter_corpus_file(tmp_path, _spec(expected_count=1)))

    _write_corpus_zip(
        tmp_path,
        "id\ttext\ttitle\np1\tText.\tTitle\n",
    )
    with pytest.raises(CorpusValidationError, match="Record count mismatch"):
        list(iter_corpus_file(tmp_path, _spec(expected_count=2)))


def test_write_corpus_jsonl_is_deterministic_and_verifies_gold_ids(
    tmp_path: Path,
) -> None:
    documents = [_document("p1"), _document("p2", title="Other title")]
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"

    first = write_corpus_jsonl(
        documents,
        first_path,
        expected_gold_passage_ids={"p1"},
    )
    second = write_corpus_jsonl(
        documents,
        second_path,
        expected_gold_passage_ids={"p1"},
    )

    assert first_path.read_bytes() == second_path.read_bytes()
    assert first.sha256 == second.sha256
    assert first.record_count == 2
    assert first.unique_title_count == 2
    assert first.verified_gold_passage_id_count == 1

    missing_path = tmp_path / "missing.jsonl"
    with pytest.raises(CorpusValidationError, match="Gold Passage IDs missing"):
        write_corpus_jsonl(
            documents,
            missing_path,
            expected_gold_passage_ids={"missing"},
        )
    assert not missing_path.exists()


_PUBLIC_CHECKOUT = Path("data/raw/clapnq") / CLAPNQ_REVISION


@pytest.mark.skipif(not _PUBLIC_CHECKOUT.is_dir(), reason="CLAPNQ Raw Data is not prepared")
def test_public_corpus_matches_internal_document_audit() -> None:
    """All fixed passages load once and resolve every public Gold Passage ID."""
    gold_passage_ids = {
        gold_id
        for record in load_clapnq_qa_records(_PUBLIC_CHECKOUT)
        for gold_id in record.gold_passage_ids
    }
    observed_gold_ids: set[str] = set()
    titles: set[str] = set()
    record_count = 0

    for document in iter_clapnq_corpus(_PUBLIC_CHECKOUT):
        record_count += 1
        titles.add(document.title)
        if document.passage_id in gold_passage_ids:
            observed_gold_ids.add(document.passage_id)
        assert _SHA256_PATTERN.fullmatch(document.text_sha256)

    assert record_count == CLAPNQ_CORPUS_PASSAGE_COUNT
    assert len(titles) == 4_293
    assert len(gold_passage_ids) == 2_074
    assert observed_gold_ids == gold_passage_ids
