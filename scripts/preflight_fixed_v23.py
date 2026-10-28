"""Reproduce fixed assets, actual CUDA/tokenizer and known inputs with zero completions."""

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.evaluation.claimwise import payloads  # noqa: E402
from rag_research.experiments.bilingual_runner import load_config  # noqa: E402
from rag_research.experiments.fixed_v23 import bound, load_study, verify_release  # noqa: E402
from rag_research.experiments.frozen_trace import digest, require  # noqa: E402
from rag_research.experiments.protocol import build_messages, task_config  # noqa: E402
from rag_research.experiments.storage import read_json, write_json  # noqa: E402
from rag_research.generation.auxiliary import auxiliary_server_kwargs  # noqa: E402
from rag_research.generation.auxiliary_config import (  # noqa: E402
    CHATML_THINK_SUFFIX,
    THINK_PREFILL,
)
from rag_research.generation.context import build_context  # noqa: E402
from rag_research.generation.cuda_runtime import execution_kwargs  # noqa: E402
from rag_research.generation.local import LocalServer  # noqa: E402
from rag_research.retrieval.bilingual import load_retriever  # noqa: E402
from rag_research.retrieval.common import RetrievalHit, file_hash  # noqa: E402


def preflight(output):
    output = output.resolve()
    require(Path.cwd() == ROOT and output.is_relative_to(ROOT / "data/runs/model_screening")
            and not output.exists(), "Use a new fixed-checkout preflight directory")
    release = verify_release()
    study, prior, _ = load_study(bound(ROOT, release["study"]))
    output.mkdir(parents=True)
    started = time.monotonic()
    report = {"status": "started", "completion_attempts": 0, "main_started": False,
              "actual_qa_inference_tested": False, "old_gate11_passed": False, "phase12_allowed": False,
              "release_sha256": file_hash(ROOT / "fixed-v23-release.json"), "checks": []}
    try:
        contracts = {lang: load_config(bound(ROOT, release["configs"][lang])) for lang in ("en", "ja")}
        # Search only synthetic text, never newly selected QA or Reference.
        for lang, contract in contracts.items():
            retriever = load_retriever(contract[1], lang)
            hits = retriever.search("preflight synthetic query" if lang == "en" else "事前確認用の合成検索", top_k=5)
            require(len(hits) == 5, "Synthetic hybrid retrieval failed")
            report["checks"].append({"language": lang, "synthetic_hybrid_hits": len(hits)})
            del retriever
        base_generation = contracts["en"][5]
        with LocalServer(base_generation, output / "baseline-server.log",
                         **execution_kwargs(contracts["en"][4])) as server:
            for lang in ("en", "ja"):
                sources = sorted((ROOT / "data/runs/bilingual_development" /
                    ("phase11-connection-en-v2" if lang == "en" else "phase11-connection-ja-v1") /
                    "baseline").glob("*/record.json"))
                require(len(sources) == 1, "Use the one historical connection input")
                record = read_json(sources[0])
                hits = [RetrievalHit(**d, source_revision=file_hash(sources[0]), score=0., rank=i)
                        for i, d in enumerate(record["used_context"], 1)]
                packed = build_context(record["question"], hits, server.client, base_generation, contracts[lang][6])
                require(packed["used_context"] == record["used_context"], "Known baseline source was cut")
                report["checks"].append({"task": "baseline", "language": lang,
                    "input_tokens": packed["input_tokens"], "reserved_output": base_generation.max_output_tokens,
                    "source_sha256": file_hash(sources[0]), "message_sha256": digest(packed["messages"])})
            require(server.client.completion_attempts == 0, "No baseline generation allowed")
            report["baseline_server"] = server.report()
        diagnostics = read_json(ROOT / prior["diagnostics"])
        with LocalServer(task_config(prior, "verify_claims"), output / "judge-server.log",
                         **auxiliary_server_kwargs(prior)) as server:
            for lang in ("en", "ja"):
                case = next(c for c in diagnostics["cases"] if c["language"] == lang)
                prompts = yaml.safe_load((ROOT / prior["prompts"][lang]).read_text())
                full = {key: case[key] for key in ("question", "answer", "claims", "documents")}
                payload = payloads(full, "claimwise-v1")[0][1]
                for task, item in (("verify_claims", payload),
                                   ("rewrite_answer", {k: full[k] for k in ("question", "answer", "documents")})):
                    messages = build_messages(prompts, task, item)
                    rendered = server.client.render(messages)
                    tokens = server.client.tokenize(rendered, special=True)
                    suffix = server.client.tokenize(THINK_PREFILL, special=True)
                    require(rendered.endswith(CHATML_THINK_SUFFIX) and tokens[-len(suffix):] == suffix,
                            "Original v23 reasoning-prefill contract differs")
                    generation = task_config(prior, task)
                    require(len(tokens) + generation.max_output_tokens <= generation.context_tokens,
                            "Known Judge/rewrite input overflow")
                    report["checks"].append({"task": task, "language": lang,
                        "input_tokens": len(tokens), "reserved_output": generation.max_output_tokens,
                        "message_sha256": digest(messages), "tokens_sha256": digest(tokens)})
            require(server.client.completion_attempts == 0, "No Judge/rewrite generation allowed")
            report["judge_server"] = server.report()
        report["status"] = "passed"
    except BaseException as error:
        report.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        report["wall_seconds"] = time.monotonic() - started
        write_json(output / "report.json", report)
    write_json(ROOT / "fixed-v23-readiness.json", {
        "release_sha256": report["release_sha256"],
        "preflight": {"path": (output / "report.json").relative_to(ROOT).as_posix(),
                      "sha256": file_hash(output / "report.json")},
        "actual_qa_inference_tested": False, "main_started": False, "old_gate11_passed": False})
    print(json.dumps({k: report[k] for k in ("status", "completion_attempts", "wall_seconds", "main_started")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    preflight(parser.parse_args().output_dir)
