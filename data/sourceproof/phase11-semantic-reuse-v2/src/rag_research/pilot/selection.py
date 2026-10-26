"""Outcome-independent sample selection with explicit exclusion of inspected titles."""

import hashlib
import json
import unicodedata

from rag_research.experiments.frozen_trace import require
from rag_research.experiments.protocol import ROOT
from rag_research.experiments.storage import read_json, write_json
from rag_research.retrieval.common import file_hash


def title_key(value):
    require(isinstance(value, str) and bool(value.strip()), "Missing source title")
    return unicodedata.normalize("NFC", value).casefold()


def select_rows(rows, excluded_ids, count, seed):
    require(type(count) is int and count > 0 and type(seed) is int and seed >= 0, "Invalid selection")
    require(all(r["research_split"] == "development" for r in rows), "Development only")
    require(len({r["record_id"] for r in rows}) == len(rows), "Duplicate QA ID")
    lookup = {r["record_id"]: r for r in rows}
    require(set(excluded_ids) <= set(lookup), "Unknown inspected ID")
    banned = {title_key(lookup[i]["source_title"]) for i in excluded_ids}
    eligible = [r for r in rows if r["is_answerable"] and
                title_key(r["source_title"]) not in banned and r["record_id"] not in excluded_ids]
    eligible.sort(key=lambda r: hashlib.sha256(f"{seed}:{r['record_id']}".encode()).hexdigest())
    chosen, seen = [], set()
    for row in eligible:
        key = title_key(row["source_title"])
        if key not in seen:
            chosen.append(row)
            seen.add(key)
        if len(chosen) == count:
            break
    require(len(chosen) == count, "Not enough eligible unique titles")
    return chosen


def freeze_selection(config, path):
    qa_path = ROOT / config["qa_path"]
    rows = list(map(json.loads, qa_path.read_text("utf-8").splitlines()))
    inspected = set()
    excluded_sources = {}
    baseline = ROOT / config["exclude_baseline"]
    inspected.update(r["record_id"] for r in map(json.loads, baseline.read_text("utf-8").splitlines()))
    excluded_sources[baseline.relative_to(ROOT).as_posix()] = file_hash(baseline)
    for name in config.get("exclude_selection_manifests", []):
        source = (ROOT / name).resolve()
        require(source.is_relative_to(ROOT / "data/manifests"), "Selection exclusion escapes manifests")
        previous = read_json(source)
        require(previous["qa_sha256"] == file_hash(qa_path), "Excluded selection uses different data")
        inspected.update(r["record_id"] for r in previous["records"])
        excluded_sources[source.relative_to(ROOT).as_posix()] = file_hash(source)
    for trace_path in sorted((ROOT / "data/runs/order_sensitivity").glob("*/*/trace.json")):
        inspected.add(read_json(trace_path)["record_id"])
        excluded_sources[trace_path.relative_to(ROOT).as_posix()] = file_hash(trace_path)
    chosen = select_rows(rows, inspected, config["count"], config["selection_seed"])
    value = {"schema_version": 1, "purpose": "phase10-preselected-before-model-results",
             "study_version": config["study_version"], "qa_sha256": file_hash(qa_path),
             "selection_seed": config["selection_seed"], "count": len(chosen),
             "selection_rule": "sha256(seed:record_id)_ascending_first_unique_NFC_casefold_title",
             "excluded_ids": sorted(inspected), "excluded_sources_sha256": excluded_sources,
             "one_question_per_title": True, "replace_failed_questions": False,
             "records": [{k: row[k] for k in ("record_id", "question", "source_title")} for row in chosen]}
    if path.exists():
        require(read_json(path) == value, "Selection changed; preserve original and use a new version")
    else:
        write_json(path, value)
    return value
