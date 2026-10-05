"""Tests for reproducible title grouping and frozen split artifacts."""

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from rag_research.data.clapnq_records import build_stable_record_id
from rag_research.data.clapnq_source import CLAPNQ_REVISION
from rag_research.data.clapnq_split import (
    DEFAULT_BASE_QA_PATH,
    SPLIT_NAMES,
    SplitValidationError,
    generate_research_split,
    split_base_records,
    title_group_key,
    validate_base_records,
    validate_split,
)


@pytest.fixture
def base_records() -> list[dict]:
    records = []
    for index in range(200):
        answerable = index % 2 == 0
        source_split = "train" if answerable else "dev"
        source_id = str(index)
        records.append(
            {
                "record_id": build_stable_record_id(
                    source_revision=CLAPNQ_REVISION,
                    source_split=source_split,
                    source_id=source_id,
                    is_answerable=answerable,
                ),
                "source_dataset": "CLAPNQ",
                "source_revision": CLAPNQ_REVISION,
                "source_split": source_split,
                "research_split": None,
                "source_id": source_id,
                "source_line_index": index,
                "source_record_sha256": "a" * 64,
                "source_title": f"Title {index // 2}",
                "question": f"Question {index}",
                "reference_answers": ["Answer"] if answerable else [],
                "selected_sentences_by_reference": [["Evidence"]] if answerable else [],
                "is_answerable": answerable,
                "gold_passage_ids": [f"gold-{index}"] if answerable else [],
                "provided_passage": None
                if answerable
                else {
                    "title": f"Title {index // 2}",
                    "text": "Provided",
                    "sentences": ["Provided"],
                },
                "dataset_type": "normal" if answerable else "unanswerable",
                "derived_from_id": None,
                "derivation": None,
            }
        )
    return records


def _write_base(path: Path, records: list[dict]) -> bytes:
    payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records).encode("utf-8")
    path.write_bytes(payload)
    return payload


def test_split_covers_qa_and_keeps_cross_source_titles_together(base_records: list[dict]) -> None:
    before = copy.deepcopy(base_records)
    result = split_base_records(base_records)
    assert base_records == before
    assert validate_split(base_records, result)["passed"]
    assert {r["record_id"] for r in result} == {r["record_id"] for r in base_records}
    for name in SPLIT_NAMES:
        subset = [r for r in result if r["research_split"] == name]
        assert Counter(r["source_split"] for r in subset)["train"] == len(subset) // 2
        assert Counter(r["is_answerable"] for r in subset)[True] == len(subset) // 2
    assert Counter(r["research_split"] for r in result) == {
        "development": 130,
        "calibration": 20,
        "evaluation": 50,
    }
    title_splits: dict[str, set[str]] = {}
    for record in result:
        title_splits.setdefault(record["source_title"], set()).add(record["research_split"])
    assert all(len(names) == 1 for names in title_splits.values())


def test_assignments_ignore_input_order_and_answer_text(base_records: list[dict]) -> None:
    first = split_base_records(base_records)
    assert first == split_base_records(list(reversed(base_records)))
    changed = copy.deepcopy(base_records)
    for record in changed:
        record["question"] = "Completely different question"
        if record["is_answerable"]:
            record["reference_answers"] = ["Different reference"]
            record["gold_passage_ids"] = ["different-gold"]
    assert {r["record_id"]: r["research_split"] for r in first} == {
        r["record_id"]: r["research_split"] for r in split_base_records(changed)
    }
    assert first != split_base_records(base_records, seed=43)


def test_unequal_and_pure_answerability_groups_preserve_labels(base_records: list[dict]) -> None:
    for index, record in enumerate(base_records):
        record["source_title"] = f"Unequal {index // 5}" if index < 40 else f"Single {index}"
    result = split_base_records(base_records)
    assert validate_split(base_records, result)["title_overlap_count"] == 0
    for name, ratio in zip(SPLIT_NAMES, (0.65, 0.10, 0.25), strict=True):
        subset = [r for r in result if r["research_split"] == name]
        assert abs(len(subset) - len(result) * ratio) <= 5
        assert abs(sum(r["is_answerable"] for r in subset) - 100 * ratio) <= 5


def test_unicode_and_case_variants_share_group_without_changing_raw_titles(
    base_records: list[dict],
) -> None:
    base_records[0]["source_title"] = "The Dragon (Beowulf)"
    base_records[1]["source_title"] = "The dragon (Beowulf)"
    base_records[2]["source_title"] = "CAFÉ"
    base_records[3]["source_title"] = "cafe\u0301"
    result = split_base_records(base_records)
    assert validate_split(base_records, result)["group_overlap_count"] == 0
    by_id = {r["record_id"]: r for r in result}
    for left, right in ((0, 1), (2, 3)):
        assert (
            by_id[base_records[left]["record_id"]]["research_split"]
            == (by_id[base_records[right]["record_id"]]["research_split"])
        )
    assert {r["source_title"] for r in result} == {r["source_title"] for r in base_records}


