"""Verbatim sentence units: deterministic coverage, not atomic fact decomposition.

Only narrowly recognized standalone refusals and numeric citation markers are
excluded. Ambiguous prose is retained. No question, source or gold is consulted.
"""

import re

VERSION = "verbatim-sentence-units-v1"
CITATION = re.compile(r"\[(?:p\d+|\d+(?:_\d+-\d+)?)\]", re.IGNORECASE)
REFUSAL = re.compile(
    r"(?:the )?(?:(?:retrieved|provided|supplied|given) )?"
    r"(?:passages|documents|context|information) "
    r"(?:do not|does not|don't|doesn't) (?:provide|contain|include) "
    r"(?:enough|sufficient|the necessary) information (?:to answer|for) "
    r"(?:this|the|your) question[.!]?", re.IGNORECASE)
ABBREVIATIONS = {"mr.", "mrs.", "ms.", "dr.", "prof.", "st.", "jr.", "sr.",
                 "a.m.", "p.m.", "u.s.", "u.k.", "e.g.", "i.e.", "vs."}


def extract_sentence_units(answer):
    if not isinstance(answer, str):
        raise ValueError("Answer must be text")
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
