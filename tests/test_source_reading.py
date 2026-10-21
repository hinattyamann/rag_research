"""Draft-blind inputs, literal quote coverage, full costs and durable two-stage resume."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from rag_research.evaluation import claimwise, source_reading
from rag_research.experiments.protocol import build_messages
from rag_research.experiments.quality import cost
from rag_research.experiments.storage import checkpoint, read_json
from rag_research.generation.config import GenerationConfig
from rag_research.generation.local import GenerationError


@pytest.fixture
def reading(tmp_path):
    payload = {"question": "Who acted?", "answer": "Draft A. Draft B.",
               "claims": [{"claim_id": "c1", "text": "Draft A."}, {"claim_id": "c2", "text": "Draft B."}],
               "documents": [{"passage_id": "d1", "title": "One", "text": "Alice acted."},
                             {"passage_id": "d2", "title": "Two", "text": "Bob waited."}]}
    prompts = {"source_reading_auxiliary": "untrusted_reading_v1", "judge_layout": "draft_sources_target",
               "tasks": {"read_sources": {"system": "Read sources only."}, "verify_claims": {"system": "Verify target."}}}
    generation = GenerationConfig(context_tokens=65536, max_output_tokens=512)

    class Client:
        def __init__(self):
            self.requests = []
            self.fail = None
            self.invalid = None

        def render(self, messages):
            self.messages = deepcopy(messages)
            return json.dumps(messages)

        def tokenize(self, text, *, special=False):
            return list(map(ord, text))

        def complete(self, tokens, config, **kwargs):
            self.requests.append(deepcopy(self.messages))
            p = json.loads(self.messages[1]["content"].removeprefix("Input JSON:\n"))
            reader = self.messages[0]["content"] == "Read sources only."
            stage = "reader" if reader else p["claims"][0]["text"]
            if self.fail == stage:
                raise GenerationError("Preserved stage failure")
            if self.fail == "interrupt-" + stage:
                raise KeyboardInterrupt()
            if reader:
                assert set(p) == {"question", "documents"} and "Draft" not in json.dumps(p)
                rows = [{"passage_id": d["passage_id"], "actor": "Source actor", "action": "Source action",
                         "quote": d["text"]} for d in p["documents"]]
                if self.invalid == "quote":
                    rows[0]["quote"] = "Invented source text"
                elif self.invalid == "missing":
                    rows.pop()
                elif self.invalid == "duplicate":
                    rows[-1] = rows[0]
                value = {"readings": rows}
            else:
                assert list(p) == ["answer", "documents", "question", "claims", "source_reading"]
                assert p["answer"] == payload["answer"] and p["documents"] == payload["documents"]
                assert len(p["source_reading"]["readings"]) == 2 and p["claims"][0]["claim_id"] == "c1"
                support = p["claims"][0]["text"] == "Draft A."
                value = {"verdicts": [{"claim_id": "c1", "label": "supported" if support else "not_supported",
                    "reason": "Fixture", "evidence": [{"passage_id": "d1", "quote": "Alice acted."}] if support else []}]}
            return {"content": json.dumps(value), "tokens": [1, 2], "stop_type": "eos", "truncated": False}

    return Client(), generation, prompts, payload, tmp_path / "trial.json"


def invoke(reading, *, client=True, generation=None):
    c, g, prompts, payload, path = reading
    return claimwise.verify_once(c if client else None, generation or g, prompts, payload, path, {"trace": "fixed"},
                                 mode=source_reading.MODE, reader_generation=g)


def test_reading_has_no_draft_and_every_sentence_costs_and_resume_are_verified(reading):
    client, _, _, payload, path = reading
    result = invoke(reading)
    assert result["status"] == "ok" and result["parsed"]["score"] == .5
    assert [v["claim_id"] for v in result["parsed"]["verdicts"]] == ["c1", "c2"]
    assert cost([result])["completion_attempts"] == 3 and result["output_tokens"] == 6
    assert invoke(reading, client=False) == result and len(client.requests) == 3
    assert not claimwise.pending(path, source_reading.MODE)
    # A different trial with identical input must perform its own reader and both checks.
    another = (*reading[:4], path.with_name("repeat.json"))
    invoke(another)
    assert len(client.requests) == 6
    assert source_reading.reading_schema(payload["documents"]) == source_reading.reading_schema(list(reversed(payload["documents"])))


@pytest.mark.parametrize("invalid", ["quote", "missing", "duplicate"])
def test_invalid_reading_stops_before_any_verdict_without_changing_denominator(reading, invalid):
    reading[0].invalid = invalid
    result = invoke(reading)
    assert result["status"] == "error" and result["parsed"] is None
    assert result["not_attempted_claim_ids"] == ["c1", "c2"] and result["completion_attempts_recorded"] == 1
    assert invoke(reading, client=False) == result and len(reading[0].requests) == 1


def test_sentence_failure_keeps_reader_and_successful_sentence_costs_but_no_partial_score(reading):
    reading[0].fail = "Draft B."
    result = invoke(reading)
    assert result["status"] == "error" and result["parsed"] is None and result["cost_incomplete"]
    assert result["completion_attempts_recorded"] == 3
    assert invoke(reading, client=False) == result and len(reading[0].requests) == 3


@pytest.mark.parametrize("stage,calls", [("reader", 1), ("Draft A.", 2)])
def test_interrupted_reader_or_verifier_is_unknown_and_never_resampled(reading, stage, calls):
    reading[0].fail = "interrupt-" + stage
    with pytest.raises(KeyboardInterrupt):
        invoke(reading)
    assert len(reading[0].requests) == calls and not claimwise.pending(reading[4], source_reading.MODE)
    result = invoke(reading, client=False)
    assert result["status"] == "error" and result["cost_incomplete"]
    assert result["error_code"] == "interrupted_unknown_outcome" and result["completion_attempts_recorded"] == calls
    assert invoke(reading, client=False) == result


def test_partial_resume_only_calls_missing_sentence_and_keeps_reader(reading, monkeypatch):
    original = claimwise.execute_task

    def interrupted(*args, **kwargs):
        if args[5].name == "c2.json":
            raise KeyboardInterrupt()
        return original(*args, **kwargs)

    monkeypatch.setattr(claimwise, "execute_task", interrupted)
    with pytest.raises(KeyboardInterrupt):
        invoke(reading)
    assert len(reading[0].requests) == 2 and claimwise.pending(reading[4], source_reading.MODE)
    monkeypatch.setattr(claimwise, "execute_task", original)
    assert invoke(reading)["parsed"]["score"] == .5 and len(reading[0].requests) == 3


def test_overflow_after_reading_is_not_truncated_or_called(reading):
    result = invoke(reading, generation=replace(reading[1], context_tokens=600))
    assert result["status"] == "error" and result["error_code"] == "input_overflow"
    assert result["completion_attempts_recorded"] == 1 and len(reading[0].requests) == 1


def test_tampered_intermediate_costs_gold_and_changed_configuration_are_rejected(reading):
    invoke(reading)
    client, generation, prompts, payload, path = reading
    bad = {"question": payload["question"], "documents": payload["documents"], "answer": "GOLD-SECRET"}
    with pytest.raises(ValueError, match="forbidden"):
        build_messages(prompts, "read_sources", bad)
    payload["reference"] = "GOLD-SECRET"
    with pytest.raises(ValueError, match="forbidden"):
        invoke(reading)
    payload.pop("reference")
    with pytest.raises(ValueError, match="inputs changed"):
        invoke(reading, generation=replace(generation, max_output_tokens=513))
    root = read_json(path)
    root["output_tokens"] += 1
    root.pop("result_sha256")
    checkpoint(path, root)
    with pytest.raises(ValueError, match="differs from raw"):
        invoke(reading)
    assert len(client.requests) == 3


def test_empty_fixed_units_do_not_call_reader_or_invent_score(reading):
    reading[3]["claims"] = []
    result = invoke(reading)
    assert result["status"] == "not_applicable" and result["parsed"] is None
    assert not reading[0].requests and result["completion_attempts_recorded"] == 0
