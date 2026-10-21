"""Full-context sentence mapping, denominator, actual calls and partial/unknown resume."""

import json
from copy import deepcopy

import pytest

from rag_research.evaluation import claimwise
from rag_research.experiments.quality import cost
from rag_research.experiments.storage import checkpoint, read_json
from rag_research.generation.config import GenerationConfig
from rag_research.generation.local import GenerationError


@pytest.fixture
def case(tmp_path):
    payload = {"question": "Who did it?", "answer": "A. B.",
               "claims": [{"claim_id": "c1", "text": "A."}, {"claim_id": "c2", "text": "B."}],
               "documents": [{"passage_id": "d1", "title": "T", "text": "Evidence A."}]}
    prompts = {"schema_version": 1, "tasks": {"verify_claims": {"system": "Only the target is evaluated."}}}
    config = GenerationConfig(context_tokens=8192, max_output_tokens=512)

    class Client:
        calls = 0

        def __init__(self):
            self.requests = []
            self.fail = False

        def render(self, messages):
            self.messages = deepcopy(messages)
            return json.dumps(messages)

        def tokenize(self, text, *, special=False):
            return list(map(ord, text))

        def complete(self, tokens, generation, **kwargs):
            assert generation.seed == 42
            self.calls += 1
            self.requests.append(deepcopy(self.messages))
            data = json.loads(self.messages[1]["content"].removeprefix("Input JSON:\n"))
            assert set(data) == {"question", "answer", "claims", "documents"}
            assert data["answer"] == payload["answer"] and data["documents"] == payload["documents"]
            assert data["claims"][0]["claim_id"] == "c1" and len(data["claims"]) == 1
            if self.fail and data["claims"][0]["text"] == "B.":
                raise GenerationError("Preserved runtime failure")
            support = data["claims"][0]["text"] == "A."
            return {"content": json.dumps({"verdicts": [{"claim_id": "c1", "label": "supported" if support else "not_supported",
                "reason": "Fixture", "evidence": [{"passage_id": "d1", "quote": "Evidence A."}] if support else []}]}),
                "tokens": [1, 2], "truncated": False, "stop_type": "eos"}

    return Client(), config, prompts, payload, tmp_path / "trial.json", {"trace": "fixed"}


def invoke(case, client=None):
    original, config, prompts, payload, path, binding = case
    return claimwise.verify_once(client or original, config, prompts, payload, path, binding, mode=claimwise.MODE)


def test_all_sentences_mapped_global_score_and_actual_costs_cached_without_calls(case):
    client, _, _, payload, path, _ = case
    saved = invoke(case)
    assert saved["status"] == "ok" and saved["parsed"]["score"] == .5
    assert [v["claim_id"] for v in saved["parsed"]["verdicts"]] == ["c1", "c2"]
    assert saved["completion_attempts_recorded"] == client.calls == 2
    actual = cost([saved])
    assert actual["completion_attempts"] == 2 and actual["input_tokens"] == saved["input_tokens"]
    assert actual["output_tokens"] == 4
    assert claimwise.verify_aggregate(path, saved) == saved
    assert invoke(case) == saved and client.calls == 2
    assert not claimwise.pending(path, claimwise.MODE)
    assert payload["claims"][1]["claim_id"] == "c2"


def test_one_failed_sentence_never_produces_partial_denominator_score(case):
    client, _, _, payload, path, _ = case
    payload["answer"] += " C."
    payload["claims"].append({"claim_id": "c3", "text": "C."})
    client.fail = True
    saved = invoke(case)
    assert saved["status"] == "error" and saved["parsed"] is None
    assert saved["completion_attempts_recorded"] == 2
    assert saved["not_attempted_claim_ids"] == ["c3"]
    assert cost([saved])["incomplete"]
    assert invoke(case) == saved and client.calls == 2
    assert not claimwise.pending(path, claimwise.MODE)


def test_partial_resume_calls_only_missing_unit_and_handles_unaggregated_completion(case, monkeypatch):
    client, _, _, _, path, _ = case
    actual = claimwise.execute_task

    def stop_before_second(*args, **kwargs):
        if args[4]["claims"][0]["text"] == "B.":
            raise KeyboardInterrupt()
        return actual(*args, **kwargs)

    monkeypatch.setattr(claimwise, "execute_task", stop_before_second)
    with pytest.raises(KeyboardInterrupt):
        invoke(case)
    assert client.calls == 1 and read_json(path)["status"] == "partial"
    partial = read_json(path)
    assert claimwise.pending(path, claimwise.MODE)
    monkeypatch.setattr(claimwise, "execute_task", actual)
    complete = invoke(case)
    assert client.calls == 2 and complete["parsed"]["score"] == .5
    # Simulate crash after final child but before aggregate replacement.
    partial.pop("result_sha256")
    checkpoint(path, partial)
    assert not claimwise.pending(path, claimwise.MODE)
    assert invoke(case) == complete and client.calls == 2


def test_interrupted_child_is_not_resampled_and_cost_remains_unknown(case, monkeypatch):
    client, _, _, _, path, _ = case
    actual = client.complete

    def interrupted(tokens, config, **kwargs):
        data = json.loads(client.messages[1]["content"].removeprefix("Input JSON:\n"))
        if data["claims"][0]["text"] == "B.":
            client.calls += 1
            raise KeyboardInterrupt()
        return actual(tokens, config, **kwargs)

    monkeypatch.setattr(client, "complete", interrupted)
    with pytest.raises(KeyboardInterrupt):
        invoke(case)
    assert client.calls == 2 and not claimwise.pending(path, claimwise.MODE)
    saved = invoke(case)
    assert saved["status"] == "error" and saved["error_code"] == "interrupted_unknown_outcome"
    assert saved["parsed"] is None and cost([saved])["completion_attempts"] is None
    assert client.calls == 2


def test_input_change_child_tamper_and_aggregate_cost_forgery_fail_closed(case):
    client, _, _, payload, path, _ = case
    saved = invoke(case)
    payload["answer"] += " changed"
    with pytest.raises(ValueError, match="inputs changed"):
        invoke(case)
    payload["answer"] = "A. B."
    forged = deepcopy(saved)
    forged.pop("result_sha256")
    forged["subtask_costs"][0]["input_tokens"] += 1
    checkpoint(path, forged)
    with pytest.raises(ValueError, match="Aggregate differs"):
        invoke(case)
    saved.pop("result_sha256")
    checkpoint(path, saved)
    child = path.parent / "trial.claims/c2.json"
    value = read_json(child)
    value["parsed"]["score"] = 1.
    child.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="hash mismatch"):
        invoke(case)
    assert client.calls == 2


def test_empty_claims_never_call_model_and_gold_fields_rejected_before_call(case):
    client, config, prompts, payload, path, binding = case
    payload["claims"] = []
    saved = invoke(case)
    assert saved["status"] == "not_applicable" and saved["parsed"]["score"] is None and client.calls == 0
    payload["gold"] = "SECRET"
    with pytest.raises(ValueError, match="forbidden"):
        claimwise.verify_once(client, config, prompts, payload, path, binding, mode=claimwise.MODE)
    assert client.calls == 0
