"""Resume fixed Phase 6 inference for the preselected pilot without repeating attempts."""

import json
import os
from datetime import UTC, datetime

import yaml

from rag_research.baseline import BaselinePipeline
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.protocol import ROOT
from rag_research.experiments.storage import (
    checkpoint,
    read_json,
    run_lock,
    verify_checkpoint,
    write_json,
)
from rag_research.generation.artifacts import model_identity
from rag_research.generation.config import load_config
from rag_research.generation.context import PromptSpec
from rag_research.generation.generator import LocalGenerator
from rag_research.generation.local import LocalServer
from rag_research.retrieval.common import CORPUS_PATH, file_hash, json_bytes
from rag_research.retrieval.factory import load_retriever


class JournalClient:
    def __init__(self, client, journal, path):
        self.client, self.journal, self.path = client, journal, path

    def __getattr__(self, key):
        return getattr(self.client, key)

    def complete(self, tokens, config):
        self.journal.update(completion_attempted=True, input_tokens=len(tokens), prompt_tokens=tokens)
        write_json(self.path, self.journal)
        response = self.client.complete(tokens, config)
        self.journal.update(runtime_response=response, output_tokens=len(response.get("tokens", [])))
        write_json(self.path, self.journal)
        return response


def baseline_once(client, retriever, generation, prompt, top_k, spec, folder, binding):
    path = folder / "record.json"
    key = digest({"binding": binding, "spec": spec})
    if path.exists():
        saved = read_json(path)
        require(saved["request_sha256"] == key, "Baseline resume inputs changed")
        if saved["status"] == "started":
            saved.pop("result_sha256", None)
            saved.update(status="error", error="Interrupted baseline; no automatic retry",
                         error_code="interrupted_unknown_outcome" if saved["completion_attempted"]
                         else "interrupted_before_completion", cost_incomplete=saved["completion_attempted"],
                         answer_generation_calls=int(saved["completion_attempted"]))
            return checkpoint(path, saved)
        verify_checkpoint(saved)
        return saved
    journal = {"record_id": spec["record_id"], "question": spec["question"], "status": "started",
               "request_sha256": key, "binding": binding, "completion_attempted": False,
               "cost_incomplete": False, "answer": None, "error": None,
               "started_at_utc": datetime.now(UTC).isoformat()}
    write_json(path, journal)
    proxy = JournalClient(client, journal, path)
    pipeline = BaselinePipeline(retriever, LocalGenerator(proxy, generation, prompt), top_k=top_k)
    try:
        result = pipeline.run(spec["question"])
        journal.update(result)
    except Exception as error:
        journal.update(status="error", error=f"{type(error).__name__}: {error}",
                       answer_generation_calls=int(journal["completion_attempted"]),
                       cost_incomplete=journal["completion_attempted"])
    return checkpoint(path, journal)


def run_baseline(config, selection, output):
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    original, generation = load_config(ROOT / config["baseline_config"])
    prompts_path = ROOT / config["baseline_prompts"]
    prompt = PromptSpec(**yaml.safe_load(prompts_path.read_text("utf-8")))
    sources = [ROOT / "src/rag_research/pilot/baseline.py", ROOT / "src/rag_research/baseline.py",
               *sorted((ROOT / "src/rag_research/generation").glob("*.py")),
               *sorted((ROOT / "src/rag_research/retrieval").glob("*.py"))]
    identity = {"schema_version": 1, "purpose": "phase10-fixed-phase6-baseline",
                "config": original, "config_sha256": file_hash(ROOT / config["baseline_config"]),
                "prompts_sha256": file_hash(prompts_path), "generator": model_identity(),
                "development_sha256": file_hash(ROOT / config["qa_path"]), "split": "development",
                "questions": [{"question": r["question"], "record_id": r["record_id"]}
                              for r in selection["records"]], "selection_sha256": digest(selection),
                "source_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in sources}}
    with run_lock(output):
        static = output / "identity.json"
        if static.exists():
            require(read_json(static) == identity, "Pilot baseline identity changed")
        else:
            require({p.name for p in output.iterdir()} == {".run.lock"}, "Unbound baseline directory")
            write_json(static, identity)
        write_json(output / "run_manifest.json", {**identity, "status": "running"})
        missing = [r for r in selection["records"] if not
                   (output / digest(r["record_id"])[:24] / "record.json").exists()]
        records = []

        def collect(client, retriever):
            for index, spec in enumerate(selection["records"]):
                folder = output / digest(spec["record_id"])[:24]
                folder.mkdir(exist_ok=True)
                result = baseline_once(client, retriever, generation, prompt, original["retrieval"]["top_k"],
                                       spec, folder, {"identity_sha256": digest(identity)})
                records.append(result)
                # No answers, scores, or reference metadata in console progress.
                print(json.dumps({"stage": "baseline", "completed": index + 1,
                                  "planned": len(selection["records"]), "status": result["status"]}), flush=True)

        session_index = len(list(output.glob("session-*.json"))) + 1
        if missing:
            retriever = load_retriever(original["retrieval"], corpus=CORPUS_PATH)
            with LocalServer(generation, output / f"server-{session_index}.log") as server:
                collect(server.client, retriever)
                session = {"completion_attempts_this_session": server.client.completion_attempts, **server.report()}
        else:
            collect(None, None)
            session = {"completion_attempts_this_session": 0, "server_started": False}
        write_json(output / f"session-{session_index}.json", session)
        temporary = output / "answers.jsonl.tmp"
        with temporary.open("wb") as handle:
            for record in records:
                handle.write(json_bytes(record))
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(output / "answers.jsonl")
        report = {**identity, "status": "completed", "completed_questions": len(records),
                  "successful_questions": sum(r["status"] == "ok" for r in records),
                  "answer_generation_calls": sum(r.get("answer_generation_calls", 0) for r in records),
                  "sessions": [read_json(p) for p in sorted(output.glob("session-*.json"))]}
        write_json(output / "run_manifest.json", report)
    return report
