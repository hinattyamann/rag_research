"""Safe acquisition of the CLAPNQ repository at its fixed revision."""

import re
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from rag_research.data.clapnq_source import (
    CLAPNQ_REPOSITORY_URL,
    CLAPNQ_REVISION,
    CLAPNQ_SOURCE_FILES,
    SourceFileSpec,
)

DEFAULT_RAW_ROOT = Path("data/raw/clapnq")
_FULL_COMMIT_HASH = re.compile(r"[0-9a-f]{40}")


class AcquisitionError(RuntimeError):
    """Raised when a CLAPNQ checkout cannot be acquired or verified."""


@dataclass(frozen=True, slots=True)
class AcquisitionResult:
    """Result of acquiring or safely reusing a fixed source checkout."""

    checkout_path: Path
    revision: str
    reused_existing: bool


def _run_git(*arguments: str) -> str:
    command = ["git", *arguments]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as error:
        raise AcquisitionError("Git executable was not found") from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "unknown Git error").strip()
        raise AcquisitionError(f"Git command failed: {' '.join(command)}\n{detail}") from error
    return completed.stdout.strip()


def _validate_revision(revision: str) -> None:
    if _FULL_COMMIT_HASH.fullmatch(revision) is None:
        raise ValueError("CLAPNQ revision must be a full 40-character lowercase commit hash")


def _required_file_path(checkout_path: Path, relative_path: str) -> Path:
    return checkout_path.joinpath(*PurePosixPath(relative_path).parts)


def verify_source_checkout(
    checkout_path: Path,
    revision: str,
    source_files: Sequence[SourceFileSpec] = CLAPNQ_SOURCE_FILES,
) -> None:
    """Verify the checked-out commit and presence of every required source file."""
    _validate_revision(revision)
    if not checkout_path.is_dir():
        raise AcquisitionError(f"Checkout directory does not exist: {checkout_path}")

    actual_revision = _run_git("-C", str(checkout_path), "rev-parse", "HEAD")
    if actual_revision != revision:
        raise AcquisitionError(
            f"Checkout revision mismatch: expected {revision}, found {actual_revision}"
        )

    missing_paths = [
        spec.relative_path
        for spec in source_files
        if not _required_file_path(checkout_path, spec.relative_path).is_file()
    ]
    if missing_paths:
        formatted_paths = "\n".join(f"- {path}" for path in missing_paths)
        raise AcquisitionError(f"Required CLAPNQ files are missing:\n{formatted_paths}")


def _remove_staging_directory(staging_path: Path, raw_root: Path) -> None:
    resolved_staging = staging_path.resolve()
    resolved_root = raw_root.resolve()
    if resolved_root not in resolved_staging.parents:
        raise AcquisitionError(f"Refusing to clean staging path outside raw root: {staging_path}")

    def make_writable_and_retry(
        function: Callable[[str], object], path: str, error: BaseException
    ) -> None:
        if not isinstance(error, PermissionError):
            raise error
        Path(path).chmod(stat.S_IWRITE)
        function(path)

    shutil.rmtree(resolved_staging, onexc=make_writable_and_retry)


def acquire_clapnq(
    raw_root: Path = DEFAULT_RAW_ROOT,
    *,
    repository_url: str = CLAPNQ_REPOSITORY_URL,
    revision: str = CLAPNQ_REVISION,
    source_files: Sequence[SourceFileSpec] = CLAPNQ_SOURCE_FILES,
    progress: Callable[[str], None] | None = None,
) -> AcquisitionResult:
    """Acquire a detached fixed-revision checkout without overwriting existing data."""
    _validate_revision(revision)
    resolved_root = raw_root.resolve()
    resolved_root.mkdir(parents=True, exist_ok=True)
    checkout_path = resolved_root / revision

    if checkout_path.exists():
        if checkout_path.is_symlink():
            raise AcquisitionError(f"Refusing to reuse a symbolic link: {checkout_path}")
        if progress is not None:
            progress("既存の取得先を検証しています。")
        verify_source_checkout(checkout_path, revision, source_files)
        return AcquisitionResult(checkout_path, revision, reused_existing=True)

    staging_path = Path(tempfile.mkdtemp(prefix=f".{revision[:12]}-", dir=resolved_root))
    try:
        if progress is not None:
            progress("固定Commitを一時Directoryへ取得しています。")
        _run_git("init", str(staging_path))
        _run_git("-C", str(staging_path), "remote", "add", "origin", repository_url)
        _run_git("-C", str(staging_path), "fetch", "--depth", "1", "origin", revision)
        _run_git("-C", str(staging_path), "checkout", "--detach", "FETCH_HEAD")

        if progress is not None:
            progress("取得したCommitと必須Fileを検証しています。")
        verify_source_checkout(staging_path, revision, source_files)
        staging_path.rename(checkout_path)
    except Exception:
        if staging_path.exists():
            _remove_staging_directory(staging_path, resolved_root)
        raise

    return AcquisitionResult(checkout_path, revision, reused_existing=False)
