"""Tests for CLAPNQ source manifest generation and validation."""

import json
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

import pytest

from rag_research.data.clapnq_manifest import (
    ManifestValidationError,
    build_source_manifest,
    calculate_sha256,
    generate_source_manifest,
)
from rag_research.data.clapnq_source import SourceFileRole, SourceFileSpec


def _run_git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _fixture_specs() -> tuple[SourceFileSpec, ...]:
    specs: list[SourceFileSpec] = []
    for split in ("train", "dev"):
        for answerable in (True, False):
            label = "answerable" if answerable else "unanswerable"
            specs.append(
                SourceFileSpec(
                    f"annotated_data/{split}/clapnq_{split}_{label}.jsonl",
                    SourceFileRole.ANNOTATION,
                    expected_record_count=1,
                    source_split=split,
                    is_answerable=answerable,
                )
            )
    for split in ("train", "dev"):
        for answerable in (True, False):
            label = "answerable" if answerable else "unanswerable"
            specs.append(
                SourceFileSpec(
                    f"retrieval/{split}/question_{split}_{label}.tsv",
                    SourceFileRole.RETRIEVAL_QUERY,
                    expected_record_count=1,
                    source_split=split,
                    is_answerable=answerable,
                )
            )
    specs.extend(
        [
            SourceFileSpec(
                "retrieval/passages.tsv.zip",
                SourceFileRole.RETRIEVAL_CORPUS,
                expected_record_count=2,
            ),
            SourceFileSpec("LICENSE", SourceFileRole.LICENSE),
        ]
    )
    return tuple(specs)


def _create_source_checkout(
    root: Path,
    *,
    gold_id: str = "p1",
    corpus_ids: tuple[str, ...] = ("p1", "p2"),
) -> tuple[Path, str, tuple[SourceFileSpec, ...]]:
    checkout = root / "checkout"
    specs = _fixture_specs()
    _run_git("init", str(checkout))

    for index, spec in enumerate(specs):
        path = checkout.joinpath(*PurePosixPath(spec.relative_path).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        if spec.role is SourceFileRole.ANNOTATION:
            record = {
                "id": f"annotation-{index}",
                "input": "fixture question",
                "passages": [],
                "output": [],
            }
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        elif spec.role is SourceFileRole.RETRIEVAL_QUERY:
            query_gold = gold_id if spec.is_answerable else ""
            path.write_text(
                "id\tquestion\tdoc-id-list\tanswers\n"
                f"query-{index}\tfixture question\t{query_gold}\tfixture answer\n",
                encoding="utf-8",
            )
        elif spec.role is SourceFileRole.RETRIEVAL_CORPUS:
            rows = "".join(
                f"{passage_id}\tfixture text\tFixture title\n"
                for passage_id in corpus_ids
            )
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("passages.tsv", f"id\ttext\ttitle\n{rows}")
        elif spec.role is SourceFileRole.LICENSE:
            path.write_text("Apache License\nVersion 2.0\n", encoding="utf-8")

    _run_git("-C", str(checkout), "add", ".")
    _run_git(
        "-C",
        str(checkout),
        "-c",
        "user.name=CLAPNQ Test",
        "-c",
        "user.email=clapnq-test@example.invalid",
        "commit",
        "-m",
        "Create manifest fixture",
    )
    revision = _run_git("-C", str(checkout), "rev-parse", "HEAD")
    return checkout, revision, specs


def test_build_source_manifest_records_hash_counts_schema_and_validation(
    tmp_path: Path,
) -> None:
    """A valid checkout produces complete provenance and validation metadata."""
    checkout, revision, specs = _create_source_checkout(tmp_path)

    manifest = build_source_manifest(
        checkout,
        repository_url=str(checkout),
        revision=revision,
        source_files=specs,
        acquired_at="2026-08-26T08:39:00Z",
    )

    assert manifest["dataset"]["revision"] == revision
    assert manifest["dataset"]["acquired_at"] == "2026-08-26T08:39:00Z"
    assert len(manifest["files"]) == 10
    assert all(len(entry["sha256"]) == 64 for entry in manifest["files"])
    assert manifest["validation"] == {
        "passed": True,
        "required_file_count": 10,
        "missing_file_count": 0,
        "annotation_record_count": 4,
        "annotation_record_count_by_source_split": {"train": 2, "dev": 2},
        "query_record_count": 4,
        "corpus_passage_count": 2,
        "corpus_passage_ids_unique": True,
        "answerable_gold_passage_id_count": 1,
        "missing_gold_passage_id_count": 0,
        "unanswerable_rows_with_gold_passage_id": 0,
    }
    annotation = manifest["files"][0]
    assert annotation["schema"]["fields_present_in_every_record"] == [
        "id",
        "input",
        "output",
        "passages",
    ]
    assert annotation["sha256"] == calculate_sha256(
        checkout / annotation["relative_path"]
    )


def test_generate_source_manifest_preserves_first_acquisition_time(tmp_path: Path) -> None:
    """Regeneration does not rewrite when the source was first acquired."""
    checkout, revision, specs = _create_source_checkout(tmp_path)
    output_path = tmp_path / "manifest.json"

    first = generate_source_manifest(
        checkout,
        output_path,
        repository_url=str(checkout),
        revision=revision,
        source_files=specs,
    )
    second = generate_source_manifest(
        checkout,
        output_path,
        repository_url=str(checkout),
        revision=revision,
        source_files=specs,
    )

    assert second["dataset"]["acquired_at"] == first["dataset"]["acquired_at"]
    assert json.loads(output_path.read_text(encoding="utf-8")) == second


def test_build_source_manifest_rejects_duplicate_corpus_id(tmp_path: Path) -> None:
    """Duplicate retrieval units make the canonical Corpus invalid."""
    checkout, revision, specs = _create_source_checkout(
        tmp_path,
        corpus_ids=("p1", "p1"),
    )

    with pytest.raises(ManifestValidationError, match="Duplicate TSV id"):
        build_source_manifest(checkout, revision=revision, source_files=specs)


def test_build_source_manifest_rejects_missing_gold_passage(tmp_path: Path) -> None:
    """Every answerable Gold Passage ID must resolve in the canonical Corpus."""
    checkout, revision, specs = _create_source_checkout(tmp_path, gold_id="missing")

    with pytest.raises(ManifestValidationError, match="Gold Passage IDs missing"):
        build_source_manifest(checkout, revision=revision, source_files=specs)

