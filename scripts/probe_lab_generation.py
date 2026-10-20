"""Replay known Development inputs on CUDA; never uses the unused Calibration batch."""

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.storage import write_json  # noqa: E402
from rag_research.generation.config import load_config  # noqa: E402
from rag_research.generation.context import literal_json  # noqa: E402
from rag_research.generation.cuda_runtime import execution_kwargs  # noqa: E402
from rag_research.generation.local import LocalServer  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prompts", type=Path, default=ROOT / "configs/prompts.yaml")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / "data/runs/lab"):
        raise ValueError("Choose a new probe directory")
    output.mkdir(parents=True)
    config, generation = load_config(ROOT / "configs/phase11_gpu_baseline.yaml")
    examples = []
    for cohort in ("phase10-five-v2", "phase10-five-extra-v2"):
        source = ROOT / "data/runs/pilot" / cohort / "baseline/answers.jsonl"
        for row in map(json.loads, source.read_text().splitlines()):
            if any(word in row["question"] for word in ("friday", "mitochondria", "bernette", "tar heels")):
                examples.append({"question": row["question"], "documents": row["used_context"],
                                 "original_answer": row["answer"], "source_sha256": file_hash(source),
                                 "saved_messages": row["messages"], "saved_prompt_tokens": row["prompt_tokens"],
                                 "record_id": row["record_id"]})
    examples.append({"question": "At what time did the museum close?",
                     "documents": [{"passage_id": "d1", "title": "Development diagnostic",
                                    "text": "The museum opened at 08:00. The ceremony began at 10:00."}],
                     "expected_behavior": "refuse_missing_closing_time", "synthetic_control": True})
    prompt = yaml.safe_load(args.prompts.read_text())
    plan = {"purpose": "known-development-refusal-diagnostics-not-calibration",
            "prompt_sha256": file_hash(args.prompts), "config": config, "examples": examples,
            "automatic_retries": 0, "calibration20_used": False}
    write_json(output / "plan.json", plan)
    results = []
    with LocalServer(generation, output / "server.log", **execution_kwargs(config)) as server:
        for i, example in enumerate(examples):
            messages = [{"role": "system", "content": prompt["system"]},
                        {"role": "user", "content": "Original question (JSON string):\n"
                         + literal_json(example["question"]) + "\n\nRetrieved passages (JSON array):\n"
                         + literal_json(example["documents"])}]
            if "saved_messages" in example:
                messages = [{**m} for m in example["saved_messages"]]
                messages[0]["content"] = prompt["system"]
            rendered = server.client.render(messages)
            tokens = server.client.tokenize(rendered, special=True)
            if "saved_messages" in example and args.prompts.resolve() == ROOT / "configs/prompts.yaml":
                if tokens != example["saved_prompt_tokens"]:
                    raise ValueError("CPU/GPU probe prompt tokens differ; preserve and investigate")
            if len(tokens) + generation.max_output_tokens > generation.context_tokens:
                raise ValueError("Development probe input overflow; preserve this attempt")
            started = time.perf_counter()
            response = server.client.complete(tokens, generation)
            row = {"example": example, "messages": messages, "prompt_tokens": tokens,
                   "response": response, "input_tokens": len(tokens),
                   "output_tokens": len(response["tokens"]), "elapsed_seconds": time.perf_counter() - started}
            write_json(output / f"probe-{i + 1:02d}.json", row)
            results.append(row)
            print(json.dumps({"question": example["question"], "answer": response["content"],
                              "stop_type": response["stop_type"], "seconds": row["elapsed_seconds"]}), flush=True)
        write_json(output / "summary.json", {"results": results, "server": server.report(),
                                             "completion_attempts": server.client.completion_attempts})


if __name__ == "__main__":
    main()
