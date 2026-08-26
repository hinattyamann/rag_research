"""Tests for CLAPNQ annotation loading and reference normalization."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from rag_research.data.clapnq_annotations import (
    AnnotationValidationError,
    load_annotation_file,
    load_clapnq_annotations,
    normalize_references,
)
from rag_research.data.clapnq_source import (
    CLAPNQ_REVISION,
    SourceFileRole,
    SourceFileSpec,
)


def _output(
    answer: str | None,
    *,
    skip: bool = False,
    selected_sentences: list[str] | None = None,
) -> dict[str, object]:
    return {
        "answer": answer,
        "selected_sentences": selected_sentences or [],
        "meta": {"skip": skip},
    }


def _record(outputs: list[dict[str, object]]) -> dict[str, object]:
    return {
        "id": "source-1",
        "input": "fixture question",
        "passages": [
            {
                "title": "Fixture title",
                "text": "Fixture passage text.",
                "sentences": ["Fixture passage text."],
            }
        ],
        "output": outputs,
    }


def _annotation_spec(expected_record_count: int = 1) -> SourceFileSpec:
    return SourceFileSpec(
        "annotated_data/train/fixture.jsonl",
        SourceFileRole.ANNOTATION,
        expected_record_count=expected_record_count,
        source_split="train",
        is_answerable=True,
    )


def test_normalize_references_filters_invalid_and_preserves_pairing() -> None:
    """Valid duplicate answers retain source order, evidence, and output positions."""
    outputs = [
        _output("valid answer", selected_sentences=["evidence 1"]),
        _output("skipped answer", skip=True, selected_sentences=["ignored"]),
        _output(None),
        _output("   "),
        _output("nA"),
        _output("valid answer", selected_sentences=[]),
    ]

    references = normalize_references(
        outputs,
        is_answerable=True,
        location="fixture:1",
    )

    assert [reference.output_index for reference in references] == [0, 5]
    assert [reference.answer for reference in references] == [
        "valid answer",
        "valid answer",
    ]
    assert [reference.selected_sentences for reference in references] == [
        ["evidence 1"],
        [],
    ]


def test_normalize_references_enforces_answerability() -> None:
    """Answerable records need a valid answer and Unanswerable records must have none."""
    with pytest.raises(AnnotationValidationError, match="no valid reference"):
        normalize_references(
            [_output("")],
            is_answerable=True,
            location="answerable:1",
        )

    with pytest.raises(AnnotationValidationError, match="unexpectedly has a valid"):
        normalize_references(
            [_output("unexpected answer")],
            is_answerable=False,
            location="unanswerable:1",
        )


def test_load_annotation_file_preserves_raw_record_and_hash(tmp_path: Path) -> None:
    """Loaded fields and SHA-256 trace back to exact JSON bytes without the line ending."""
    spec = _annotation_spec()
    path = tmp_path / spec.relative_path
    path.parent.mkdir(parents=True)
    raw_record = _record([_output("answer", selected_sentences=["evidence"])])
    raw_record_bytes = json.dumps(raw_record, ensure_ascii=False).encode("utf-8")
    path.write_bytes(raw_record_bytes + b"\n")

    records = load_annotation_file(tmp_path, spec)

    assert len(records) == 1
    loaded = records[0]
    assert loaded.source_dataset == "CLAPNQ"
    assert loaded.source_revision == CLAPNQ_REVISION
    assert loaded.source_split == "train"
    assert loaded.source_line_index == 0
    assert loaded.source_record_sha256 == hashlib.sha256(raw_record_bytes).hexdigest()
    assert loaded.source_id == "source-1"
    assert loaded.source_title == "Fixture title"
    assert loaded.question == "fixture question"
    assert loaded.reference_answers == ["answer"]
    assert loaded.selected_sentences_by_reference == [["evidence"]]
    assert loaded.raw_record == raw_record


def test_load_annotation_file_rejects_invalid_selected_sentences(tmp_path: Path) -> None:
    """Evidence must remain a list so answer-to-evidence pairing is unambiguous."""
    spec = _annotation_spec()
    path = tmp_path / spec.relative_path
    path.parent.mkdir(parents=True)
    raw_record = _record([_output("answer")])
    output = raw_record["output"]
    assert isinstance(output, list)
    output[0]["selected_sentences"] = "not-a-list"
    path.write_text(json.dumps(raw_record) + "\n", encoding="utf-8")

    with pytest.raises(AnnotationValidationError, match="selected_sentences"):
        load_annotation_file(tmp_path, spec)


def test_load_annotation_file_enforces_expected_count(tmp_path: Path) -> None:
    """A truncated final-round file cannot silently become research input."""
    spec = _annotation_spec(expected_record_count=2)
    path = tmp_path / spec.relative_path
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_record([_output("answer")])) + "\n", encoding="utf-8")

    with pytest.raises(AnnotationValidationError, match="Record count mismatch"):
        load_annotation_file(tmp_path, spec)


_PUBLIC_CHECKOUT = Path("data/raw/clapnq") / CLAPNQ_REVISION


@pytest.mark.skipif(not _PUBLIC_CHECKOUT.is_dir(), reason="CLAPNQ Raw Data is not prepared")
def test_public_annotations_match_fixed_revision_audit() -> None:
    """The fixed public checkout matches documented partitions and reference counts."""
    records = load_clapnq_annotations(_PUBLIC_CHECKOUT)
    partitions = Counter((record.source_split, record.is_answerable) for record in records)
    references = Counter()
    empty_selected = 0
    duplicate_answers = 0

    for record in records:
        references[(record.source_split, record.is_answerable)] += len(record.references)
        empty_selected += sum(
            not reference.selected_sentences for reference in record.references
        )
        answers = record.reference_answers
        duplicate_answers += len(answers) - len(set(answers))
        if record.is_answerable:
            assert record.references
        else:
            assert record.references == []

    assert len(records) == 4_345
    assert partitions == {
        ("train", True): 1_954,
        ("train", False): 1_791,
        ("dev", True): 300,
        ("dev", False): 300,
    }
    assert references == {
        ("train", True): 2_667,
        ("train", False): 0,
        ("dev", True): 475,
        ("dev", False): 0,
    }
    assert max(len(record.references) for record in records) == 7
    assert empty_selected == 2
    assert duplicate_answers == 2
