"""Load a candidate bilingual retriever with exact shared corpus/config/model binding."""

from rag_research.data.study_assets import ROOT, local_path, verify_file
from rag_research.experiments.frozen_trace import require
from rag_research.retrieval.bm25 import BM25Retriever
from rag_research.retrieval.dense import DenseRetriever
from rag_research.retrieval.hybrid import HybridRetriever
from rag_research.retrieval.multilingual import MultilingualE5Encoder


def load_retriever(assets, language, *, root=ROOT):
    require(language in {"en", "ja"}, "Unknown retrieval language")
    data = assets["datasets"][language]
    corpus = verify_file(data["corpus"], root)
    for binding in data["indexes"].values():
        verify_file(binding, root)
    encoder = MultilingualE5Encoder(local_path(assets["embedding"]["model_root"], root),
                                    threads=assets["embedding"]["threads"], provider="cuda", device_id=0)
    bm25 = BM25Retriever(corpus, local_path(data["indexes"]["bm25"]["path"], root).parent,
                         tokenizer=encoder.tokenizer)
    dense = DenseRetriever(corpus, local_path(data["indexes"]["embedding"]["path"], root).parent, encoder)
    require(bm25.manifest["corpus"]["source_dataset"] == data["source_dataset"], "Index dataset differs")
    selection = assets["retrieval"]
    return HybridRetriever(bm25, dense, candidate_count=selection["candidate_count"],
                           rrf_constant=selection["rrf_constant"])
