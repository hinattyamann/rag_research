"""Result-independent selection, used-group closure, and incomplete baseline journals."""

from copy import deepcopy

import pytest

from rag_research.experiments.development_selection import select_rows, used_inventory
from rag_research.experiments.storage import write_json
from rag_research.retrieval.common import file_hash


def rows():
    return [{"record_id": str(i), "document_group_id": "g" + str(i // 2),
             "research_split": "development", "language": "ja", "is_answerable": True,
             "question": "QUESTION", "reference_answers": ["SECRET"], "gold_parent_ids": []}
            for i in range(12)]


def test_selection_is_invariant_to_input_order_and_all_answer_or_gold_changes():
    original = rows()
    chosen = select_rows(original, "ja", {"0"}, {"g1"}, count=3)
    changed = deepcopy(original[::-1])
    for r in changed:
        r.update(question="OTHER", reference_answers=["OTHER"], gold_parent_ids=["NOW AVAILABLE"], answer="MODEL OUTPUT")
    assert select_rows(changed, "ja", {"0"}, {"g1"}, count=3) == chosen
    assert len({r["document_group_id"] for r in chosen["selected"]}) == 3
    assert not {r["document_group_id"] for r in chosen["selected"]} & {"g0", "g1"}
    assert original == rows()
    # Used sibling 0 blocks 1 as well, even if the used row is not source-answered.
    original[0]["is_answerable"] = False
    assert all(r["record_id"] != "1" for r in select_rows(original, "ja", {"0"}, set(), count=5)["selected"])


def test_selection_never_refills_or_accepts_evaluation_mixed_language_or_duplicate_ids():
    with pytest.raises(ValueError, match="Insufficient"):
        select_rows(rows(), "ja", {"0"}, {"g1", "g2", "g3", "g4"}, count=3)
    for key, value in (("research_split", "evaluation"), ("language", "en")):
        changed = rows()
        changed[0][key] = value
        with pytest.raises(ValueError, match="Development"):
            select_rows(changed, "ja", set(), set(), count=1)
    changed = rows()
    changed[1]["record_id"] = changed[0]["record_id"]
    with pytest.raises(ValueError, match="Duplicate"):
        select_rows(changed, "ja", set(), set(), count=1)


def test_inventory_includes_failed_and_pre_call_journals_and_preserves_hashes(tmp_path):
    folder = tmp_path / "data/runs/phase5/old"
    folder.mkdir(parents=True)
    answer = folder / "answers.jsonl"
    answer.write_text('{"record_id":"old","status":"error"}\n')
    journal = tmp_path / "data/runs/bilingual_development/interrupted/baseline/a/record.json"
    journal.parent.mkdir(parents=True)
    write_json(journal, {"record_id": "started-before-call", "status": "started", "completion_attempted": False})
    ids, hashes, legacy = used_inventory(tmp_path)
    assert ids == {"old", "started-before-call"}
    assert legacy == []
    assert hashes == {str(p.relative_to(tmp_path)): file_hash(p) for p in (answer, journal)}
    # Unknown journals fail closed instead of being silently omitted.
    write_json(journal, {"status": "error"})
    with pytest.raises(ValueError, match="Unrecognized"):
        used_inventory(tmp_path)


def test_legacy_custom_queries_keep_exact_identity_and_exclude_exposed_source_groups(tmp_path):
    folder = tmp_path / "data/runs/phase5/custom"
    folder.mkdir(parents=True)
    path = folder / "answers.jsonl"
    path.write_text('{"record_id":null,"question":"same question","used_context":[{"title":"CAFE\\u0301"}],"retrieved_context":[]}\n')
    with pytest.raises(ValueError, match="identity resolution"):
        used_inventory(tmp_path)
    ids, _, legacy = used_inventory(tmp_path, development_rows=[{"question": "same question", "record_id": "source-id"}])
    assert ids == {"source-id"}
    assert legacy[0]["conservatively_excluded_english_groups"] == ["clapnq-title:café"]
    assert "question" not in legacy[0]
    chosen = select_rows(rows(), "ja", set(), set(), count=5, extra_used_groups={"g0"})
    assert all(r["document_group_id"] != "g0" for r in chosen["selected"])
