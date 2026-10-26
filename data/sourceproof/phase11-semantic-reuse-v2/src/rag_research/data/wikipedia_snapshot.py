"""Serial historical article acquisition with immutable request journals and hashes.

HTML is retained as data, never executed. Rendering an old revision can still use
current templates; archived responses/text hashes, not oldid alone, pin this corpus.
"""

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser

from rag_research.experiments.storage import checkpoint, read_json, verify_checkpoint
from rag_research.retrieval.common import file_hash

ENDPOINT = "https://ja.wikipedia.org/w/api.php"
TEXT_VERSION = "wikipedia-rendered-article-text-v1"
USER_AGENT = "rag-research/0.1 (https://github.com/hinattyamann/rag_research; academic snapshot)"
BLOCKS = {"p", "div", "section", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "dl", "dt", "dd", "br"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
OMIT_TAGS = {"script", "style", "noscript", "sup"}
OMIT_CLASSES = {"mw-editsection", "navbox", "vertical-navbox", "metadata", "noprint", "reflist", "toc"}


class SnapshotError(ValueError):
    """A failed source acquisition; no replacement or silent current-page fallback."""


class ArticleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        hidden = bool(self.stack and self.stack[-1][1]) or tag in OMIT_TAGS or bool(
            set(attributes.get("class", "").split()) & OMIT_CLASSES)
        if not hidden and tag in BLOCKS:
            self.parts.append("\n")
        if tag not in VOID:
            self.stack.append((tag, hidden))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                hidden = self.stack[index][1]
                del self.stack[index:]
                if not hidden and tag in BLOCKS:
                    self.parts.append("\n")
                if not hidden and tag in {"td", "th"}:
                    self.parts.append(" ")
                break

    def handle_data(self, data):
        if not self.stack or not self.stack[-1][1]:
            self.parts.append(data)


def article_text(html):
    parser = ArticleText()
    parser.feed(html)
    parser.close()
    lines = [" ".join(line.split()) for line in "".join(parser.parts).splitlines()]
    return "\n".join(line for line in lines if line)


def validate_spec(spec):
    if (spec.get("schema_version") != 1 or spec.get("purpose") != "phase11-japanese-corpus-acquisition"
            or spec.get("endpoint") != ENDPOINT or spec.get("text_version") != TEXT_VERSION
            or spec.get("model_calls") != 0 or spec.get("phase12_allowed") is not False):
        raise ValueError("Unsupported Japanese corpus acquisition specification")
    cutoff = datetime.fromisoformat(spec["cutoff_utc"].replace("Z", "+00:00"))
    if cutoff.utcoffset() is None:
        raise ValueError("Article cutoff needs a timezone")
    for name, low, high in (("timeout_seconds", 1, 60), ("request_attempt_limit", 1, 3),
                            ("maximum_response_bytes", 1, 20_000_000),
                            ("maximum_consecutive_network_failures", 1, 10)):
        if type(spec.get(name)) is not int or not low <= spec[name] <= high:
            raise ValueError(f"Invalid acquisition bound: {name}")
    interval = spec.get("minimum_request_interval_seconds")
    if type(interval) not in {int, float} or not .25 <= interval <= 10:
        raise ValueError("Serial request interval must be bounded")
    if spec.get("maxlag_seconds") != 5:
        raise ValueError("Use the declared maxlag policy")


class MediaWikiClient:
    def __init__(self, spec):
        validate_spec(spec)
        self.spec = spec
        self.last_request = 0.0
        self.network_requests = 0

    def get(self, parameters, path):
        parameters = {"format": "json", "formatversion": 2, "maxlag": 5, **parameters}
        if path.exists():
            saved = read_json(path)
            verify_checkpoint(saved)
            if saved["parameters"] != parameters:
                raise SnapshotError("Saved source request parameters changed")
            if saved["status"] != "ok":
                raise SnapshotError("Saved terminal source request failure; keep its history")
            return saved["response"]
        path.parent.mkdir(parents=True, exist_ok=True)
        attempts = []
        url = ENDPOINT + "?" + urllib.parse.urlencode(parameters)
        for index in range(self.spec["request_attempt_limit"]):
            delay = self.spec["minimum_request_interval_seconds"] - (time.monotonic() - self.last_request)
            if delay > 0:
                time.sleep(delay)
            self.last_request = time.monotonic()
            self.network_requests += 1
            attempt = {"started_at_utc": datetime.now(UTC).isoformat(), "number": index + 1}
            retryable = False
            retry_after = 0
            response_value = None
            try:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=self.spec["timeout_seconds"]) as response:
                    payload = response.read(self.spec["maximum_response_bytes"] + 1)
                    attempt["http_status"] = response.status
                if len(payload) > self.spec["maximum_response_bytes"]:
                    raise SnapshotError("Article API response exceeds bound")
                attempt["response_sha256"] = hashlib.sha256(payload).hexdigest()
                response_value = json.loads(payload)
                if not isinstance(response_value, dict):
                    raise SnapshotError("Article API response is not an object")
                if "error" in response_value:
                    code = response_value["error"].get("code")
                    retryable = code in {"maxlag", "ratelimited", "readonly"}
                    raise SnapshotError(f"MediaWiki error: {code}")
            except (urllib.error.URLError, TimeoutError, SnapshotError, json.JSONDecodeError) as error:
                retryable = retryable or isinstance(error, (urllib.error.URLError, TimeoutError))
                if isinstance(error, urllib.error.HTTPError):
                    retryable = error.code in {429, 500, 502, 503, 504}
                    attempt["http_status"] = error.code
                    header = error.headers.get("Retry-After", "0") if error.headers else "0"
                    if header.isdigit():
                        retry_after = int(header)
                        attempt["retry_after_seconds"] = retry_after
                attempt["error"] = str(error)
                if response_value is not None:
                    attempt["error_response"] = response_value
                attempts.append(attempt)
                if retryable and index + 1 < self.spec["request_attempt_limit"]:
                    time.sleep(max(5 * (index + 1), retry_after))
                    continue
                checkpoint(path, {"purpose": "historical-wikipedia-api-request", "parameters": parameters,
                                  "url": url, "status": "error", "attempts": attempts})
                raise SnapshotError(str(error)) from error
            attempts.append(attempt)
            checkpoint(path, {"purpose": "historical-wikipedia-api-request", "parameters": parameters,
                              "url": url, "status": "ok", "attempts": attempts,
                              "response": response_value})
            return response_value
        raise AssertionError("Request loop must terminate with a journal")


