"""Tests for CLAPNQ Retrieval Query loading and Annotation linkage."""

from collections import Counter
from pathlib import Path

import pytest

from rag_research.data.clapnq_annotations import LoadedAnnotationRecord
from rag_research.data.clapnq_queries import (
    LoadedRetrievalQuery,
    QueryValidationError,
    link_annotations_to_queries,
    load_and_link_clapnq,
    load_query_file,
)
from rag_research.data.clapnq_source import (
    CLAPNQ_REVISION,
    SourceFileRole,
    SourceFileSpec,
)


def _query_spec(*, answerable: bool = True, expected_count: int = 1) -> SourceFileSpec:
    label = "answerable" if answerable else "unanswerable"
    return SourceFileSpec(
        f"retrieval/train/question_train_{label}.tsv",
        SourceFileRole.RETRIEVAL_QUERY,
        expected_record_count=expected_count,
        source_split="train",
        is_answerable=answerable,
    )


def _annotation(source_id: str, question: str) -> LoadedAnnotationRecord:
    return LoadedAnnotationRecord(
        source_dataset="CLAPNQ",
        source_revision=CLAPNQ_REVISION,
        source_split="train",
        source_line_index=0,
        source_record_sha256="a" * 64,
        source_id=source_id,
        source_title="Fixture title",
        question=question,
        is_answerable=True,
        references=[],
        raw_record={},
    )


def _query(source_id: str, question: str, gold_id: str) -> LoadedRetrievalQuery:
    return LoadedRetrievalQuery(
        source_dataset="CLAPNQ",
        source_revision=CLAPNQ_REVISION,
        source_split="train",
        source_line_index=0,
        source_id=source_id,
        question=question,
        is_answerable=True,
        gold_passage_ids=[gold_id],
        raw_row={},
    )


def test_load_query_file_normalizes_gold_id_and_multiline_answer(tmp_path: Path) -> None:
    """An Answerable logical TSV row may span physical lines in its quoted answer."""
    spec = _query_spec()
    path = tmp_path / spec.relative_path
    path.parent.mkdir(parents=True)
    path.write_bytes(
        b"id\tquestion\tdoc-id-list\tanswers\n"
        b'source-1\tfixture question\tpassage-1\t"answer line 1\nanswer line 2"\n'
    )

    queries = load_query_file(tmp_path, spec)

    assert len(queries) == 1
    query = queries[0]
    assert query.source_line_index == 0
    assert query.source_id == "source-1"
    assert query.question == "fixture question"
    assert query.gold_passage_ids == ["passage-1"]
    assert query.raw_row == {
        "id": "source-1",
        "question": "fixture question",
        "doc-id-list": "passage-1",
        "answers": "answer line 1\nanswer line 2",
    }


def test_load_query_file_normalizes_unanswerable_gold_ids_to_empty(tmp_path: Path) -> None:
    """An Unanswerable TSV row must have no Gold Passage ID."""
    spec = _query_spec(answerable=False)
    path = tmp_path / spec.relative_path
    path.parent.mkdir(parents=True)
    path.write_text(
        "id\tquestion\tdoc-id-list\tanswers\n"
        "source-1\tfixture question\t\t\n",
        encoding="utf-8",
    )

    queries = load_query_file(tmp_path, spec)

    assert queries[0].gold_passage_ids == []


@pytest.mark.parametrize(
    ("answerable", "gold_value", "message"),
    [
        (True, "", "no Gold Passage ID"),
        (True, "passage-1 passage-2", "exactly one"),
        (False, "passage-1", "has a Gold Passage ID"),
    ],
)
def test_load_query_file_rejects_invalid_gold_presence(
    tmp_path: Path,
    answerable: bool,
    gold_value: str,
    message: str,
) -> None:
    """Gold IDs must match the Answerability role fixed by the source partition."""
    spec = _query_spec(answerable=answerable)
    path = tmp_path / spec.relative_path
    path.parent.mkdir(parents=True)
    path.write_text(
        "id\tquestion\tdoc-id-list\tanswers\n"
        f"source-1\tfixture question\t{gold_value}\tfixture answer\n",
        encoding="utf-8",
    )

    with pytest.raises(QueryValidationError, match=message):
        load_query_file(tmp_path, spec)


def test_link_annotations_to_queries_is_one_to_one_and_preserves_order() -> None:
    """The exact composite key links each Annotation while retaining Annotation order."""
    annotations = [
        _annotation("source-2", "question 2"),
        _annotation("source-1", "question 1"),
    ]
    queries = [
        _query("source-1", "question 1", "passage-1"),
        _query("source-2", "question 2", "passage-2"),
    ]

    pairs = link_annotations_to_queries(annotations, queries)

    assert [pair.annotation.source_id for pair in pairs] == ["source-2", "source-1"]
    assert [pair.gold_passage_ids for pair in pairs] == [
        ["passage-2"],
        ["passage-1"],
    ]


def test_link_annotations_to_queries_rejects_question_mismatch() -> None:
    """Matching IDs cannot hide a changed or incorrectly paired question."""
    annotations = [_annotation("source-1", "annotation question")]
    queries = [_query("source-1", "different question", "passage-1")]

    with pytest.raises(QueryValidationError, match="Question mismatch"):
        link_annotations_to_queries(annotations, queries)


def test_link_annotations_to_queries_rejects_missing_or_extra_rows() -> None:
    """Neither side of the intended one-to-one mapping may be absent."""
    with pytest.raises(QueryValidationError, match="no matching Retrieval Query"):
        link_annotations_to_queries([_annotation("source-1", "question")], [])

    with pytest.raises(QueryValidationError, match="no matching Annotation"):
        link_annotations_to_queries([], [_query("source-1", "question", "passage-1")])


_PUBLIC_CHECKOUT = Path("data/raw/clapnq") / CLAPNQ_REVISION


@pytest.mark.skipif(not _PUBLIC_CHECKOUT.is_dir(), reason="CLAPNQ Raw Data is not prepared")
def test_public_annotations_and_queries_have_exact_gold_mapping() -> None:
    """All 4,345 fixed public records form exact one-to-one pairs with expected Gold IDs."""
    pairs = load_and_link_clapnq(_PUBLIC_CHECKOUT)
    partitions = Counter(
        (pair.annotation.source_split, pair.annotation.is_answerable) for pair in pairs
    )
    answerable_pairs = [pair for pair in pairs if pair.annotation.is_answerable]
    unanswerable_pairs = [pair for pair in pairs if not pair.annotation.is_answerable]
    unique_gold_ids = {
        gold_id for pair in answerable_pairs for gold_id in pair.gold_passage_ids
    }

    assert len(pairs) == 4_345
    assert partitions == {
        ("train", True): 1_954,
        ("train", False): 1_791,
        ("dev", True): 300,
        ("dev", False): 300,
    }
    assert len(answerable_pairs) == 2_254
    assert all(len(pair.gold_passage_ids) == 1 for pair in answerable_pairs)
    assert len(unanswerable_pairs) == 2_091
    assert all(pair.gold_passage_ids == [] for pair in unanswerable_pairs)
    assert len(unique_gold_ids) == 2_074
