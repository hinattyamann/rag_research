"""A deleted-text absence is an evidence classification, not a success rewrite."""

from copy import deepcopy
from pathlib import Path

import pytest

from rag_research.data.japanese_dataset import validate_spec
from rag_research.data.source_availability import (
    DELETED_TEXT_MESSAGE,
    POLICY,
    restricted_historical_text,
)
from rag_research.retrieval.common import read_json

ROOT = Path(__file__).resolve().parents[2]


def fixture():
    row = {"status": "error", "requested_title": "架空の記事", "canonical_title": "架空の記事",
           "page_id": 1, "revision_id": 2, "revision_timestamp_utc": "2023-12-01T00:00:00Z",
           "cutoff_utc": "2023-12-25T23:59:59Z", "error": "MediaWiki error: permissiondenied"}
    requests = {"x-revision.json": {"status": "ok", "parameters": {
        "action": "query", "titles": "架空の記事", "rvstart": row["cutoff_utc"], "rvdir": "older", "rvlimit": 1},
        "response": {"query": {"pages": [{"pageid": 1, "title": "架空の記事", "ns": 0,
                     "revisions": [{"revid": 2, "timestamp": row["revision_timestamp_utc"]}]}]}}},
        "x-parse.json": {"status": "error", "parameters": {"action": "parse", "oldid": 2},
            "attempts": [{"http_status": 200, "error_response": {
                "error": {"code": "permissiondenied", "info": DELETED_TEXT_MESSAGE}}}]}}
    return row, requests


def test_documented_absence_preserves_raw_error_and_has_no_text_or_fallback():
    row, requests = fixture()
    before = deepcopy((row, requests))
    result = restricted_historical_text(row, requests, POLICY)
    assert result["original_status"] == "error" and result["body_retrieved"] is False
    assert result["corpus_availability"] == "unavailable_deleted_historical_text"
    assert result["fallback_performed"] is False and (row, requests) == before


@pytest.mark.parametrize("mutation", ["network", "other_permission", "http_403", "wrong_page",
                                     "wrong_revision", "future_revision", "current_parse", "has_text"])
def test_transport_errors_unrelated_permissions_and_unverified_identities_fail_closed(mutation):
    row, requests = fixture()
    query = requests["x-revision.json"]["response"]["query"]["pages"][0]
    attempt = requests["x-parse.json"]["attempts"][0]
    if mutation == "network":
        attempt["error_response"] = {"error": {"code": "maxlag", "info": "Retry later"}}
    elif mutation == "other_permission":
        attempt["error_response"]["error"]["info"] = "Your account has no permission"
    elif mutation == "http_403":
        attempt["http_status"] = 403
    elif mutation == "wrong_page":
        query["pageid"] = 3
    elif mutation == "wrong_revision":
        query["revisions"][0]["revid"] = 3
    elif mutation == "future_revision":
        row["revision_timestamp_utc"] = query["revisions"][0]["timestamp"] = "2024-01-01T00:00:00Z"
    elif mutation == "current_parse":
        requests["x-parse.json"]["parameters"] = {"action": "parse", "page": "架空の記事"}
    else:
        row["text"] = "捏造した本文"
    with pytest.raises(ValueError):
        restricted_historical_text(row, requests, POLICY)


def test_a_new_policy_needs_an_explicit_new_dataset_version():
    original = read_json(ROOT / "configs/phase11_japanese_dataset_v1.json")
    original["terminal_source_unavailability_policy"] = POLICY
    with pytest.raises(ValueError, match="new Japanese dataset version"):
        validate_spec(original)
    updated = read_json(ROOT / "configs/phase11_japanese_dataset_v2.json")
    validate_spec(updated)
    updated["terminal_source_unavailability_policy"] = "allow_every_error"
    with pytest.raises(ValueError):
        validate_spec(updated)
