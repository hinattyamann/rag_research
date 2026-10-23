"""Smoke sends exactly the original claimwise input, including later claim IDs."""

import importlib.util
from pathlib import Path

import pytest

from rag_research.evaluation.claims import validate_claims
from rag_research.evaluation.claimwise import payloads

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("runtime_smoke", ROOT / "scripts/run_review_runtime_smoke.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize("claim_id", ["c1", "c2"])
def test_probe_uses_consecutive_local_id_and_preserves_complete_answer_and_evidence(claim_id):
    case = {"question": "Q", "answer": "All sentences, unchanged", "claims": [
        {"claim_id": "c1", "text": "First"}, {"claim_id": "c2", "text": "Second"}],
        "documents": [{"passage_id": "p1", "title": "T", "text": "Complete context"}]}
    target = {"order": "original", "claim_id": claim_id}
    result = module.probe_payload(case, target)
    validate_claims(result["claims"])
    assert result == dict(payloads(case, "claimwise-v1"))[claim_id]
    assert result["claims"][0]["claim_id"] == "c1" and result["answer"] == case["answer"]
    assert result["documents"] == case["documents"]
