"""Unused calibration reservations exclude prior retrieval and Development exposure."""

from copy import deepcopy

import pytest

from rag_research.experiments import calibration_selection as selection
from rag_research.experiments.development_selection import LEGACY_RULE, used_inventory
from rag_research.experiments.storage import write_json
from rag_research.retrieval.common import file_hash


def rows(language="en", split="development", groups=50):
    return [{"record_id": f"{language}:{split}:{i}", "document_group_id": f"{language}:{split}:g{i // 2}",
             "research_split": split, "language": language, "is_answerable": True,
             "question": "QUESTION", "reference_answers": ["REFERENCE"], "gold_parent_ids": []}
            for i in range(2 * groups)]


def test_ranking_never_uses_text_quality_gold_or_input_order_and_closes_used_groups():
    original = rows(groups=8)
    original[0]["is_answerable"] = False
    chosen = selection.select_rows(original, "en", {original[0]["record_id"]},
        {original[2]["document_group_id"]}, count=3, exposed_groups={original[4]["document_group_id"]})
    changed = deepcopy(original[::-1])
    for row in changed:
        row.update(question="DIFFERENT", reference_answers=["OTHER"], gold_parent_ids=["AVAILABLE"],
                   answer="MODEL ANSWER", F=1, quality=1)
    assert selection.select_rows(changed, "en", {original[0]["record_id"]},
        {original[2]["document_group_id"]}, count=3, exposed_groups={original[4]["document_group_id"]}) == chosen
    assert not {r["document_group_id"] for r in chosen["selected"]} & {
        original[i]["document_group_id"] for i in [0, 2, 4]}


@pytest.mark.parametrize("own", ["own", "collection/en"])
def test_resume_inventory_exclusion_is_explicit_and_never_hides_another_run(tmp_path, own):
    paths = {"history": "data/runs/phase6/old/record.json", "own": f"data/runs/bilingual_calibration/{own}/baseline/a/record.json",
        "other": "data/runs/bilingual_calibration/other/baseline/a/record.json"}
    if "/" in own:
        paths["sibling"] = "data/runs/bilingual_calibration/collection/ja/baseline/a/record.json"
    for record_id, name in paths.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, {"record_id": record_id, "status": "started"})
    ids, hashes, _ = used_inventory(tmp_path, inventory_roots=selection.USAGE_ROOTS)
    assert ids == set(paths) and len(hashes) == len(paths)
    ids, hashes, _ = used_inventory(tmp_path, inventory_roots=selection.USAGE_ROOTS,
        excluded_resume_runs=["data/runs/bilingual_calibration/" + own])
    assert ids == set(paths) - {"own"} and len(hashes) == len(paths) - 1
    for name in ["data/runs/bilingual_calibration", "data/runs/phase6", "../outside"]:
        with pytest.raises(ValueError, match="validated Calibration"):
            used_inventory(tmp_path, inventory_roots=selection.USAGE_ROOTS, excluded_resume_runs=[name])


def test_reservation_rejects_wrong_source_split_language_duplicates_and_group_shortfall():
    for language, split in [("en", "calibration"), ("en", "evaluation"), ("ja", "development")]:
        with pytest.raises(ValueError, match="source split"):
            selection.select_rows(rows(language, split), language, set(), set(), count=1)
    duplicate = rows()
    duplicate[1]["record_id"] = duplicate[0]["record_id"]
    with pytest.raises(ValueError, match="Duplicate"):
        selection.select_rows(duplicate, "en", set(), set(), count=1)
    mixed = rows()
    mixed[0]["language"] = "ja"
    with pytest.raises(ValueError, match="source split/language"):
        selection.select_rows(mixed, "en", set(), set(), count=1)
    with pytest.raises(ValueError, match="Insufficient"):
        selection.select_rows(rows(groups=2), "en", set(), set(), count=3)


