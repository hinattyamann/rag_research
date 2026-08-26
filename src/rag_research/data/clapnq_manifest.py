"""Build and validate a reproducible source manifest for CLAPNQ."""

import csv
import hashlib
import io
import json
import os
import tempfile
import zipfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, TextIO

from rag_research.data.clapnq_acquisition import verify_source_checkout
from rag_research.data.clapnq_source import (
    CLAPNQ_LICENSE_LINEAGE,
    CLAPNQ_REPOSITORY_URL,
    CLAPNQ_REVISION,
    CLAPNQ_SOURCE_FILES,
    LicenseLineage,
    SourceFileRole,
    SourceFileSpec,
)

MANIFEST_SCHEMA_VERSION = "1.0"
DEFAULT_MANIFEST_PATH = Path("data/manifests/clapnq_source_manifest.json")
_ANNOTATION_REQUIRED_FIELDS = frozenset({"id", "input", "passages", "output"})
_QUERY_COLUMNS = ("id", "question", "doc-id-list", "answers")
_CORPUS_COLUMNS = ("id", "text", "title")


class ManifestValidationError(ValueError):
    """Raised when source content differs from the fixed CLAPNQ contract."""


@dataclass(slots=True)
class _InspectionResult:
    record_count: int | None
    schema: dict[str, Any]
    record_ids: set[str] | None = None
    gold_passage_ids: set[str] | None = None
    rows_with_gold_passage_id: int = 0


