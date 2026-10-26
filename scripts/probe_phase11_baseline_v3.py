"""Probe the unchanged 3B generator on the isolated runtime with two old known inputs."""

import argparse
import json
import os
import subprocess
import sys
import time
from copy import deepcopy
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.frozen_trace import (  # noqa: E402
    digest,
    require,
    validate_documents,
)
from rag_research.experiments.storage import read_json, run_lock, write_json  # noqa: E402
from rag_research.generation.artifacts import model_identity  # noqa: E402
from rag_research.generation.config import load_config as baseline_config  # noqa: E402
from rag_research.generation.context import PromptSpec, build_context  # noqa: E402
from rag_research.generation.cuda_runtime import (  # noqa: E402
    GRAPH_OFF_SPEC,
    execution_identity,
    execution_kwargs,
)
from rag_research.generation.generator import LocalGenerator  # noqa: E402
from rag_research.generation.local import LocalServer  # noqa: E402
from rag_research.retrieval.common import RetrievalHit, file_hash  # noqa: E402

JUDGE_IDENTITY = "9aebd9f0fb221d5820b1c54a58782ac7bcb46d92ac388ee51bebb3cee932a6a6"
KNOWN_RUNS = {
    "en": "data/runs/bilingual_development/phase11-connection-en-v2",
    "ja": "data/runs/bilingual_development/phase11-connection-ja-v1",
}
TARGET_FIELDS = {"target_id", "language", "record_id", "source_manifest", "source_record",
                 "initial_prompt", "question", "documents", "input_sha256"}


def local(name):
    require(isinstance(name, str) and not Path(name).is_absolute(), "Use a relative input path")
    path = (ROOT / name).resolve()
    require(path.is_relative_to(ROOT), "Probe input escapes checkout")
    return path


def bound(binding):
    require(isinstance(binding, dict) and set(binding) == {"path", "sha256"},
            "Bind each input by exact path and SHA256")
    path = local(binding["path"])
    require(path.is_file() and file_hash(path) == binding["sha256"], "Probe input changed")
    return path


