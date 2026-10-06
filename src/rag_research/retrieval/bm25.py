"""BM25S Lucene BM25 over Corpus text, independent of QA labels."""

from pathlib import Path

import bm25s

from rag_research.retrieval.common import (
    CorpusStore,
    IndexValidationError,
    ResourceMonitor,
    finalize_index,
    package_versions,
    ranked_rows,
    validate_query,
    verify_index,
    write_json,
)

TOKEN_PATTERN = r"(?u)\b\w+\b"


def tokenize(texts, *, return_ids=True):
    return bm25s.tokenize(
        texts,
        lower=True,
        token_pattern=TOKEN_PATTERN,
        stopwords=[],
        stemmer=None,
        return_ids=return_ids,
        show_progress=False,
    )


def bm25_config() -> dict:
    return {
        "kind": "bm25",
        "algorithm": "bm25s-lucene-v1",
        "k1": 1.2,
        "b": 0.75,
        "method": "lucene",
        "idf_method": "lucene",
        "dtype": "float32",
        "input": "text",
        "token_pattern": TOKEN_PATTERN,
        "lower": True,
        "stopwords": [],
        "stemmer": None,
        "tie_break": "corpus_row_ascending",
        "packages": package_versions(["bm25s", "numpy"]),
    }


def build_bm25(corpus_path: Path, output_dir: Path) -> dict:
    config = bm25_config()
    if output_dir.exists():
        return verify_index(output_dir, corpus_path, config)
    stage = output_dir.with_name(output_dir.name + ".building")
    if stage.exists():
        if (stage / "manifest.json").exists():
            manifest = verify_index(stage, corpus_path, config)
            stage.rename(output_dir)
            return manifest
        raise IndexValidationError(f"Incomplete BM25 build at {stage}; use another output path")
    stage.mkdir(parents=True)
    with ResourceMonitor() as monitor:
        metadata = CorpusStore.prepare(corpus_path, stage)
        corpus = CorpusStore(corpus_path, stage, metadata)
        print(f"BM25: tokenizing {metadata['record_count']} passages", flush=True)
        tokens = tokenize(list(corpus.iter_texts()))
        retriever = bm25s.BM25(k1=1.2, b=0.75, method="lucene", idf_method="lucene")
        retriever.index(tokens, show_progress=False)
        retriever.save(str(stage / "bm25"), show_progress=False)
        del corpus  # Close offsets mmap before Windows directory rename.
    write_json(stage / "build_measurements.json", monitor.report())
    return finalize_index(stage, output_dir, config, metadata)


class BM25Retriever:
    def __init__(self, corpus_path: Path, index_dir: Path):
        self.manifest = verify_index(index_dir, corpus_path, bm25_config())
        self.store = CorpusStore(corpus_path, index_dir, self.manifest["corpus"])
        self.index = bm25s.BM25.load(str(index_dir / "bm25"), mmap=True, show_progress=False)

    def search(self, question: str, *, top_k: int = 5):
        validate_query(question, top_k)
        terms = tokenize([question], return_ids=False)[0]
        # No lexical evidence: don't return arbitrary zero-score passages.
        if not terms or not any(term in self.index.vocab_dict for term in terms):
            return []
        scores = self.index.get_scores(terms)
        rows = ranked_rows(scores, top_k)
        rows = rows[scores[rows] > 0]
        return self.store.hits(rows, scores)
