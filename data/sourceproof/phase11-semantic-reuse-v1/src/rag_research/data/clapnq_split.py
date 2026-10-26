"""Deterministic, title-disjoint research splits of normalized CLAPNQ QA."""

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any

from rag_research.data.clapnq_records import (
    CLAPNQ_BASE_DATASET_VERSION,
    DEFAULT_PROCESSED_ROOT,
    InternalQARecord,
    build_stable_record_id,
)
from rag_research.data.clapnq_source import CLAPNQ_REVISION, CLAPNQ_SOURCE_FILES, SourceFileRole

SPLIT_NAMES = ("development", "calibration", "evaluation")
SPLIT_PERCENTAGES = (65, 10, 25)
SPLIT_SEED = 42
SPLIT_ALGORITHM_VERSION = "title-nfc-casefold-stratified-greedy-sha256-v1"
SPLIT_DATASET_VERSION = f"{CLAPNQ_REVISION[:7]}-split-v1"
DEFAULT_BASE_QA_PATH = DEFAULT_PROCESSED_ROOT / CLAPNQ_BASE_DATASET_VERSION / "qa.jsonl"
DEFAULT_SPLIT_MANIFEST_PATH = Path("data/manifests/clapnq_split_manifest.json")

QARecord = dict[str, Any]


class SplitValidationError(ValueError):
    """Raised for invalid inputs, leaked splits, or conflicting frozen artifacts."""


def title_group_key(title: str) -> str:
    """Conservatively keep case/Unicode title variants in one group; preserve raw titles."""
    return unicodedata.normalize("NFC", title.casefold())


def _json_bytes(value: Any, *, pretty: bool = False) -> bytes:
    options = {"indent": 2} if pretty else {"separators": (",", ":")}
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, **options) + "\n").encode("utf-8")