def load_contract(config_path, plan_path):
    config, generation = baseline_config(config_path)
    plan = read_json(plan_path)
    require(plan.get("schema_version") == 3 and
            plan.get("purpose") == "phase11-baseline-known-runtime-probe-v3" and
            plan.get("status") == "preregistered" and
            plan.get("source_scope") == "known_development_connection_only" and
            plan.get("maximum_calls") == 2 and plan.get("automatic_retries") == 0 and
            plan.get("phase12_allowed") is False and
            plan.get("judge_candidate_identity_sha256") == JUDGE_IDENTITY,
            "Use the registered two-known-input baseline probe, never a draft or Main/Cal")
    require(bound(plan["baseline_config"]) == config_path, "Registered baseline config differs")
    identity = read_json(bound(plan["generation_identity"]))
    require(identity.get("schema_version") == 3 and
            identity.get("purpose") == "phase11-baseline-graph-off-identity-v3" and
            identity.get("status") == "preregistered_pending_baseline_smoke" and
            identity.get("judge_candidate_identity_sha256") == JUDGE_IDENTITY and
            identity.get("phase12_allowed") is False and
            identity.get("baseline_config") == plan["baseline_config"] and
            identity.get("model") == model_identity(), "Baseline generation identity differs")
    original = yaml.safe_load(bound(identity["baseline_origin"]).read_text("utf-8"))
    expected = deepcopy(original)
    require(original["execution"]["runtime_spec"] == "configs/lab_cuda_runtime.json",
            "Preserve the historical baseline origin")
    expected["execution"]["runtime_spec"] = GRAPH_OFF_SPEC
    require(config == expected and identity.get("generation") == config["generation"] and
            identity.get("execution") == config["execution"] and
            generation.context_tokens == 4096 and generation.max_output_tokens == 512 and
            generation.timeout_seconds == 300,
            "Only the baseline runtime may change; preserve Model/Prompt/Sampler/budgets")
    runtime = execution_identity(config)
    require(identity.get("runtime") == runtime["runtime"], "Baseline runtime manifest differs")
    targets = plan.get("targets")
    require(isinstance(targets, list) and len(targets) == 2 and
            [t.get("language") for t in targets] == ["en", "ja"], "Use one EN and one JA target")
    paths = [config_path, plan_path, bound(plan["generation_identity"]),
             bound(identity["baseline_origin"]), bound(identity["prior_generation_identity"])]
    for target in targets:
        require(set(target) == TARGET_FIELDS, "Unexpected probe fields; Gold is not input")
        language = target["language"]
        run = ROOT / KNOWN_RUNS[language]
        manifest_path, record_path = bound(target["source_manifest"]), bound(target["source_record"])
        require(manifest_path == run / "manifest.json" and
                record_path.is_relative_to(run / "baseline") and record_path.name == "record.json",
                "Probe sources must be the two historical known connection baselines")
        manifest, saved = read_json(manifest_path), read_json(record_path)
        require(manifest.get("language") == language and
                manifest["config"].get("execution_scope") == "connection_smoke_only" and
                manifest["config"]["data"]["record_ids"] == [target["record_id"]] and
                target["target_id"] == f"baseline/{language}/{target['record_id']}" and
                saved.get("status") == "ok" and saved["record_id"] == target["record_id"],
                "Never substitute a Main/Cal, failed, or different known QA")
        validate_documents(target["documents"])
        inputs = {key: target[key] for key in ("question", "documents")}
        require(target["question"] == saved["question"] and
                target["documents"] == saved["used_context"] and
                digest(inputs) == target["input_sha256"], "Keep complete known question and used Source")
        prompt_path = bound(target["initial_prompt"])
        require(target["initial_prompt"] == identity["initial_prompts"][language] and
                target["initial_prompt"]["path"] == f"configs/phase11_bilingual_initial_{language}_v1.yaml" and
                saved["prompt_spec"] == asdict(PromptSpec(**yaml.safe_load(prompt_path.read_text()))),
                "Preserve the initial language prompt byte identity")
        paths.extend([manifest_path, record_path, prompt_path])
    return config, generation, plan, runtime, paths


def source_hits(target):
    """Reconstruct rank wrappers; only the three saved document fields enter the prompt."""
    return [RetrievalHit(**document, source_revision=target["source_record"]["sha256"],
                         score=0.0, rank=index)
            for index, document in enumerate(target["documents"], 1)]


def prepare_payload(client, generation, prompt, target):
    packed = build_context(target["question"], source_hits(target), client, generation, prompt)
    require(packed["used_context"] == target["documents"] and
            not any(row["truncated"] or row["omitted"] for row in packed["context_audit"]),
            "The new tokenizer must retain every saved used Source without repacking")
    require(packed["input_tokens"] + generation.max_output_tokens <= generation.context_tokens,
            "Whole baseline payload exceeds its fixed input/output reservation")
    return packed


