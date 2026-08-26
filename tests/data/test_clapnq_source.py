"""Tests for the fixed CLAPNQ source contract."""

from pathlib import PurePosixPath

from rag_research.data.clapnq_source import (
    CLAPNQ_LICENSE_LINEAGE,
    CLAPNQ_REVISION,
    CLAPNQ_SOURCE_FILES,
    SourceFileRole,
)


def test_revision_is_a_full_git_commit_hash() -> None:
    """The dataset revision must not be a moving branch or shortened hash."""
    assert len(CLAPNQ_REVISION) == 40
    assert all(character in "0123456789abcdef" for character in CLAPNQ_REVISION)


def test_source_paths_are_unique_and_repository_relative() -> None:
    """Every acquisition target has one safe, repository-relative path."""
    paths = [spec.relative_path for spec in CLAPNQ_SOURCE_FILES]

    assert len(paths) == len(set(paths))
    assert all(not PurePosixPath(path).is_absolute() for path in paths)
    assert all(".." not in PurePosixPath(path).parts for path in paths)


def test_final_round_annotation_counts_match_public_dataset() -> None:
    """Only the four final-round public annotation files are in scope."""
    annotations = [
        spec for spec in CLAPNQ_SOURCE_FILES if spec.role is SourceFileRole.ANNOTATION
    ]
    counts = {
        (spec.source_split, spec.is_answerable): spec.expected_record_count
        for spec in annotations
    }

    assert counts == {
        ("train", True): 1_954,
        ("train", False): 1_791,
        ("dev", True): 300,
        ("dev", False): 300,
    }
    assert sum(count for count in counts.values() if count is not None) == 4_345
    assert all("single" not in spec.relative_path for spec in annotations)


def test_retrieval_queries_mirror_annotation_partitions() -> None:
    """Each annotation partition has one matching retrieval-query file."""
    annotations = {
        (spec.source_split, spec.is_answerable, spec.expected_record_count)
        for spec in CLAPNQ_SOURCE_FILES
        if spec.role is SourceFileRole.ANNOTATION
    }
    queries = {
        (spec.source_split, spec.is_answerable, spec.expected_record_count)
        for spec in CLAPNQ_SOURCE_FILES
        if spec.role is SourceFileRole.RETRIEVAL_QUERY
    }

    assert queries == annotations


def test_source_contract_includes_corpus_and_license() -> None:
    """Retrieval corpus and upstream license are mandatory acquisition targets."""
    corpus = [
        spec
        for spec in CLAPNQ_SOURCE_FILES
        if spec.role is SourceFileRole.RETRIEVAL_CORPUS
    ]
    licenses = [
        spec for spec in CLAPNQ_SOURCE_FILES if spec.role is SourceFileRole.LICENSE
    ]

    assert len(corpus) == 1
    assert corpus[0].relative_path == "retrieval/passages.tsv.zip"
    assert corpus[0].expected_record_count == 178_890
    assert [spec.relative_path for spec in licenses] == ["LICENSE"]


def test_license_lineage_covers_clapnq_and_natural_questions() -> None:
    """Both the derived dataset and its Natural Questions source are attributed."""
    licenses = {item.dataset: item.license_name for item in CLAPNQ_LICENSE_LINEAGE}

    assert licenses == {
        "CLAPNQ": "Apache License 2.0",
        "Natural Questions": "CC BY-SA 3.0",
    }
