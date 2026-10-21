"""Audit the actual E5 encoder on synthetic inputs before any QA inference."""

import argparse
import gc
import importlib.metadata
import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.retrieval.common import ResourceMonitor, file_hash, write_json  # noqa: E402
from rag_research.retrieval.multilingual import (  # noqa: E402
    MODEL_ROOT,
    E5Tokenizer,
    MultilingualE5Encoder,
)


def main():
    parser = argparse.ArgumentParser(description="合成文で正式E5 EncoderのCUDA/CPU数値と実演算を監査")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, default=MODEL_ROOT)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--threads", type=int, default=6)
    args = parser.parse_args()
    if args.batch_size < 1 or args.threads < 1:
        parser.error("Positive batch size and thread count required")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    criteria = {"minimum_cpu_cuda_cosine": 0.99999,
                "maximum_absolute_vector_difference": 0.0001,
                "cuda_compute_nodes_required": True, "tf32": False,
                "finite_l2_atol": 1e-5, "maximum_input_tokens": 512,
                "batch_size": args.batch_size, "benchmark_batches": 2}
    write_json(args.output_dir / "criteria.json", criteria)
    report = {"purpose": "actual-e5-encoder-synthetic-cuda-audit-not-qa-quality",
              "recorded_at_utc": datetime.now(UTC).isoformat(), "criteria": criteria,
              "qa_inputs_used": 0, "generative_model_calls": 0, "passed": False,
              "gate11_passed": False, "phase12_allowed": False}
    try:
        with ResourceMonitor() as monitor:
            tokenizer = E5Tokenizer(args.model_root)
            texts = ["The museum opens at eight.", "博物館は8時に開館します。"]
            for sentence in ("The museum has two floors. ", "博物館には二つの階があります。"):
                text = sentence
                while tokenizer.count(text + sentence) <= 512:
                    text += sentence
                texts.append(text)
            report["synthetic_input_tokens"] = [tokenizer.count(t) for t in texts]
            started = time.perf_counter()
            cuda = MultilingualE5Encoder(args.model_root, threads=args.threads, provider="cuda",
                                         profile_prefix=args.output_dir / "cuda_profile")
            cuda_passages = cuda.encode_passages(texts)
            cuda_queries = cuda.encode_queries(texts[:2])
            report["cuda_init_and_initial_two_batches_seconds"] = time.perf_counter() - started
            report["cuda_config"] = cuda.retrieval_config(args.batch_size)
            batch = [texts[2 + i % 2] for i in range(args.batch_size)]
            started = time.perf_counter()
            for _ in range(criteria["benchmark_batches"]):
                vectors = cuda.encode_passages(batch)
                assert np.isfinite(vectors).all()
                assert np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=criteria["finite_l2_atol"])
            seconds = time.perf_counter() - started
            report["synthetic_long_batch_benchmark"] = {
                "batch_size": args.batch_size, "batches": criteria["benchmark_batches"],
                "seconds": seconds,
                "passages_per_second": args.batch_size * criteria["benchmark_batches"] / seconds,
                "full_corpus_performance_established": False}
            profile = Path(cuda.session.end_profiling())
            events = json.loads(profile.read_text())
            counts = Counter(e.get("args", {}).get("provider", "unknown")
                             for e in events if e.get("cat") == "Node")
            report.update(profile=str(profile), node_provider_counts=dict(counts),
                          cuda_encoded_batches=cuda.encoded_batches)
            assert counts["CUDAExecutionProvider"] > 0, "Profile contains no CUDA computation"
            del cuda
            gc.collect()
            cpu = MultilingualE5Encoder(args.model_root, threads=args.threads, provider="cpu")
            cpu_passages, cpu_queries = cpu.encode_passages(texts), cpu.encode_queries(texts[:2])
            comparisons = []
            for kind, actual, expected in (("passage", cuda_passages, cpu_passages),
                                            ("query", cuda_queries, cpu_queries)):
                assert actual.dtype == expected.dtype == np.float32
                assert np.isfinite(actual).all() and np.isfinite(expected).all()
                for values in (actual, expected):
                    assert np.allclose(np.linalg.norm(values, axis=1), 1,
                                       atol=criteria["finite_l2_atol"])
                # Double precision for the comparison statistic, after actual float32 pooling.
                a, b = actual.astype(np.float64), expected.astype(np.float64)
                cosine = np.sum(a * b, axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))
                maximum = float(np.max(np.abs(a - b)))
                comparisons.append({"kind": kind, "cosines": cosine.tolist(), "maximum_abs": maximum})
                assert cosine.min() >= criteria["minimum_cpu_cuda_cosine"]
                assert maximum <= criteria["maximum_absolute_vector_difference"]
            report["comparisons"] = comparisons
            report["installed_runtime_packages"] = {
                p.metadata["Name"]: p.version for p in importlib.metadata.distributions()
                if p.metadata["Name"].lower().startswith(("onnxruntime", "nvidia-"))}
            report["passed"] = True
        report["resources"] = monitor.report()
    except Exception as error:
        report.update(error_type=type(error).__name__, error=str(error))
    finally:
        root = Path(__file__).resolve().parents[1]
        report["source_sha256"] = {str(p.relative_to(root)): file_hash(p) for p in (
            Path(__file__).resolve(), root / "src/rag_research/retrieval/multilingual.py",
            root / "configs/phase11_multilingual_embedding_v1.json",
            root / "environments/embedding_gpu/pyproject.toml", root / "environments/embedding_gpu/uv.lock")}
        write_json(args.output_dir / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
