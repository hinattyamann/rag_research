"""Load fixed indexes and enforce the selected Hybrid conditions at inference."""

from pathlib import Path

from rag_research.retrieval.bm25 import BM25Retriever
from rag_research.retrieval.common import (
    CORPUS_PATH,
    INDEX_ROOT,
    MODEL_ROOT,
    IndexValidationError,
    file_hash,
    read_json,
)
from rag_research.retrieval.dense import DenseRetriever, OnnxEncoder
from rag_research.retrieval.hybrid import HybridRetriever

COMMON_MANIFEST = Path("data/manifests/clapnq_retrieval_manifest.json")
HYBRID_MANIFEST = Path("data/manifests/phase6_hybrid_manifest.json")
CALIBRATION_REPORT = Path("data/manifests/phase6_calibration_report.json")
CALIBRATION_PROTOCOL = Path("configs/phase6_calibration.yaml")


def load_indexes(*, corpus=CORPUS_PATH, index_root=INDEX_ROOT, model_root=MODEL_ROOT):
    bm25 = BM25Retriever(corpus, index_root / "bm25")
    embedding = DenseRetriever(corpus, index_root / "embedding", OnnxEncoder(model_root))
    verify_common(bm25, "bm25", index_root)
    verify_common(embedding, "embedding", index_root)
    return bm25, embedding


def verify_common(retriever, kind, index_root):
    common = read_json(COMMON_MANIFEST)
    if (
        file_hash(index_root / kind / "manifest.json") != common["indexes"][kind]["manifest_sha256"]
        or retriever.manifest["corpus"] != common["corpus"]
    ):
        raise IndexValidationError("Retriever differs from the fixed common Manifest")


def verify_hybrid(retriever, selection, manifest_path=HYBRID_MANIFEST):
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema_version") != 1
        or manifest.get("purpose") != "phase6-fixed-hybrid-retriever"
        or manifest["selection"] != selection
        or manifest["retriever"] != retriever.manifest
        or manifest["common_manifest_sha256"] != file_hash(COMMON_MANIFEST)
        or manifest["protocol_sha256"] != file_hash(CALIBRATION_PROTOCOL)
        or manifest["calibration_report_sha256"] != file_hash(CALIBRATION_REPORT)
        or manifest["hybrid_implementation_sha256"]
        != file_hash(Path(__file__).with_name("hybrid.py"))
    ):
        raise IndexValidationError("Hybrid conditions differ from the frozen Manifest")
    report = read_json(CALIBRATION_REPORT)
    if report["selection"] != selection or report["retriever"] != retriever.manifest:
        raise IndexValidationError("Calibration selection disagrees with Hybrid Manifest")
    return manifest


def load_retriever(selection, *, corpus=CORPUS_PATH, index_root=INDEX_ROOT, model_root=MODEL_ROOT):
    if selection["kind"] == "embedding":
        retriever = DenseRetriever(corpus, index_root / "embedding", OnnxEncoder(model_root))
        verify_common(retriever, "embedding", index_root)
        return retriever
    if selection["kind"] != "hybrid":
        raise ValueError("Unsupported Baseline retriever")
    bm25, embedding = load_indexes(corpus=corpus, index_root=index_root, model_root=model_root)
    retriever = HybridRetriever(
        bm25,
        embedding,
        candidate_count=selection["candidate_count"],
        rrf_constant=selection["rrf_constant"],
    )
    verify_hybrid(retriever, selection)
    return retriever
