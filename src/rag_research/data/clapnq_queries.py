"""Load CLAPNQ Retrieval Query TSV files and link them to annotations."""

import csv
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from rag_research.data.clapnq_acquisition import verify_source_checkout
from rag_research.data.clapnq_annotations import (
    LoadedAnnotationRecord,
    load_clapnq_annotations,
)
from rag_research.data.clapnq_source import (
    CLAPNQ_REVISION,
    CLAPNQ_SOURCE_FILES,
    SourceFileRole,
    SourceFileSpec,
)

_QUERY_COLUMNS = ("id", "question", "doc-id-list", "answers")


class QueryValidationError(ValueError):
    """Raised when Retrieval Query data or Annotation linkage is invalid."""


@dataclass(slots=True)
class LoadedRetrievalQuery:
    """One Retrieval Query row with source provenance and normalized Gold IDs."""

    source_dataset: str
    source_revision: str
    source_split: str
    source_line_index: int
    source_id: str
    question: str
    is_answerable: bool
    gold_passage_ids: list[str]
    raw_row: dict[str, str]


@dataclass(slots=True)
class AnnotationQueryPair:
    """One exact Annotation-to-Retrieval-Query match."""

    annotation: LoadedAnnotationRecord
    retrieval_query: LoadedRetrievalQuery

    @property
    def gold_passage_ids(self) -> list[str]:
        """Return a copy of the evaluation-only Gold Passage IDs."""
        return list(self.retrieval_query.gold_passage_ids)


def _require_nonblank(value: str, *, field: str, location: str) -> str:
    if not value.strip():
        raise QueryValidationError(f"Blank {field} at {location}")
    return value


def _normalize_gold_passage_ids(
    raw_value: str,
    *,
    is_answerable: bool,
    location: str,
) -> list[str]:
    value = raw_value.strip()
    if is_answerable:
        if not value:
            raise QueryValidationError(
                f"Answerable query has no Gold Passage ID at {location}"
            )
        if any(character.isspace() for character in value) or "," in value:
            raise QueryValidationError(
                f"Expected exactly one Gold Passage ID at {location}: {value}"
            )
        return [value]
    if value:
        raise QueryValidationError(
            f"Unanswerable query has a Gold Passage ID at {location}: {value}"
        )
    return []


def _parse_query_row(
    raw_row: dict[str, str],
    *,
    spec: SourceFileSpec,
    revision: str,
    line_index: int,
    physical_line_number: int,
) -> LoadedRetrievalQuery:
    location = (
        f"{spec.relative_path} logical row {line_index + 1} "
        f"ending at physical line {physical_line_number}"
    )

    if spec.source_split is None or spec.is_answerable is None:
        raise QueryValidationError(
            f"Retrieval Query SourceFileSpec lacks split or answerability: {spec.relative_path}"
        )
    source_id = _require_nonblank(raw_row["id"], field="query id", location=location)
    question = _require_nonblank(
        raw_row["question"], field="query question", location=location
    )
    gold_passage_ids = _normalize_gold_passage_ids(
        raw_row["doc-id-list"],
        is_answerable=spec.is_answerable,
        location=location,
    )

    return LoadedRetrievalQuery(
        source_dataset="CLAPNQ",
        source_revision=revision,
        source_split=spec.source_split,
        source_line_index=line_index,
        source_id=source_id,
        question=question,
        is_answerable=spec.is_answerable,
        gold_passage_ids=gold_passage_ids,
        raw_row=raw_row,
    )


