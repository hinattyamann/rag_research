"""Select new Development groups without using model output, quality, or gold coverage."""

import json
import unicodedata
from pathlib import Path

from rag_research.data.study_assets import load_assets, load_rows, local_path
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.storage import read_json
from rag_research.retrieval.common import file_hash

ROOT = Path(__file__).resolve().parents[3]
INVENTORY_ROOTS = ["data/runs/phase5", "data/runs/phase6", "data/runs/pilot",
                   "data/runs/calibration", "data/runs/bilingual_development"]
METHOD = "phase11-main-development-one-qa-per-group-sha256-v1"
LEGACY_RULE = "Phase5 custom queries with null QA ID: exact Development question match plus conservative exclusion of all used/retrieved English title groups; never invent source IDs or silently skip unresolved schema"


def used_inventory(root=ROOT, *, development_rows=()):
    """Include failures and pre-call journals conservatively; never inspect internal F."""
    paths = set()
    for name in INVENTORY_ROOTS:
        folder = local_path(name, root)
        for pattern in ("answers.jsonl", "record.json"):
            paths.update(folder.rglob(pattern))
    require(paths, "No prior baseline inventory; do not claim unused QA")
    identifiers, hashes, legacy = set(), {}, []
    by_question = {}
    for row in development_rows:
        by_question.setdefault(row["question"], []).append(row["record_id"])
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        require("evaluation" not in relative.casefold(), "Evaluation must not enter usage inventory")
        if path.name == "answers.jsonl":
            rows = [json.loads(line) for line in path.read_text("utf-8").splitlines()]
        else:
            rows = [read_json(path)]
        for row in rows:
            if (isinstance(row, dict) and row.get("record_id") is None and
                    relative.startswith("data/runs/phase5/") and isinstance(row.get("question"), str) and
                    row["question"].strip()):
                require(development_rows, "Legacy custom questions need Development identity resolution")
                contexts = row.get("used_context", []) + row.get("retrieved_context", [])
                require(contexts and all(isinstance(d, dict) and isinstance(d.get("title"), str) and d["title"].strip() for d in contexts),
                        "Legacy custom question has no resolvable source titles")
                matched = by_question.get(row["question"], [])
                identifiers.update(matched)
                exposed = sorted({"clapnq-title:" + unicodedata.normalize("NFC", d["title"]).casefold() for d in contexts})
                legacy.append({"path": relative, "question_sha256": digest(row["question"]),
                               "exact_question_matched_development_ids": sorted(matched),
                               "conservatively_excluded_english_groups": exposed,
                               "scope": "legacy Phase5 custom query without QA ID; no invented ID"})
                continue
            require(isinstance(row, dict) and isinstance(row.get("record_id"), str) and row["record_id"],
                    "Unrecognized baseline journal; preserve and investigate")
            identifiers.add(row["record_id"])
        hashes[relative] = file_hash(path)
    return identifiers, hashes, legacy


def select_rows(rows, language, used_ids, reserved_groups, *, count=20, seed=42, extra_used_groups=()):
    require(language in {"en", "ja"} and type(count) is int and count > 0 and
            type(seed) is int and seed >= 0, "Invalid Development selection parameters")
    require(rows and len({r["record_id"] for r in rows}) == len(rows), "Duplicate or missing Development IDs")
    require(all(r["research_split"] == "development" and r["language"] == language and
                isinstance(r["document_group_id"], str) and r["document_group_id"] and
                type(r["is_answerable"]) is bool for r in rows), "Only one language of Development is allowed")
    used_groups = {r["document_group_id"] for r in rows if r["record_id"] in used_ids} | set(extra_used_groups)
    excluded_groups = used_groups | set(reserved_groups)
    available = [r for r in rows if r["is_answerable"] and r["record_id"] not in used_ids and
                 r["document_group_id"] not in excluded_groups]

    def rank(row):
        return digest([METHOD, seed, language, row["record_id"]]), row["record_id"]

    chosen, groups = [], set()
    for row in sorted(available, key=rank):
        if row["document_group_id"] in groups:
            continue
        chosen.append({"record_id": row["record_id"], "document_group_id": row["document_group_id"],
                       "selection_rank_sha256": rank(row)[0]})
        groups.add(row["document_group_id"])
        if len(chosen) == count:
            break
    require(len(chosen) == count, "Insufficient new Development groups; do not refill from used groups")
    return {"language": language, "planned_qa": count, "selected": chosen,
            "population_qa": len(rows), "source_answered_qa": sum(r["is_answerable"] for r in rows),
            "excluded_used_development_qa": sum(r["record_id"] in used_ids for r in rows),
            "excluded_used_development_groups": sorted(used_groups),
            "excluded_reserved_groups": sorted(reserved_groups),
            "eligible_source_answered_qa": len(available),
            "eligible_groups": len({r["document_group_id"] for r in available}),
            "selected_group_overlap_with_used_or_reserved": len(groups & excluded_groups)}


