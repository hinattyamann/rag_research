"""Hash-bound bilingual assets; offline QA stays separate from inference strings."""

import json
import unicodedata
from copy import deepcopy
from pathlib import Path

from rag_research.experiments.frozen_trace import require
from rag_research.retrieval.common import file_hash, read_json

ROOT = Path(__file__).resolve().parents[3]


def local_path(value, root=ROOT):
    require(isinstance(value, str) and value and not Path(value).is_absolute(), "Asset path must be repository relative")
    path = (root / value).resolve()
    require(path.is_relative_to(root.resolve()), "Asset path escapes repository")
    return path


def verify_file(binding, root=ROOT):
    require(set(binding) >= {"path", "sha256"}, "Asset file binding missing")
    path = local_path(binding["path"], root)
    require(file_hash(path) == binding["sha256"], "Study asset file changed: " + binding["path"])
    return path


def load_assets(path, *, root=ROOT):
    value = read_json(Path(path))
    require(value.get("schema_version") == 1 and value.get("purpose") == "phase11-bilingual-assets-candidate" and
            value.get("status") == "candidate_not_frozen" and value.get("phase12_allowed") is False and
            set(value.get("datasets", {})) == {"en", "ja"}, "Unsupported bilingual asset registry")
    for language, data in value["datasets"].items():
        require(data["language"] == language and set(data["qa"]) == {"development", "calibration", "evaluation"},
                "Dataset language/split registry differs")
        require(data["source_dataset"] == ("CLAPNQ" if language == "en" else
                "baobab-trees/wikipedia-human-retrieval-ja"), "Dataset identity differs from language")
        # File hashes may include Evaluation metadata; its question/answer rows are not loaded.
        for binding in [*data["qa"].values(), data["corpus"], data["parent_map"], *data["indexes"].values()]:
            verify_file(binding, root)
        require(set(data["indexes"]) == {"bm25", "embedding"}, "Both corpus indexes are required")
    for binding in value["fixed_files"]:
        verify_file(binding, root)
    require(value["fixed_files"] and len({b["path"] for b in value["fixed_files"]}) == len(value["fixed_files"]),
            "Missing/duplicate fixed asset bindings")
    embedding = value["embedding"]
    require(embedding["provider"] == "cuda" and embedding["device_id"] == 0 and embedding["use_tf32"] == 0 and
            type(embedding["threads"]) is int and embedding["threads"] > 0, "Embedding runtime conditions changed")
    selection = value["retrieval"]
    require(selection["kind"] == "hybrid" and
            all(type(selection[k]) is int and selection[k] > 0 for k in ("candidate_count", "rrf_constant", "top_k"))
            and selection["top_k"] <= selection["candidate_count"], "Invalid shared retrieval selection")
    return value


def load_rows(assets, language, split, *, root=ROOT):
    require(language in {"en", "ja"} and split in {"development", "calibration"},
            "Phase 11 loads Development/Calibration only")
    data = assets["datasets"][language]
    path = verify_file(data["qa"][split], root)
    rows = [json.loads(line) for line in path.read_text("utf-8").splitlines()]
    require(rows and len({r["record_id"] for r in rows}) == len(rows), "Missing/duplicate QA IDs")
    result = []
    for original in rows:
        require(original["research_split"] == split and original["source_dataset"] == data["source_dataset"] and
                isinstance(original["question"], str) and original["question"].strip(), "QA identity/split differs")
        row = deepcopy(original)
        row["language"] = language
        if language == "en":
            row["gold_parent_ids"] = list(row["gold_passage_ids"])
            row["unavailable_cited_reference_ids"] = []
            row["document_group_id"] = "clapnq-title:" + unicodedata.normalize("NFC", row["source_title"]).casefold()
        else:
            require(row.get("gold_passage_mapping_status") == "audited_cited_article_and_source_reference_markup_mapping_v2"
                    and row.get("reference_corpus_metadata_offline_only") is True,
                    "Japanese QA needs the verified source projection audit")
        result.append(row)
    return result, path


def parent_map(assets, language, *, root=ROOT):
    data = assets["datasets"][language]
    path = verify_file(data["parent_map"], root)
    mapping = {}
    with path.open() as stream:
        for line in stream:
            row = json.loads(line)
            for child in row["child_passage_ids"]:
                require(child not in mapping, "Duplicate child in parent relevance map")
                mapping[child] = row["parent_passage_id"]
    require(bool(mapping), "Empty parent relevance map")
    return mapping
