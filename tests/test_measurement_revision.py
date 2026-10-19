"""Coverage and budget changes must not weaken order-comparison boundaries."""

from copy import deepcopy
from pathlib import Path

import pytest

from rag_research.evaluation.schema import compact_quote_candidates, output_schema
from rag_research.evaluation.sentence_claims import extract_sentence_units
from rag_research.evaluation.tasks import execute_task
from rag_research.experiments.protocol import load_protocol, task_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("answer,fragments", [
    ('[123_0-90] According to the passage, Lina wrote the song.', ['Lina', 'wrote']),
    ("[12] The airport was renamed in 1987 as a tribute to Ada Chen.", ['1987', 'Ada Chen']),
    ("The city built the wall to prevent emigration. It opened in 1990.", ['prevent emigration', '1990']),
    ("The object is not [a planet]. It weighs 1.5 kg.", ['not [a planet]', '1.5 kg']),
    ("Dr. Chen met U.S. officials at 5 a.m. local time. The vote failed.", ['5 a.m.', 'vote failed']),
])
def test_sentence_units_keep_all_prose_and_important_details(answer, fragments):
    result = extract_sentence_units(answer)
    rebuilt = " ".join(c["text"] for c in result["claims"])
    assert rebuilt == result["normalized_prose"]
    assert all(fragment in rebuilt for fragment in fragments)
    assert [c["claim_id"] for c in result["claims"]] == [f"c{i + 1}" for i in range(len(result["claims"]))]


def test_refusal_is_excluded_only_when_the_whole_answer_is_a_recognized_refusal():
    refusal = "The retrieved passages do not provide enough information to answer this question."
    assert extract_sentence_units(refusal)["exclusion"] == "standalone_refusal"
    mixed = extract_sentence_units(refusal + " Moose occur in Alaska.")
    assert len(mixed["claims"]) == 2 and mixed["exclusion"] is None
    assert extract_sentence_units("[123] [456_0-99]")["claims"] == []
    assert extract_sentence_units("I do not know the name. The city is in Canada.")["claims"]


def test_deterministic_extraction_never_calls_model_and_resumes_without_resampling(tmp_path):
    config, prompts, _ = load_protocol(ROOT / "configs/order_phase10_v3.yaml")
    path = tmp_path / "claims.json"
    payload = {"answer": "The name honors Ada Chen. It changed in 1987."}
    result = execute_task(None, task_config(config, "extract_claims"), prompts, "extract_claims",
                          payload, path, {}, constraints=config["output_constraints"])
    assert result["status"] == "ok" and not result["completion_attempted"]
    assert result["input_tokens"] == result["output_tokens"] == 0
    assert len(result["parsed"]["claims"]) == 2
    before = path.read_bytes()
    assert execute_task(None, task_config(config, "extract_claims"), prompts, "extract_claims",
                        payload, path, {}, constraints=config["output_constraints"]) == result
    assert before == path.read_bytes()
    with pytest.raises(ValueError, match="hash mismatch"):
        execute_task(None, task_config(config, "extract_claims"), prompts, "extract_claims",
                     {"answer": "Changed."}, path, {}, constraints=config["output_constraints"])


def test_compact_evidence_is_verbatim_bounded_and_independent_of_order():
    text = " ".join(["A long factual source passage with many repeated tokens."] * 30)
    spans = compact_quote_candidates(text)
    assert spans and all(s in text and len(s) <= 320 for s in spans)
    assert compact_quote_candidates("Z" * 1000) == ["Z" * 320]
    payload = {"claims": [{"claim_id": "c1", "text": "A claim."}],
               "documents": [{"passage_id": "a", "title": "A", "text": text},
                             {"passage_id": "b", "title": "B", "text": "Other evidence."}]}
    schema = output_schema("verify_claims", payload, bounded=True, compact=True)
    reversed_payload = deepcopy(payload)
    reversed_payload["documents"].reverse()
    assert schema == output_schema("verify_claims", reversed_payload, bounded=True, compact=True)
    assert schema != output_schema("verify_claims", payload, bounded=True)


def test_refreshed_selection_excludes_old_titles_without_changing_original_rule(tmp_path, monkeypatch):
    import json

    from rag_research.pilot import selection
    from rag_research.retrieval.common import file_hash

    rows = [{"record_id": f"q{i}", "source_title": f"Title {i // 2}",
             "question": "Q?", "is_answerable": True, "research_split": "development"} for i in range(12)]
    (tmp_path / "data/manifests").mkdir(parents=True)
    qa = tmp_path / "qa.jsonl"
    qa.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    (tmp_path / "baseline.jsonl").write_text(json.dumps(rows[0]), encoding="utf-8")
    old = tmp_path / "data/manifests/old.json"
    old.write_text(json.dumps({"qa_sha256": file_hash(qa), "records": [rows[2]]}), encoding="utf-8")
    monkeypatch.setattr(selection, "ROOT", tmp_path)
    config = {"qa_path": "qa.jsonl", "exclude_baseline": "baseline.jsonl", "count": 3,
              "selection_seed": 42, "study_version": "test", "exclude_selection_manifests": ["data/manifests/old.json"]}
    manifest = selection.freeze_selection(config, tmp_path / "selected.json")
    assert len(manifest["records"]) == 3
    assert all(r["source_title"] not in {"Title 0", "Title 1"} for r in manifest["records"])
    before = (tmp_path / "selected.json").read_bytes()
    selection.freeze_selection(config, tmp_path / "selected.json")
    assert (tmp_path / "selected.json").read_bytes() == before


def test_auxiliary_model_is_explicit_verified_and_does_not_replace_baseline(tmp_path, monkeypatch):
    import json

    from rag_research.generation import auxiliary
    from rag_research.generation.artifacts import model_identity
    from rag_research.retrieval.common import file_hash

    baseline = model_identity()
    assert auxiliary.auxiliary_server_kwargs({}) == {}
    assert auxiliary.auxiliary_identity({}) == baseline
    (tmp_path / "data/models/test").mkdir(parents=True)
    (tmp_path / "data/manifests").mkdir(parents=True)
    artifact = tmp_path / "data/models/test/candidate.gguf"
    artifact.write_bytes(b"synthetic unit test, never loaded as a model")
    manifest = {"schema_version": 1, "purpose": "development-auxiliary-model",
                "entrypoint": "data/models/test/candidate.gguf",
                "files": [{"path": "data/models/test/candidate.gguf", "bytes": artifact.stat().st_size,
                           "sha256": file_hash(artifact)}]}
    path = tmp_path / "data/manifests/model.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(auxiliary, "ROOT", tmp_path)
    config = {"auxiliary_model_manifest": "data/manifests/model.json"}
    assert auxiliary.auxiliary_server_kwargs(config) == {"model_path": artifact}
    artifact.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="size/hash"):
        auxiliary.auxiliary_server_kwargs(config)
    manifest["files"][0]["path"] = "../outside.gguf"
    manifest["entrypoint"] = "../outside.gguf"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="escapes"):
        auxiliary.auxiliary_identity(config)
    assert model_identity() == baseline
