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


def test_quote_alignment_preserves_exact_word_order_numbers_and_negation():
    import json

    from rag_research.evaluation.quote_alignment import align_quotes

    documents = [{"passage_id": "p", "text": "The tower was built in 1986 . It is not open on Mondays ."}]

    def raw(quote):
        return json.dumps({"verdicts": [{"claim_id": "c1", "reason": "Test", "label": "supported",
                                       "evidence": [{"passage_id": "p", "quote": quote}]}]})

    normalized, audit = align_quotes(raw("The tower was built in 1986."), documents)
    projected = json.loads(normalized)["verdicts"][0]["evidence"][0]["quote"]
    assert projected in documents[0]["text"]
    assert audit[0]["raw_quote"] == "The tower was built in 1986."
    assert audit[0]["alignment"] == "unique_contiguous_word_tokens"
    for quote in ("The tower was built in 1987.", "It is open on Mondays.", "In 1986 the tower was built."):
        with pytest.raises(ValueError, match="unique source"):
            align_quotes(raw(quote), documents)
    doubled = [{"passage_id": "p", "text": "The tower was built in 1986 . The tower was built in 1986 ."}]
    with pytest.raises(ValueError, match="unique source"):
        align_quotes(raw("The tower was built in 1986."), doubled)


def test_simple_verdict_grammar_and_premise_layout_stay_order_independent():
    from rag_research.experiments.protocol import build_messages

    config, prompts, _ = load_protocol(ROOT / "configs/order_phase10_v6.yaml")
    payload = {"question": "Q?", "answer": "A.", "claims": [{"claim_id": "c1", "text": "A."}],
               "documents": [{"passage_id": "a", "title": "A", "text": "A."},
                             {"passage_id": "b", "title": "B", "text": "B."}]}
    schema = output_schema("verify_claims", payload, bounded=True, compact=True, aligned=True)
    changed = deepcopy(payload)
    changed["documents"].reverse()
    assert schema == output_schema("verify_claims", changed, bounded=True, compact=True, aligned=True)
    message = build_messages(prompts, "verify_claims", payload)[1]["content"]
    assert message.index('"documents"') < message.index('"claims"')
    assert payload["documents"][0]["text"] == "A."
    assert config["tasks"]["verify_claims"]["max_output_tokens"] == 4096


def test_aligned_task_retains_raw_quote_and_keeps_legacy_literal_validation(tmp_path):
    import json

    config, prompts, _ = load_protocol(ROOT / "configs/order_phase10_v6.yaml")
    payload = {"question": "When?", "answer": "The tower opened in 1986.",
               "claims": [{"claim_id": "c1", "text": "The tower opened in 1986."}],
               "documents": [{"passage_id": "p", "title": "Tower", "text": "The tower opened in 1986 ."}]}

    class Client:
        def render(self, messages):
            return json.dumps(messages)

        def tokenize(self, text, *, special):
            return [1] * 20

        def complete(self, tokens, settings, **kwargs):
            return {"content": json.dumps({"verdicts": [{"claim_id": "c1", "label": "supported",
                    "reason": "The year is explicitly stated.", "evidence": [{"passage_id": "p",
                    "quote": "The tower opened in 1986."}]}]}), "stop_type": "eos", "tokens": [1],
                    "truncated": False}

    revised = execute_task(Client(), task_config(config, "verify_claims"), prompts, "verify_claims",
                           payload, tmp_path / "revised.json", {}, constraints=config["output_constraints"])
    assert revised["status"] == "ok" and revised["parsed"]["score"] == 1
    assert revised["quote_alignment"][0]["raw_quote"] == "The tower opened in 1986."
    legacy = execute_task(Client(), task_config(config, "verify_claims"), prompts, "verify_claims",
                          payload, tmp_path / "legacy.json", {}, constraints="json_schema_source_spans_bounded_v2")
    assert legacy["status"] == "error" and "not verbatim" in legacy["error"]


