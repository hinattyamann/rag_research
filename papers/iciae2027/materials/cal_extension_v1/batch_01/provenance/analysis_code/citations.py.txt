"""Anonymous evidence selections resolve to exact, unchanged source substrings."""

from copy import deepcopy

from common import require


class AnnotationFormatError(ValueError):
    """A completed annotation response needs the bounded format repair."""


def prepare(payload, kind):
    catalog, slots, properties = {}, {}, {}
    for case in payload["cases"]:
        documents = [(d, "actual") for d in case["documents"]]
        if kind == "quality":
            documents += [(d, "reference") for d in case["gold_documents"]]
        for document, source in documents:
            text = document["text"]
            for start, end in [(0, len(text))]:
                quote = text[start:end]
                if quote.strip():
                    catalog[f"e{len(catalog):04d}"] = {"annotation_id": case["annotation_id"],
                        "passage_id": document["passage_id"], "quote": quote,
                        "source": source, "start": start, "end": end}
    for index, template in enumerate(payload["annotations"]):
        slot = f"a{index:03d}"
        slots[slot] = deepcopy(template)
        actual = [k for k, v in catalog.items() if v["annotation_id"] == template["annotation_id"] and v["source"] == "actual"]
        allowed = [k for k, v in catalog.items() if v["annotation_id"] == template["annotation_id"]]
        def branch(labels, codes, minimum):
            props = {"label": {"type": "string", "enum": labels}, "reason": {"type": "string", "minLength": 1},
                "evidence": {"type": "array", "items": {"type": "string", **({"enum": codes} if codes else {})},
                    "minItems": minimum, **({"maxItems": 0} if not codes else {})}}
            if kind == "quality":
                props["essential_points"] = {"type": "string", "minLength": 1}
                criteria = {k: {"type": "string", "enum": ["pass", "fail", "uncertain"]} for k in template["criteria"]}
                props["criteria"] = {"type": "object", "properties": criteria, "required": list(criteria), "additionalProperties": False}
                if labels == ["reliable"]:
                    for value in criteria.values():
                        value["enum"] = ["pass"]
                else:
                    needed = "fail" if labels == ["unreliable"] else "uncertain"
                    if needed == "uncertain":
                        for value in criteria.values():
                            value["enum"] = ["pass", "uncertain"]
                    choices = []
                    for key in criteria:
                        selected = deepcopy(criteria)
                        selected[key]["enum"] = [needed]
                        choices.append({"type": "object", "properties": selected,
                            "required": list(selected), "additionalProperties": False})
                    props["criteria"] = {"anyOf": choices}
            return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
        branches = ([branch(["supported", "contradicted"], actual, 1)] if actual else []) if kind == "units" else (
            [branch(["reliable"], actual, 1)] if actual else [])
        branches += ([branch(["not_supported", "ambiguous"], actual, 0)] if kind == "units" else
            [branch(["unreliable"], allowed, 0), branch(["indeterminate"], allowed, 0)])
        properties[slot] = {"anyOf": branches}
    schema = {"type": "object", "properties": {"annotations": {"type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False}}, "required": ["annotations"], "additionalProperties": False}
    return {"catalog": catalog, "slots": slots}, schema


def decode(result, binding, kind):
    try:
        require(set(result) == {"annotations"} and isinstance(result["annotations"], dict)
                and set(result["annotations"]) == set(binding["slots"]), "Missing/extra annotation slots")
        rows = []
        for slot, template in binding["slots"].items():
            decision = result["annotations"][slot]
            fields = {"label", "reason", "evidence"} | ({"criteria", "essential_points"} if kind == "quality" else set())
            require(set(decision) == fields and isinstance(decision["reason"], str) and decision["reason"].strip(),
                    "Invalid annotation decision fields/reason")
            require(isinstance(decision["evidence"], list), "Evidence selection must be a list")
            evidence, sources = [], []
            for code in decision["evidence"]:
                citation = binding["catalog"][code]
                require(citation["annotation_id"] == template["annotation_id"] and
                        (kind == "quality" or citation["source"] == "actual"), "Evidence belongs to another candidate/source")
                evidence.append({"passage_id": citation["passage_id"], "quote": citation["quote"]})
                sources.append(citation["source"])
            if kind == "units":
                require(decision["label"] in {"supported", "contradicted", "not_supported", "ambiguous"}, "Invalid unit label")
                require(decision["label"] not in {"supported", "contradicted"} or bool(evidence), "Support/conflict requires evidence selection")
            else:
                require(decision["label"] != "reliable" or "actual" in sources, "Reliable requires actual context evidence")
            rows.append({**template, **decision, "evidence": evidence})
        return {"annotations": rows}
    except (ValueError, KeyError, TypeError) as failure:
        raise AnnotationFormatError(str(failure)) from failure
