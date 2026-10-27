"""v2: apply the common prefill before counting every full input, Native0."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.evaluation.claimwise import payloads  # noqa: E402
from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.protocol import build_messages, task_config  # noqa: E402
from rag_research.experiments.semantic_diagnostics import load_config, specs  # noqa: E402
from rag_research.experiments.storage import run_lock, write_json  # noqa: E402
from rag_research.generation.auxiliary import (  # noqa: E402
    auxiliary_identity,
    auxiliary_server_kwargs,
)
from rag_research.generation.auxiliary_config import tokenize_reasoning_prompt  # noqa: E402
from rag_research.generation.local import LocalServer  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def prepare_input(client, messages, settings, path):
    row = {"messages": messages, "status": "started", "raw_rendered_prompt": client.render(messages)}
    write_json(path, row)
    try:
        row.update(tokenize_reasoning_prompt(client, row["raw_rendered_prompt"],
            getattr(settings, "reasoning_prefill_mode", "none")), status="prepared")
    except Exception as error:
        row.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        write_json(path, row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    config_path, output = args.config.resolve(), args.output_dir.resolve()
    require(Path.cwd().resolve() == ROOT and output.is_relative_to(ROOT / "data/runs/model_screening"),
            "Run model preflight from repository root into model_screening")
    config, plan, prompts, plan_path = load_config(config_path)
    generation = task_config(config, "verify_claims")
    with run_lock(output):
        require({p.name for p in output.iterdir()} == {".run.lock"}, "Preserve previous model preflight")
        binding = {"purpose": "phase11-model-startup-token-prefill-preflight-v2-no-completions",
                   "config_sha256": file_hash(config_path), "plan_sha256": file_hash(plan_path),
                   "script_sha256": file_hash(Path(__file__)), "model": auxiliary_identity(config)}
        write_json(output / "plan.json", binding)
        report = {**binding, "status": "started", "completion_attempts": 0, "phase12_allowed": False}
        try:
            with LocalServer(generation, output / "server.log", **auxiliary_server_kwargs(config)) as server:
                inputs = []
                for case, order, key in specs(plan):
                    documents = case["documents"] if order == "original" else list(reversed(case["documents"]))
                    full = {
                        "question": case["question"], "answer": case["answer"],
                        "claims": case["claims"], "documents": documents}
                    mode = config.get("verification_mode", "joint")
                    if mode == "source-reading-v1":
                        reader = task_config(config, "read_sources")
                        messages = build_messages(prompts[case["language"]], "read_sources",
                                                  {k: full[k] for k in ("question", "documents")})
                        prepared = prepare_input(server.client, messages, reader,
                            output / f"input-{len(inputs):03d}.json")
                        tokens = prepared["input_tokens"]
                        inputs.append({**prepared, "messages": messages, "condition": key, "stage": "read_sources",
                            "reserved_output_tokens": reader.max_output_tokens,
                            "fits": tokens + reader.max_output_tokens <= reader.context_tokens})
                        # Conservative planning reserve. The real generated reading is token-checked again before every Judge call.
                        full["source_reading"] = {"readings": [{"passage_id": d["passage_id"], "actor": "Preflight",
                            "action": "Preflight", "quote": d["text"][:1]} for d in documents]}
                    for original_id, payload in payloads(full, "claimwise-v1" if mode == "source-reading-v1" else mode):
                        messages = build_messages(prompts[case["language"]], "verify_claims", payload)
                        prepared = prepare_input(server.client, messages, generation,
                            output / f"input-{len(inputs):03d}.json")
                        tokens = prepared["input_tokens"]
                        row = {**prepared, "messages": messages, "condition": key, "original_claim_id": original_id,
                               "reserved_output_tokens": generation.max_output_tokens,
                               "intermediate_additional_reservation": reader.max_output_tokens if mode == "source-reading-v1" else 0,
                               "actual_intermediate_must_be_checked": mode == "source-reading-v1",
                               "fits": tokens + generation.max_output_tokens + (reader.max_output_tokens if mode == "source-reading-v1" else 0)
                                       <= generation.context_tokens}
                        inputs.append(row)
                        write_json(output / "prepared-inputs.json", inputs)
                report.update(inputs=inputs, server=server.report(), completion_attempts=server.client.completion_attempts,
                    gpu_memory_single_observation=subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total",
                        "--format=csv,noheader"], check=True, capture_output=True, text=True).stdout.strip())
                require(report["completion_attempts"] == 0, "Preflight must never call completion")
                require(len([row for row in inputs if row.get("stage") != "read_sources"]) == plan["max_completion_attempts"],
                        "Preflight must include every planned full input, without omissions")
                require(all(row["fits"] for row in inputs), "Preflight input overflow; no inference allowed")
                report["status"] = "passed"
        except Exception as error:
            report.update(status="failed", error=f"{type(error).__name__}: {error}")
            write_json(output / "report.json", report)
            raise
        write_json(output / "report.json", report)
    print(json.dumps({"status": report["status"], "conditions": len(report["inputs"]), "completion_attempts": 0,
                      "max_input_tokens": max(r["input_tokens"] for r in report["inputs"]),
                      "full_gpu_offload": report["server"]["full_gpu_offload"],
                      "gpu_memory_single_observation": report["gpu_memory_single_observation"]}))


if __name__ == "__main__":
    main()