@pytest.mark.parametrize("answer_tokens,expected", [(20, "ok"), (513, "error")])
def test_one_checked_rewrite_exposes_only_final_candidate_with_same_answer_budget(tmp_path, answer_tokens, expected):
    import json

    from rag_research.recovery.answer_rewrite import rewrite_once

    config, prompts, _ = load_protocol(ROOT / "configs/order_phase10_v7.yaml")

    class Client:
        calls = 0

        def render(self, messages):
            payload = json.loads(messages[1]["content"].removeprefix("Input JSON:\n"))
            assert list(payload) == ["answer", "documents", "question"]
            assert "reference_answer" not in payload
            return json.dumps(messages)

        def tokenize(self, text, *, special):
            return [1] * (10 if special else answer_tokens)

        def complete(self, tokens, settings, **kwargs):
            self.calls += 1
            assert kwargs["json_schema"]["required"] == ["source_facts", "draft_issues", "answer"]
            return {"content": json.dumps({"source_facts": "Correct source fact [p].",
                    "draft_issues": "The draft gives a wrong fact.", "answer": "Correct fact [p]."}),
                    "tokens": [1] * 50, "truncated": False, "stop_type": "eos"}

    client = Client()
    trace = {"question": "Q?", "answer": "Wrong draft.", "reference_answer": "DO NOT LEAK",
             "documents": [{"passage_id": "p", "title": "P", "text": "Correct fact."}]}
    result = rewrite_once(client, task_config(config, "rewrite_answer"), prompts, trace,
                          tmp_path / "rewrite.json", {})
    assert client.calls == 1 and result["status"] == expected
    assert result["output_tokens"] == 50
    if expected == "ok":
        assert result["answer"] == "Correct fact [p]."
        assert result["source_review"]["draft_issues"] == "The draft gives a wrong fact."
    else:
        assert result["answer"] is None and "512-token" in result["error"]


def test_reasoned_parser_uses_only_closed_final_json_and_attaches_declared_source_scope():
    import json

    from rag_research.evaluation.reasoned_json import attach_cited_passages, final_json

    text, thinking = final_json('<think>{"answer":"wrong draft"}</think>\n```json\n{"verdicts":[]}\n```')
    assert json.loads(text) == {"verdicts": []} and "wrong draft" in thinking["text"]
    for invalid in ('{"verdicts":[]}', '<think>unclosed {"verdicts":[]}', '</think>Here is {"verdicts":[]}'):
        with pytest.raises(ValueError):
            final_json(invalid)
    payload = {"verdicts": [{"claim_id": "c1", "label": "supported", "reason": "Test", "evidence_ids": ["p"]}]}
    normalized, raw = attach_cited_passages(json.dumps(payload), [{"passage_id": "p", "text": "Whole original source."}])
    assert json.loads(normalized)["verdicts"][0]["evidence"] == [{"passage_id": "p", "quote": "Whole original source."}]
    assert raw == payload
    payload["verdicts"][0]["evidence_ids"] = ["unknown"]
    with pytest.raises(ValueError, match="Unknown citation"):
        attach_cited_passages(json.dumps(payload), [{"passage_id": "p", "text": "Whole source."}])


def test_auxiliary_sampling_does_not_change_baseline_sampler_or_temperature_contract(monkeypatch):
    from rag_research.generation.auxiliary_config import AuxiliaryGenerationConfig
    from rag_research.generation.config import GenerationConfig
    from rag_research.generation.local import LlamaClient

    with pytest.raises(ValueError, match="zero"):
        GenerationConfig(temperature=0.6)
    auxiliary = AuxiliaryGenerationConfig(temperature=0.6)
    client = LlamaClient(1)
    requests = []
    monkeypatch.setattr(client, "request", lambda route, payload: requests.append(payload) or {})
    client.complete([1], GenerationConfig())
    client.complete([1], auxiliary)
    assert requests[0]["temperature"] == 0 and requests[0]["samplers"] == ["temperature"]
    assert "top_k" not in requests[0]
    assert requests[1]["temperature"] == 0.6 and requests[1]["top_k"] == 20
    assert requests[1]["samplers"] == ["penalties", "top_k", "top_p", "min_p", "temperature"]
    assert requests[0]["seed"] == requests[1]["seed"] == 42
    budgeted = AuxiliaryGenerationConfig(temperature=0.6, reasoning_budget_tokens=512)
    client.complete([1], budgeted)
    assert requests[2]["reasoning_budget_tokens"] == 512
    assert requests[2]["reasoning_budget_start_tag"] == "<think>"
    assert requests[2]["reasoning_budget_end_tags"] == ["</think>"]
    assert requests[2]["preserved_tokens"] == ["<think>", "</think>"]


