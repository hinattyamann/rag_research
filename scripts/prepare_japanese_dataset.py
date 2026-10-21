"""Adapt fixed Japanese QA and prepare source-only audits or complete-snapshot splits."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.data.baobab_source import (  # noqa: E402
    DATASET_ID,
    REVISION,
    SOURCE_FILES,
    article_titles,
    load_source,
)
from rag_research.data.japanese_dataset import (  # noqa: E402
    SPLITS,
    assign_splits,
    connected_groups,
    group_statistics,
    json_bytes,
    normalize_answered,
    publish_immutable,
    read_complete_snapshot,
    validate_assignments,
    validate_spec,
)
from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.storage import read_json, run_lock  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def prepare(source_dir, output, spec_path, *, snapshot=None):
    spec = read_json(spec_path)
    validate_spec(spec)
    reservation_path = (ROOT / spec["development_reservation_manifest"]).resolve()
    require(reservation_path.is_relative_to(ROOT), "Reservation manifest escapes repository")
    reservation = read_json(reservation_path)
    require(reservation["dataset_id"] == DATASET_ID and reservation["source_revision"] == REVISION,
            "Japanese reservation source mismatch")
    reserved = reservation["development_reservation"]["reserved_source_ids"]
    chunks = load_source(source_dir)
    require(len(chunks["answered.jsonl"]) == 838 and len(chunks["not_answered.jsonl"]) == 433,
            "Pinned Japanese population changed")
    articles = []
    if snapshot is not None:
        with run_lock(snapshot):
            _, articles = read_complete_snapshot(snapshot, expected_titles=article_titles(chunks))
        require(not any(r["status"] == "error" for r in articles),
                "Unresolved article acquisition errors prevent final identity Group split")
    groups = connected_groups(chunks["answered.jsonl"], reserved_source_ids=reserved, articles=articles)
    assignments = assign_splits(groups, spec) if snapshot is not None else None
    mapping = {identifier: g["group_id"] for g in groups for identifier in g["source_ids"]}
    raw_lines = (source_dir / "answered.jsonl").read_bytes().splitlines(keepends=True)
    records = []
    for index, (row, line) in enumerate(zip(chunks["answered.jsonl"], raw_lines, strict=True)):
        record = normalize_answered(row, raw_line=line, line_index=index)
        record["document_group_id"] = mapping[row["id"]]
        if assignments is not None:
            record["research_split"] = assignments[record["document_group_id"]]
        records.append(record)
    records.sort(key=lambda r: r["record_id"])
    def encode_rows(rows):
        return b"".join(
            (json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
            for r in rows)
    qa_bytes = encode_rows(records)
    artifacts = {output / "qa.jsonl": qa_bytes, output / "groups.json": json_bytes(groups)}
    if assignments is not None:
        for name in SPLITS:
            artifacts[output / f"{name}.jsonl"] = encode_rows(r for r in records if r["research_split"] == name)
    code_paths = [Path(__file__), ROOT / "src/rag_research/data/japanese_dataset.py",
                  ROOT / "src/rag_research/data/baobab_source.py", spec_path]
    report = {"schema_version": 1, "purpose": "phase11-japanese-qa-group-preparation-not-final-freeze",
              "stage": "complete_snapshot_groups" if snapshot is not None else "source_title_audit_only",
              "dataset_id": DATASET_ID, "source_revision": REVISION, "spec": spec,
              "source_files_sha256": SOURCE_FILES,
              "reservation_manifest_sha256": file_hash(reservation_path),
              "source_code_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in code_paths},
              "article_identities_verified": snapshot is not None,
              "snapshot_plan_sha256": file_hash(snapshot / "plan.json") if snapshot is not None else None,
              "snapshot_article_statuses": {status: sum(r["status"] == status for r in articles)
                                            for status in ("ok", "unavailable", "error")},
              "statistics": group_statistics(groups, assignments),
              "group_validation": validate_assignments(groups, assignments) if assignments else None,
              "artifacts": {p.name: {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}
                            for p, b in artifacts.items()},
              "gold_passage_mapping_status": "pending_passage_build",
              "source_answerable_does_not_imply_corpus_coverage": True,
              "new_model_calls": 0, "gate11_passed": False, "phase12_allowed": False}
    # Execution dates are deliberately outside deterministic dataset bytes.
    artifacts[output / "report.json"] = json_bytes(report)
    publish_immutable(artifacts)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["audit-source", "build"])
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--snapshot-dir", type=Path)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/phase11_japanese_dataset_v1.json")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    require(output.is_relative_to(ROOT / "data/processed/wikipedia_human_retrieval_ja"),
            "Choose a new Japanese processed dataset directory")
    require(args.config.resolve().is_relative_to(ROOT), "Dataset config escapes repository")
    require((args.stage == "build") == (args.snapshot_dir is not None),
            "Build needs a complete historical snapshot; source audit must not pretend to use one")
    snapshot = args.snapshot_dir.resolve() if args.snapshot_dir is not None else None
    require(snapshot is None or (snapshot / "plan.json").is_file(), "Missing historical snapshot plan")
    with run_lock(output):
        report = prepare(args.source_dir.resolve(), output, args.config.resolve(), snapshot=snapshot)
    print(json.dumps({"stage": report["stage"], "statistics": report["statistics"],
                      "article_identities_verified": report["article_identities_verified"],
                      "gold_passage_mapping_status": report["gold_passage_mapping_status"],
                      "model_calls": 0, "gate11_passed": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
