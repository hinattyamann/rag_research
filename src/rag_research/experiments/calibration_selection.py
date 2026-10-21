"""Reserve unused calibration QA without rebranding retrieval-tuned English QA."""

from pathlib import Path

from rag_research.data.study_assets import load_assets, load_rows, verify_file
from rag_research.experiments.development_selection import (
    INVENTORY_ROOTS,
    LEGACY_RULE,
    used_inventory,
)
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.storage import read_json
from rag_research.retrieval.common import file_hash

ROOT = Path(__file__).resolve().parents[3]
METHOD = "phase11-new-calibration-reservation-one-qa-per-group-sha256-v1"
SOURCE_SPLITS = {"en": "development", "ja": "calibration"}
USAGE_ROOTS = [*INVENTORY_ROOTS, "data/runs/bilingual_calibration"]


def select_rows(rows, language, used_ids, reserved_groups, *, count=20, seed=42, exposed_groups=()):
    require(language in SOURCE_SPLITS and type(count) is int and count > 0 and
            type(seed) is int and seed >= 0, "Invalid calibration reservation parameters")
    require(rows and all(isinstance(r["record_id"], str) and r["record_id"] for r in rows) and
            len({r["record_id"] for r in rows}) == len(rows), "Duplicate or missing calibration source IDs")
    require(all(r["research_split"] == SOURCE_SPLITS[language] and r["language"] == language and
                isinstance(r["document_group_id"], str) and r["document_group_id"] and
                type(r["is_answerable"]) is bool for r in rows), "Wrong calibration reservation source split/language")
    used_groups = {r["document_group_id"] for r in rows if r["record_id"] in used_ids} | set(exposed_groups)
    excluded = used_groups | set(reserved_groups)
    eligible = [r for r in rows if r["is_answerable"] and r["record_id"] not in used_ids and
                r["document_group_id"] not in excluded]

    def rank(row):
        return digest([METHOD, seed, language, row["record_id"]]), row["record_id"]

    chosen, groups = [], set()
    for row in sorted(eligible, key=rank):
        if row["document_group_id"] in groups:
            continue
        chosen.append({"record_id": row["record_id"], "document_group_id": row["document_group_id"],
                       "selection_rank_sha256": rank(row)[0]})
        groups.add(row["document_group_id"])
        if len(chosen) == count:
            break
    require(len(chosen) == count, "Insufficient unused calibration groups; never refill from used groups")
    return {"language": language, "analysis_split": "calibration", "source_split": SOURCE_SPLITS[language],
            "planned_qa": count, "selected": chosen, "population_qa": len(rows),
            "source_answered_qa": sum(r["is_answerable"] for r in rows),
            "excluded_used_source_qa": sum(r["record_id"] in used_ids for r in rows),
            "excluded_used_source_groups": sorted(used_groups), "excluded_reserved_groups": sorted(reserved_groups),
            "eligible_source_answered_qa": len(eligible),
            "eligible_groups": len({r["document_group_id"] for r in eligible}),
            "selected_group_overlap_with_used_or_reserved": len(groups & excluded)}