def test_thinking_judge_uses_fixed_claims_without_repeating_untrusted_answer(tmp_path):
    import json

    from rag_research.experiments.protocol import build_messages

    config, prompts, _ = load_protocol(ROOT / "configs/order_phase10_v8.yaml")
    payload = {"question": "Q?", "answer": "The library opened in 2003. [p]",
               "claims": [{"claim_id": "c1", "text": "The library opened in 2003."}],
               "documents": [{"passage_id": "p", "title": "Library", "text": "The library opened in 2003."}]}
    sent = json.loads(build_messages(prompts, "verify_claims", payload)[1]["content"].removeprefix("Input JSON:\n"))
    assert set(sent) == {"documents", "question", "claims"} and sent["documents"] == payload["documents"]
    with pytest.raises(ValueError, match="forbidden"):
        build_messages(prompts, "verify_claims", {**payload, "gold": "leak"})

    class Client:
        def render(self, messages):
            return json.dumps(messages)

        def tokenize(self, text, *, special):
            return [1] * 10

        def complete(self, tokens, settings, **kwargs):
            assert not kwargs
            return {"content": '<think>Compare the exact year.</think>' + json.dumps({"verdicts": [
                {"claim_id": "c1", "label": "supported", "reason": "The same year is given.", "evidence_ids": ["p"]}]}),
                "tokens": [1] * 50, "stop_type": "eos", "truncated": False}

    result = execute_task(Client(), task_config(config, "verify_claims"), prompts, "verify_claims",
                          payload, tmp_path / "judge.json", {}, constraints=config["output_constraints"])
    assert result["status"] == "ok" and result["parsed"]["score"] == 1
    assert result["output_tokens"] == 50 and result["model_reasoning"]["text"]
    assert result["json_schema"] is None and "not_model_quotations" in result["evidence_scope"]


def test_runtime_reasoning_budget_audit_rejects_ignored_budget():
    from rag_research.evaluation.reasoning_budget import audit_reasoning_budget
    from rag_research.generation.auxiliary_config import AuxiliaryGenerationConfig

    class Client:
        def tokenize(self, text, *, special):
            return [101] if text == "<think>" else ([102] if text == "</think>" else [3] * 5)

    config = AuxiliaryGenerationConfig(temperature=0.6, reasoning_budget_tokens=10)
    result = audit_reasoning_budget(Client(), {"tokens": [101] + [1] * 15 + [102, 9]}, config)
    assert result["tokens_before_end_marker"] == 15
    with pytest.raises(ValueError, match="did not honor"):
        audit_reasoning_budget(Client(), {"tokens": [101] + [1] * 50 + [102]}, config)


def test_conflict_and_complete_support_checks_have_a_fixed_non_correcting_mapping():
    import json

    from rag_research.evaluation.reasoned_json import attach_cited_passages

    docs = [{"passage_id": "p", "text": "Original source."}]
    for conflict, complete, expected in ((True, False, "contradicted"), (False, True, "supported"),
                                         (False, False, "not_supported")):
        raw = {"verdicts": [{"claim_id": "c1", "has_explicit_conflict": conflict,
                "all_details_supported": complete, "reason": "Test only", "evidence_ids": ["p"]}]}
        normalized, saved = attach_cited_passages(json.dumps(raw), docs, boolean_checks=True)
        assert json.loads(normalized)["verdicts"][0]["label"] == expected and saved == raw
    raw["verdicts"][0].update(has_explicit_conflict=True, all_details_supported=True)
    with pytest.raises(ValueError, match="inconsistent"):
        attach_cited_passages(json.dumps(raw), docs, boolean_checks=True)
