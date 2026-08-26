"""Convert linked CLAPNQ source records into the internal QA schema."""

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from rag_research.data.clapnq_queries import (
    AnnotationQueryPair,
    load_and_link_clapnq,
)
from rag_research.data.clapnq_source import CLAPNQ_REVISION

CLAPNQ_QA_SCHEMA_VERSION = "1"
CLAPNQ_BASE_DATASET_VERSION = (
    f"{CLAPNQ_REVISION[:7]}-base-v{CLAPNQ_QA_SCHEMA_VERSION}"
)
DEFAULT_PROCESSED_ROOT = Path("data/processed/clapnq")

_FULL_GIT_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class QARecordValidationError(ValueError):
    """Raised when a linked source pair cannot form a valid internal QA record."""


@dataclass(slots=True)
class ProvidedPassage:
    """A source-provided passage that is not a Gold Passage."""

    title: str
    text: str
    sentences: list[str]


@dataclass(slots=True)
class InternalQARecord:
    """One normalized QA record used by downstream research stages."""

    record_id: str
    source_dataset: str
    source_revision: str
    source_split: str
    research_split: str | None
    source_id: str
    source_line_index: int
    source_record_sha256: str
    source_title: str
    question: str
    reference_answers: list[str]
    selected_sentences_by_reference: list[list[str]]
    is_answerable: bool
    gold_passage_ids: list[str]
    provided_passage: ProvidedPassage | None
    dataset_type: str
    derived_from_id: str | None
    derivation: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible representation of this record."""
        provided_passage = None
        if self.provided_passage is not None:
            provided_passage = {
                "title": self.provided_passage.title,
                "text": self.provided_passage.text,
                "sentences": list(self.provided_passage.sentences),
            }
        return {
            "record_id": self.record_id,
            "source_dataset": self.source_dataset,
            "source_revision": self.source_revision,
            "source_split": self.source_split,
            "research_split": self.research_split,
            "source_id": self.source_id,
            "source_line_index": self.source_line_index,
            "source_record_sha256": self.source_record_sha256,
            "source_title": self.source_title,
            "question": self.question,
            "reference_answers": list(self.reference_answers),
            "selected_sentences_by_reference": [
                list(sentences) for sentences in self.selected_sentences_by_reference
            ],
            "is_answerable": self.is_answerable,
            "gold_passage_ids": list(self.gold_passage_ids),
            "provided_passage": provided_passage,
            "dataset_type": self.dataset_type,
            "derived_from_id": self.derived_from_id,
            "derivation": self.derivation,
        }


@dataclass(frozen=True, slots=True)
class QAWriteSummary:
    """Deterministic JSONL output metadata."""

    output_path: Path
    record_count: int
    byte_count: int
    sha256: str


def build_stable_record_id(
    *,
    source_revision: str,
    source_split: str,
    source_id: str,
    is_answerable: bool,
) -> str:
    """Build an ID independent of research split and processing location."""
    if _FULL_GIT_COMMIT_PATTERN.fullmatch(source_revision) is None:
        raise QARecordValidationError(
            f"source_revision must be a lowercase 40-character Git commit: {source_revision}"
        )
    if source_split not in {"train", "dev"}:
        raise QARecordValidationError(f"Unsupported source_split: {source_split}")
    if not source_id or ":" in source_id:
        raise QARecordValidationError(f"Invalid source_id for Stable ID: {source_id}")
    answerability = "answerable" if is_answerable else "unanswerable"
    return f"clapnq:{source_revision[:7]}:{source_split}:{source_id}:{answerability}"


def _validate_pair(pair: AnnotationQueryPair) -> None:
    annotation = pair.annotation
    query = pair.retrieval_query
    if annotation.source_dataset != "CLAPNQ":
        raise QARecordValidationError(
            f"Unsupported source_dataset: {annotation.source_dataset}"
        )
    comparable_fields = (
        "source_dataset",
        "source_revision",
        "source_split",
        "source_id",
        "question",
        "is_answerable",
    )
    for field in comparable_fields:
        if getattr(annotation, field) != getattr(query, field):
            raise QARecordValidationError(
                f"Annotation and Retrieval Query disagree on {field}: "
                f"{getattr(annotation, field)!r} != {getattr(query, field)!r}"
            )
    if _SHA256_PATTERN.fullmatch(annotation.source_record_sha256) is None:
        raise QARecordValidationError(
            f"Invalid source_record_sha256 for source_id {annotation.source_id}"
        )
    if len(annotation.reference_answers) != len(
        annotation.selected_sentences_by_reference
    ):
        raise QARecordValidationError(
            f"Reference and evidence counts differ for source_id {annotation.source_id}"
        )


def _extract_provided_passage(pair: AnnotationQueryPair) -> ProvidedPassage | None:
    annotation = pair.annotation
    passages = annotation.raw_record.get("passages")
    if not isinstance(passages, list) or len(passages) != 1:
        raise QARecordValidationError(
            f"Expected exactly one Annotation passage for source_id {annotation.source_id}"
        )
    passage = passages[0]
    if not isinstance(passage, dict):
        raise QARecordValidationError(
            f"Invalid Annotation passage for source_id {annotation.source_id}"
        )
    title = passage.get("title")
    text = passage.get("text")
    sentences = passage.get("sentences")
    if (
        not isinstance(title, str)
        or not title.strip()
        or not isinstance(text, str)
        or not isinstance(sentences, list)
        or not all(isinstance(sentence, str) for sentence in sentences)
    ):
        raise QARecordValidationError(
            f"Invalid Provided Passage for source_id {annotation.source_id}"
        )
    if title != annotation.source_title:
        raise QARecordValidationError(
            f"Source title differs from Annotation passage for {annotation.source_id}"
        )
    if annotation.is_answerable:
        return None
    return ProvidedPassage(title=title, text=text, sentences=list(sentences))


def convert_pair_to_qa_record(pair: AnnotationQueryPair) -> InternalQARecord:
    """Convert one validated Annotation/Query pair to the internal QA schema."""
    _validate_pair(pair)
    annotation = pair.annotation
    gold_passage_ids = pair.gold_passage_ids
    if annotation.is_answerable:
        if len(gold_passage_ids) != 1 or not annotation.references:
            raise QARecordValidationError(
                f"Answerable record lacks one Gold Passage or a Reference: "
                f"{annotation.source_id}"
            )
        dataset_type = "normal"
    else:
        if gold_passage_ids or annotation.references:
            raise QARecordValidationError(
                f"Unanswerable record contains Gold data: {annotation.source_id}"
            )
        dataset_type = "unanswerable"

    return InternalQARecord(
        record_id=build_stable_record_id(
            source_revision=annotation.source_revision,
            source_split=annotation.source_split,
            source_id=annotation.source_id,
            is_answerable=annotation.is_answerable,
        ),
        source_dataset=annotation.source_dataset,
        source_revision=annotation.source_revision,
        source_split=annotation.source_split,
        research_split=None,
        source_id=annotation.source_id,
        source_line_index=annotation.source_line_index,
        source_record_sha256=annotation.source_record_sha256,
        source_title=annotation.source_title,
        question=annotation.question,
        reference_answers=annotation.reference_answers,
        selected_sentences_by_reference=annotation.selected_sentences_by_reference,
        is_answerable=annotation.is_answerable,
        gold_passage_ids=gold_passage_ids,
        provided_passage=_extract_provided_passage(pair),
        dataset_type=dataset_type,
        derived_from_id=None,
        derivation=None,
    )


def convert_pairs_to_qa_records(
    pairs: Iterable[AnnotationQueryPair],
) -> list[InternalQARecord]:
    """Convert linked pairs and reject any Stable ID collision."""
    records: list[InternalQARecord] = []
    record_ids: set[str] = set()
    for pair in pairs:
        record = convert_pair_to_qa_record(pair)
        if record.record_id in record_ids:
            raise QARecordValidationError(f"Duplicate Stable ID: {record.record_id}")
        record_ids.add(record.record_id)
        records.append(record)
    return records


def load_clapnq_qa_records(
    checkout_path: Path,
    *,
    revision: str = CLAPNQ_REVISION,
) -> list[InternalQARecord]:
    """Load fixed CLAPNQ sources and return final-schema base QA records."""
    pairs = load_and_link_clapnq(checkout_path, revision=revision)
    return convert_pairs_to_qa_records(pairs)


def serialize_qa_record(record: InternalQARecord) -> str:
    """Serialize one record to canonical compact JSON."""
    return json.dumps(
        record.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def write_qa_records_jsonl(
    records: Iterable[InternalQARecord],
    output_path: Path,
) -> QAWriteSummary:
    """Atomically write deterministic UTF-8 JSONL and report its checksum."""
    record_list = list(records)
    record_ids = [record.record_id for record in record_list]
    if len(record_ids) != len(set(record_ids)):
        raise QARecordValidationError("Cannot write duplicate Stable IDs")
    serialized = "".join(f"{serialize_qa_record(record)}\n" for record in record_list)
    payload = serialized.encode("utf-8")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return QAWriteSummary(
        output_path=output_path,
        record_count=len(record_list),
        byte_count=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )
