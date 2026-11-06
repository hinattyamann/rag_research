"""Counterexamples against the actual exported supplement, not synthetic results."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("provenance_verifier", PACKAGE / "verify_audit.py")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


@pytest.fixture
def package(tmp_path):
    root = tmp_path / "supplement"
    shutil.copytree(PACKAGE, root, ignore=shutil.ignore_patterns("__pycache__"))
    return root


def modify(root, relative, update):
    path = root / relative
    value = json.loads(path.read_bytes())
    update(value)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    manifest_path = root / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    data = path.read_bytes()
    manifest["files"][relative] = {"bytes": len(data), "sha256": VERIFIER.sha(data)}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_actual_package():
    result = VERIFIER.verify(PACKAGE)
    assert result["status"] == "passed"
    assert result["exact_serving_identifier_recovered"] is False
    assert result["exact_corpus_revision_bindings_recovered"] == 0


def test_missing_evidence(package):
    (package / "evidence/japanese/public/move_log_response.json").unlink()
    with pytest.raises(ValueError, match="inventory"):
        VERIFIER.verify(package)


def test_extra_data(package):
    (package / "unexpected.txt").write_text("unregistered")
    with pytest.raises(ValueError, match="inventory"):
        VERIFIER.verify(package)


def test_modified_bytes(package):
    with (package / "findings.json").open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(ValueError, match="Hash mismatch"):
        VERIFIER.verify(package)


def test_nested_manifest_is_not_ignored(package):
    (package / "evidence/artifact_manifest.json").write_text("{}")
    with pytest.raises(ValueError, match="inventory"):
        VERIFIER.verify(package)


def test_path_traversal(package):
    with pytest.raises(ValueError, match="Unsafe"):
        VERIFIER.confined(package, "../original-run.json")


def test_symlink(package):
    (package / "linked.json").symlink_to(package / "findings.json")
    with pytest.raises(ValueError, match="Symlink"):
        VERIFIER.verify(package)


def test_candidate_cannot_become_confirmed_after_rehash(package):
    modify(package, "english_passage_revisions.json",
           lambda rows: rows[0].update(identified_corpus_revision_oldid=123))
    with pytest.raises(ValueError, match="Candidate upgraded"):
        VERIFIER.verify(package)


def test_oldid_must_match_explicit_url_after_rehash(package):
    def change(rows):
        row = next(r for r in rows if r["matches"])
        row["matches"][0]["oldid_from_explicit_url"] = 123
    modify(package, "english_passage_revisions.json", change)
    with pytest.raises(ValueError, match="URL identifier"):
        VERIFIER.verify(package)


def test_no_invented_serving_id_after_rehash(package):
    rows = json.loads((package / "annotation_jobs.json").read_bytes())
    modify(package, rows[0]["evidence_path"], lambda row: row.update(exact_serving_model_identifier="unverified-snapshot"))
    with pytest.raises(ValueError, match="Unsupported serving"):
        VERIFIER.verify(package)


def test_job_input_binding_after_rehash(package):
    rows = json.loads((package / "annotation_jobs.json").read_bytes())
    modify(package, rows[0]["evidence_path"], lambda row: row.update(input_sha256="0" * 64))
    with pytest.raises(ValueError, match="input/output"):
        VERIFIER.verify(package)


def test_quote_mismatch_cannot_be_hidden_after_rehash(package):
    modify(package, "japanese_reference.json", lambda row: row.update(entire_reference_quote_verbatim_match=True))
    with pytest.raises(ValueError, match="Quote mismatch"):
        VERIFIER.verify(package)


def test_english_missing_qa_after_rehash(package):
    modify(package, "english_qa_sources.json", lambda rows: rows.pop())
    with pytest.raises(ValueError, match="40 QA"):
        VERIFIER.verify(package)


def test_japanese_wrong_revision_after_rehash(package):
    modify(package, "japanese_reference.json", lambda row: row.update(recovered_revision_id=1))
    with pytest.raises(ValueError, match="Recovered page"):
        VERIFIER.verify(package)
