"""Two-node LangGraph baseline; inference state never receives evaluation metadata."""

import time
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from rag_research.retrieval.common import RetrievalHit, validate_query


class BaselineState(TypedDict, total=False):
    question: str
    documents: list[RetrievalHit]
    retrieval_seconds: float
    retrieval_details: dict
    generation: dict


class BaselinePipeline:
    def __init__(self, retriever, generator, *, top_k=5):
        validate_query("validate top_k", top_k)
        self.top_k = top_k
        self.retriever = retriever
        self.generator = generator
        graph = StateGraph(BaselineState)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("generate", self._generate)
        graph.add_edge(START, "retrieve")
        graph.add_edge("retrieve", "generate")
        graph.add_edge("generate", END)
        self.graph = graph.compile()

    def _retrieve(self, state):
        started = time.perf_counter()
        documents = self.retriever.search(state["question"], top_k=self.top_k)
        return {
            "documents": documents,
            "retrieval_seconds": time.perf_counter() - started,
            "retrieval_details": dict(getattr(self.retriever, "last_search_details", {})),
        }

    def _generate(self, state):
        return {"generation": self.generator.generate_record(state["question"], state["documents"])}

    def run(self, question: str):
        validate_query(question, self.top_k)
        started = time.perf_counter()
        state = self.graph.invoke({"question": question})
        return {
            "question": question,
            "retrieved_context": [hit.to_dict() for hit in state["documents"]],
            "retrieval_seconds": state["retrieval_seconds"],
            "retrieval_details": state["retrieval_details"],
            **state["generation"],
            "pipeline_seconds": time.perf_counter() - started,
        }
