"""Check new pooled statistics against all frozen questions and original outputs."""

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
SPEC = importlib.util.spec_from_file_location("pooled_results", HERE / "derive_pooled_results.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.fixture(scope="module")
def result():
    return MODULE.derive()


def test_pooled_reproduces_saved_data_and_every_source_hash(result):
    saved = json.loads((PAPER / "notes/pooled_results_v1.json").read_text(encoding="utf-8"))
    assert result == saved
    assert result["post_hoc"] is True
    assert result["new_inference_calls"] == result["new_annotation_calls"] == 0
    for relative, digest in result["source_sha256"].items():
        assert hashlib.sha256((PAPER / relative).read_bytes()).hexdigest() == digest, relative


def test_pooled_population_and_means_reconcile_original_qa_rows(result):
    packages = [PAPER / "materials/fixed_v23_v1"] + [
        PAPER / "materials/cal_extension_v1" / f"batch_{i:02d}" for i in (1, 2, 3)
    ]
    rows = []
    for package in packages:
        with (package / "qa_summary.csv").open(encoding="utf-8", newline="") as stream:
            rows.extend(csv.DictReader(stream))
    assert len({r["record_id"] for r in rows}) == len(rows) == 200
    for summary in result["primary"]:
        selected = [r for r in rows if r["language"] == summary["language"]]
        comparable = [r for r in selected if r["comparable"] == "True"]
        assert len(selected) == summary["selected_qa"] == 100
        assert len(comparable) == summary["comparable_qa"]
        assert summary["mean_increment"] == pytest.approx(
            sum(float(r["increment"]) for r in comparable) / len(comparable)
        )
        assert sum(r["initial_status"] == "error" for r in selected) == summary["initial_failures"]
        assert sum(r["rewrite_status"] == "error" for r in selected) == summary["rewrite_failures"]
        threshold = next(
            r
            for r in result["thresholds"]
            if r["language"] == summary["language"] and r["threshold"] == 0.7
        )
        assert threshold["mean_increment"] == pytest.approx(summary["mean_increment"])
    assert [r["comparable_qa"] for r in result["primary"]] == [80, 68]
    assert sum(r["rewrite_failures"] for r in result["primary"]) == 4


def test_bootstrap_keeps_whole_document_groups_and_question_weights():
    class FixedDraws:
        def integers(self, low, high, size):
            assert low == 0 and high == 2 and size == (3, 2)
            return np.array([[0, 1], [0, 0], [1, 1]])

    # Group a has two QA, group b one. Resampling groups must not average their
    # averages or turn the three QA into independent resampling units.
    records = [
        {"document_group_id": "a", "increment": 1.0},
        {"document_group_id": "a", "increment": 0.0},
        {"document_group_id": "b", "increment": 0.0},
    ]
    actual = MODULE.grouped_bootstrap(records, FixedDraws(), repetitions=3)
    assert actual.tolist() == pytest.approx([1 / 3, 1 / 2, 0])


def test_disagreement_counts_pairs_without_double_counting_original():
    assert MODULE.disagreement(["accept", "accept", "rewrite", "rewrite", "rewrite"]) == 0.6
    assert MODULE.disagreement(["accept"] * 5) == 0
    with pytest.raises(ValueError):
        MODULE.disagreement(["accept", None])
    with pytest.raises(ValueError):
        MODULE.disagreement(["accept"])