def _artifact(payload: bytes) -> dict[str, Any]:
    return {"sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)}


def validate_base_records(records: list[QARecord], *, require_public_counts: bool = False) -> None:
    """Validate unassigned base QA without inspecting text to choose assignments."""
    if not records:
        raise SplitValidationError("Base QA is empty")
    seen: set[str] = set()
    for index, record in enumerate(records):
        location = f"Base QA record {index}"
        if (
            not isinstance(record, dict)
            or not set(InternalQARecord.__dataclass_fields__) <= record.keys()
        ):
            raise SplitValidationError(f"{location}: incomplete internal QA schema")
        if record["source_dataset"] != "CLAPNQ" or record["source_revision"] != CLAPNQ_REVISION:
            raise SplitValidationError(f"{location}: unexpected source dataset/revision")
        title = record["source_title"]
        if not isinstance(title, str) or not title.strip():
            raise SplitValidationError(f"{location}: blank or invalid source_title")
        if type(record["is_answerable"]) is not bool:
            raise SplitValidationError(f"{location}: is_answerable must be a boolean")
        if not isinstance(record["source_id"], str):
            raise SplitValidationError(f"{location}: source_id must be a string")
        if not isinstance(record["source_split"], str):
            raise SplitValidationError(f"{location}: source_split must be a string")
        try:
            expected_id = build_stable_record_id(
                source_revision=record["source_revision"],
                source_split=record["source_split"],
                source_id=record["source_id"],
                is_answerable=record["is_answerable"],
            )
        except ValueError as error:
            raise SplitValidationError(f"{location}: invalid source identity") from error
        if record["record_id"] != expected_id or expected_id in seen:
            raise SplitValidationError(f"{location}: invalid or duplicate Stable ID")
        seen.add(expected_id)
        if record["research_split"] is not None:
            raise SplitValidationError(f"{location}: research_split must be unassigned")
        if record["derived_from_id"] is not None or record["derivation"] is not None:
            raise SplitValidationError(f"{location}: derived QA is not base QA")
        expected_type = "normal" if record["is_answerable"] else "unanswerable"
        if record["dataset_type"] != expected_type:
            raise SplitValidationError(f"{location}: inconsistent base dataset_type")
    if require_public_counts:
        expected = Counter(
            {
                (spec.source_split, spec.is_answerable): spec.expected_record_count
                for spec in CLAPNQ_SOURCE_FILES
                if spec.role is SourceFileRole.ANNOTATION
            }
        )
        actual = Counter((record["source_split"], record["is_answerable"]) for record in records)
        if actual != expected:
            raise SplitValidationError(
                f"Public source counts differ: {dict(actual)} != {dict(expected)}"
            )


def split_base_records(records: list[QARecord], *, seed: int = SPLIT_SEED) -> list[QARecord]:
    """Greedily minimize total and answerability count errors with exact arithmetic."""
    validate_base_records(records)
    if type(seed) is not int or seed < 0:
        raise SplitValidationError("Seed must be a non-negative integer")
    groups: dict[str, list[QARecord]] = defaultdict(list)
    for record in records:
        groups[title_group_key(record["source_title"])].append(record)
    if len(groups) < len(SPLIT_NAMES):
        raise SplitValidationError("At least three titles are required for three research splits")

    def group_order(title: str) -> tuple[int, str, str]:
        digest = hashlib.sha256(_json_bytes([seed, title])).hexdigest()
        return -len(groups[title]), digest, title

    totals = (len(records), sum(r["is_answerable"] for r in records))
    totals = (*totals, totals[0] - totals[1])
    counts = {name: [0, 0, 0] for name in SPLIT_NAMES}
    assignments: dict[str, str] = {}
    for title in sorted(groups, key=group_order):
        size = len(groups[title])
        answerable = sum(r["is_answerable"] for r in groups[title])
        addition = (size, answerable, size - answerable)

        def objective_delta(split_index: int) -> Fraction:
            name = SPLIT_NAMES[split_index]
            ratio = Fraction(SPLIT_PERCENTAGES[split_index], 100)
            change = Fraction(0)
            for dimension, total in enumerate(totals):
                if total:
                    before = counts[name][dimension] - total * ratio
                    after = before + addition[dimension]
                    change += (after * after - before * before) / (total * total)
            return change

        chosen = min(range(len(SPLIT_NAMES)), key=lambda i: (objective_delta(i), i))
        name = SPLIT_NAMES[chosen]
        assignments[title] = name
        counts[name] = [count + add for count, add in zip(counts[name], addition, strict=True)]
    if any(counts[name][0] == 0 for name in SPLIT_NAMES):
        raise SplitValidationError("Grouping produced an empty split; inspect group sizes")
    return [
        {**record, "research_split": assignments[title_group_key(record["source_title"])]}
        for record in sorted(records, key=lambda r: r["record_id"])
    ]


def validate_split(base_records: list[QARecord], split_records: list[QARecord]) -> dict[str, Any]:
    """Check complete coverage, unique IDs, title separation, and metadata preservation."""
    validate_base_records(base_records)
    base_by_id = {record["record_id"]: record for record in base_records}
    seen: set[str] = set()
    titles: dict[str, str] = {}
    for record in split_records:
        record_id = record["record_id"]
        name = record["research_split"]
        if record_id not in base_by_id or record_id in seen or name not in SPLIT_NAMES:
            raise SplitValidationError(
                "Split contains extra/duplicate IDs or an invalid research_split"
            )
        if {**record, "research_split": None} != base_by_id[record_id]:
            raise SplitValidationError(f"Base QA metadata changed: {record_id}")
        title = title_group_key(record["source_title"])
        if title in titles and titles[title] != name:
            raise SplitValidationError(f"Title leakage: {title}")
        titles[title] = name
        seen.add(record_id)
    if seen != base_by_id.keys():
        raise SplitValidationError("Split is missing base QA records")
    if {r["research_split"] for r in split_records} != set(SPLIT_NAMES):
        raise SplitValidationError("A research split is empty")
    return {
        "passed": True,
        "record_count": len(seen),
        "missing_record_count": 0,
        "extra_record_count": 0,
        "duplicate_record_count": 0,
        "title_overlap_count": 0,
        "group_overlap_count": 0,
        "metadata_preserved": True,
    }


def _statistics(records: list[QARecord]) -> dict[str, Any]:
    return {
        name: {
            "record_count": len(subset),
            "answerable_count": sum(r["is_answerable"] for r in subset),
            "unanswerable_count": sum(not r["is_answerable"] for r in subset),
            "title_count": len({r["source_title"] for r in subset}),
            "group_count": len({title_group_key(r["source_title"]) for r in subset}),
            "record_ratio": len(subset) / len(records),
            "answerable_ratio": sum(r["is_answerable"] for r in subset) / len(subset),
            "source_split_counts": dict(sorted(Counter(r["source_split"] for r in subset).items())),
        }
        for name in SPLIT_NAMES
        for subset in [[r for r in records if r["research_split"] == name]]
    }


def _write_frozen_artifacts(artifacts: dict[Path, bytes]) -> None:
    """Preflight every conflict, then publish individually atomic immutable artifacts."""
    for path, payload in artifacts.items():
        if path.exists() and path.read_bytes() != payload:
            raise SplitValidationError(
                f"Frozen artifact differs; use a new dataset version/path: {path}"
            )
    for path, payload in artifacts.items():
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=path.parent, prefix=f".{path.name}.", delete=False
            ) as tmp:
                temporary_path = Path(tmp.name)
                tmp.write(payload)
                tmp.flush()
                os.fsync(tmp.fileno())
            # Publish complete bytes atomically; hard links never replace an existing path.
            os.link(temporary_path, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise SplitValidationError(f"Concurrent frozen artifact conflict: {path}") from None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


def generate_research_split(
    input_path: Path = DEFAULT_BASE_QA_PATH,
    output_dir: Path | None = None,
    manifest_path: Path = DEFAULT_SPLIT_MANIFEST_PATH,
    *,
    seed: int = SPLIT_SEED,
    dataset_version: str = SPLIT_DATASET_VERSION,
    require_public_counts: bool = True,
) -> dict[str, Any]:
    """Generate a portable manifest and separate split QA without changing base QA."""
    if re.fullmatch(rf"{CLAPNQ_REVISION[:7]}-split-v[1-9][0-9]*", dataset_version) is None:
        raise SplitValidationError("Dataset version must be c508d78-split-vN with N >= 1")
    if seed != SPLIT_SEED and dataset_version == SPLIT_DATASET_VERSION:
        raise SplitValidationError("A different seed requires a new dataset version")
    output_dir = output_dir if output_dir is not None else DEFAULT_PROCESSED_ROOT / dataset_version
    output_paths = [
        output_dir / name
        for name in ("qa.jsonl", *[f"{n}.jsonl" for n in SPLIT_NAMES], "split_report.json")
    ]
    resolved = [path.resolve() for path in (*output_paths, manifest_path)]
    if len(set(resolved)) != len(resolved) or input_path.resolve() in resolved:
        raise SplitValidationError("Input, output QA/report, and manifest paths must be distinct")
    payload = input_path.read_bytes()
    try:
        records = [json.loads(line) for line in payload.decode("utf-8").splitlines()]
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SplitValidationError("Input is not valid UTF-8 internal QA JSONL") from error
    validate_base_records(records, require_public_counts=require_public_counts)
    split_records = split_base_records(records, seed=seed)
    validation = validate_split(records, split_records)
    stats = _statistics(split_records)
    report = {
        "dataset_version": dataset_version,
        "source_revision": CLAPNQ_REVISION,
        "algorithm_version": SPLIT_ALGORITHM_VERSION,
        "seed": seed,
        "grouping_key": "source_title",
        "title_normalization": "casefold_then_unicode_nfc",
        "target_ratios": dict(zip(SPLIT_NAMES, (p / 100 for p in SPLIT_PERCENTAGES), strict=True)),
        "total_record_count": len(records),
        "total_title_count": len({r["source_title"] for r in records}),
        "total_group_count": len({title_group_key(r["source_title"]) for r in records}),
        "splits": stats,
        "validation": validation,
    }
    outputs = {"qa.jsonl": b"".join(_json_bytes(r) for r in split_records)}
    outputs.update(
        {
            f"{name}.jsonl": b"".join(
                _json_bytes(r) for r in split_records if r["research_split"] == name
            )
            for name in SPLIT_NAMES
        }
    )
    outputs["split_report.json"] = _json_bytes(report, pretty=True)
    manifest = {
        **report,
        "manifest_schema_version": "1",
        "base_dataset_version": CLAPNQ_BASE_DATASET_VERSION,
        "input": _artifact(payload),
        "outputs": {name: _artifact(content) for name, content in outputs.items()},
        "record_ids_by_split": {
            name: [r["record_id"] for r in split_records if r["research_split"] == name]
            for name in SPLIT_NAMES
        },
        "title_assignments": {r["source_title"]: r["research_split"] for r in split_records},
        "group_assignments": {
            title_group_key(r["source_title"]): r["research_split"] for r in split_records
        },
    }
    artifacts = {output_dir / name: content for name, content in outputs.items()}
    artifacts[manifest_path] = _json_bytes(manifest, pretty=True)
    _write_frozen_artifacts(artifacts)
    return manifest
