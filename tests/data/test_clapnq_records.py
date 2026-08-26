"""Tests for CLAPNQ Stable IDs and final internal QA records."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from rag_research.data.clapnq_annotations import (
    LoadedAnnotationRecord,
    NormalizedReference,
)
from rag_research.data.clapnq_queries import (
    AnnotationQueryPair,
    LoadedRetrievalQuery,
)
from rag_research.data.clapnq_records import (
    QARecordValidationError,
    build_stable_record_id,
    convert_pair_to_qa_record,
    convert_pairs_to_qa_records,
    load_clapnq_qa_records,
    serialize_qa_record,
    write_qa_records_jsonl,
)
from rag_research.data.clapnq_source import CLAPNQ_REVISION


def _pair(*, answerable: bool = True, source_id: str = "source-1") -> AnnotationQueryPair:
    references = (
        [
            NormalizedReference(
                output_index=0,
                answer="fixture answer",
                selected_sentences=["Fixture evidence."],
            )
        ]
        if answerable
        else []
    )
    raw_record = {
        "id": source_id,
        "input": "fixture question",
        "passages": [
            {
                "title": "Fixture title",
                "text": "Fixture passage text.",
                "sentences": ["Fixture passage text."],
            }
        ],
        "output": [],
    }
    annotation = LoadedAnnotationRecord(
        source_dataset="CLAPNQ",
        source_revision=CLAPNQ_REVISION,
        source_split="train",
        source_line_index=3,
        source_record_sha256="a" * 64,
        source_id=source_id,
        source_title="Fixture title",
        question="fixture question",
        is_answerable=answerable,
        references=references,
        raw_record=raw_record,
    )
    query = LoadedRetrievalQuery(
        source_dataset="CLAPNQ",
        source_revision=CLAPNQ_REVISION,
        source_split="train",
        source_line_index=3,
        source_id=source_id,
        question="fixture question",
        is_answerable=answerable,
        gold_passage_ids=["passage-1"] if answerable else [],
        raw_row={},
    )
    return AnnotationQueryPair(annotation=annotation, retrieval_query=query)


def test_build_stable_record_id_uses_source_identity_not_research_split() -> None:
    record_id = build_stable_record_id(
        source_revision=CLAPNQ_REVISION,
        source_split="train",
        source_id="8045984229282682032",
        is_answerable=True,
    )

    assert record_id == "clapnq:c508d78:train:8045984229282682032:answerable"


def test_convert_answerable_pair_separates_gold_and_provided_passages() -> None:
    record = convert_pair_to_qa_record(_pair(answerable=True))

    assert record.record_id == "clapnq:c508d78:train:source-1:answerable"
    assert record.research_split is None
    assert record.reference_answers == ["fixture answer"]
    assert record.selected_sentences_by_reference == [["Fixture evidence."]]
    assert record.gold_passage_ids == ["passage-1"]
    assert record.provided_passage is None
    assert record.dataset_type == "normal"
    assert record.derived_from_id is None
    assert record.derivation is None


def test_convert_unanswerable_pair_preserves_random_provided_passage() -> None:
    record = convert_pair_to_qa_record(_pair(answerable=False))

    assert record.record_id == "clapnq:c508d78:train:source-1:unanswerable"
    assert record.reference_answers == []
    assert record.selected_sentences_by_reference == []
    assert record.gold_passage_ids == []
    assert record.provided_passage is not None
    assert record.provided_passage.title == "Fixture title"
    assert record.provided_passage.text == "Fixture passage text."
    assert record.provided_passage.sentences == ["Fixture passage text."]
    assert record.dataset_type == "unanswerable"


def test_convert_pair_rejects_provenance_mismatch_and_duplicate_stable_id() -> None:
    mismatched = _pair()
    mismatched.retrieval_query.source_revision = "b" * 40
    with pytest.raises(QARecordValidationError, match="source_revision"):
        convert_pair_to_qa_record(mismatched)

    duplicate = _pair()
    with pytest.raises(QARecordValidationError, match="Duplicate Stable ID"):
        convert_pairs_to_qa_records([duplicate, duplicate])


def test_serialization_and_jsonl_output_are_deterministic(tmp_path: Path) -> None:
    records = convert_pairs_to_qa_records(
        [_pair(answerable=True), _pair(answerable=False, source_id="source-2")]
    )
    first_serialization = serialize_qa_record(records[0])
    assert first_serialization == serialize_qa_record(records[0])
    assert json.loads(first_serialization)["source_record_sha256"] == "a" * 64

    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"
    first = write_qa_records_jsonl(records, first_path)
    second = write_qa_records_jsonl(records, second_path)

    assert first_path.read_bytes() == second_path.read_bytes()
    assert first.sha256 == second.sha256
    assert first.sha256 == hashlib.sha256(first_path.read_bytes()).hexdigest()
    assert first.record_count == 2


_PUBLIC_CHECKOUT = Path("data/raw/clapnq") / CLAPNQ_REVISION


@pytest.mark.skipif(not _PUBLIC_CHECKOUT.is_dir(), reason="CLAPNQ Raw Data is not prepared")
def test_public_records_match_final_schema_audit() -> None:
    """All 4,345 public QA records have unique IDs and correctly separated roles."""
    records = load_clapnq_qa_records(_PUBLIC_CHECKOUT)
    partitions = Counter((record.source_split, record.is_answerable) for record in records)
    dataset_types = Counter(record.dataset_type for record in records)
    record_ids = {record.record_id for record in records}

    assert len(records) == 4_345
    assert len(record_ids) == 4_345
    assert partitions == {
        ("train", True): 1_954,
        ("train", False): 1_791,
        ("dev", True): 300,
        ("dev", False): 300,
    }
    assert dataset_types == {"normal": 2_254, "unanswerable": 2_091}
    assert sum(len(record.reference_answers) for record in records) == 3_142
    assert all(record.research_split is None for record in records)
    assert all(record.derived_from_id is None for record in records)
    assert all(record.derivation is None for record in records)
    assert all(
        len(record.gold_passage_ids) == 1 and record.provided_passage is None
        for record in records
        if record.is_answerable
    )
    assert all(
        record.gold_passage_ids == [] and record.provided_passage is not None
        for record in records
        if not record.is_answerable
    )
    assert all(_SHA256_PATTERN.fullmatch(record.source_record_sha256) for record in records)


_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
