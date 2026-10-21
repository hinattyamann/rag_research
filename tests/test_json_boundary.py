"""Reasoning-end boundary, strict schema identity and unchanged legacy request behavior."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from rag_research.evaluation.reasoned_json import audit_final_json_grammar
from rag_research.evaluation.schema import cited_verdict_schema, object_schema
from rag_research.generation.auxiliary_config import AuxiliaryGenerationConfig
from rag_research.generation.json_grammar import closing_tag_grammar
from rag_research.generation.local import LlamaClient


def test_closing_boundary_is_part_of_grammar_and_raw_schema_is_not_sent(monkeypatch):
    client = LlamaClient(1)
    requests = []
    monkeypatch.setattr(client, "request", lambda route, payload: requests.append(payload) or {})
    settings = AuxiliaryGenerationConfig(temperature=.6, final_json_grammar=True, final_json_grammar_mode="closing_tag_root_v2")
    schema = object_schema({"result": {"const": "allowed"}})
    client.complete([1], settings, json_schema=schema)
    assert requests[0]["grammar_triggers"] == [{"type": 1, "value": "</think>"}]
    assert "json_schema" not in requests[0] and requests[0]["grammar"].startswith('root ::= "</think>" ws ')
    client.complete([1], replace(settings, final_json_grammar_mode="brace_trigger_v1"), json_schema=schema)
    assert requests[1]["json_schema"] == schema and "grammar" not in requests[1]
    assert requests[1]["grammar_triggers"] == [{"type": 2, "value": r"</think>\s*(\{)"}]


def test_new_audit_requires_exact_native_grammar_trigger_and_object():
    settings = AuxiliaryGenerationConfig(temperature=.6, final_json_grammar=True, final_json_grammar_mode="closing_tag_root_v2")
    schema = object_schema({"result": {"const": "allowed"}})
    response = {"content": '<think>Check.</think>{"result":"allowed"}', "generation_settings": {
        "grammar_lazy": True, "grammar_triggers": [{"type": 1, "value": "</think>"}], "grammar": closing_tag_grammar(schema)}}
    assert audit_final_json_grammar(response, settings, schema=schema)["end_tag_consumed_by_declared_grammar"]
    with pytest.raises(ValueError, match="differs"):
        audit_final_json_grammar(response, settings, schema=object_schema({"other": {"const": "changed"}}))
    with pytest.raises(ValueError, match="did not follow"):
        audit_final_json_grammar({**response, "content": '<think>Check.</think>[{"result":"allowed"}]'}, settings, schema=schema)


def test_grammar_preserves_fixed_ids_citation_order_invariance_and_large_rewrite_bounds():
    payload = {"claims": [{"claim_id": "c1", "text": "A"}], "documents": [
        {"passage_id": "b", "title": "B", "text": "B"}, {"passage_id": "a", "title": "A", "text": "A"}]}
    one = closing_tag_grammar(cited_verdict_schema(payload, boolean_checks=True))
    two = closing_tag_grammar(cited_verdict_schema({**payload, "documents": payload["documents"][::-1]}, boolean_checks=True))
    assert one == two
    # Native rewrite uses maxLength2400; avoid one unsupported >2000 repetition expansion.
    large = closing_tag_grammar(object_schema({"answer": {"type": "string", "minLength": 1, "maxLength": 2400}}))
    assert "upto2399 ::=" in large and "{0,2399}" not in large


@pytest.mark.parametrize("schema", [object_schema({"x": {"type": "number"}}),
    object_schema({"x": {"type": "string", "pattern": ".*"}}),
    {"type": "object", "properties": {}, "required": [], "additionalProperties": True},
    object_schema({"x": {"type": "array", "items": {"type": "boolean"}}})])
def test_unsupported_or_open_schemas_fail_closed(schema):
    with pytest.raises(ValueError):
        closing_tag_grammar(schema)


def test_bounded_candidate_accepts_only_tokenizer_verified_preserved_trigger(monkeypatch):
    config = AuxiliaryGenerationConfig(temperature=.6, final_json_grammar=True, final_json_grammar_mode="closing_tag_root_v3")
    schema = object_schema({"result": {"const": "allowed"}})
    client = LlamaClient(1)
    requests = []
    monkeypatch.setattr(client, "request", lambda route, payload: requests.append(payload) or {})
    client.complete([1], config, json_schema=schema)
    grammar = requests[0]["grammar"]
    assert r"ws ::= [ \t\n\r]{0,2}" in grammar
    settings = {"grammar": grammar, "grammar_lazy": True, "preserved_tokens": [123],
                "grammar_triggers": [{"type": 0, "value": "</think>", "token": 123}]}
    response = {"content": '</think>{"result":"allowed"}', "generation_settings": settings}
    tokenizer = SimpleNamespace(tokenize=lambda text, special: [123])
    assert audit_final_json_grammar(response, config, schema=schema, client=tokenizer)["runtime_settings_verified"]
    for bad in ({**settings, "preserved_tokens": []},
                {**settings, "grammar_triggers": [{"type": 0, "value": "</think>", "token": 124}]}):
        with pytest.raises(ValueError, match="differs"):
            audit_final_json_grammar({**response, "generation_settings": bad}, config, schema=schema, client=tokenizer)
    with pytest.raises(ValueError, match="differs"):
        audit_final_json_grammar(response, config, schema=schema)
