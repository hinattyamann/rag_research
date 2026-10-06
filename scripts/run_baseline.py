"""Run local Embedding -> LLM baseline, saving exact inputs and execution conditions."""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.baseline import BaselinePipeline  # noqa: E402
from rag_research.generation.artifacts import (  # noqa: E402
    MANIFEST_PATH,
    model_identity,
)
from rag_research.generation.config import load_config  # noqa: E402
from rag_research.generation.context import PromptSpec  # noqa: E402
from rag_research.generation.generator import LocalGenerator  # noqa: E402
from rag_research.generation.local import LocalServer  # noqa: E402
from rag_research.generation.smoke import (  # noqa: E402
    inference_input,
    offline_check,
    select_development,
)
from rag_research.retrieval.common import (  # noqa: E402
    CORPUS_PATH,
    DEVELOPMENT_PATH,
    INDEX_ROOT,
    MODEL_ROOT,
    file_hash,
    json_bytes,
    package_versions,
    read_json,
    write_json,
)
from rag_research.retrieval.dense import DenseRetriever, OnnxEncoder  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    # The baseline is local even if tracing was enabled in the caller's shell.
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    parser = argparse.ArgumentParser(description="Phase 5: ノートPC上の開発用Baseline RAG")
    parser.add_argument("question", nargs="?")
    parser.add_argument("--smoke", action="store_true", help="固定Development少数問を実行")
    parser.add_argument("--limit", type=int, default=5, help="Smoke件数（1〜10、既定5）")
    parser.add_argument("--config", type=Path, default=Path("configs/phase5.yaml"))
    parser.add_argument("--prompts", type=Path, default=Path("configs/prompts.yaml"))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if bool(args.question) == args.smoke:
        parser.error("質問または--smokeのいずれか一方を指定してください")
    config, generation_config = load_config(args.config)
    prompt = PromptSpec(**yaml.safe_load(args.prompts.read_text(encoding="utf-8")))
    rows = select_development(DEVELOPMENT_PATH, limit=args.limit) if args.smoke else []
    questions = [inference_input(row) for row in rows] if args.smoke else [args.question]
    output = args.output_dir or Path("data/runs/phase5") / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    )
    output.mkdir(parents=True, exist_ok=False)
    print(f"Run directory: {output}", flush=True)
    started = time.perf_counter()
    report = {
        "schema_version": 1,
        "purpose": "phase5-development-only",
        "status": "running",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "config": config,
        "config_sha256": file_hash(args.config),
        "prompt_spec": prompt.__dict__,
        "prompts_sha256": file_hash(args.prompts),
        "generator": model_identity(),
        "generation_manifest_sha256": file_hash(MANIFEST_PATH),
        "retrieval_manifest_sha256": file_hash(
            Path("data/manifests/clapnq_retrieval_manifest.json")
        ),
        "questions": [
            {"question": question, "record_id": rows[i]["record_id"] if rows else None}
            for i, question in enumerate(questions)
        ],
        "development_sha256": file_hash(DEVELOPMENT_PATH) if rows else None,
        "split": "development" if rows else "user_question",
        "packages": package_versions(["langgraph", "PyYAML", "psutil"]),
        "implementation_sha256": {
            str(path): file_hash(path)
            for path in [
                Path(__file__),
                Path("src/rag_research/baseline.py"),
                *sorted(Path("src/rag_research/generation").glob("*.py")),
            ]
        },
    }
    write_json(output / "run_manifest.json", report)
    results = []
    try:
        # DenseRetriever verifies the frozen Corpus, vectors and encoder conditions.
        retriever = DenseRetriever(CORPUS_PATH, INDEX_ROOT / "embedding", OnnxEncoder(MODEL_ROOT))
        common = read_json(Path("data/manifests/clapnq_retrieval_manifest.json"))
        if (
            file_hash(INDEX_ROOT / "embedding" / "manifest.json")
            != (common["indexes"]["embedding"]["manifest_sha256"])
        ):
            raise ValueError("Retriever differs from the frozen common manifest")
        report["retriever_config"] = retriever.manifest["config"]
        report["corpus"] = retriever.manifest["corpus"]
        with LocalServer(generation_config, output / "server.log") as server:
            report["runtime"] = server.runtime
            pipeline = BaselinePipeline(
                retriever,
                LocalGenerator(server.client, generation_config, prompt),
                top_k=config["retrieval"]["top_k"],
            )
            try:
                with (output / "answers.jsonl").open("xb") as answer_file:
                    for index, question in enumerate(questions):
                        print(f"[{index + 1}/{len(questions)}] {question}", flush=True)
                        result = pipeline.run(question)
                        result["record_id"] = rows[index]["record_id"] if rows else None
                        answer_file.write(json_bytes(result))
                        answer_file.flush()
                        results.append(result)
                        print(
                            json.dumps(
                                {
                                    "answer": result["answer"],
                                    "status": result["status"],
                                    "input_tokens": result["input_tokens"],
                                    "output_tokens": result.get("output_tokens"),
                                    "pipeline_seconds": result["pipeline_seconds"],
                                },
                                ensure_ascii=False,
                                indent=2,
                            ),
                            flush=True,
                        )
                        if result["status"] != "ok":
                            raise RuntimeError(result["error"])
            finally:
                report["resources"] = server.report()
                report["actual_completion_attempts"] = server.client.completion_attempts
        if rows:
            write_json(
                output / "offline_checks.json",
                {
                    "purpose": "offline-only-not-inference-not-quality-evaluation",
                    "records": [offline_check(row, result) for row, result in zip(rows, results)],
                },
            )
        report["status"] = "completed"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        report["completed_questions"] = len(results)
        report["wall_seconds_including_load"] = time.perf_counter() - started
        report["answer_generation_calls"] = sum(r["answer_generation_calls"] for r in results)
        write_json(output / "run_manifest.json", report)
    print(f"Saved answers, prompts, context and conditions: {output}")


if __name__ == "__main__":
    main()
