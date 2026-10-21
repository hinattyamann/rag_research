"""Source/corpus boundaries: historical versions, stable journals, no Gold injection."""

import hashlib
import importlib.util
import io
import json
import urllib.error
from copy import deepcopy
from pathlib import Path

import pytest

from rag_research.data.baobab_source import article_titles, validate_rows
from rag_research.data.wikipedia_snapshot import (
    MediaWikiClient,
    SnapshotError,
    article_text,
    fetch_article,
    validate_spec,
)
from rag_research.experiments.storage import checkpoint, read_json

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def spec():
    return json.loads((ROOT / "configs/phase11_japanese_corpus_v1.json").read_text())


def sample():
    return {"id": 1, "question": "合成の開発用質問", "answer": {
        "text": "架空の都市です。住民がいます。", "sentences": [
            {"text": "架空の都市です。", "citations": [0]},
            {"text": "住民がいます。", "citations": [1]}]},
        "references": [
            {"page": {"title": "架空の都市", "url": "https://ja.wikipedia.org/wiki/fixture",
                      "quote": {"text": "合成の根拠本文"}}},
            {"page": {"title": "架空の住民", "url": "https://ja.wikipedia.org/wiki/fixture2",
                      "summary": {"text": "人手要約という設定の合成例"}}}]}


def test_reference_mapping_and_nonquote_are_preserved_offline():
    row = sample()
    before = deepcopy(row)
    validate_rows([row], answered=True)
    assert row == before and row["references"][1]["page"].get("quote") is None
    for mutate in (
        lambda r: r["answer"]["sentences"][0].update(citations=[2]),
        lambda r: r["answer"]["sentences"][0].update(citations=[True]),
        lambda r: r["answer"].update(text="別の回答"),
        lambda r: r["references"][0]["page"].update(url="https://unrelated.example/wiki/fixture"),
    ):
        changed = deepcopy(row)
        mutate(changed)
        with pytest.raises(ValueError):
            validate_rows([changed], answered=True)


def test_corpus_titles_include_failed_searches_and_ignore_answer_quality():
    answered = sample()
    unsuccessful = {"id": 2, "question": "別の合成質問", "references": [
        {"page": {"title": "別の参照記事", "url": "https://ja.wikipedia.org/wiki/fixture3"}},
        {"not_found": {"url": "https://ja.wikipedia.org/w/index.php?search=fixture"}}]}
    validate_rows([unsuccessful], answered=False)
    chunks = {"answered": [answered], "not_answered": [unsuccessful]}
    expected = article_titles(chunks)
    assert set(expected) == {"架空の都市", "架空の住民", "別の参照記事"}
    answered["answer"]["text"] = "This altered answer must not select corpus documents."
    answered["question"] = "Changed question"
    assert article_titles(chunks) == expected
    with pytest.raises(ValueError, match="Unexpected answer"):
        validate_rows([{**unsuccessful, "answer": {}}], answered=False)


def test_html_is_text_data_and_keeps_inline_words_and_table_values():
    html = ('<style>bad CSS</style><div><p>日本の<a href="evil">記事</a>です。'
            '<sup>[999]</sup>次の文です。</p><div class="navbox"><span>navigation</span></div>'
            '<script>bad script</script><p>A <b>source</b> remains.</p>'
            '<table><tr><td>項目</td><td>3.14</td></tr></table><p>本文末尾</p></div>')
    result = article_text(html)
    assert result == "日本の記事です。次の文です。\nA source remains.\n項目 3.14\n本文末尾"
    assert article_text("<p>本文<br/>続き</p>") == "本文\n続き"


class FakeClient:
    def __init__(self, *, timestamp="2023-12-01T00:00:00Z", missing=False):
        self.calls = []
        self.timestamp = timestamp
        self.missing = missing

    def get(self, parameters, path):
        self.calls.append(parameters)
        if parameters["action"] == "query":
            page = {"pageid": 1, "ns": 0, "title": "合成記事"}
            if not self.missing:
                page["revisions"] = [{"revid": 10, "timestamp": self.timestamp}]
            value = {"query": {"pages": [page], "redirects": [{"from": "別名", "to": "合成記事"}]}}
        else:
            value = {"parse": {"pageid": 1, "revid": 10, "text": "<p>合成の本文。</p>"}}
        checkpoint(path, {"response": value})
        return value