def load_query_file(
    checkout_path: Path,
    spec: SourceFileSpec,
    *,
    revision: str = CLAPNQ_REVISION,
) -> list[LoadedRetrievalQuery]:
    """Load and validate one public CLAPNQ Retrieval Query TSV file."""
    if spec.role is not SourceFileRole.RETRIEVAL_QUERY:
        raise ValueError(f"SourceFileSpec is not a Retrieval Query: {spec.relative_path}")
    path = checkout_path.joinpath(*PurePosixPath(spec.relative_path).parts)
    queries: list[LoadedRetrievalQuery] = []
    source_ids: set[str] = set()

    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t", restkey="__extra_columns__")
        if tuple(reader.fieldnames or ()) != _QUERY_COLUMNS:
            raise QueryValidationError(
                f"TSV schema mismatch for {spec.relative_path}: "
                f"expected {list(_QUERY_COLUMNS)}, found {reader.fieldnames}"
            )
        try:
            rows = enumerate(reader)
            for line_index, parsed_row in rows:
                if "__extra_columns__" in parsed_row or any(
                    parsed_row.get(column) is None for column in _QUERY_COLUMNS
                ):
                    raise QueryValidationError(
                        f"TSV column count mismatch for {spec.relative_path} "
                        f"at logical row {line_index + 1}"
                    )
                raw_row = {column: parsed_row[column] for column in _QUERY_COLUMNS}
                if not any(raw_row.values()):
                    raise QueryValidationError(
                        f"Blank TSV row for {spec.relative_path} at logical row {line_index + 1}"
                    )
                query = _parse_query_row(
                    raw_row,
                    spec=spec,
                    revision=revision,
                    line_index=line_index,
                    physical_line_number=reader.line_num,
                )
                if query.source_id in source_ids:
                    raise QueryValidationError(
                        f"Duplicate query id in {spec.relative_path}: {query.source_id}"
                    )
                source_ids.add(query.source_id)
                queries.append(query)
        except csv.Error as error:
            raise QueryValidationError(
                f"Invalid TSV in {spec.relative_path} near physical line {reader.line_num}: {error}"
            ) from error

    if spec.expected_record_count is not None and len(queries) != spec.expected_record_count:
        raise QueryValidationError(
            f"Record count mismatch for {spec.relative_path}: "
            f"expected {spec.expected_record_count}, found {len(queries)}"
        )
    return queries


def load_clapnq_queries(
    checkout_path: Path,
    *,
    revision: str = CLAPNQ_REVISION,
    source_files: tuple[SourceFileSpec, ...] = CLAPNQ_SOURCE_FILES,
) -> list[LoadedRetrievalQuery]:
    """Load all four public CLAPNQ Retrieval Query partitions."""
    query_specs = tuple(
        spec for spec in source_files if spec.role is SourceFileRole.RETRIEVAL_QUERY
    )
    if not query_specs:
        raise QueryValidationError("No Retrieval Query SourceFileSpec was provided")
    verify_source_checkout(checkout_path, revision, query_specs)

    queries: list[LoadedRetrievalQuery] = []
    for spec in query_specs:
        queries.extend(load_query_file(checkout_path, spec, revision=revision))
    return queries


def _link_key(
    source_split: str,
    is_answerable: bool,
    source_id: str,
) -> tuple[str, bool, str]:
    return source_split, is_answerable, source_id


def link_annotations_to_queries(
    annotations: list[LoadedAnnotationRecord],
    queries: list[LoadedRetrievalQuery],
) -> list[AnnotationQueryPair]:
    """Join every Annotation to exactly one Query while preserving Annotation order."""
    queries_by_key: dict[tuple[str, bool, str], LoadedRetrievalQuery] = {}
    for query in queries:
        key = _link_key(query.source_split, query.is_answerable, query.source_id)
        if key in queries_by_key:
            raise QueryValidationError(f"Duplicate Retrieval Query link key: {key}")
        queries_by_key[key] = query

    annotation_keys: set[tuple[str, bool, str]] = set()
    pairs: list[AnnotationQueryPair] = []
    for annotation in annotations:
        key = _link_key(
            annotation.source_split,
            annotation.is_answerable,
            annotation.source_id,
        )
        if key in annotation_keys:
            raise QueryValidationError(f"Duplicate Annotation link key: {key}")
        annotation_keys.add(key)
        query = queries_by_key.get(key)
        if query is None:
            raise QueryValidationError(f"Annotation has no matching Retrieval Query: {key}")
        if annotation.question != query.question:
            raise QueryValidationError(f"Question mismatch for Annotation and Query: {key}")
        pairs.append(AnnotationQueryPair(annotation=annotation, retrieval_query=query))

    extra_query_keys = set(queries_by_key) - annotation_keys
    if extra_query_keys:
        preview = sorted(extra_query_keys)[:5]
        raise QueryValidationError(
            f"Retrieval Queries have no matching Annotation "
            f"({len(extra_query_keys)}): {preview}"
        )
    return pairs


def load_and_link_clapnq(
    checkout_path: Path,
    *,
    revision: str = CLAPNQ_REVISION,
    source_files: tuple[SourceFileSpec, ...] = CLAPNQ_SOURCE_FILES,
) -> list[AnnotationQueryPair]:
    """Load fixed annotations and queries, then enforce their one-to-one mapping."""
    annotations = load_clapnq_annotations(
        checkout_path,
        revision=revision,
        source_files=source_files,
    )
    queries = load_clapnq_queries(
        checkout_path,
        revision=revision,
        source_files=source_files,
    )
    return link_annotations_to_queries(annotations, queries)
