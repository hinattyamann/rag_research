"""Optional bounded public-source acquisition, separate from offline verification.

The output directory must be new. No authentication or model request is used.
"""

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

QUERIES = {
    "cutoff": {"action": "query", "prop": "revisions", "titles": "ニューラルネットワーク",
               "rvprop": "ids|timestamp", "rvstart": "2023-12-25T23:59:59Z", "rvdir": "older",
               "rvlimit": 1, "redirects": 1},
    "earliest": {"action": "query", "prop": "revisions", "pageids": 5273510,
                 "rvprop": "ids|timestamp", "rvdir": "newer", "rvlimit": 1},
    "move_log": {"action": "query", "list": "logevents", "letitle": "ニューラルネットワーク",
                 "letype": "move", "leprop": "ids|title|type|timestamp|details", "lelimit": 10},
    "delete_log": {"action": "query", "list": "logevents", "letitle": "ニューラルネットワーク",
                   "letype": "delete", "leprop": "ids|title|type|timestamp|details", "lelimit": 10},
    "moved_cutoff": {"action": "query", "prop": "revisions", "pageids": 56523,
                     "rvprop": "ids|timestamp", "rvstart": "2023-12-25T23:59:59Z",
                     "rvdir": "older", "rvlimit": 1},
    "historical_parse": {"action": "parse", "oldid": 98057227, "prop": "text|revid|wikitext",
                         "disableeditsection": 1, "disabletoc": 1},
}


def fetch(output):
    output.mkdir(parents=True, exist_ok=False)
    for name, parameters in QUERIES.items():
        parameters = {**parameters, "format": "json", "formatversion": 2, "maxlag": 5}
        url = "https://ja.wikipedia.org/w/api.php?" + urllib.parse.urlencode(parameters)
        record = {"url": url, "parameters": parameters, "retrieved_at_utc": datetime.now(UTC).isoformat()}
        try:
            request = urllib.request.Request(url, headers={"User-Agent":
                "rag-research/0.1 provenance-audit (https://github.com/hinattyamann/rag_research)"})
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read(2_000_001)
                record.update(http_status=response.status, final_url=response.url)
            if len(payload) > 2_000_000:
                raise ValueError("Public response exceeds the audit bound")
            (output / f"{name}_response.json").write_bytes(payload)
            record.update(response_sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            record.update(error_type=type(error).__name__, error=str(error))
        (output / f"{name}_request.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        time.sleep(.5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    fetch(parser.parse_args().output)
