"""Tests for safe fixed-revision CLAPNQ acquisition."""

import subprocess
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

import pytest

from rag_research.data.clapnq_acquisition import (
    AcquisitionError,
    acquire_clapnq,
    verify_source_checkout,
)
from rag_research.data.clapnq_source import CLAPNQ_SOURCE_FILES, SourceFileSpec


def _run_git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _create_local_upstream(
    root: Path,
    source_files: Sequence[SourceFileSpec] = CLAPNQ_SOURCE_FILES,
) -> tuple[Path, str]:
    repository = root / "upstream"
    _run_git("init", str(repository))

    for spec in source_files:
        path = repository.joinpath(*PurePosixPath(spec.relative_path).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"fixture for {spec.relative_path}\n", encoding="utf-8")

    _run_git("-C", str(repository), "add", ".")
    _run_git(
        "-C",
        str(repository),
        "-c",
        "user.name=CLAPNQ Test",
        "-c",
        "user.email=clapnq-test@example.invalid",
        "commit",
        "-m",
        "Create source fixture",
    )
    revision = _run_git("-C", str(repository), "rev-parse", "HEAD")
    return repository, revision


def test_acquire_clapnq_checks_out_and_verifies_fixed_revision(tmp_path: Path) -> None:
    """A valid upstream becomes a detached revision-named checkout."""
    repository, revision = _create_local_upstream(tmp_path)
    raw_root = tmp_path / "raw"

    result = acquire_clapnq(
        raw_root,
        repository_url=str(repository),
        revision=revision,
    )

    assert result.checkout_path == raw_root.resolve() / revision
    assert result.revision == revision
    assert result.reused_existing is False
    assert _run_git("-C", str(result.checkout_path), "rev-parse", "HEAD") == revision
    verify_source_checkout(result.checkout_path, revision)


def test_acquire_clapnq_reuses_valid_checkout_without_overwriting(tmp_path: Path) -> None:
    """A second run verifies and reuses the checkout instead of replacing it."""
    repository, revision = _create_local_upstream(tmp_path)
    raw_root = tmp_path / "raw"
    first_result = acquire_clapnq(
        raw_root,
        repository_url=str(repository),
        revision=revision,
    )
    marker = first_result.checkout_path / "local-marker.txt"
    marker.write_text("must remain\n", encoding="utf-8")

    second_result = acquire_clapnq(
        raw_root,
        repository_url=str(repository),
        revision=revision,
    )

    assert second_result.reused_existing is True
    assert marker.read_text(encoding="utf-8") == "must remain\n"


def test_acquire_clapnq_cleans_incomplete_checkout_on_failure(tmp_path: Path) -> None:
    """Missing required files fail before publication and staging data is removed."""
    repository, revision = _create_local_upstream(
        tmp_path,
        source_files=CLAPNQ_SOURCE_FILES[:-1],
    )
    raw_root = tmp_path / "raw"

    with pytest.raises(AcquisitionError, match="Required CLAPNQ files are missing"):
        acquire_clapnq(
            raw_root,
            repository_url=str(repository),
            revision=revision,
        )

    assert not (raw_root / revision).exists()
    assert list(raw_root.iterdir()) == []


def test_acquire_clapnq_rejects_moving_revision(tmp_path: Path) -> None:
    """Branch names and abbreviated hashes cannot identify research input."""
    with pytest.raises(ValueError, match="full 40-character"):
        acquire_clapnq(tmp_path / "raw", revision="main")

