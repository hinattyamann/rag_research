"""Resolve formatting-only quote differences to a unique literal source span.

No paraphrase, fuzzy similarity, word insertion, removal or reordering is allowed.
Both raw quotation and projected source span remain in the audit.
"""

import json
import re
from copy import deepcopy

from rag_research.evaluation.claims import parse_json
from rag_research.experiments.frozen_trace import require


def align_quotes(text, documents):
    value = deepcopy(parse_json(text))
    require(isinstance(value.get("verdicts"), list), "Missing verdict list")
    sources = {d["passage_id"]: d["text"] for d in documents}
    audit = []
    for verdict in value["verdicts"]:
        require(isinstance(verdict, dict) and isinstance(verdict.get("evidence"), list),
                "Invalid evidence container")
        for evidence in verdict["evidence"]:
            require(isinstance(evidence, dict) and set(evidence) == {"passage_id", "quote"},
                    "Invalid alignment evidence")
            identifier, raw = evidence["passage_id"], evidence["quote"]
            require(isinstance(identifier, str) and identifier in sources, "Unknown source ID")
            require(isinstance(raw, str) and bool(raw.strip()), "Empty quotation")
            source = sources[identifier]
            if raw in source:
                start = source.index(raw)
                end, kind = start + len(raw), "verbatim"
            else:
                # Case-sensitive word/number tokens. 'not', dates and quantities
                # must still be present in their original order without gaps.
                wanted = re.findall(r"\w+", raw)
                words = list(re.finditer(r"\w+", source))
                require(len(wanted) >= 3, "Too short for nonliteral quote alignment")
                tokens = [m.group() for m in words]
                candidates = [i for i in range(len(tokens) - len(wanted) + 1)
                              if tokens[i:i + len(wanted)] == wanted]
                require(len(candidates) == 1, "Quote does not match a unique source token span")
                index = candidates[0]
                start, end = words[index].start(), words[index + len(wanted) - 1].end()
                kind = "unique_contiguous_word_tokens"
                evidence["quote"] = source[start:end]
            audit.append({"claim_id": verdict.get("claim_id"), "passage_id": identifier,
                          "raw_quote": raw, "source_quote": evidence["quote"],
                          "alignment": kind, "start": start, "end": end})
    return json.dumps(value, ensure_ascii=False), audit