def prepare(policy_path, *, root=ROOT):
    policy_path = Path(policy_path)
    policy = read_json(policy_path)
    require(policy["schema_version"] == 1 and policy["purpose"] == "phase11-main-development-selection-policy" and
            policy["method"] == METHOD and policy["split"] == "development" and
            policy["count_per_language"] == 20 and policy["seed"] == 42 and
            policy["phase12_allowed"] is False and policy["automatic_refill"] is False,
            "Preserve the preregistered Development selection policy")
    asset_path = local_path(policy["assets"]["path"], root)
    require(file_hash(asset_path) == policy["assets"]["sha256"], "Selection assets changed")
    assets = load_assets(asset_path, root=root)
    group_path = local_path(policy["japanese_group_metadata"]["path"], root)
    require(file_hash(group_path) == policy["japanese_group_metadata"]["sha256"], "Japanese reservations changed")
    groups = read_json(group_path)
    reserved = {g["group_id"] for g in groups if g["development_reserved"]}
    require(reserved and len({g["group_id"] for g in groups}) == len(groups), "Invalid Japanese group registry")
    all_rows, qa_hashes = {}, {}
    for language in ("en", "ja"):
        rows, path = load_rows(assets, language, "development", root=root)
        all_rows[language] = rows
        qa_hashes[path.relative_to(root).as_posix()] = file_hash(path)
    used_ids, usage_hashes, legacy = used_inventory(root, development_rows=all_rows["en"] + all_rows["ja"])
    require(not legacy or policy.get("legacy_identity_rule") == LEGACY_RULE,
            "Legacy source-identity resolution must be declared before selection")
    exposed = {group for record in legacy for group in record["conservatively_excluded_english_groups"]}
    languages = {}
    for language, rows in all_rows.items():
        languages[language] = select_rows(rows, language, used_ids, reserved if language == "ja" else set(),
                                         count=policy["count_per_language"], seed=policy["seed"],
                                         extra_used_groups=exposed if language == "en" else ())
    return {"schema_version": 1, "purpose": "phase11-main-development-preselected-ids-not-execution-approval",
            "method": METHOD, "split": "development", "seed": policy["seed"], "languages": languages,
            "policy_sha256": file_hash(policy_path), "assets_sha256": file_hash(asset_path),
            "japanese_group_metadata_sha256": file_hash(group_path), "development_qa_sha256": qa_hashes,
            "used_baseline_input_sha256": usage_hashes, "used_baseline_unique_ids": sorted(used_ids),
            "legacy_custom_query_identity_resolution": legacy,
            "exclusion_scope": "all recorded baseline answers and journals in explicit Phase5/6/pilot/calibration/bilingual roots plus Japanese preview-group closure",
            "selection_does_not_use": ["model_answers", "quality_labels", "internal_F", "gold_coverage", "evaluation_qa_rows"],
            "model_completion_attempts": 0, "candidate_not_yet_adopted": True,
            "main_execution_protocol_required": True, "gate11_passed": False, "phase12_allowed": False}
