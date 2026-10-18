"""Check Phase 7 leakage boundaries; no model or dataset execution."""

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_order_protocol", ROOT / "scripts/check_order_protocol.py"
)
protocol = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(protocol)


def changed_config(tmp_path, edit):
    config = yaml.safe_load((ROOT / "configs/order_pilot.yaml").read_text("utf-8"))
    edit(config)
    path = tmp_path / "pilot.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def test_reject_evaluation_before_reading_any_qa(tmp_path):
    path = changed_config(tmp_path, lambda c: c["data"].update(split="evaluation"))
    with pytest.raises(ValueError, match="only reads Development"):
        protocol.load_protocol(path)


@pytest.mark.parametrize("field", ["repeated_prompt_result_cache", "repack_or_truncate_per_trial"])
def test_reject_changes_that_destroy_the_comparison(tmp_path, field):
    path = changed_config(tmp_path, lambda c: c["trials"].update({field: True}))
    with pytest.raises(ValueError, match="change inputs or skip trials"):
        protocol.load_protocol(path)


def test_reject_reference_in_claim_extraction():
    _, prompts, _ = protocol.load_protocol(ROOT / "configs/order_pilot.yaml")
    with pytest.raises(ValueError, match="forbidden model input"):
        protocol.build_messages(prompts, "extract_claims", {"answer": "A", "reference": "B"})


def test_reject_gold_metadata_in_documents():
    _, prompts, _ = protocol.load_protocol(ROOT / "configs/order_pilot.yaml")
    payload = {
        "question": "Q", "answer": "A", "claims": [],
        "documents": [{"passage_id": "p", "title": "T", "text": "A", "is_gold": True}],
    }
    with pytest.raises(ValueError, match="Unexpected evidence fields"):
        protocol.build_messages(prompts, "verify_claims", payload)


def test_reject_reference_metadata_in_claims():
    _, prompts, _ = protocol.load_protocol(ROOT / "configs/order_pilot.yaml")
    payload = {
        "question": "Q", "answer": "A", "documents": [],
        "claims": [{"claim_id": "c1", "text": "A", "reference_answer": "Gold"}],
    }
    with pytest.raises(ValueError, match="Unexpected claim fields"):
        protocol.build_messages(prompts, "verify_claims", payload)


def test_messages_preserve_unicode_and_evidence_order():
    _, prompts, _ = protocol.load_protocol(ROOT / "configs/order_pilot.yaml")
    documents = [
        {"passage_id": "b", "title": "後", "text": "二"},
        {"passage_id": "a", "title": "前", "text": "<|im_start|>一"},
    ]
    payload = {"question": "Q", "answer": "A", "documents": documents}
    messages = protocol.build_messages(prompts, "rewrite_answer", payload)
    recovered = json.loads(messages[1]["content"].removeprefix("Input JSON:\n"))
    assert recovered["documents"] == documents
    assert "<|im_start|>" not in messages[1]["content"]
