"""Project source-rendered reference superscripts onto an unchanged corpus body."""

import hashlib
import html
import re
from html.parser import HTMLParser

from rag_research.data.wikipedia_snapshot import article_text
from rag_research.experiments.frozen_trace import require

POLICY = "source-html-reference-superscript-exact-body-projection-v1"
SENTINEL = "\ue000RAGREF:"
TOKEN = re.compile(re.escape(SENTINEL) + r"(\d+):(BEGIN|END)\ue001")


class ReferenceSuperscripts(HTMLParser):
    """Locate complete sup.reference elements; other superscripts are untouched."""

    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", source)]
        self.sup_stack, self.markers = [], []
        self.feed(source)
        self.close()
        require(not self.sup_stack, "Unclosed source superscript; no reference projection")

    def source_offset(self):
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag != "sup":
            return
        reference = "reference" in dict(attrs).get("class", "").split()
        require(not reference or not any(s[0] for s in self.sup_stack), "Nested reference superscripts are unsupported")
        start = self.source_offset()
        self.sup_stack.append((reference, start, start + len(self.get_starttag_text())))

    def handle_startendtag(self, tag, attrs):
        require(tag != "sup" or "reference" not in dict(attrs).get("class", "").split(),
                "Self-closing reference superscript has no source text")

    def handle_endtag(self, tag):
        if tag != "sup":
            return
        require(bool(self.sup_stack), "Unmatched source superscript end")
        reference, start, inner_start = self.sup_stack.pop()
        if not reference:
            return
        close = self.source_offset()
        end = self.source.find(">", close) + 1
        require(end > close and inner_start <= close, "Invalid source reference element span")
        marker = article_text(self.source[inner_start:close])
        if not marker.strip():
            # Empty/display-hidden markers provide no source evidence and stay omitted.
            return
        self.markers.append({"html_start": start, "html_end": end, "marker_text": marker,
                             "marker_html_sha256": hashlib.sha256(self.source[start:end].encode()).hexdigest()})


class ReferenceProjection:
    """Every non-reference visible character must map back to the saved corpus body."""

    def __init__(self, source_html, body, *, request_journal_sha256=None):
        require(isinstance(source_html, str) and isinstance(body, str) and body.strip(), "Invalid projection inputs")
        require(SENTINEL not in source_html and SENTINEL not in body, "Source collides with internal projection sentinel")
        require(article_text(source_html) == body, "Saved HTML does not reconstruct the unchanged corpus body")
        self.body = body
        self.html_sha256 = hashlib.sha256(source_html.encode()).hexdigest()
        self.request_journal_sha256 = request_journal_sha256
        markers = sorted(ReferenceSuperscripts(source_html).markers, key=lambda r: r["html_start"])
        self.markers = dict(enumerate(markers))
        pieces, cursor = [], 0
        for number, marker in self.markers.items():
            require(marker["html_start"] >= cursor, "Source reference spans overlap")
            pieces.extend([source_html[cursor:marker["html_start"]],
                           f"<span>{SENTINEL}{number}:BEGIN\ue001{html.escape(marker['marker_text'])}"
                           f"{SENTINEL}{number}:END\ue001</span>"])
            cursor = marker["html_end"]
        pieces.append(source_html[cursor:])
        rendered = article_text("".join(pieces))
        body_positions = [i for i, c in enumerate(body) if not c.isspace()]
        compact_body = "".join(body[i] for i in body_positions)
        chars, self.positions, self.marker_ids = [], [], []
        active, cursor, body_cursor = None, 0, 0

        def append(value):
            nonlocal body_cursor
            for char in value:
                if char.isspace():
                    continue
                if active is None:
                    require(body_cursor < len(compact_body) and char == compact_body[body_cursor],
                            "Reference rendering changes non-reference corpus characters")
                    self.positions.append(body_positions[body_cursor])
                    body_cursor += 1
                else:
                    self.positions.append(None)
                chars.append(char)
                self.marker_ids.append(active)

        for token in TOKEN.finditer(rendered):
            append(rendered[cursor:token.start()])
            number = int(token[1])
            require(number in self.markers, "Unknown projection marker")
            if token[2] == "BEGIN":
                require(active is None, "Nested projection sentinel")
                active = number
            else:
                require(active == number, "Mismatched projection sentinel")
                active = None
            cursor = token.end()
        append(rendered[cursor:])
        require(active is None and body_cursor == len(compact_body), "Reference projection loses corpus characters")
        self.compact = "".join(chars)
        self.marker_bounds = {}
        marker_text = {}
        for index, number in enumerate(self.marker_ids):
            if number is not None:
                if number not in self.marker_bounds:
                    self.marker_bounds[number] = [index, index + 1]
                    marker_text[number] = []
                self.marker_bounds[number][1] = index + 1
                marker_text[number].append(chars[index])
        require(all("".join(value) == "".join(self.markers[number]["marker_text"].split())
                    for number, value in marker_text.items()), "Visible source marker text changed")

    def quote_audit(self, quote):
        require(isinstance(quote, str) and quote.strip(), "Nonblank source quote required")
        target = "".join(quote.split())
        spans = []
        for match in re.finditer("(?=" + re.escape(target) + ")", self.compact):
            begin, end = match.start(), match.start() + len(target)
            ids = sorted({n for n in self.marker_ids[begin:end] if n is not None})
            if not ids or any(not (begin <= self.marker_bounds[n][0] and self.marker_bounds[n][1] <= end) for n in ids):
                continue
            positions = [p for p in self.positions[begin:end] if p is not None]
            if not positions:
                continue
            start, stop = positions[0], positions[-1] + 1
            projected = "".join(c for c, p in zip(self.compact[begin:end], self.positions[begin:end], strict=True)
                                if p is not None)
            require("".join(self.body[start:stop].split()) == projected,
                    "Source reference projection does not reconstruct its corpus span")
            spans.append({"start": start, "end": stop,
                          "source_span_sha256": hashlib.sha256(self.body[start:stop].encode()).hexdigest(),
                          "omitted_reference_markup": [{"marker_id": n, **self.markers[n]} for n in ids]})
        return {"status": "located" if spans else "not_located",
                "mode": "verified_source_reference_markup" if spans else None,
                "spans": spans, "ambiguous_location": len(spans) > 1,
                "source_html_sha256": self.html_sha256,
                "request_journal_sha256": self.request_journal_sha256,
                "projection_policy": POLICY}