def verify_supervisor(mode, config_path, plan_path, output, probe_plan):
    """Bind this arbitrary Python entrypoint and its custom --probe-plan to v3."""
    context = json.loads(os.environ["RAG_PHASE11_AUTONOMY_CONTEXT"])
    ledger = read_json(Path(context["ledger_dir"]) / "ledger.json")
    require(ledger.get("version") == "phase11-autonomy-v3", "Use the v3 cumulative ledger")
    rows = [row for row in ledger["runs"] if row["run_id"] == context["run_id"]]
    require(len(rows) == 1 and rows[0]["state"] == "running", "Probe needs its live registered run")
    registered = rows[0]["plan"]
    calls = 0 if mode == "preflight" else 2
    require(registered["stage"] == mode and
            registered["candidate_identity_sha256"] == JUDGE_IDENTITY and
            registered["budget"]["planned_calls"] == registered["budget"]["maximum_calls"] == calls and
            registered["automatic_retries"] == 0 and registered["phase12_allowed"] is False and
            set(registered["targets"]) == {t["target_id"] for t in probe_plan["targets"]} and
            local(registered["output_dir"]) == output,
            "Registered probe mode, targets, output, candidate or call budget differs")
    bindings = {b["path"]: b["sha256"] for b in registered["bindings"]}
    for path in (Path(__file__), config_path, plan_path, bound(probe_plan["generation_identity"])):
        require(bindings.get(str(path.relative_to(ROOT))) == file_hash(path),
                "Supervisor must bind the entrypoint, config, custom probe plan and generation identity")
    command = registered["command"]
    require(command[0] == str(Path(__file__).relative_to(ROOT)) and
            all(flag in command and command[command.index(flag) + 1] == value for flag, value in
                (("--mode", mode), ("--config", str(config_path.relative_to(ROOT))),
                 ("--probe-plan", str(plan_path.relative_to(ROOT))),
                 ("--output-dir", str(output.relative_to(ROOT))))), "Registered probe command differs")


class ProbeJournalClient:
    def __init__(self, client, journal, path, expected_tokens):
        self.client, self.journal, self.path = client, journal, path
        self.expected_tokens = expected_tokens

    def __getattr__(self, key):
        return getattr(self.client, key)

    def complete(self, tokens, config):
        require(not self.journal["completion_attempted"] and tokens == self.expected_tokens,
                "Never retry or change a prepared probe request")
        self.journal.update(completion_attempted=True, cost_incomplete=True,
                            input_tokens=len(tokens), prompt_tokens=tokens,
                            started_at_utc=datetime.now(UTC).isoformat())
        write_json(self.path, self.journal)
        started = time.perf_counter()
        try:
            response = self.client.complete(tokens, config)
        except BaseException as error:
            self.journal.update(error=f"{type(error).__name__}: {error}", cost_incomplete=True,
                                elapsed_seconds=time.perf_counter() - started)
            write_json(self.path, self.journal)
            raise
        count = len(response["tokens"]) if isinstance(response.get("tokens"), list) else None
        self.journal.update(runtime_response=response, response_received=True, output_tokens=count,
                            cost_incomplete=count is None, elapsed_seconds=time.perf_counter() - started)
        write_json(self.path, self.journal)
        return response


