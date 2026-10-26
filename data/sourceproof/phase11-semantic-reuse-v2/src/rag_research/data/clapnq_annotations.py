"""Load CLAPNQ annotations and normalize evaluation references."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from rag_research.data.clapnq_acquisition import verify_source_checkout
from rag_research.data.clapnq_source import (
    CLAPNQ_REVISION,
    CLAPNQ_SOURCE_FILES,
    SourceFileRole,
    SourceFileSpec,
)

_REQUIRED_RECORD_FIELDS = frozenset({"id", "input", "passages", "output"})
_REQUIRED_PASSAGE_FIELDS = frozenset({"title", "text", "sentences"})
_INVALID_ANSWER_MARKERS = frozenset({"na"})


class AnnotationValidationError(ValueError):
    """Raised when a CLAPNQ annotation violates the fixed source contract."""


@dataclass(slots=True)
class NormalizedReference:
    """One valid answer paired with its evidence and original output position."""

    output_index: int
    answer: str
    selected_sentences: list[str]


@dataclass(slots=True)
class LoadedAnnotationRecord:
    """Loaded source annotation before Stable ID and Gold Passage attachment."""

    source_dataset: str
    source_revision: str
    source_split: str
    source_line_index: int
    source_record_sha256: str
    source_id: str
    source_title: str
    question: str
    is_answerable: bool
    references: list[NormalizedReference]
    raw_record: dict[str, Any]

    @property
    def reference_answers(self) -> list[str]:
        """Return the normalized answer view in source-output order."""
        return [reference.answer for reference in self.references]

    @property
    def selected_sentences_by_reference(self) -> list[list[str]]:
        """Return evidence lists paired one-to-one with normalized answers."""
        return [list(reference.selected_sentences) for reference in self.references]


def _location(source_name: str, line_index: int) -> str:
    return f"{source_name}:{line_index + 1}"


def _require_nonblank_string(value: object, *, field: str, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AnnotationValidationError(f"Invalid {field} at {location}")
    return value


def _validate_passages(passages: object, *, location: str) -> list[dict[str, Any]]:
    if not isinstance(passages, list) or not passages:
        raise AnnotationValidationError(f"passages must be a non-empty list at {location}")

    validated: list[dict[str, Any]] = []
    for passage_index, passage in enumerate(passages):
        passage_location = f"{location} passages[{passage_index}]"
        if not isinstance(passage, dict):
            raise AnnotationValidationError(f"Passage is not an object at {passage_location}")
        missing_fields = _REQUIRED_PASSAGE_FIELDS - set(passage)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise AnnotationValidationError(
                f"Missing passage fields at {passage_location}: {missing}"
            )
        _require_nonblank_string(
            passage["title"], field="passage title", location=passage_location
        )
        if not isinstance(passage["text"], str):
            raise AnnotationValidationError(f"Invalid passage text at {passage_location}")
        sentences = passage["sentences"]
        if not isinstance(sentences, list) or not all(
            isinstance(sentence, str) for sentence in sentences
        ):
            raise AnnotationValidationError(
                f"Passage sentences must be a list of strings at {passage_location}"
            )
        validated.append(passage)
    return validated


def _is_invalid_answer(answer: str | None) -> bool:
    if answer is None:
        return True
    normalized = answer.strip()
    return not normalized or normalized.casefold() in _INVALID_ANSWER_MARKERS


def normalize_references(
    outputs: object,
    *,
    is_answerable: bool,
    location: str,
) -> list[NormalizedReference]:
    """Filter invalid references while preserving order, evidence, and output index."""
    if not isinstance(outputs, list):
        raise AnnotationValidationError(f"output must be a list at {location}")

    references: list[NormalizedReference] = []
    for output_index, output in enumerate(outputs):
        output_location = f"{location} output[{output_index}]"
        if not isinstance(output, dict):
            raise AnnotationValidationError(f"Output is not an object at {output_location}")
        if "answer" not in output or "selected_sentences" not in output or "meta" not in output:
            raise AnnotationValidationError(
                f"Output requires answer, selected_sentences, and meta at {output_location}"
            )

        answer = output["answer"]
        if answer is not None and not isinstance(answer, str):
            raise AnnotationValidationError(f"Answer must be a string or null at {output_location}")
        selected_sentences = output["selected_sentences"]
        if not isinstance(selected_sentences, list) or not all(
            isinstance(sentence, str) for sentence in selected_sentences
        ):
            raise AnnotationValidationError(
                f"selected_sentences must be a list of strings at {output_location}"
            )
        meta = output["meta"]
        if not isinstance(meta, dict) or "skip" not in meta or not isinstance(meta["skip"], bool):
            raise AnnotationValidationError(
                f"meta.skip must be a boolean at {output_location}"
            )

        if meta["skip"] or _is_invalid_answer(answer):
            continue
        if answer is None:
            raise AssertionError("Invalid null answer passed reference filtering")
        references.append(
            NormalizedReference(
                output_index=output_index,
                answer=answer,
                selected_sentences=list(selected_sentences),
            )
        )

    if is_answerable and not references:
        raise AnnotationValidationError(f"Answerable record has no valid reference at {location}")
    if not is_answerable and references:
        raise AnnotationValidationError(
            f"Unanswerable record unexpectedly has a valid reference at {location}"
        )
    return references


def _parse_record(
    raw_record_bytes: bytes,
    *,
    spec: SourceFileSpec,
    revision: str,
    line_index: int,
) -> LoadedAnnotationRecord:
    location = _location(spec.relative_path, line_index)
    try:
        raw_text = raw_record_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AnnotationValidationError(f"Invalid UTF-8 at {location}") from error
    try:
        raw_record = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise AnnotationValidationError(f"Invalid JSON at {location}: {error.msg}") from error
    if not isinstance(raw_record, dict):
        raise AnnotationValidationError(f"Annotation is not an object at {location}")

    missing_fields = _REQUIRED_RECORD_FIELDS - set(raw_record)
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise AnnotationValidationError(f"Missing annotation fields at {location}: {missing}")
    source_id = _require_nonblank_string(
        raw_record["id"], field="source id", location=location
    )
    question = _require_nonblank_string(
        raw_record["input"], field="question", location=location
    )
    passages = _validate_passages(raw_record["passages"], location=location)
    if spec.is_answerable is None or spec.source_split is None:
        raise AnnotationValidationError(
            f"Annotation SourceFileSpec lacks split or answerability: {spec.relative_path}"
        )
    references = normalize_references(
        raw_record["output"],
        is_answerable=spec.is_answerable,
        location=location,
    )

    return LoadedAnnotationRecord(
        source_dataset="CLAPNQ",
        source_revision=revision,
        source_split=spec.source_split,
        source_line_index=line_index,
        source_record_sha256=hashlib.sha256(raw_record_bytes).hexdigest(),
        source_id=source_id,
        source_title=passages[0]["title"],
        question=question,
        is_answerable=spec.is_answerable,
        references=references,
        raw_record=raw_record,
    )


def load_annotation_file(
    checkout_path: Path,
    spec: SourceFileSpec,
    *,
    revision: str = CLAPNQ_REVISION,
) -> list[LoadedAnnotationRecord]:
    """Load and validate one final-round CLAPNQ Annotation JSONL file."""
    if spec.role is not SourceFileRole.ANNOTATION:
        raise ValueError(f"SourceFileSpec is not an annotation: {spec.relative_path}")
    path = checkout_path.joinpath(*PurePosixPath(spec.relative_path).parts)
    records: list[LoadedAnnotationRecord] = []
    source_ids: set[str] = set()

    with path.open("rb") as source:
        for line_index, raw_line in enumerate(source):
            raw_record_bytes = raw_line.rstrip(b"\r\n")
            if not raw_record_bytes.strip():
                raise AnnotationValidationError(
                    f"Blank JSONL line at {_location(spec.relative_path, line_index)}"
                )
            record = _parse_record(
                raw_record_bytes,
                spec=spec,
                revision=revision,
                line_index=line_index,
            )
            if record.source_id in source_ids:
                raise AnnotationValidationError(
                    f"Duplicate source id in {spec.relative_path}: {record.source_id}"
                )
            source_ids.add(record.source_id)
            records.append(record)

    if spec.expected_record_count is not None and len(records) != spec.expected_record_count:
        raise AnnotationValidationError(
            f"Record count mismatch for {spec.relative_path}: "
            f"expected {spec.expected_record_count}, found {len(records)}"
        )
    return records


def load_clapnq_annotations(
    checkout_path: Path,
    *,
    revision: str = CLAPNQ_REVISION,
    source_files: tuple[SourceFileSpec, ...] = CLAPNQ_SOURCE_FILES,
) -> list[LoadedAnnotationRecord]:
    """Load all four public final-round CLAPNQ annotation partitions."""
    annotation_specs = tuple(
        spec for spec in source_files if spec.role is SourceFileRole.ANNOTATION
    )
    if not annotation_specs:
        raise AnnotationValidationError("No Annotation SourceFileSpec was provided")
    verify_source_checkout(checkout_path, revision, annotation_specs)

    records: list[LoadedAnnotationRecord] = []
    for spec in annotation_specs:
        records.extend(load_annotation_file(checkout_path, spec, revision=revision))
    return records

