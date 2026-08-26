"""Immutable source specification for the CLAPNQ research dataset."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

CLAPNQ_REPOSITORY_URL = "https://github.com/primeqa/clapnq.git"
CLAPNQ_REVISION = "c508d78d8c5c2eecbf172fcf5f789004206e11fb"
CLAPNQ_CORPUS_PASSAGE_COUNT = 178_891


class SourceFileRole(StrEnum):
    """Role of a file in the CLAPNQ source distribution."""

    ANNOTATION = "annotation"
    RETRIEVAL_QUERY = "retrieval_query"
    RETRIEVAL_CORPUS = "retrieval_corpus"
    LICENSE = "license"


@dataclass(frozen=True, slots=True)
class SourceFileSpec:
    """Expected properties of one file at the fixed upstream revision."""

    relative_path: str
    role: SourceFileRole
    expected_record_count: int | None = None
    source_split: str | None = None
    is_answerable: bool | None = None

    def __post_init__(self) -> None:
        path = PurePosixPath(self.relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Source path must be repository-relative: {self.relative_path}")
        if self.expected_record_count is not None and self.expected_record_count < 0:
            raise ValueError("Expected record count must be non-negative")


@dataclass(frozen=True, slots=True)
class LicenseLineage:
    """License information that must be retained in the source manifest."""

    dataset: str
    license_name: str
    source_url: str


CLAPNQ_SOURCE_FILES = (
    SourceFileSpec(
        "annotated_data/train/clapnq_train_answerable.jsonl",
        SourceFileRole.ANNOTATION,
        expected_record_count=1_954,
        source_split="train",
        is_answerable=True,
    ),
    SourceFileSpec(
        "annotated_data/train/clapnq_train_unanswerable.jsonl",
        SourceFileRole.ANNOTATION,
        expected_record_count=1_791,
        source_split="train",
        is_answerable=False,
    ),
    SourceFileSpec(
        "annotated_data/dev/clapnq_dev_answerable.jsonl",
        SourceFileRole.ANNOTATION,
        expected_record_count=300,
        source_split="dev",
        is_answerable=True,
    ),
    SourceFileSpec(
        "annotated_data/dev/clapnq_dev_unanswerable.jsonl",
        SourceFileRole.ANNOTATION,
        expected_record_count=300,
        source_split="dev",
        is_answerable=False,
    ),
    SourceFileSpec(
        "retrieval/train/question_train_answerable.tsv",
        SourceFileRole.RETRIEVAL_QUERY,
        expected_record_count=1_954,
        source_split="train",
        is_answerable=True,
    ),
    SourceFileSpec(
        "retrieval/train/question_train_unanswerable.tsv",
        SourceFileRole.RETRIEVAL_QUERY,
        expected_record_count=1_791,
        source_split="train",
        is_answerable=False,
    ),
    SourceFileSpec(
        "retrieval/dev/question_dev_answerable.tsv",
        SourceFileRole.RETRIEVAL_QUERY,
        expected_record_count=300,
        source_split="dev",
        is_answerable=True,
    ),
    SourceFileSpec(
        "retrieval/dev/question_dev_unanswerable.tsv",
        SourceFileRole.RETRIEVAL_QUERY,
        expected_record_count=300,
        source_split="dev",
        is_answerable=False,
    ),
    SourceFileSpec(
        "retrieval/passages.tsv.zip",
        SourceFileRole.RETRIEVAL_CORPUS,
        expected_record_count=CLAPNQ_CORPUS_PASSAGE_COUNT,
    ),
    SourceFileSpec("LICENSE", SourceFileRole.LICENSE),
)

CLAPNQ_LICENSE_LINEAGE = (
    LicenseLineage(
        dataset="CLAPNQ",
        license_name="Apache License 2.0",
        source_url=(
            "https://github.com/primeqa/clapnq/blob/"
            f"{CLAPNQ_REVISION}/LICENSE"
        ),
    ),
    LicenseLineage(
        dataset="Natural Questions",
        license_name="CC BY-SA 3.0",
        source_url="https://ai.google.com/research/NaturalQuestions/download",
    ),
)

