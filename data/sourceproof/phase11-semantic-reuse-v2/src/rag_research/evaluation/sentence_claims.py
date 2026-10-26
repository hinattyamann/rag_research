"""Verbatim sentence units: deterministic coverage, not atomic fact decomposition.

Only narrowly recognized standalone refusals and numeric citation markers are
excluded. Ambiguous prose is retained. No question, source or gold is consulted.
"""

import re

VERSION = "verbatim-sentence-units-v1"
JAPANESE_VERSION = "verbatim-sentence-units-ja-v1"
CLAIM_UNIT_LANGUAGES = {"verbatim-sentences-v1": "en", "verbatim-sentences-ja-v1": "ja"}
CITATION = re.compile(r"\[(?:p\d+|\d+(?:_\d+-\d+)?)\]", re.IGNORECASE)
REFUSAL = re.compile(
    r"(?:the )?(?:(?:retrieved|provided|supplied|given) )?"
    r"(?:passages|documents|context|information) "
    r"(?:do not|does not|don't|doesn't) (?:provide|contain|include) "
    r"(?:enough|sufficient|the necessary) information (?:to answer|for) "
    r"(?:this|the|your) question[.!]?", re.IGNORECASE)
ABBREVIATIONS = {"mr.", "mrs.", "ms.", "dr.", "prof.", "st.", "jr.", "sr.",
                 "a.m.", "p.m.", "u.s.", "u.k.", "e.g.", "i.e.", "vs."}


def claim_unit_language(mode):
    """An absent mode preserves legacy model extraction; unknown modes fail closed."""
    if mode is None:
        return None
    if not isinstance(mode, str) or mode not in CLAIM_UNIT_LANGUAGES:
        raise ValueError("Unknown claim units mode")
    return CLAIM_UNIT_LANGUAGES[mode]


def extract_sentence_units(answer, *, language="en"):
    if not isinstance(answer, str):
        raise ValueError("Answer must be text")
    if language == "ja":
        return _extract_japanese_units(answer)
    if language != "en":
        raise ValueError("Unknown sentence units language")
    # Whitespace is normalized; every other retained character is covered once.
    prose = " ".join(CITATION.sub(" ", answer).split())
    if not prose:
        return {"claims": [], "unit_version": VERSION, "normalized_prose": prose,
                "exclusion": "empty_or_citations", "spans": []}
    if REFUSAL.fullmatch(prose):
        return {"claims": [], "unit_version": VERSION, "normalized_prose": prose,
                "exclusion": "standalone_refusal", "spans": []}
    boundaries = [0]
    for match in re.finditer(r"[.!?][\"']?\s+(?=[\"']?[A-Z0-9])", prose):
        end = match.start() + 1
        word = prose[:end].rsplit(" ", 1)[-1].lower()
        if word in ABBREVIATIONS or re.fullmatch(r"(?:[a-z]\.)+", word):
            continue
        boundaries.append(match.end())
    boundaries.append(len(prose))
    spans, claims = [], []
    for start, end in zip(boundaries, boundaries[1:]):
        text = prose[start:end].strip()
        if text:
            claims.append({"claim_id": f"c{len(claims) + 1}", "text": text})
            spans.append({"start": start, "end": end})
    assert " ".join(c["text"] for c in claims) == prose
    return {"claims": claims, "unit_version": VERSION, "normalized_prose": prose,
            "exclusion": None, "spans": spans}


# Quoted/bracketed compound assertions remain one unit rather than lose context.
# Unclosed delimiters conservatively keep the remaining prose together.
JAPANESE_PAIRS = {"「": "」", "『": "』", "（": "）", "(": ")", "[": "]",
                  "【": "】", "［": "］", "〈": "〉", "《": "》", "“": "”", "‘": "’",
                  "{": "}"}
JAPANESE_PUNCTUATION = "。！？!?"
URL = re.compile(r'https?://[^\s。！？「」『』（）"<>【】]+', re.IGNORECASE)
JAPANESE_REFUSAL = "提示された根拠には、この質問に答えるための十分な情報がありません"


def _japanese_boundaries(prose):
    url_ends = {match.start(): match.end() for match in URL.finditer(prose)}
    period_ends = set()
    for match in re.finditer(r"\.\s+(?=\S)", prose):
        token = re.search(r"[A-Za-z.]+$", prose[:match.start() + 1])
        word = token.group().lower() if token else ""
        if word not in ABBREVIATIONS and not re.fullmatch(r"(?:[a-z]\.)+", word):
            period_ends.add(match.start())
    boundaries, closers, index = [0], [], 0
    while index < len(prose):
        if index in url_ends:
            index = url_ends[index]
            continue
        char = prose[index]
        if char == '"':
            # Count escapes so an escaped quote does not change nesting.
            escapes, previous = 0, index - 1
            while previous >= 0 and prose[previous] == "\\":
                escapes += 1
                previous -= 1
            if escapes % 2 == 0:
                if closers and closers[-1] == char:
                    closers.pop()
                else:
                    closers.append(char)
        elif closers and char == closers[-1]:
            closers.pop()
        elif char in JAPANESE_PAIRS:
            closers.append(JAPANESE_PAIRS[char])
        if not closers and (char in JAPANESE_PUNCTUATION or index in period_ends):
            index += 1
            while index < len(prose) and prose[index] in JAPANESE_PUNCTUATION:
                index += 1
            while index < len(prose) and prose[index].isspace():
                index += 1
            boundaries.append(index)
        else:
            index += 1
    if boundaries[-1] != len(prose):
        boundaries.append(len(prose))
    return boundaries, closers


def _extract_japanese_units(answer):
    prose = " ".join(CITATION.sub(" ", answer).split())
    result = {"claims": [], "unit_version": JAPANESE_VERSION, "normalized_prose": prose,
              "exclusion": None, "spans": [], "unclosed_delimiters": []}
    if not prose:
        result["exclusion"] = "empty_or_citations"
        return result
    if prose in {JAPANESE_REFUSAL, JAPANESE_REFUSAL + "。"} or REFUSAL.fullmatch(prose):
        result["exclusion"] = "standalone_refusal"
        return result
    boundaries, result["unclosed_delimiters"] = _japanese_boundaries(prose)
    for start, end in zip(boundaries, boundaries[1:]):
        text = prose[start:end].strip()
        if text:
            result["claims"].append({"claim_id": f"c{len(result['claims']) + 1}", "text": text})
            result["spans"].append({"start": start, "end": end})
    assert "".join(prose[s["start"]:s["end"]] for s in result["spans"]) == prose
    return result