@pytest.mark.parametrize("defect", ["missing", "duplicate", "leak", "metadata"])
def test_split_validation_rejects_coverage_leaks_and_metadata_changes(
    base_records: list[dict],
    defect: str,
) -> None:
    result = split_base_records(base_records)
    if defect == "missing":
        result.pop()
    elif defect == "duplicate":
        result.append(copy.deepcopy(result[0]))
    elif defect == "metadata":
        result[0]["question"] = "Changed by split"
    else:
        peer = next(r for r in result[1:] if r["source_title"] == result[0]["source_title"])
        peer["research_split"] = next(n for n in SPLIT_NAMES if n != peer["research_split"])
    with pytest.raises(SplitValidationError):
        validate_split(base_records, result)


@pytest.mark.parametrize(
    "field,value",
    [
        ("research_split", "evaluation"),
        ("is_answerable", 1),
        ("source_split", "test"),
        ("source_title", " "),
        ("source_revision", "b" * 40),
        ("derived_from_id", "parent"),
    ],
)
def test_base_validation_rejects_invalid_or_already_split_qa(
    base_records: list[dict],
    field: str,
    value: object,
) -> None:
    base_records[0][field] = value
    with pytest.raises(SplitValidationError):
        validate_base_records(base_records)


def test_frozen_outputs_are_portable_and_keep_base_bytes(
    base_records: list[dict],
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "base.jsonl"
    base_payload = _write_base(input_path, base_records)
    outputs = tmp_path / "first"
    manifest_path = tmp_path / "manifest.json"
    first = generate_research_split(input_path, outputs, manifest_path, require_public_counts=False)
    manifest_bytes = manifest_path.read_bytes()
    assert input_path.read_bytes() == base_payload
    assert first["input"]["sha256"] == hashlib.sha256(base_payload).hexdigest()
    for filename, info in first["outputs"].items():
        payload = (outputs / filename).read_bytes()
        assert info == {"sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)}
        assert b"\r\n" not in payload
    split_ids = []
    for name in SPLIT_NAMES:
        rows = [
            json.loads(line) for line in (outputs / f"{name}.jsonl").read_text("utf-8").splitlines()
        ]
        assert all(r["research_split"] == name for r in rows)
        assert [r["record_id"] for r in rows] == first["record_ids_by_split"][name]
        split_ids.extend(r["record_id"] for r in rows)
    assert len(split_ids) == len(set(split_ids)) == len(base_records)
    assert (
        generate_research_split(
            input_path,
            outputs,
            manifest_path,
            require_public_counts=False,
        )
        == first
    )
    second_path = tmp_path / "second_manifest.json"
    assert (
        generate_research_split(
            input_path,
            tmp_path / "second",
            second_path,
            require_public_counts=False,
        )
        == first
    )
    assert second_path.read_bytes() == manifest_bytes


def test_conflicts_are_rejected_before_any_output_is_written(
    base_records: list[dict],
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "base.jsonl"
    _write_base(input_path, base_records)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_bytes(b"existing manifest\n")
    outputs = tmp_path / "outputs"
    with pytest.raises(SplitValidationError, match="Frozen artifact differs"):
        generate_research_split(input_path, outputs, manifest_path, require_public_counts=False)
    assert not outputs.exists()
    assert manifest_path.read_bytes() == b"existing manifest\n"


def test_public_counts_and_input_output_aliases_are_rejected(
    base_records: list[dict],
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "qa.jsonl"
    payload = _write_base(input_path, base_records)
    with pytest.raises(SplitValidationError, match="Public source counts"):
        generate_research_split(input_path, tmp_path / "output", tmp_path / "manifest.json")
    with pytest.raises(SplitValidationError, match="distinct"):
        generate_research_split(input_path, tmp_path, tmp_path / "manifest.json")
    with pytest.raises(SplitValidationError, match="new dataset version"):
        generate_research_split(input_path, seed=43, require_public_counts=False)
    assert input_path.read_bytes() == payload


def test_public_processed_qa_split_matches_fixed_source_counts() -> None:
    if not DEFAULT_BASE_QA_PATH.is_file():
        pytest.skip("Phase 2 base QA is not prepared")
    records = [json.loads(line) for line in DEFAULT_BASE_QA_PATH.read_text("utf-8").splitlines()]
    validate_base_records(records, require_public_counts=True)
    result = split_base_records(records)
    assert validate_split(records, result)["record_count"] == 4_345
    assert len({r["source_title"] for r in result}) == 3_799
    assert len({title_group_key(r["source_title"]) for r in result}) == 3_798
    assert sum(r["is_answerable"] for r in result) == 2_254