def _json_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def calculate_sha256(path: Path) -> str:
    """Calculate a file SHA-256 without loading the whole file into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _inspect_annotation(path: Path) -> _InspectionResult:
    observed_fields: set[str] = set()
    fields_in_every_record: set[str] | None = None
    field_types: dict[str, set[str]] = {}
    record_count = 0
    record_ids: set[str] = set()

    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                raise ManifestValidationError(f"Blank JSONL line: {path}:{line_number}")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ManifestValidationError(
                    f"Invalid JSONL record: {path}:{line_number}: {error.msg}"
                ) from error
            if not isinstance(record, dict):
                raise ManifestValidationError(
                    f"JSONL record is not an object: {path}:{line_number}"
                )

            fields = set(record)
            missing_fields = _ANNOTATION_REQUIRED_FIELDS - fields
            if missing_fields:
                missing = ", ".join(sorted(missing_fields))
                raise ManifestValidationError(
                    f"Missing annotation fields at {path}:{line_number}: {missing}"
                )

            record_id = record["id"]
            if not isinstance(record_id, str) or not record_id:
                raise ManifestValidationError(f"Invalid annotation id: {path}:{line_number}")
            if record_id in record_ids:
                raise ManifestValidationError(f"Duplicate annotation id in {path}: {record_id}")
            record_ids.add(record_id)

            observed_fields.update(fields)
            fields_in_every_record = fields if fields_in_every_record is None else (
                fields_in_every_record & fields
            )
            for field, value in record.items():
                field_types.setdefault(field, set()).add(_json_type(value))
            record_count += 1

    schema = {
        "format": "jsonl",
        "top_level_fields": sorted(observed_fields),
        "fields_present_in_every_record": sorted(fields_in_every_record or set()),
        "top_level_types": {
            field: sorted(types) for field, types in sorted(field_types.items())
        },
    }
    return _InspectionResult(record_count, schema, record_ids=record_ids)


def _read_tsv(
    source: TextIO,
    *,
    source_name: str,
    expected_columns: Sequence[str],
    collect_gold_ids: bool = False,
) -> _InspectionResult:
    reader = csv.reader(source, delimiter="\t")
    try:
        header = next(reader)
    except StopIteration as error:
        raise ManifestValidationError(f"Empty TSV file: {source_name}") from error
    if tuple(header) != tuple(expected_columns):
        raise ManifestValidationError(
            f"TSV schema mismatch in {source_name}: expected {list(expected_columns)}, "
            f"found {header}"
        )

    record_count = 0
    record_ids: set[str] = set()
    gold_passage_ids: set[str] = set()
    rows_with_gold_passage_id = 0
    id_index = header.index("id")
    gold_index = header.index("doc-id-list") if collect_gold_ids else None

    for line_number, row in enumerate(reader, start=2):
        if len(row) != len(header):
            raise ManifestValidationError(
                f"TSV column count mismatch: {source_name}:{line_number}"
            )
        record_id = row[id_index]
        if not record_id:
            raise ManifestValidationError(f"Empty TSV id: {source_name}:{line_number}")
        if record_id in record_ids:
            raise ManifestValidationError(f"Duplicate TSV id in {source_name}: {record_id}")
        record_ids.add(record_id)

        if gold_index is not None:
            gold_id = row[gold_index].strip()
            if gold_id:
                if any(character.isspace() for character in gold_id) or "," in gold_id:
                    raise ManifestValidationError(
                        f"Unexpected multiple Gold Passage IDs: {source_name}:{line_number}"
                    )
                gold_passage_ids.add(gold_id)
                rows_with_gold_passage_id += 1
        record_count += 1

    return _InspectionResult(
        record_count,
        {"format": "tsv", "columns": header},
        record_ids=record_ids,
        gold_passage_ids=gold_passage_ids if collect_gold_ids else None,
        rows_with_gold_passage_id=rows_with_gold_passage_id,
    )


def _inspect_query(path: Path) -> _InspectionResult:
    with path.open("r", encoding="utf-8", newline="") as source:
        return _read_tsv(
            source,
            source_name=str(path),
            expected_columns=_QUERY_COLUMNS,
            collect_gold_ids=True,
        )


def _inspect_corpus_archive(path: Path) -> _InspectionResult:
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as error:
        raise ManifestValidationError(f"Invalid Corpus Zip: {path}") from error

    with archive:
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
        if len(entries) != 1 or entries[0].filename != "passages.tsv":
            names = [entry.filename for entry in entries]
            raise ManifestValidationError(
                f"Unexpected Corpus Zip entries in {path}: {names}"
            )
        entry = entries[0]
        with archive.open(entry) as binary_source:
            with io.TextIOWrapper(binary_source, encoding="utf-8", newline="") as source:
                result = _read_tsv(
                    source,
                    source_name=f"{path}!/{entry.filename}",
                    expected_columns=_CORPUS_COLUMNS,
                )
        result.schema = {
            "format": "zip",
            "entry_path": entry.filename,
            "entry_size_bytes": entry.file_size,
            "entry_format": "tsv",
            "columns": list(_CORPUS_COLUMNS),
        }
        return result


def _inspect_license(path: Path) -> _InspectionResult:
    text = path.read_text(encoding="utf-8")
    if "Apache License" not in text or "Version 2.0" not in text:
        raise ManifestValidationError(f"Expected Apache License 2.0 text in {path}")
    return _InspectionResult(None, {"format": "text", "encoding": "utf-8"})


def _validate_record_count(spec: SourceFileSpec, actual_count: int | None) -> None:
    if spec.expected_record_count is None:
        return
    if actual_count != spec.expected_record_count:
        raise ManifestValidationError(
            f"Record count mismatch for {spec.relative_path}: "
            f"expected {spec.expected_record_count}, found {actual_count}"
        )


def _source_path(checkout_path: Path, relative_path: str) -> Path:
    return checkout_path.joinpath(*PurePosixPath(relative_path).parts)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_source_manifest(
    checkout_path: Path,
    *,
    repository_url: str = CLAPNQ_REPOSITORY_URL,
    revision: str = CLAPNQ_REVISION,
    source_files: Sequence[SourceFileSpec] = CLAPNQ_SOURCE_FILES,
    license_lineage: Sequence[LicenseLineage] = CLAPNQ_LICENSE_LINEAGE,
    acquired_at: str | None = None,
) -> dict[str, Any]:
    """Inspect all fixed CLAPNQ sources and return a validated manifest."""
    verify_source_checkout(checkout_path, revision, source_files)

    file_entries: list[dict[str, Any]] = []
    annotation_counts: dict[str, int] = {"train": 0, "dev": 0}
    query_record_count = 0
    answerable_gold_ids: set[str] = set()
    unanswerable_rows_with_gold = 0
    corpus_ids: set[str] | None = None

    for spec in source_files:
        path = _source_path(checkout_path, spec.relative_path)
        if spec.role is SourceFileRole.ANNOTATION:
            inspection = _inspect_annotation(path)
            if spec.source_split is not None:
                annotation_counts.setdefault(spec.source_split, 0)
                annotation_counts[spec.source_split] += inspection.record_count or 0
        elif spec.role is SourceFileRole.RETRIEVAL_QUERY:
            inspection = _inspect_query(path)
            query_record_count += inspection.record_count or 0
            if spec.is_answerable:
                if inspection.rows_with_gold_passage_id != inspection.record_count:
                    raise ManifestValidationError(
                        f"Answerable query without Gold Passage ID: {spec.relative_path}"
                    )
                answerable_gold_ids.update(inspection.gold_passage_ids or set())
            else:
                unanswerable_rows_with_gold += inspection.rows_with_gold_passage_id
        elif spec.role is SourceFileRole.RETRIEVAL_CORPUS:
            inspection = _inspect_corpus_archive(path)
            corpus_ids = inspection.record_ids
        elif spec.role is SourceFileRole.LICENSE:
            inspection = _inspect_license(path)
        else:
            raise ManifestValidationError(f"Unsupported source role: {spec.role}")

        _validate_record_count(spec, inspection.record_count)
        file_entries.append(
            {
                "relative_path": spec.relative_path,
                "role": spec.role.value,
                "source_split": spec.source_split,
                "is_answerable": spec.is_answerable,
                "sha256": calculate_sha256(path),
                "size_bytes": path.stat().st_size,
                "record_count": inspection.record_count,
                "expected_record_count": spec.expected_record_count,
                "schema": inspection.schema,
            }
        )

    if corpus_ids is None:
        raise ManifestValidationError("Retrieval Corpus was not inspected")
    missing_gold_ids = sorted(answerable_gold_ids - corpus_ids)
    if missing_gold_ids:
        preview = ", ".join(missing_gold_ids[:5])
        raise ManifestValidationError(
            f"Gold Passage IDs missing from Corpus ({len(missing_gold_ids)}): {preview}"
        )
    if unanswerable_rows_with_gold:
        raise ManifestValidationError(
            f"Unanswerable query rows with Gold Passage IDs: {unanswerable_rows_with_gold}"
        )

    annotation_total = sum(annotation_counts.values())
    corpus_entry = next(
        entry for entry in file_entries if entry["role"] == SourceFileRole.RETRIEVAL_CORPUS
    )
    return {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "dataset": {
            "name": "CLAPNQ",
            "repository_url": repository_url,
            "revision": revision,
            "checkout_layout": f"data/raw/clapnq/{revision}",
            "acquired_at": acquired_at or _utc_now(),
        },
        "license_lineage": [asdict(item) for item in license_lineage],
        "files": file_entries,
        "validation": {
            "passed": True,
            "required_file_count": len(source_files),
            "missing_file_count": 0,
            "annotation_record_count": annotation_total,
            "annotation_record_count_by_source_split": annotation_counts,
            "query_record_count": query_record_count,
            "corpus_passage_count": corpus_entry["record_count"],
            "corpus_passage_ids_unique": True,
            "answerable_gold_passage_id_count": len(answerable_gold_ids),
            "missing_gold_passage_id_count": 0,
            "unanswerable_rows_with_gold_passage_id": 0,
        },
    }


def _existing_acquired_at(output_path: Path, revision: str) -> str | None:
    if not output_path.exists():
        return None
    try:
        existing = json.loads(output_path.read_text(encoding="utf-8"))
        dataset = existing["dataset"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ManifestValidationError(f"Invalid existing Manifest: {output_path}") from error
    if dataset.get("revision") != revision:
        raise ManifestValidationError(
            f"Existing Manifest revision differs from requested revision: {output_path}"
        )
    acquired_at = dataset.get("acquired_at")
    return acquired_at if isinstance(acquired_at, str) else None


def write_source_manifest(
    manifest: dict[str, Any], output_path: Path = DEFAULT_MANIFEST_PATH
) -> None:
    """Atomically write a source manifest, preserving no partial output on failure."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=output_path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as target:
            target.write(serialized)
        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def generate_source_manifest(
    checkout_path: Path,
    output_path: Path = DEFAULT_MANIFEST_PATH,
    *,
    repository_url: str = CLAPNQ_REPOSITORY_URL,
    revision: str = CLAPNQ_REVISION,
    source_files: Sequence[SourceFileSpec] = CLAPNQ_SOURCE_FILES,
    license_lineage: Sequence[LicenseLineage] = CLAPNQ_LICENSE_LINEAGE,
) -> dict[str, Any]:
    """Build and atomically write a validated manifest."""
    acquired_at = _existing_acquired_at(output_path, revision)
    manifest = build_source_manifest(
        checkout_path,
        repository_url=repository_url,
        revision=revision,
        source_files=source_files,
        license_lineage=license_lineage,
        acquired_at=acquired_at,
    )
    write_source_manifest(manifest, output_path)
    return manifest