def test_historical_identity_and_resume_are_bound_to_raw_requests(tmp_path, spec):
    client = FakeClient()
    saved = fetch_article(client, spec, "別名", tmp_path, "fixed-plan")
    assert saved["status"] == "ok" and saved["revision_id"] == 10
    assert client.calls[0]["rvlimit"] == 1 and client.calls[0]["rvstart"] == spec["cutoff_utc"]
    assert client.calls[1]["oldid"] == 10 and "page" not in client.calls[1]
    assert fetch_article(client, spec, "別名", tmp_path, "fixed-plan") == saved
    assert len(client.calls) == 2
    with pytest.raises(SnapshotError, match="plan changed"):
        fetch_article(client, spec, "別名", tmp_path, "changed-plan")
    request = next(iter(saved["request_files_sha256"]))
    (tmp_path / request).write_text("tampered")
    with pytest.raises(SnapshotError, match="request changed"):
        fetch_article(client, spec, "別名", tmp_path, "fixed-plan")


@pytest.mark.parametrize("kwargs,status", [
    ({"timestamp": "2024-01-01T00:00:00Z"}, "error"), ({"missing": True}, "unavailable")])
def test_no_current_revision_fallback_for_missing_or_too_new_history(tmp_path, spec, kwargs, status):
    client = FakeClient(**kwargs)
    result = fetch_article(client, spec, "合成記事", tmp_path, "p")
    assert result["status"] == status and "text" not in result
    assert len(client.calls) == 1


def test_api_retry_history_and_terminal_failures_do_not_get_overwritten(tmp_path, spec, monkeypatch):
    import rag_research.data.wikipedia_snapshot as snapshot

    sleeps = []
    monkeypatch.setattr(snapshot.time, "sleep", sleeps.append)
    calls = []

    def unavailable(*args, **kwargs):
        calls.append(args)
        raise urllib.error.HTTPError("https://ja.wikipedia.org/", 429, "rate limited",
                                     {"Retry-After": "20"}, None)

    monkeypatch.setattr(snapshot.urllib.request, "urlopen", unavailable)
    client = MediaWikiClient(spec)
    target = tmp_path / "request.json"
    with pytest.raises(SnapshotError):
        client.get({"action": "query"}, target)
    saved = read_json(target)
    assert len(calls) == spec["request_attempt_limit"] == len(saved["attempts"])
    assert sleeps.count(20) == 2
    before = target.read_bytes()
    with pytest.raises(SnapshotError, match="terminal"):
        client.get({"action": "query"}, target)
    assert len(calls) == 3 and target.read_bytes() == before


def test_spec_rejects_endpoint_changes_and_unbounded_requests(spec):
    validate_spec(spec)
    for name, value in (("endpoint", "https://unrelated.example"), ("request_attempt_limit", 999),
                        ("minimum_request_interval_seconds", 0), ("phase12_allowed", True)):
        with pytest.raises(ValueError):
            validate_spec({**spec, name: value})


def test_acquisition_plan_resume_detects_tampered_source_archive(tmp_path, monkeypatch):
    module_spec = importlib.util.spec_from_file_location(
        "prepare_japanese", ROOT / "scripts/prepare_japanese_corpus.py")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    monkeypatch.setattr(module, "load_source", lambda _: {"answered": [sample()]})
    config_path = ROOT / "configs/phase11_japanese_corpus_v1.json"
    output = tmp_path / "corpus"
    saved = module.prepare(tmp_path, output, config_path)
    assert saved["titles"] == ["架空の住民", "架空の都市"]
    assert module.prepare(tmp_path, output, config_path) == saved
    archived = output / "source_snapshot/src/rag_research/data/wikipedia_snapshot.py"
    archived.write_text("changed")
    with pytest.raises(ValueError, match="Archived acquisition source"):
        module.prepare(tmp_path, output, config_path)


def test_source_download_checks_fixed_hash_before_publish_and_refuses_changed_cache(tmp_path, monkeypatch):
    from rag_research.data import baobab_source

    payload = b"synthetic public source fixture"
    monkeypatch.setattr(baobab_source, "SOURCE_FILES", {"answered.jsonl": hashlib.sha256(payload).hexdigest()})
    monkeypatch.setattr(baobab_source.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b"wrong"))
    with pytest.raises(ValueError, match="Downloaded Japanese source hash differs"):
        baobab_source.download_source(tmp_path)
    assert not (tmp_path / "answered.jsonl").exists()
    monkeypatch.setattr(baobab_source.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(payload))
    baobab_source.download_source(tmp_path)
    assert (tmp_path / "answered.jsonl").read_bytes() == payload
    (tmp_path / "answered.jsonl").write_bytes(b"local change")
    with pytest.raises(ValueError, match="Existing Japanese source hash differs"):
        baobab_source.download_source(tmp_path)
    assert (tmp_path / "answered.jsonl").read_bytes() == b"local change"
