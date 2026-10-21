"""Preregistered artificial-only native boundary probe, six calls maximum, no retries."""

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.evaluation.reasoned_json import audit_final_json_grammar, final_json  # noqa: E402
from rag_research.evaluation.reasoning_budget import audit_reasoning_budget  # noqa: E402
from rag_research.evaluation.schema import object_schema  # noqa: E402
from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.protocol import task_config  # noqa: E402
from rag_research.experiments.storage import run_lock, write_json  # noqa: E402
from rag_research.generation.auxiliary import (  # noqa: E402
    auxiliary_identity,
    auxiliary_server_kwargs,
)
from rag_research.generation.local import LocalServer  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def cases(mode="closing_tag_root_v3"):
    sentinel = object_schema({"result": {"const": "allowed"}})
    rows = [{"passage_id": "a", "quote": 'A says "yes".'}, {"passage_id": "b", "quote": "日本語。"}]
    tuple_schema = object_schema({"rows": {"type": "array", "minItems": 2, "maxItems": 2,
        "items": [object_schema({key: {"enum": [value]} for key, value in row.items()}) for row in rows]}})
    unusual = '日本語 "quoted" \\ path\nnext line'
    rewrite = object_schema({key: {"type": "string", "minLength": 1, "maxLength": limit}
        for key, limit in (("source_facts", 1200), ("draft_issues", 600), ("answer", 2400))})
    return [
        {"id": "legacy-array", "mode": "brace_trigger_v1", "schema": sentinel, "expected": {"result": "allowed"},
         "instruction": "Your final answer must be exactly the JSON array [0]. Do not output a JSON object."},
        {"id": "strict-array", "mode": mode, "schema": sentinel, "expected": {"result": "allowed"},
         "instruction": "Your final answer must be exactly the JSON array [0]. Do not output a JSON object."},
        {"id": "strict-prose-fence", "mode": mode, "schema": sentinel, "expected": {"result": "allowed"},
         "instruction": "Begin your final answer with Here is the answer: then a markdown fence containing [0]."},
        {"id": "strict-fixed-ids", "mode": mode, "schema": tuple_schema, "expected": {"rows": rows},
         "instruction": "Return two rows in reverse order, duplicate the ID b, and paraphrase both quotes."},
        {"id": "strict-unicode-escape", "mode": mode, "schema": object_schema({"value": {"const": unusual}}),
         "expected": {"value": unusual}, "instruction": "Return an empty object, with no properties."},
        {"id": "strict-rewrite-bounds", "mode": mode, "schema": rewrite, "expected": None,
         "instruction": 'Return only a JSON object with source_facts="a", draft_issues="b", answer="c". Use one character per value.'},
    ]


