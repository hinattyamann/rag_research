"""One answer generation per baseline question, with the complete request audit."""

import re
import time

from rag_research.generation.context import build_context
from rag_research.generation.local import GenerationError


class LocalGenerator:
    def __init__(self, client, config, prompt):
        self.client = client
        self.config = config
        self.prompt = prompt

    def generate_record(self, question: str, context: list):
        started = time.perf_counter()
        packed = build_context(question, context, self.client, self.config, self.prompt)
        prepared = time.perf_counter()
        try:
            response = self.client.complete(packed["prompt_tokens"], self.config)
        except GenerationError as error:
            return {
                **packed,
                "status": "error",
                "answer": None,
                "error": str(error),
                "answer_generation_calls": 1,
                "context_seconds": prepared - started,
                "generation_seconds": time.perf_counter() - prepared,
            }
        answer = response.get("content")
        error = None
        if not isinstance(answer, str) or not answer.strip():
            error = "Empty or invalid answer from runtime"
        if response.get("truncated"):
            error = "Runtime unexpectedly truncated the context"
        finish = response.get("stop_type")
        if finish == "limit":
            error = "Output token limit reached; answer may be incomplete"
        elif finish not in {"eos", "word"}:
            error = f"Unexpected finish reason: {finish}"
        used_ids = {document["passage_id"] for document in packed["used_context"]}
        brackets = (
            set(re.findall(r"\[([^\[\]\n]+)\]", answer)) if isinstance(answer, str) else set()
        )
        citations = sorted(used_ids & brackets)
        return {
            **packed,
            "status": "error" if error else "ok",
            "answer": answer,
            "error": error,
            "answer_generation_calls": 1,
            "finish_reason": finish,
            "output_tokens": len(response.get("tokens", [])),
            "cited_passage_ids": citations,
            "unrecognized_citations": sorted(brackets - used_ids),
            "context_seconds": prepared - started,
            "generation_seconds": time.perf_counter() - prepared,
            "runtime_response": response,
        }

    def generate(self, question: str, context: list) -> str:
        result = self.generate_record(question, context)
        if result["status"] != "ok":
            raise GenerationError(result["error"])
        return result["answer"]