def prepare(policy_path, *, root=ROOT):
    policy_path = Path(policy_path)
    policy = read_json(policy_path)
    require(policy["schema_version"] == 1 and policy["purpose"] == "phase11-new-calibration-reservation-policy" and
            policy["method"] == METHOD and policy["analysis_split"] == "calibration" and
            policy["source_splits"] == SOURCE_SPLITS and policy["count_per_language"] == 20 and
            policy["seed"] == 42 and policy["inventory_roots"] == USAGE_ROOTS and
            policy["legacy_identity_rule"] == LEGACY_RULE and policy["automatic_refill"] is False and
            policy["candidate_execution_allowed"] is False and policy["phase12_allowed"] is False,
            "Preserve the preregistered new-calibration reservation policy")
    asset_path = verify_file(policy["assets"], root)
    assets = load_assets(asset_path, root=root)
    main_path = verify_file(policy["main_development_selection"], root)
    main = read_json(main_path)
    require(main["purpose"] == "phase11-main-development-preselected-ids-not-execution-approval" and
            main["assets_sha256"] == file_hash(asset_path) and set(main["languages"]) == {"en", "ja"},
            "Main Development reservation identity differs")
    group_path = verify_file(policy["japanese_group_metadata"], root)
    group_rows = read_json(group_path)
    preview_reserved = {g["group_id"] for g in group_rows if g["development_reserved"]}
    require(preview_reserved and len({g["group_id"] for g in group_rows}) == len(group_rows), "Japanese reservation registry differs")
    retrieval_path = verify_file(policy["prior_english_retrieval_calibration"], root)
    retrieval = read_json(retrieval_path)
    retrieval_ids = retrieval["record_ids"]
    require(retrieval["purpose"] == "calibration-not-final-evaluation" and retrieval["split"] == "calibration" and
            retrieval["qa_sha256"] == assets["datasets"]["en"]["qa"]["calibration"]["sha256"] and
            retrieval_ids and all(isinstance(i, str) and i for i in retrieval_ids) and
            retrieval["sample_count"] == len(set(retrieval_ids)) == len(retrieval_ids),
            "Prior English retrieval exposure is not verified")
    development, source_rows, hashes = {}, {}, {}
    for language in ("en", "ja"):
        development[language], path = load_rows(assets, language, "development", root=root)
        hashes[path.relative_to(root).as_posix()] = file_hash(path)
        if SOURCE_SPLITS[language] == "development":
            source_rows[language] = development[language]
        else:
            source_rows[language], path = load_rows(assets, language, SOURCE_SPLITS[language], root=root)
            hashes[path.relative_to(root).as_posix()] = file_hash(path)
            require(not {r["document_group_id"] for r in source_rows[language]} &
                    {r["document_group_id"] for r in development[language]}, "Japanese source split groups overlap")
    old_english, path = load_rows(assets, "en", "calibration", root=root)
    hashes[path.relative_to(root).as_posix()] = file_hash(path)
    require({r["record_id"] for r in old_english if r["is_answerable"]} == set(retrieval_ids) and
            not {r["document_group_id"] for r in old_english} &
            {r["document_group_id"] for r in development["en"]},
            "English historical retrieval IDs or source split groups differ")
    used_ids, usage_hashes, legacy = used_inventory(root, development_rows=development["en"] + development["ja"],
                                                   inventory_roots=USAGE_ROOTS)
    used_ids |= set(retrieval_ids)
    exposed = {g for item in legacy for g in item["conservatively_excluded_english_groups"]}
    languages = {}
    for language, rows in source_rows.items():
        selected = main["languages"][language]["selected"]
        require(main["languages"][language]["planned_qa"] == len(selected) == 20 and
                len({r["record_id"] for r in selected}) == len({r["document_group_id"] for r in selected}) == 20,
                "Main Development must keep all 20 reserved groups")
        by_id = {r["record_id"]: r["document_group_id"] for r in development[language]}
        require(all(by_id.get(r["record_id"]) == r["document_group_id"] for r in selected), "Main reservation source changed")
        reserved = {r["document_group_id"] for r in selected} | (preview_reserved if language == "ja" else set())
        languages[language] = select_rows(rows, language, used_ids, reserved,
                                         exposed_groups=exposed if language == "en" else ())
    bindings = {key: policy[key] for key in ("assets", "main_development_selection", "japanese_group_metadata",
                                             "prior_english_retrieval_calibration")}
    return {"schema_version": 1, "purpose": "phase11-new-calibration-preselected-reservation-not-execution-approval",
            "method": METHOD, "analysis_split": "calibration", "source_splits": SOURCE_SPLITS,
            "seed": 42, "languages": languages, "policy_sha256": file_hash(policy_path), "inputs": bindings,
            "source_qa_sha256": hashes, "used_baseline_input_sha256": usage_hashes,
            "used_or_retrieval_exposed_unique_ids": sorted(used_ids),
            "prior_english_retrieval_used_qa": len(retrieval_ids),
            "legacy_custom_query_identity_resolution": legacy,
            "original_source_splits_unchanged": True, "reservation_is_not_a_main_development_result": True,
            "selection_does_not_use": ["question_or_reference_text", "model_answers", "quality_labels", "internal_F",
                                       "gold_coverage", "evaluation_qa_rows"],
            "question_text_use_exception": "Only known legacy Phase5 custom questions are matched to Development identity; source question text never enters ranking",
            "unused_scope": "Recorded baseline/retrieval QA usage, native Japanese preview closure and main Development group reservations; not a proof about unrecorded external use or model pretraining",
            "model_completion_attempts": 0, "execution_protocol_and_passing_main_evidence_required": True,
            "gate11_passed": False, "phase12_allowed": False}