def fetch_article(client, spec, title, directory, plan_hash):
    key = hashlib.sha256(title.encode()).hexdigest()[:24]
    path = directory / "articles" / f"{key}.json"
    if path.exists():
        saved = read_json(path)
        verify_checkpoint(saved)
        if saved["plan_sha256"] != plan_hash or saved["requested_title"] != title:
            raise SnapshotError("Historical article plan changed")
        for artifact, expected in saved.get("request_files_sha256", {}).items():
            if file_hash(directory / artifact) != expected:
                raise SnapshotError("Historical source request changed")
        return saved
    path.parent.mkdir(parents=True, exist_ok=True)
    (directory / "requests").mkdir(parents=True, exist_ok=True)
    result = {"purpose": "historical-wikipedia-article", "requested_title": title,
              "plan_sha256": plan_hash, "text_version": TEXT_VERSION,
              "cutoff_utc": spec["cutoff_utc"], "request_files_sha256": {}}
    request_files = []
    try:
        query_path = directory / "requests" / f"{key}-revision.json"
        request_files.append(query_path)
        data = client.get({"action": "query", "prop": "revisions", "titles": title, "redirects": 1,
                           "rvprop": "ids|timestamp", "rvstart": spec["cutoff_utc"],
                           "rvdir": "older", "rvlimit": 1}, query_path)
        pages = data.get("query", {}).get("pages", [])
        if len(pages) != 1:
            raise SnapshotError("Historical lookup returned an unexpected page set")
        page = pages[0]
        result.update(canonical_title=page["title"], page_id=page.get("pageid"),
                      normalized_titles=data["query"].get("normalized", []),
                      current_redirects=data["query"].get("redirects", []))
        if page.get("missing") is True or not page.get("revisions"):
            result.update(status="unavailable", error="No article revision at declared cutoff")
        elif page.get("ns") != 0:
            result.update(status="unavailable", error="Not an encyclopedia article namespace")
        else:
            revision = page["revisions"][0]
            timestamp = datetime.fromisoformat(revision["timestamp"].replace("Z", "+00:00"))
            cutoff = datetime.fromisoformat(spec["cutoff_utc"].replace("Z", "+00:00"))
            if timestamp > cutoff:
                raise SnapshotError("Article revision exceeds declared cutoff")
            result.update(revision_id=revision["revid"], revision_timestamp_utc=revision["timestamp"],
                          source_url="https://ja.wikipedia.org/w/index.php?oldid=" + str(revision["revid"]))
            parse_path = directory / "requests" / f"{key}-parse.json"
            request_files.append(parse_path)
            parsed = client.get({"action": "parse", "oldid": revision["revid"],
                                 "prop": "text|revid|wikitext", "disableeditsection": 1,
                                 "disabletoc": 1}, parse_path)["parse"]
            if parsed["revid"] != revision["revid"] or parsed["pageid"] != page["pageid"]:
                raise SnapshotError("Rendered historical page identity differs")
            text = article_text(parsed["text"])
            if not text:
                raise SnapshotError("Historical article rendered no text")
            result.update(status="ok", text=text, text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                          characters=len(text), rendering_may_use_current_templates=True)
    except (SnapshotError, KeyError, TypeError) as error:
        result.update(status="error", error=str(error))
    result["request_files_sha256"] = {p.relative_to(directory).as_posix(): file_hash(p)
                                      for p in request_files if p.exists()}
    return checkpoint(path, result)