def run(mode, config_path, plan_path, output):
    require(mode in {"preflight", "smoke"}, "Unknown baseline probe mode")
    require(os.environ.get("RAG_PHASE11_AUTONOMY_CONTEXT"), "Run under the v3 finite supervisor")
    config_path, plan_path, output = (Path(p).resolve() for p in (config_path, plan_path, output))
    parent = ROOT / "data/runs/runtime_screening"
    require(Path.cwd().resolve() == ROOT and output.is_relative_to(parent) and output != parent and
            not output.exists(), "Use a fresh output in the fixed checkout; never resume a probe")
    require(config_path.is_relative_to(ROOT) and plan_path.is_relative_to(ROOT), "Inputs escape checkout")
    config, generation, plan, runtime, paths = load_contract(config_path, plan_path)
    verify_supervisor(mode, config_path, plan_path, output, plan)
    output.mkdir(parents=True, exist_ok=False)
    source_paths = [*paths, Path(__file__), *sorted((ROOT / "src/rag_research").rglob("*.py"))]
    manifest = {"schema_version": 3, "purpose": plan["purpose"], "mode": mode,
        "config": config, "config_sha256": file_hash(config_path), "probe_plan_sha256": file_hash(plan_path),
        "fixed_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "judge_candidate_identity_sha256": JUDGE_IDENTITY,
        "generation_identity": plan["generation_identity"], "baseline_model": model_identity(),
        "targets": plan["targets"], **runtime,
        "source_sha256": {str(path.relative_to(ROOT)): file_hash(path) for path in source_paths},
        "planned_completion_limit": 0 if mode == "preflight" else 2,
        "automatic_retries": 0, "old_results_replaced": False, "semantic_adoption_claimed": False,
        "gate11_passed": False, "phase12_allowed": False}
    journals, prepared, fatal, started = [], [], None, time.perf_counter()
    with run_lock(output):
        write_json(output / "manifest.json", manifest)
        for index, target in enumerate(plan["targets"], 1):
            write_json(output / f"source-{index}.json", {key: target[key] for key in
                ("target_id", "language", "question", "documents", "initial_prompt", "source_record",
                 "source_manifest", "input_sha256")})
        try:
            with LocalServer(generation, output / "server.log", **execution_kwargs(config)) as server:
                try:
                    require(server.client.completion_attempts == 0, "Server must start without probe calls")
                    for index, target in enumerate(plan["targets"], 1):
                        prompt = PromptSpec(**yaml.safe_load(bound(target["initial_prompt"]).read_text()))
                        packed = prepare_payload(server.client, generation, prompt, target)
                        write_json(output / f"prepared-{index}.json", packed)
                        prepared.append(packed)
                        if mode == "preflight":
                            continue
                        journal = {"target_id": target["target_id"], "status": "started",
                            "completion_attempted": False, "response_received": False,
                            "runtime_response": None, "output_tokens": None, "cost_incomplete": False,
                            "source_input_sha256": target["input_sha256"]}
                        path = output / f"probe-{index}.json"
                        write_json(path, journal)
                        journals.append(journal)
                        proxy = ProbeJournalClient(server.client, journal, path, packed["prompt_tokens"])
                        answer = LocalGenerator(proxy, generation, prompt).generate_record(
                            target["question"], source_hits(target))
                        journal.update(answer, status=answer["status"])
                        write_json(path, journal)
                        if journal["status"] != "ok" or journal["cost_incomplete"]:
                            break
                finally:
                    session = server.report()
                    session["completion_attempts_this_session"] = server.client.completion_attempts
                    write_json(output / "session.json", session)
                    require(session["full_gpu_offload"] is True and
                            session["server_context_tokens"] == generation.context_tokens,
                            "Baseline probe requires its declared context and full CUDA offload")
        except Exception as error:
            fatal = f"{type(error).__name__}: {error}"
        attempts = sum(bool(row["completion_attempted"]) for row in journals)
        unknown = any(row["cost_incomplete"] for row in journals)
        report = {"purpose": plan["purpose"], "mode": mode, "manifest_sha256": digest(manifest),
            "runtime_health_passed": fatal is None and len(prepared) == 2 and
                (attempts == 0 if mode == "preflight" else len(journals) == attempts == 2 and
                 all(row["status"] == "ok" and not row["cost_incomplete"] for row in journals)),
            "planned_completion_limit": manifest["planned_completion_limit"],
            "completion_attempts_recorded": attempts, "prepared_payloads": len(prepared),
            "response_received": sum(row["response_received"] for row in journals),
            "unknown_responses": sum(row["completion_attempted"] and not row["response_received"]
                                     for row in journals),
            "cost_incomplete": unknown, "observed_input_tokens": sum(row.get("input_tokens", 0)
                                                                      for row in journals),
            "observed_output_tokens": sum(row.get("output_tokens") or 0 for row in journals),
            "total_output_tokens": None if unknown else sum(row.get("output_tokens") or 0
                                                            for row in journals),
            "summed_task_seconds": sum(row.get("elapsed_seconds", 0) for row in journals),
            "wall_seconds": time.perf_counter() - started, "fatal_error": fatal,
            "automatic_retries": 0, "semantic_adoption_claimed": False,
            "gate11_passed": False, "phase12_allowed": False}
        write_json(output / "report.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["preflight", "smoke"], required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--probe-plan", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.mode, args.config, args.probe_plan, args.output_dir)
    print(json.dumps(result))
    sys.exit(0 if result["runtime_health_passed"] else 1)
