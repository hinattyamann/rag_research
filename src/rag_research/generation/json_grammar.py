"""Closed subset of JSON Schema compiled to a grammar that consumes the thinking end tag."""

import json

from rag_research.experiments.frozen_trace import require


def literal(value):
    return json.dumps(value, ensure_ascii=False)


def closing_tag_grammar(schema, *, bounded_whitespace=False):
    """b11433 WORD replays the trigger itself; the grammar explicitly accepts it."""
    require(isinstance(schema, dict) and schema.get("type") == "object", "Final grammar requires an object root")
    rules = {"ws": r"[ \t\n\r]{0,2}" if bounded_whitespace else r"[ \t\n\r]*",
             "jchar": r'[^"\\\x00-\x1F] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F]{4})',
             "upto0": '""'}
    cache, largest = {}, 0

    def upto(count):
        nonlocal largest
        # Explicit right recursion avoids b11433's limit on a single large {m,n} expansion.
        while largest < count:
            largest += 1
            rules["upto" + str(largest)] = '"" | jchar upto' + str(largest - 1)
        return "upto" + str(count)

    def visit(node):
        require(isinstance(node, dict), "Schema node must be an object")
        key = json.dumps(node, ensure_ascii=False)
        if key in cache:
            return cache[key]
        name = "value" + str(len(cache))
        cache[key] = name
        if "const" in node or "enum" in node:
            field = "const" if "const" in node else "enum"
            require(set(node) <= {field, "type"}, "Unsupported literal schema fields")
            values = [node[field]] if field == "const" else node[field]
            require(isinstance(values, list) and values, "Empty literal alternatives")
            expression = " | ".join(literal(json.dumps(v, ensure_ascii=False, allow_nan=False, separators=(",", ":"))) for v in values)
        elif node.get("type") == "boolean":
            require(set(node) == {"type"}, "Unsupported boolean schema fields")
            expression = '"true" | "false"'
        elif node.get("type") == "string":
            require(set(node) <= {"type", "minLength", "maxLength"}, "Unsupported string schema fields")
            minimum, maximum = node.get("minLength", 0), node.get("maxLength")
            require(type(minimum) is int and 0 <= minimum <= 10000 and
                    (maximum is None or type(maximum) is int and minimum <= maximum <= 10000), "Invalid string bounds")
            content = " ".join(["jchar"] * minimum)
            tail = "jchar*" if maximum is None else upto(maximum - minimum)
            expression = " ".join([literal('"'), content, tail, literal('"')])
        elif node.get("type") == "object":
            require(set(node) == {"type", "properties", "required", "additionalProperties"} and
                    node["additionalProperties"] is False and isinstance(node["properties"], dict) and
                    set(node["required"]) == set(node["properties"]), "Only fully required closed objects are supported")
            fields = [literal(json.dumps(k, ensure_ascii=False)) + ' ws ":" ws ' + visit(v)
                      for k, v in node["properties"].items()]
            expression = '"{" ws ' + ' ws "," ws '.join(fields) + ' ws "}"'
        elif node.get("type") == "array":
            require(set(node) <= {"type", "items", "minItems", "maxItems"} and "items" in node,
                    "Unsupported array schema fields")
            minimum, maximum = node.get("minItems", 0), node.get("maxItems")
            require(type(minimum) is int and type(maximum) is int and 0 <= minimum <= maximum <= 128,
                    "Finite array bounds required")
            if isinstance(node["items"], list):
                require(minimum == maximum == len(node["items"]), "Tuple array bounds differ")
                variants = [' ws "," ws '.join(visit(v) for v in node["items"]) or '""']
            else:
                item = visit(node["items"])
                variants = [' ws "," ws '.join([item] * n) or '""' for n in range(minimum, maximum + 1)]
            expression = '"[" ws (' + " | ".join(variants) + ') ws "]"'
        else:
            raise ValueError("Unsupported schema type for closing-tag grammar")
        rules[name] = expression
        return name

    body = visit(schema)
    return 'root ::= "</think>" ws ' + body + ' ws\n' + "\n".join(k + " ::= " + v for k, v in rules.items()) + "\n"