@pytest.fixture
def reserved(tmp_path, monkeypatch):
    all_rows = {("en", "development"): rows(), ("en", "calibration"): [
        {**rows("en", "calibration")[0], "record_id": "old-retrieval-id"}], ("ja", "development"): rows("ja"),
                ("ja", "calibration"): rows("ja", "calibration")}
    qa_paths = {}
    for key in all_rows:
        p = tmp_path / ("-".join(key) + ".jsonl")
        p.write_text("source identity " + str(key))
        qa_paths[key] = p
    main = {"purpose": "phase11-main-development-preselected-ids-not-execution-approval", "languages": {}}
    for language in ["en", "ja"]:
        main["languages"][language] = {"planned_qa": 20, "selected": [
            {k: r[k] for k in ["record_id", "document_group_id"]}
            for r in all_rows[language, "development"][:40:2]]}
    asset_path = tmp_path / "assets.json"
    write_json(asset_path, {"synthetic": True})
    main["assets_sha256"] = file_hash(asset_path)
    main_path = tmp_path / "main.json"
    write_json(main_path, main)
    group_path = tmp_path / "groups.json"
    write_json(group_path, [{"group_id": "ja:development:g49", "development_reserved": True}])
    retrieval_path = tmp_path / "retrieval.json"
    retrieval = {"purpose": "calibration-not-final-evaluation", "split": "calibration", "qa_sha256": "old-qa-sha",
                 "sample_count": 1, "record_ids": ["old-retrieval-id"]}
    write_json(retrieval_path, retrieval)
    journal = tmp_path / "data/runs/bilingual_calibration/started/baseline/a/record.json"
    journal.parent.mkdir(parents=True)
    write_json(journal, {"record_id": "en:development:40", "status": "started", "completion_attempted": False})
    assets = {"datasets": {"en": {"qa": {"calibration": {"sha256": "old-qa-sha"}}}}}
    calls = []
    monkeypatch.setattr(selection, "load_assets", lambda *args, **kwargs: assets)

    def load_rows(assets, language, split, **kwargs):
        calls.append((language, split))
        assert split != "evaluation"
        return deepcopy(all_rows[language, split]), qa_paths[language, split]

    monkeypatch.setattr(selection, "load_rows", load_rows)
    policy = {"schema_version": 1, "purpose": "phase11-new-calibration-reservation-policy",
        "method": selection.METHOD, "analysis_split": "calibration", "source_splits": selection.SOURCE_SPLITS,
        "count_per_language": 20, "seed": 42, "inventory_roots": selection.USAGE_ROOTS,
        "legacy_identity_rule": LEGACY_RULE, "automatic_refill": False,
        "candidate_execution_allowed": False, "phase12_allowed": False}
    for key, p in [("assets", asset_path), ("main_development_selection", main_path),
                   ("japanese_group_metadata", group_path), ("prior_english_retrieval_calibration", retrieval_path)]:
        policy[key] = {"path": p.name, "sha256": file_hash(p)}
    path = tmp_path / "policy.json"
    write_json(path, policy)
    return tmp_path, path, policy, all_rows, calls


def test_actual_prepare_binds_all_sources_and_never_opens_evaluation(reserved):
    root, path, _, _, calls = reserved
    result = selection.prepare(path, root=root)
    assert calls == [("en", "development"), ("ja", "development"), ("ja", "calibration"), ("en", "calibration")]
    assert result["prior_english_retrieval_used_qa"] == 1
    assert "old-retrieval-id" in result["used_or_retrieval_exposed_unique_ids"]
    assert result["model_completion_attempts"] == 0 and result["original_source_splits_unchanged"]
    for language, row in result["languages"].items():
        assert len(row["selected"]) == len({r["document_group_id"] for r in row["selected"]}) == 20
        assert row["selected_group_overlap_with_used_or_reserved"] == 0
        assert row["source_split"] == selection.SOURCE_SPLITS[language]
    assert "en:development:g20" not in {r["document_group_id"] for r in result["languages"]["en"]["selected"]}


def test_prepare_rejects_policy_drift_changed_bindings_and_cross_split_groups(reserved):
    root, path, policy, source, _ = reserved
    changed = deepcopy(policy)
    changed["source_splits"] = {"en": "calibration", "ja": "calibration"}
    write_json(path, changed)
    with pytest.raises(ValueError, match="policy"):
        selection.prepare(path, root=root)
    write_json(path, policy)
    source["ja", "calibration"][0]["document_group_id"] = "ja:development:g30"
    with pytest.raises(ValueError, match="source split groups overlap"):
        selection.prepare(path, root=root)
    write_json(root / "assets.json", {"changed": True})
    with pytest.raises(ValueError, match="asset file changed"):
        selection.prepare(path, root=root)


def test_retrieval_exposure_proof_and_main_group_identity_must_remain_valid(reserved):
    root, path, policy, _, _ = reserved
    retrieval_path = root / "retrieval.json"
    write_json(retrieval_path, {"purpose": "calibration-not-final-evaluation", "split": "calibration",
        "qa_sha256": "wrong", "sample_count": 1, "record_ids": ["old-retrieval-id"]})
    policy["prior_english_retrieval_calibration"]["sha256"] = file_hash(retrieval_path)
    write_json(path, policy)
    with pytest.raises(ValueError, match="retrieval exposure"):
        selection.prepare(path, root=root)
    write_json(retrieval_path, {"purpose": "calibration-not-final-evaluation", "split": "calibration",
        "qa_sha256": "old-qa-sha", "sample_count": 1, "record_ids": ["old-retrieval-id"]})
    policy["prior_english_retrieval_calibration"]["sha256"] = file_hash(retrieval_path)
    main_path = root / "main.json"
    import json

    main = json.loads(main_path.read_text())
    main["languages"]["en"]["selected"][0]["document_group_id"] = "different"
    write_json(main_path, main)
    policy["main_development_selection"]["sha256"] = file_hash(main_path)
    write_json(path, policy)
    with pytest.raises(ValueError, match="Main reservation source changed"):
        selection.prepare(path, root=root)


def test_extra_inventory_root_includes_pre_call_calibration_journals(reserved):
    root, _, _, _, _ = reserved
    ids, hashes, _ = used_inventory(root, inventory_roots=selection.USAGE_ROOTS)
    assert ids == {"en:development:40"} and len(hashes) == 1
