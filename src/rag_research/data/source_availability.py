"""Evidence-backed source missingness, preserving the original acquisition failure."""

from datetime import datetime

from rag_research.experiments.frozen_trace import require

POLICY = "historical-deleted-text-permissiondenied-with-verified-identity-v1"
DELETED_TEXT_MESSAGE = "You don't have permission to view deleted text or changes between deleted revisions."


def historical_identity(row, requests):
    """Cross-check saved revision metadata, never request alternative/current text."""
    query = next((value for name, value in requests.items() if name.endswith("-revision.json")), None)
    require(query is not None and query["status"] == "ok", "Missing successful historical identity lookup")
    parameters = query["parameters"]
    require(parameters.get("action") == "query" and parameters.get("titles") == row["requested_title"] and
            parameters.get("rvstart") == row["cutoff_utc"] and parameters.get("rvdir") == "older" and
            parameters.get("rvlimit") == 1, "Historical identity lookup parameters differ")
    pages = query["response"].get("query", {}).get("pages", [])
    require(len(pages) == 1, "Historical identity lookup returned unexpected pages")
    page = pages[0]
    require(page["title"] == row["canonical_title"] and page.get("pageid") == row.get("page_id"),
            "Historical identity lookup differs from article metadata")
    revisions = page.get("revisions", [])
    if revisions:
        require(len(revisions) == 1 and revisions[0]["revid"] == row["revision_id"] and
                revisions[0]["timestamp"] == row["revision_timestamp_utc"],
                "Historical revision identity differs")
        timestamp = datetime.fromisoformat(row["revision_timestamp_utc"].replace("Z", "+00:00"))
        cutoff = datetime.fromisoformat(row["cutoff_utc"].replace("Z", "+00:00"))
        require(timestamp <= cutoff, "Historical source revision is after cutoff")
    return page


def restricted_historical_text(row, requests, policy):
    """Only this exact terminal API response is an audited source text absence."""
    require(policy == POLICY, "Unknown historical source unavailability policy")
    require(row.get("status") == "error" and "text" not in row, "Restricted source must retain its error")
    page = historical_identity(row, requests)
    require(page.get("ns") == 0 and page.get("revisions") and
            type(row.get("page_id")) is int and row["page_id"] > 0 and
            type(row.get("revision_id")) is int and row["revision_id"] > 0,
            "Restricted source has no verified article identity")
    parse = next((value for name, value in requests.items() if name.endswith("-parse.json")), None)
    require(parse is not None and parse["status"] == "error" and parse.get("attempts"),
            "Missing failed historical parse journal")
    require(parse["parameters"].get("action") == "parse" and
            parse["parameters"].get("oldid") == row["revision_id"], "Restricted source request differs")
    error = parse["attempts"][-1].get("error_response", {}).get("error", {})
    require(parse["attempts"][-1].get("http_status") == 200 and
            error.get("code") == "permissiondenied" and error.get("info") == DELETED_TEXT_MESSAGE,
            "Acquisition error is not the declared deleted-text unavailability")
    return {"requested_title": row["requested_title"], "page_id": row["page_id"],
            "revision_id": row["revision_id"], "original_status": "error",
            "corpus_availability": "unavailable_deleted_historical_text", "policy": policy,
            "body_retrieved": False, "fallback_performed": False}
