"""Synthetic boundary/coverage checks; no held-out Japanese QA is inspected."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from rag_research.evaluation.sentence_claims import (
    JAPANESE_REFUSAL,
    JAPANESE_VERSION,
    VERSION,
    extract_sentence_units,
)
from rag_research.evaluation.tasks import execute_task
from rag_research.experiments import protocol

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("answer,texts", [
    ("名前は架空市です。人口は3人です。", ["名前は架空市です。", "人口は3人です。"]),
    ("本当？記録はあります！確認します。", ["本当？", "記録はあります！", "確認します。"]),
    ("本当?記録はあります!確認します。", ["本当?", "記録はあります!", "確認します。"]),
    ("本当！？ 次です。", ["本当！？", "次です。"]),
    ("第一です。\n\t第二です。", ["第一です。", "第二です。"]),
    ("館長は「開館した。閉館は未定。」と話した。次です。",
     ["館長は「開館した。閉館は未定。」と話した。", "次です。"]),
    ("記録は「第1部。『詳細？』第2部。」である。次です。",
     ["記録は「第1部。『詳細？』第2部。」である。", "次です。"]),
    ("（詳細。補足？）結論です。次です。", ["（詳細。補足？）結論です。", "次です。"]),
    ('館長は"開館した。未定？"と話した。次です。',
     ['館長は"開館した。未定？"と話した。', "次です。"]),
    ('館長は“開館した。未定？”と話した。次です。',
     ['館長は“開館した。未定？”と話した。', "次です。"]),
    ('館長は"記号\\\"を含む。補足。"と話した。次です。',
     ['館長は"記号\\\"を含む。補足。"と話した。', "次です。"]),
    ("[a planet]という表記です。[12] 大きさは3.14です。",
     ["[a planet]という表記です。", "大きさは3.14です。"]),
    ("URLはhttps://example.test/path?a=1!b=2です。次です。",
     ["URLはhttps://example.test/path?a=1!b=2です。", "次です。"]),
    ("Dr. Chen met U.S. officials. 次は報告です。",
     ["Dr. Chen met U.S. officials.", "次は報告です。"]),
    ("博士Dr. Chenの報告です。次です。", ["博士Dr. Chenの報告です。", "次です。"]),
    ("Sentence one. Sentence two.", ["Sentence one.", "Sentence two."]),
    ("句点のない末尾も保持", ["句点のない末尾も保持"]),
    ("開館しました。末尾は「未完。補足です。", ["開館しました。", "末尾は「未完。補足です。"]),
])
def test_japanese_units_preserve_every_span_and_compound_context(answer, texts):
    result = extract_sentence_units(answer, language="ja")
    assert [claim["text"] for claim in result["claims"]] == texts
    assert result["unit_version"] == JAPANESE_VERSION
    assert result["exclusion"] is None
    assert [c["claim_id"] for c in result["claims"]] == [f"c{i + 1}" for i in range(len(texts))]
    prose, spans = result["normalized_prose"], result["spans"]
    assert spans[0]["start"] == 0 and spans[-1]["end"] == len(prose)
    assert all(a["end"] == b["start"] for a, b in zip(spans, spans[1:]))
    assert "".join(prose[s["start"]:s["end"]] for s in spans) == prose
    assert [prose[s["start"]:s["end"]].strip() for s in spans] == texts


def test_unclosed_delimiter_is_retained_and_audited():
    result = extract_sentence_units("本文。（未完「引用。次の文。", language="ja")
    assert len(result["claims"]) == 2
    assert result["unclosed_delimiters"] == ["）", "」"]


@pytest.mark.parametrize("answer,exclusion", [
    ("  \n", "empty_or_citations"),
    ("[p1] [12] [123_0-99]", "empty_or_citations"),
    (JAPANESE_REFUSAL, "standalone_refusal"),
    (JAPANESE_REFUSAL + "。[p1]", "standalone_refusal"),
    ("The retrieved passages do not provide enough information to answer this question.",
     "standalone_refusal"),
])
def test_only_explicit_standalone_refusals_and_citations_are_excluded(answer, exclusion):
    result = extract_sentence_units(answer, language="ja")
    assert result["exclusion"] == exclusion
    assert result["claims"] == result["spans"] == []


def test_mixed_refusal_and_ambiguous_refusal_keep_prose():
    answer = JAPANESE_REFUSAL + "。架空市には3人います。"
    result = extract_sentence_units(answer, language="ja")
    assert len(result["claims"]) == 2 and result["exclusion"] is None
    for ambiguous in ("わかりません。", "回答できません。", "[出典不明] 資料が足りません。"):
        assert extract_sentence_units(ambiguous, language="ja")["claims"]


def test_language_is_explicit_and_legacy_english_output_is_unchanged():
    answer = "Dr. Chen arrived. It weighs 1.5 kg."
    expected = {"claims": [{"claim_id": "c1", "text": "Dr. Chen arrived."},
                           {"claim_id": "c2", "text": "It weighs 1.5 kg."}],
                "unit_version": VERSION, "normalized_prose": answer, "exclusion": None,
                "spans": [{"start": 0, "end": 18}, {"start": 18, "end": 35}]}
    assert extract_sentence_units(answer) == extract_sentence_units(answer, language="en") == expected
    japanese = "第一です。第二です。"
    assert len(extract_sentence_units(japanese)["claims"]) == 1
    assert len(extract_sentence_units(japanese, language="ja")["claims"]) == 2
    with pytest.raises(ValueError, match="language"):
        extract_sentence_units(answer, language="auto")
    with pytest.raises(ValueError, match="text"):
        extract_sentence_units(None, language="ja")


def test_japanese_extraction_uses_no_model_and_binds_mode_on_resume(tmp_path):
    config, english, _ = protocol.load_protocol(ROOT / "configs/order_phase10_v3.yaml")
    prompts = deepcopy(english)
    prompts.update(language="ja", claim_units="verbatim-sentences-ja-v1")
    settings = protocol.task_config(config, "extract_claims")
    path = tmp_path / "claims.json"
    payload = {"answer": "開館は8時です。式典は10時です。"}
    result = execute_task(None, settings, prompts, "extract_claims", payload, path, {},
                          constraints=config["output_constraints"])
    assert result["status"] == "ok" and not result["completion_attempted"]
    assert result["input_tokens"] == result["output_tokens"] == 0
    assert len(result["parsed"]["claims"]) == 2
    assert result["unit_audit"]["unit_version"] == JAPANESE_VERSION
    before = path.read_bytes()
    assert execute_task(None, settings, prompts, "extract_claims", payload, path, {},
                        constraints=config["output_constraints"]) == result
    assert path.read_bytes() == before
    prompts["claim_units"] = "verbatim-sentences-v1"
    with pytest.raises(ValueError, match="hash mismatch"):
        execute_task(None, settings, prompts, "extract_claims", payload, path, {},
                     constraints=config["output_constraints"])
    refused = execute_task(None, settings, {**prompts, "claim_units": "verbatim-sentences-ja-v1"},
                           "extract_claims", {"answer": JAPANESE_REFUSAL + "。"},
                           tmp_path / "refusal.json", {})
    assert refused["status"] == "not_applicable" and not refused["completion_attempted"]


@pytest.mark.parametrize("mode", ["unknown", "verbatim-sentence-ja-v1", [], False])
def test_unknown_mode_fails_before_any_model_call_or_journal(tmp_path, mode):
    config, prompts, _ = protocol.load_protocol(ROOT / "configs/order_phase10_v3.yaml")
    prompts["claim_units"] = mode
    path = tmp_path / "claims.json"
    with pytest.raises(ValueError, match="Unknown claim units"):
        execute_task(None, protocol.task_config(config, "extract_claims"), prompts,
                     "extract_claims", {"answer": "開館は8時です。"}, path, {})
    assert not path.exists()


def test_protocol_validates_mode_without_changing_legacy_modes(tmp_path, monkeypatch):
    config, prompts, _ = protocol.load_protocol(ROOT / "configs/order_phase10_v3.yaml")
    config["prompts"] = "prompts.yaml"
    config_path, prompt_path = tmp_path / "protocol.yaml", tmp_path / "prompts.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(protocol, "ROOT", tmp_path)
    for mode in (None, "verbatim-sentences-v1", "verbatim-sentences-ja-v1"):
        prompts["claim_units"] = mode
        prompt_path.write_text(yaml.safe_dump(prompts), encoding="utf-8")
        assert protocol.load_protocol(config_path)[1]["claim_units"] == mode
    prompts["claim_units"] = "unknown"
    prompt_path.write_text(yaml.safe_dump(prompts), encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown claim units"):
        protocol.load_protocol(config_path)
