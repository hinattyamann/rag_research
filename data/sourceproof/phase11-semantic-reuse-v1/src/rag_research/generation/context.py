"""Fixed rank-order context packing measured with the generator's actual tokenizer."""

import hashlib
import json
from dataclasses import asdict, dataclass

from rag_research.retrieval.common import RetrievalHit, validate_query
from rag_research.retrieval.hybrid import HybridHit


@dataclass(frozen=True)
class PromptSpec:
    version: str
    system: str


def literal_json(value):
    # Evidence/question text cannot insert a model chat delimiter into the template.
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def build_context(question, context, client, config, spec):
    validate_query(question, 1)
    if not isinstance(context, list) or any(
        type(hit) not in (RetrievalHit, HybridHit) for hit in context
    ):
        raise ValueError("context must be RetrievalHit objects, not QA/Gold dictionaries")
    if len({hit.passage_id for hit in context}) != len(context):
        raise ValueError("Duplicate retrieved Passage IDs")
    if any(hit.rank != index + 1 for index, hit in enumerate(context)):
        raise ValueError("Context must be in retrieval rank order")
    budget = config.context_tokens - config.max_output_tokens

    def render(documents):
        messages = [
            {"role": "system", "content": spec.system},
            {
                "role": "user",
                "content": "Original question (JSON string):\n"
                + literal_json(question)
                + "\n\nRetrieved passages (JSON array):\n"
                + literal_json(documents),
            },
        ]
        prompt = client.render(messages)
        return messages, prompt, client.tokenize(prompt, special=True)

    documents = []
    audit = []
    messages, prompt, tokens = render(documents)
    if len(tokens) > budget:
        raise ValueError(
            "Question and instructions exceed the input budget; question is not truncated"
        )
    for hit in context:
        original = client.tokenize(hit.text)
        maximum = min(len(original), config.passage_tokens)

        def candidate(length):
            text = hit.text if length == len(original) else client.detokenize(original[:length])
            # A cutoff inside a UTF-8 byte sequence can produce a replacement
            # character on detokenization. Back off until the decoded prefix is
            # valid and its retokenized length also respects the passage cap.
            while length and (
                "\ufffd" in text
                and "\ufffd" not in hit.text
                or len(client.tokenize(text)) > config.passage_tokens
            ):
                length -= 1
                text = client.detokenize(original[:length])
            document = {"passage_id": hit.passage_id, "title": hit.title, "text": text}
            rendered = render(documents + [document])
            return document, rendered

        document, rendered = candidate(maximum)
        if len(rendered[2]) > budget:
            # Use a deterministic prefix. Every accepted candidate is checked against
            # the fully rendered chat template, including metadata/special tokens.
            low, high, best = 1, maximum - 1, None
            while low <= high:
                middle = (low + high) // 2
                trial = candidate(middle)
                if len(trial[1][2]) <= budget:
                    best = trial
                    low = middle + 1
                else:
                    high = middle - 1
            if best is None:
                audit.append(
                    {
                        "passage_id": hit.passage_id,
                        "original_tokens": len(original),
                        "used_tokens": 0,
                        "truncated": True,
                        "omitted": True,
                        "reason": "input_budget",
                    }
                )
                continue
            document, rendered = best
        documents.append(document)
        messages, prompt, tokens = rendered
        used_count = len(client.tokenize(document["text"]))
        audit.append(
            {
                "passage_id": hit.passage_id,
                "original_tokens": len(original),
                "used_tokens": used_count,
                "truncated": document["text"] != hit.text,
                "omitted": False,
            }
        )
    return {
        "messages": messages,
        "rendered_prompt": prompt,
        "prompt_tokens": tokens,
        "input_tokens": len(tokens),
        "used_context": documents,
        "context_audit": audit,
        "prompt_spec": asdict(spec),
        "rendered_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }
