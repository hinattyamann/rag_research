"""Reference-markup provenance without deleting bracketed body content or changing text."""

import hashlib

import pytest

from rag_research.data.wikipedia_reference_projection import ReferenceProjection
from rag_research.data.wikipedia_snapshot import article_text


def audit(source, quote):
    return ReferenceProjection(source, article_text(source)).quote_audit(quote)


def test_source_reference_marker_projects_to_original_body_with_html_and_span_hashes():
    source = '<p>最初<sup id="cite_ref-4" class="reference"><a><span>[</span>4<span>]</span></a></sup>です。</p>'
    body = article_text(source)
    result = ReferenceProjection(source, body, request_journal_sha256="a" * 64).quote_audit("最初[4]です。")
    assert result["status"] == "located" and result["mode"] == "verified_source_reference_markup"
    assert result["source_html_sha256"] == hashlib.sha256(source.encode()).hexdigest()
    assert result["request_journal_sha256"] == "a" * 64
    span = result["spans"][0]
    assert (span["start"], span["end"]) == (0, len(body))
    assert span["source_span_sha256"] == hashlib.sha256(body.encode()).hexdigest()
    marker = span["omitted_reference_markup"][0]
    assert marker["marker_text"] == "[4]"
    assert source[marker["html_start"]:marker["html_end"]].startswith('<sup id="cite_ref-4"')
    assert hashlib.sha256(source[marker["html_start"]:marker["html_end"]].encode()).hexdigest() == marker["marker_html_sha256"]


def test_multiple_markers_whitespace_entities_and_original_unicode_offsets_are_preserved():
    source = ('<p>猫&amp;犬 <sup class="reference"><a>&#91;2&#93;</a></sup> の説明'
              '<sup class="reference">[注釈 1]</sup>。</p>')
    result = audit(source, '猫&犬[2]の説明[注釈1]。')
    assert result["status"] == "located"
    assert [m["marker_text"] for m in result["spans"][0]["omitted_reference_markup"]] == ["[2]", "[注釈 1]"]
    assert article_text(source) == "猫&犬 の説明。"


def test_all_real_occurrences_are_kept_instead_of_choosing_a_convenient_one():
    source = '<p>同じ<sup class="reference">[4]</sup>説明。</p>' * 2
    result = audit(source, "同じ[4]説明。")
    assert result["ambiguous_location"] and len(result["spans"]) == 2
    assert len({s["start"] for s in result["spans"]}) == 2


@pytest.mark.parametrize("source,quote", [
    ('<p>値です。</p><p>別の文<sup class="reference">[4]</sup>。</p>', '値[4]です。'),
    ('<p>配列[4]の値です。<sup class="reference">[2]</sup></p>', '配列の値です。[2]'),
    ('<p>値<sup>2</sup>です。</p>', '値2です。'),
    ('<p>値<sup class="reference">[5]</sup>です。</p>', '値[4]です。'),
    ('<p>値<sup class="reference">[4]</sup>です。</p>', '値[4'),
    ('<p>値<sup class="reference">[4]</sup>です。</p>', '[4]'),
    ('<p>値<sup class="reference">[4]</sup>です。</p>', '別の値[4]です。'),
    ('<div class="navbox">隠れた<sup class="reference">[4]</sup>文。</div><p>値です。</p>', '値[4]です。'),
    ('<script>"<sup class=reference>[4]</sup>"</script><p>値です。</p>', '値[4]です。'),
])
def test_non_reference_content_other_positions_partial_markers_and_semantic_replacement_are_rejected(source, quote):
    assert audit(source, quote)["status"] == "not_located"


@pytest.mark.parametrize("source", [
    '<p>値<sup class="reference">[4]</p>',
    '<p>値</sup>です。</p>',
    '<p>値<sup class="reference"/>です。</p>',
    '<p>値<sup class="reference">[<sup class="reference">4</sup>]</sup>。</p>',
])
def test_unverifiable_reference_markup_fails_closed(source):
    with pytest.raises(ValueError):
        ReferenceProjection(source, article_text(source))


def test_changed_body_and_sentinel_collision_are_not_accepted():
    source = '<p>値<sup class="reference">[4]</sup>です。</p>'
    with pytest.raises(ValueError, match="unchanged corpus"):
        ReferenceProjection(source, "変更した本文。")
    source += '<p>\ue000RAGREF:0:BEGIN\ue001</p>'
    with pytest.raises(ValueError, match="sentinel"):
        ReferenceProjection(source, article_text(source))


def test_empty_or_display_hidden_reference_element_provides_no_evidence():
    source = ('<p>値<sup class="reference"><a></a></sup>です。</p>'
              '<p>別の<sup class="reference"><span class="noprint">[4]</span></sup>文。</p>'
              '<p>本文<sup class="reference">[2]</sup>です。</p>')
    projection = ReferenceProjection(source, article_text(source))
    assert projection.quote_audit("値[4]です。")["status"] == "not_located"
    assert projection.quote_audit("別の[4]文。")["status"] == "not_located"
    assert projection.quote_audit("本文[2]です。")["status"] == "located"