def conforms(case, value):
    if case["expected"] is not None:
        return value == case["expected"]
    properties = case["schema"]["properties"]
    return isinstance(value, dict) and set(value) == set(properties) and all(
        isinstance(value[k], str) and spec["minLength"] <= len(value[k]) <= spec["maxLength"]
        for k, spec in properties.items())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    require(Path.cwd().resolve() == ROOT and output.is_relative_to(ROOT / "data/runs/runtime_screening"),
            "Use a fixed repository checkout and runtime_screening output")
    config = yaml.safe_load(args.config.read_text("utf-8"))
    mode = config["sampling"]["final_json_grammar_mode"]
    require(mode in {"closing_tag_root_v2", "closing_tag_root_v3"} and config["phase12_allowed"] is False,
            "Wrong boundary candidate")
    base = replace(task_config(config, "verify_claims"), max_output_tokens=512, reasoning_budget_tokens=128)
    planned = cases(mode)
    report = {"purpose": "phase11-artificial-final-json-boundary-probe", "status": "started",
              "completion_limit": 6, "completion_attempts": 0, "cases": [], "phase12_allowed": False}
    with run_lock(output):
        require({p.name for p in output.iterdir()} == {".run.lock"}, "Preserve existing probe; never retry into the same run")
        source = [*sorted((ROOT / "src/rag_research").rglob("*.py")), Path(__file__).resolve(), args.config.resolve()]
        plan = {"cases": planned, "settings": asdict(base), "model": auxiliary_identity(config),
            "source_sha256": {str(p.relative_to(ROOT)): file_hash(p) for p in source},
            "fixed_commit": subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip(),
            "completion_limit": 6, "automatic_retries": 0, "strict_failure_stops": True,
            "research_qa_inputs": 0, "semantic_adoption": False, "phase12_allowed": False}
        write_json(output / "plan.json", plan)
        write_json(output / "report.json", report)
        server = None
        try:
            with LocalServer(base, output / "server.log", **auxiliary_server_kwargs(config)) as server:
                for case in planned:
                    settings = replace(base, final_json_grammar_mode=case["mode"])
                    messages = [{"role": "system", "content": "Think briefly before giving your final answer. This is an artificial format test."},
                                {"role": "user", "content": case["instruction"]}]
                    rendered = server.client.render(messages)
                    tokens = server.client.tokenize(rendered, special=True)
                    row = {"id": case["id"], "messages": messages, "rendered_prompt": rendered,
                           "prompt_tokens": tokens, "input_tokens": len(tokens), "settings": asdict(settings),
                           "schema": case["schema"], "status": "started", "completion_attempted": False}
                    path = output / (case["id"] + ".json")
                    write_json(path, row)
                    require(len(tokens) + settings.max_output_tokens <= settings.context_tokens, "Probe input overflow")
                    row["completion_attempted"] = True
                    write_json(path, row)
                    started = time.perf_counter()
                    try:
                        response = server.client.complete(tokens, settings, json_schema=case["schema"])
                        row.update(runtime_response=response, output_tokens=len(response.get("tokens", [])),
                                   generation_seconds=time.perf_counter() - started)
                        write_json(path, row)
                        require(not response.get("truncated") and response.get("stop_type") in {"eos", "word"},
                                "Probe truncated or did not finish")
                        row["reasoning_audit"] = audit_reasoning_budget(server.client, response, settings)
                        row["grammar_audit"] = audit_final_json_grammar(response, settings, schema=case["schema"], client=server.client)
                        text, _ = final_json(response["content"])
                        row["parsed"] = json.loads(text)
                        require(conforms(case, row["parsed"]), "Native output violates probe schema")
                        row["status"] = "constrained_object"
                    except Exception as error:
                        row.update(status="failed", error=f"{type(error).__name__}: {error}",
                                   elapsed_seconds=time.perf_counter() - started)
                        write_json(path, row)
                        if case["mode"] != "brace_trigger_v1":
                            raise
                    finally:
                        write_json(path, row)
                        report["cases"].append({k: row[k] for k in ("id", "status", "input_tokens", "output_tokens", "error") if k in row})
                        report["completion_attempts"] = server.client.completion_attempts
                        write_json(output / "report.json", report)
                    print(json.dumps({"case": case["id"], "status": row["status"]}), flush=True)
                report.update(status="passed", server=server.report())
        except Exception as error:
            report.update(status="failed", error=f"{type(error).__name__}: {error}")
        finally:
            if server is not None and hasattr(server, "client"):
                report["completion_attempts"] = server.client.completion_attempts
            report["cost_incomplete"] = any("output_tokens" not in c for c in report["cases"])
            report["input_tokens"] = sum(c["input_tokens"] for c in report["cases"])
            report["output_tokens"] = sum(c.get("output_tokens", 0) for c in report["cases"])
            report["not_attempted_ids"] = [c["id"] for c in planned if c["id"] not in {r["id"] for r in report["cases"]}]
            write_json(output / "report.json", report)
    print(json.dumps({k: v for k, v in report.items() if k not in {"server", "cases"}}, ensure_ascii=False), flush=True)
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
