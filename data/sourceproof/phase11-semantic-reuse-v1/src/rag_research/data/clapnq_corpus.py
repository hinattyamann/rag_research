"""Stream CLAPNQ retrieval passages into the internal Document schema."""

import csv
import hashlib
import io
import json
import os
import tempfile
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from rag_research.data.clapnq_acquisition import verify_source_checkout
from rag_research.data.clapnq_source import (
    CLAPNQ_REVISION,
    CLAPNQ_SOURCE_FILES,
    SourceFileRole,
    SourceFileSpec,
)

_CORPUS_COLUMNS = ("id", "text", "title")
_CORPUS_ENTRY_PATH = "passages.tsv"


class CorpusValidationError(ValueError):
    """Raised when the retrieval Corpus violates the fixed source contract."""


@dataclass(slots=True)
class InternalRetrievalDocument:
    """One canonical CLAPNQ passage used as a retrieval unit."""

    passage_id: str
    source_dataset: str
    source_revision: str
    title: str
    text: str
    text_sha256: str

    def to_dict(self) -> dict[str, str]:
        """Return a detached JSON-compatible representation."""
        return {
            "passage_id": self.passage_id,
            "source_dataset": self.source_dataset,
            "source_revision": self.source_revision,
            "title": self.title,
            "text": self.text,
            "text_sha256": self.text_sha256,
        }


@dataclass(frozen=True, slots=True)
class CorpusWriteSummary:
    """Metadata for a deterministic passages JSONL artifact."""

    output_path: Path
    record_count: int
    unique_title_count: int
    verified_gold_passage_id_count: int
    byte_count: int
    sha256: str


def _require_nonblank(value: str, *, field: str, location: str) -> str:
    if not value.strip():
        raise CorpusValidationError(f"Blank {field} at {location}")
    return value


def _parse_corpus_row(
    raw_row: dict[str, str],
    *,
    revision: str,
    logical_index: int,
    physical_line_number: int,
    source_name: str,
) -> InternalRetrievalDocument:
    location = (
        f"{source_name} logical row {logical_index + 1} "
        f"ending at physical line {physical_line_number}"
    )
    passage_id = _require_nonblank(raw_row["id"], field="passage id", location=location)
    if passage_id != passage_id.strip():
        raise CorpusValidationError(f"Passage ID has surrounding whitespace at {location}")
    text = _require_nonblank(raw_row["text"], field="passage text", location=location)
    title = _require_nonblank(raw_row["title"], field="passage title", location=location)
    return InternalRetrievalDocument(
        passage_id=passage_id,
        source_dataset="CLAPNQ",
        source_revision=revision,
        title=title,
        text=text,
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def iter_corpus_file(
    checkout_path: Path,
    spec: SourceFileSpec,
    *,
    revision: str = CLAPNQ_REVISION,
) -> Iterator[InternalRetrievalDocument]:
    """Yield validated Documents from one CLAPNQ Corpus ZIP without extracting it."""
    if spec.role is not SourceFileRole.RETRIEVAL_CORPUS:
        raise ValueError(f"SourceFileSpec is not a Retrieval Corpus: {spec.relative_path}")
    path = checkout_path.joinpath(*PurePosixPath(spec.relative_path).parts)
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise CorpusValidationError(f"Invalid Corpus ZIP: {path}") from error

    record_count = 0
    passage_ids: set[str] = set()
    with archive:
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
        if len(entries) != 1 or entries[0].filename != _CORPUS_ENTRY_PATH:
            names = [entry.filename for entry in entries]
            raise CorpusValidationError(
                f"Unexpected Corpus ZIP entries in {path}: {names}"
            )
        entry = entries[0]
        try:
            with archive.open(entry) as binary_source:
                with io.TextIOWrapper(
                    binary_source, encoding="utf-8", newline=""
                ) as source:
                    reader = csv.DictReader(
                        source,
                        delimiter="\t",
                        restkey="__extra_columns__",
                    )
                    if tuple(reader.fieldnames or ()) != _CORPUS_COLUMNS:
                        raise CorpusValidationError(
                            f"TSV schema mismatch for {path}!/{entry.filename}: "
                            f"expected {list(_CORPUS_COLUMNS)}, found {reader.fieldnames}"
                        )
                    for logical_index, parsed_row in enumerate(reader):
                        if "__extra_columns__" in parsed_row or any(
                            parsed_row.get(column) is None for column in _CORPUS_COLUMNS
                        ):
                            raise CorpusValidationError(
                                f"TSV column count mismatch for {path}!/{entry.filename} "
                                f"at logical row {logical_index + 1}"
                            )
                        raw_row = {
                            column: parsed_row[column] for column in _CORPUS_COLUMNS
                        }
                        document = _parse_corpus_row(
                            raw_row,
                            revision=revision,
                            logical_index=logical_index,
                            physical_line_number=reader.line_num,
                            source_name=f"{path}!/{entry.filename}",
                        )
                        if document.passage_id in passage_ids:
                            raise CorpusValidationError(
                                f"Duplicate Passage ID in {path}: {document.passage_id}"
                            )
                        passage_ids.add(document.passage_id)
                        record_count += 1
                        yield document
        except UnicodeDecodeError as error:
            raise CorpusValidationError(
                f"Corpus TSV is not valid UTF-8: {path}!/{entry.filename}"
            ) from error
        except csv.Error as error:
            raise CorpusValidationError(
                f"Invalid Corpus TSV near physical line {reader.line_num}: {path}"
            ) from error
        except zipfile.BadZipFile as error:
            raise CorpusValidationError(f"Corrupt Corpus ZIP entry: {path}") from error

    if spec.expected_record_count is not None and record_count != spec.expected_record_count:
        raise CorpusValidationError(
            f"Record count mismatch for {spec.relative_path}: "
            f"expected {spec.expected_record_count}, found {record_count}"
        )


def iter_clapnq_corpus(
    checkout_path: Path,
    *,
    revision: str = CLAPNQ_REVISION,
    source_files: tuple[SourceFileSpec, ...] = CLAPNQ_SOURCE_FILES,
) -> Iterator[InternalRetrievalDocument]:
    """Verify the fixed checkout and stream its canonical retrieval Corpus."""
    corpus_specs = tuple(
        spec for spec in source_files if spec.role is SourceFileRole.RETRIEVAL_CORPUS
    )
    if len(corpus_specs) != 1:
        raise CorpusValidationError(
            f"Expected exactly one Retrieval Corpus SourceFileSpec, found {len(corpus_specs)}"
        )
    verify_source_checkout(checkout_path, revision, corpus_specs)
    yield from iter_corpus_file(
        checkout_path,
        corpus_specs[0],
        revision=revision,
    )


def serialize_retrieval_document(document: InternalRetrievalDocument) -> str:
    """Serialize one Document to canonical compact JSON."""
    return json.dumps(
        document.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def write_corpus_jsonl(
    documents: Iterable[InternalRetrievalDocument],
    output_path: Path,
    *,
    expected_gold_passage_ids: Iterable[str] = (),
) -> CorpusWriteSummary:
    """Atomically stream deterministic JSONL and verify every expected Gold ID."""
    remaining_gold_ids = set(expected_gold_passage_ids)
    expected_gold_count = len(remaining_gold_ids)
    passage_ids: set[str] = set()
    titles: set[str] = set()
    output_hash = hashlib.sha256()
    record_count = 0
    byte_count = 0

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
            temporary_path = Path(temporary.name)
            for document in documents:
                if document.passage_id in passage_ids:
                    raise CorpusValidationError(
                        f"Cannot write duplicate Passage ID: {document.passage_id}"
                    )
                passage_ids.add(document.passage_id)
                titles.add(document.title)
                remaining_gold_ids.discard(document.passage_id)

                payload = f"{serialize_retrieval_document(document)}\n".encode("utf-8")
                temporary.write(payload)
                output_hash.update(payload)
                record_count += 1
                byte_count += len(payload)

            if remaining_gold_ids:
                preview = sorted(remaining_gold_ids)[:5]
                raise CorpusValidationError(
                    f"Gold Passage IDs missing from Corpus ({len(remaining_gold_ids)}): "
                    f"{preview}"
                )
            temporary.flush()
            os.fsync(temporary.fileno())
        temporary_path.replace(output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return CorpusWriteSummary(
        output_path=output_path,
        record_count=record_count,
        unique_title_count=len(titles),
        verified_gold_passage_id_count=expected_gold_count,
        byte_count=byte_count,
        sha256=output_hash.hexdigest(),
    )
