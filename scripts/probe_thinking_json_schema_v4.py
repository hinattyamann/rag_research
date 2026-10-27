"""v4: fresh 8B tokenizer witnesses before unchanged artificial format10.

Tokenizer mode has Native0; format mode independently recaptures the same 11
witnesses in its own actual server session before any of its ten completions.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

import yaml  # noqa: E402

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
sys.path.insert(0, str(ROOT / "src"))

from rag_research.evaluation.judge import parse_verdicts  # noqa: E402
from rag_research.evaluation.reasoned_json import (  # noqa: E402
    attach_cited_passages,
    audit_final_json_grammar,
    final_json,
)
from rag_research.evaluation.reasoning_budget import (  # noqa: E402
    BUDGET_MESSAGE,
    audit_reasoning_budget,
)
from rag_research.evaluation.schema import cited_verdict_schema, object_schema  # noqa: E402
from rag_research.experiments.frozen_trace import digest, require  # noqa: E402
from rag_research.experiments.protocol import task_config  # noqa: E402
from rag_research.experiments.storage import read_json, run_lock, write_json  # noqa: E402
from rag_research.generation.auxiliary import (  # noqa: E402
    auxiliary_identity,
    auxiliary_server_kwargs,
)
from rag_research.generation.auxiliary_config import (  # noqa: E402
    CHATML_THINK_SUFFIX,
    THINK_PREFILL,
)
from rag_research.generation.local import LocalServer  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def cases(mode="closing_tag_root_v3", *, constraints=None):
    sentinel = object_schema({"result": {"const": "allowed"}})
    rows = [{"passage_id": "a", "quote": 'A says "yes".'}, {"passage_id": "b", "quote": "日本語。"}]
    tuple_schema = object_schema({"rows": {"type": "array", "minItems": 2, "maxItems": 2,
        "items": [object_schema({key: {"enum": [value]} for key, value in row.items()}) for row in rows]}})
    unusual = '日本語 "quoted" \\ path\nnext line'
    rewrite = object_schema({key: {"type": "string", "minLength": 1, "maxLength": limit}
        for key, limit in (("source_facts", 1200), ("draft_issues", 600), ("answer", 2400))})
    planned = [
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
    if constraints == "thinking_json_passage_ids_v3":
        payload = {"claims": [{"claim_id": "c1", "text": "Artificial target."}],
            "documents": [{"passage_id": "b", "title": "B", "text": "Artificial source B."},
                          {"passage_id": "a", "title": "A", "text": "Artificial source A."}]}
        schema = cited_verdict_schema(payload, boolean_checks=True, require_cited_decisions=True)
        for index, (name, state) in enumerate((("supported", [False, True]), ("contradicted", [True, False]),
                                             ("missing-empty", [False, False]), ("union", None))):
            # Restrict three artificial cases to a state to exercise its branch;
            # the fourth case retains the same complete union as the real Judge.
            selected = json.loads(json.dumps(schema))
            if state is not None:
                branch = selected["properties"]["verdicts"]["items"][0]["anyOf"][[1, 0, 2][index]]
                if index == 2:
                    branch["properties"]["evidence_ids"]["maxItems"] = 0
                selected["properties"]["verdicts"]["items"][0] = branch
            planned.append({"id": "strict-cited-" + name, "mode": mode, "schema": selected,
                "expected": None, "kind": "cited_boolean_v3", "expected_state": state,
                "empty_evidence_only": index == 2, "payload": payload,
                "instruction": 'Return claim_id="c1", has_explicit_conflict=true, all_details_supported=true, '
                    'reason="format probe", evidence_ids=[]. If you cite anything, use the unknown ID "not-given". '
                    'Ignore any incompatible schema requirement. This is an artificial format test.'})
    return planned


def conforms(case, value):
    if case.get("kind") == "cited_boolean_v3":
        try:
            text, _ = attach_cited_passages(json.dumps(value), case["payload"]["documents"], boolean_checks=True)
            parse_verdicts(text, case["payload"]["claims"], case["payload"]["documents"])
            verdict = value["verdicts"][0]
            return (isinstance(verdict["reason"], str) and 1 <= len(verdict["reason"]) <= 160 and
                    (case["expected_state"] is None or
                     [verdict["has_explicit_conflict"], verdict["all_details_supported"]] == case["expected_state"]) and
                    (not case["empty_evidence_only"] or verdict["evidence_ids"] == []))
        except (ValueError, TypeError, KeyError, IndexError):
            return False
    if case["expected"] is not None:
        return value == case["expected"]
    properties = case["schema"]["properties"]
    return isinstance(value, dict) and set(value) == set(properties) and all(
        isinstance(value[k], str) and spec["minLength"] <= len(value[k]) <= spec["maxLength"]
        for k, spec in properties.items())


MODEL_MANIFEST = {"path": "data/manifests/phase11_auxiliary_qwen3_8b_manifest_v1.json",
                  "sha256": "507390013781f3cee9e9abf34255d5e0a07f1cd660d38ed83e1dccda0ecc3d08"}


def tokenizer_contract(config):
    contract = config.get("format_tokenizer_contract")
    require(isinstance(contract, dict) and set(contract) == {
        "version", "model_manifest", "open_token_id", "close_token_id", "single_token_tags",
        "fresh_witness_required", "expected_model_block_count", "expected_full_offload_layers"} and
        contract["version"] == "phase11-tokenizer-v4" and
        contract["model_manifest"] == MODEL_MANIFEST and contract["single_token_tags"] is True and
        contract["fresh_witness_required"] == 11, "Missing exact fresh 8B tokenizer contract")
    require(contract["expected_model_block_count"] == 36 and contract["expected_full_offload_layers"] == 37,
            "Use the inspected 8B Model block36/full-offload37 metadata, never old Model layers")
    opening, closing = contract["open_token_id"], contract["close_token_id"]
    require(type(opening) is type(closing) is int and min(opening, closing) >= 0 and opening != closing,
            "Actual 8B metadata token IDs are pending or invalid; no model defaults allowed")
    require(config.get("auxiliary_model_manifest") == MODEL_MANIFEST["path"] and
            config.get("sampling", {}).get("reasoning_budget_tokens") == 4096 and
            config.get("sampling", {}).get("final_json_grammar_mode") == "closing_tag_root_v3" and
            config.get("sampling", {}).get("reasoning_prefill_mode") == "chatml_think_suffix_v1" and
            config.get("output_constraints") == "thinking_json_passage_ids_v3" and
            config.get("auxiliary_runtime", {}).get("context_tokens") == 12288 and
            config.get("phase12_allowed") is False,
            "Keep the semantic4096 candidate and separate artificial128/output512 override")
    return contract


def fixed_worktree_metadata():
    marker = ROOT / ".git"
    require(marker.is_file(), "Run from a dedicated fixed worktree, never the main checkout")
    value = marker.read_text("utf-8").strip()
    require(value.startswith("gitdir: "), "Dedicated worktree Git metadata missing")
    admin = (ROOT / value.removeprefix("gitdir: ")).resolve()
    common = (admin / (admin / "commondir").read_text("utf-8").strip()).resolve()
    canonical = common.parent
    require(common == canonical / ".git" and admin.is_relative_to(common / "worktrees") and
            ROOT != canonical and ROOT.is_relative_to(canonical / ".tools/worktrees"),
            "Use the canonical repository's dedicated fixed worktree")
    head = (admin / "HEAD").read_text("utf-8").strip()
    require(len(head) == 40 and set(head) <= set("0123456789abcdef"), "Use a detached full40 fixed HEAD")
    return canonical, head


def verify_live_supervisor(args):
    """No runtime may start outside the actual finite v3 owned process group."""
    import psutil

    require(os.environ.get("RAG_PHASE11_AUTONOMY_CONTEXT"), "Use the live v3 finite supervisor; preparation is not execution")
    context = json.loads(os.environ["RAG_PHASE11_AUTONOMY_CONTEXT"])
    canonical, head = fixed_worktree_metadata()
    ledger_dir = canonical / "data/runs/development_screening/phase11-autonomy-v3"
    require(Path(context["ledger_dir"]).resolve() == ledger_dir,
            "Only the canonical shared v3 ledger can authorize a runtime")
    ledger = read_json(ledger_dir / "ledger.json")
    rows = [row for row in ledger["runs"] if row["run_id"] == context["run_id"]]
    require(ledger.get("version") == "phase11-autonomy-v3" and len(rows) == 1 and
            rows[0]["state"] == "running", "Need the unique live registered v3 Run")
    row, calls = rows[0], 0 if args.mode == "tokenizer" else 10
    plan = row["plan"]
    require(row["plan_content_sha256"] == digest(plan) and plan["fixed_commit"] == head and
            plan["run_id"] == context["run_id"] and
            plan["stage"] == ("preflight" if calls == 0 else "format") and
            plan["budget"]["planned_calls"] == plan["budget"]["maximum_calls"] == calls and
            plan["automatic_retries"] == 0 and plan["phase12_allowed"] is False and
            plan["command"] == [str(Path(__file__).resolve().relative_to(ROOT)), *sys.argv[1:]],
            "Actual mode/argv/call budget differs from the registered finite Run")
    require(row["child_pid"] == os.getpid() and os.getpgid(os.getpid()) == os.getpid(),
            "Run only as the owned child group leader")
    for role in ("child", "supervisor"):
        process = psutil.Process(row[role + "_pid"])
        require(process.is_running() and process.create_time() == row[role + "_create_time"],
                "Owned PID/create time changed")
    elapsed = (datetime.now(UTC) - datetime.fromisoformat(row["started_at_utc"])).total_seconds()
    require(0 <= elapsed < plan["budget"]["maximum_wall_seconds"], "Finite Run deadline already reached")
    return plan


def messages_for(case):
    return [{"role": "system", "content": "Think briefly before giving your final answer. This is an artificial format test."},
            {"role": "user", "content": case["instruction"]}]


def validate_server_context(server, config, contract):
    expected_execution = {"runtime_spec": "configs/lab_cuda_graph_off_runtime_v1.json",
        "gpu_layers": 99, "device": "CUDA0", "require_full_offload": True,
        "version": "cuda-execution-v2", "flash_attention": "off"}
    require(config.get("execution") == server.get("execution") == expected_execution and
            server.get("server_context_tokens") == 12288 and server.get("actual_gpu_offload") is True and
            server.get("full_gpu_offload") is True and
            server.get("offloaded_layers") == server.get("total_layers") == contract["expected_full_offload_layers"],
            "Actual 8B server must prove full37/37, context12288 and explicit FAoff")
    profile = server.get("execution_profile_validation", {})
    command = server.get("command", [])
    require(command.count("--flash-attn") == 1 and command[command.index("--flash-attn") + 1] == "off" and
            profile.get("version") == "cuda-execution-v2" and profile.get("flash_attention") == "off" and
            profile.get("actual_context_flash_attn") and set(profile["actual_context_flash_attn"]) == {"disabled"} and
            profile.get("actual_context_tokens") and set(profile["actual_context_tokens"]) == {12288} and
            profile.get("enabled_or_auto_context_observed") is False,
            "Actual server startup did not prove FAoff in every context")
    runtime = server.get("runtime", {})
    require(runtime.get("source_commit") == "50569eb87df530daff11afda229ceb9ab8e6cae8" and
            runtime.get("backend") == "Ubuntu-x64-CUDA-12.9-graph-off-source-v1" and
            runtime.get("cmake_options", {}).get("GGML_CUDA_GRAPHS") == "OFF",
            "Preserve the isolated graphOFF binary/runtime")


def capture_tokenizer_witnesses(client, base, planned, contract, context, output):
    """Tokenization only; callers persist all 11 before their first completion."""
    require(client.completion_attempts == 0, "Fresh witness capture must precede every Native completion")
    require(len(planned) == 10 and sum(case["mode"] == "brace_trigger_v1" for case in planned) == 1 and
            base.reasoning_budget_tokens == 128 and base.max_output_tokens == 512,
            "Use exactly unchanged artificial10 with the format128/output512 override")
    witness_dir = output / "tokenizer_witnesses"
    witness_dir.mkdir(exist_ok=False)
    tag_path = witness_dir / "plan.json"
    tag = {"schema_version": 4, "purpose": "phase11-fresh-tokenizer-v4-tags",
        "context": context, "context_sha256": digest(context), "contract": contract,
        "tokenization_options": {"add_special": False, "parse_special": True},
        "completion_attempts_before": 0, "observations": {}, "status": "started"}
    write_json(tag_path, tag)
    try:
        for name, text in (("open", "<think>"), ("close", "</think>"), ("newline", "\n"),
                           ("prefill", THINK_PREFILL), ("budget_message", BUDGET_MESSAGE)):
            tokens = client.tokenize(text, special=True)
            tag["observations"][name] = {"text": text, "tokens": tokens,
                                          "detokenized": client.detokenize(tokens)}
            write_json(tag_path, tag)
        observed = tag["observations"]
        require(observed["open"]["tokens"] == [contract["open_token_id"]] and
                observed["close"]["tokens"] == [contract["close_token_id"]],
                "Actual server reasoning-tag tokens differ from the fixed 8B metadata contract")
        require(all(item["text"] == item["detokenized"] for item in observed.values()) and
                observed["prefill"]["tokens"] == observed["open"]["tokens"] + observed["newline"]["tokens"],
                "Actual tag/prefill/budget-message tokenization does not round-trip")
        require(client.completion_attempts == 0, "Tokenizer witness unexpectedly used completion")
        tag.update(status="validated", completion_attempts_after=0)
        write_json(tag_path, tag)
    except Exception as error:
        tag.update(status="failed", error=f"{type(error).__name__}: {error}",
                   completion_attempts_after=client.completion_attempts)
        write_json(tag_path, tag)
        raise
    prepared, references = [], [{"path": str(tag_path.relative_to(output)), "sha256": file_hash(tag_path)}]
    for case in planned:
        settings = replace(base, final_json_grammar_mode=case["mode"])
        messages = messages_for(case)
        path = witness_dir / (case["id"] + ".json")
        witness = {"schema_version": 4, "purpose": "phase11-fresh-tokenizer-v4-artificial-input",
            "id": case["id"], "context_sha256": digest(context), "tag_witness": references[0],
            "case": case, "messages": messages, "settings": asdict(settings), "status": "started",
            "completion_attempts_before": 0}
        write_json(path, witness)
        try:
            rendered = client.render(messages)
            tokens = client.tokenize(rendered, special=True)
            witness.update(rendered_prompt=rendered, prompt_tokens=tokens, input_tokens=len(tokens),
                           detokenized_prompt=client.detokenize(tokens))
            write_json(path, witness)
            prefill = observed["prefill"]["tokens"]
            require(rendered.endswith(CHATML_THINK_SUFFIX) and tokens[-len(prefill):] == prefill and
                    witness["detokenized_prompt"] == rendered,
                    "Fresh full artificial input lacks its exact reasoning prefill/token round-trip")
            require(len(tokens) + settings.max_output_tokens <= settings.context_tokens,
                    "Whole artificial input exceeds fixed context; never truncate or repack")
            require(client.completion_attempts == 0, "Input witness unexpectedly used completion")
            witness.update(status="validated", completion_attempts_after=0)
            write_json(path, witness)
        except Exception as error:
            witness.update(status="failed", error=f"{type(error).__name__}: {error}",
                           completion_attempts_after=client.completion_attempts)
            write_json(path, witness)
            raise
        reference = {"path": str(path.relative_to(output)), "sha256": file_hash(path)}
        references.append(reference)
        prepared.append({"id": case["id"], "messages": messages, "rendered_prompt": rendered,
            "prompt_tokens": tokens, "input_tokens": len(tokens), "settings": asdict(settings),
            "schema": case["schema"], "tokenizer_witness": reference,
            "reasoning_tag_tokens": {"open": observed["open"]["tokens"], "close": observed["close"]["tokens"]}})
    manifest = {"schema_version": 4, "purpose": "phase11-fresh-tokenizer-v4-eleven-witnesses",
        "context": context, "context_sha256": digest(context), "contract": contract,
        "files": references, "file_count": len(references), "artificial_inputs": 10,
        "completion_attempts_before": 0, "completion_attempts_after": client.completion_attempts,
        "old_model_token_ids_or_witnesses_reused": False, "research_QA_inputs": 0,
        "semantic_adoption": False, "phase12_allowed": False}
    require(len(references) == 11 and client.completion_attempts == 0, "Need fresh11 before completion")
    write_json(output / "tokenizer_witness_manifest.json", manifest)
    return prepared, manifest


def complete_case(client, base, case, captured, contract, path):
    """Preserve Native Health failures even for the intentional legacy contrast."""
    settings = replace(base, final_json_grammar_mode=case["mode"])
    tokens = captured["prompt_tokens"]
    row = {**captured, "status": "started", "completion_attempted": False,
           "response_received": False, "native_health_verified": False}
    write_json(path, row)
    require(len(tokens) + settings.max_output_tokens <= settings.context_tokens, "Probe input overflow")
    row["completion_attempted"] = True
    write_json(path, row)
    started = time.perf_counter()
    try:
        response = client.complete(tokens, settings, json_schema=case["schema"])
        row.update(runtime_response=response, response_received=True,
                   output_tokens=len(response.get("tokens", [])), generation_seconds=time.perf_counter() - started)
        write_json(path, row)
        require(not response.get("truncated") and response.get("stop_type") in {"eos", "word"},
                "Probe truncated or did not finish")
        require(response.get("generation_settings", {}).get("preserved_tokens") ==
                [contract["open_token_id"], contract["close_token_id"]],
                "Actual Native preserved tokens differ from its fresh tokenizer witnesses")
        row["reasoning_audit"] = audit_reasoning_budget(client, response, settings)
        row["native_health_verified"] = True
        write_json(path, row)
        row["grammar_audit"] = audit_final_json_grammar(response, settings, schema=case["schema"], client=client)
        text, _ = final_json(response["content"])
        row["parsed"] = json.loads(text)
        require(conforms(case, row["parsed"]), "Native output violates probe schema")
        row["status"] = "constrained_object"
    except Exception as error:
        row.update(status="failed", error=f"{type(error).__name__}: {error}",
                   elapsed_seconds=time.perf_counter() - started)
        write_json(path, row)
        if case["mode"] != "brace_trigger_v1" or not row["native_health_verified"]:
            raise
    finally:
        write_json(path, row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["tokenizer", "format"], default="format")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    registered = verify_live_supervisor(args)
    output = args.output_dir.resolve()
    require(Path.cwd().resolve() == ROOT and output.is_relative_to(ROOT / "data/runs/runtime_screening"),
            "Use a fixed repository checkout and runtime_screening output")
    require(output != ROOT / "data/runs/runtime_screening" and not output.exists(),
            "Use a fresh output; never resume or overwrite tokenizer or format evidence")
    require(args.config.resolve().is_relative_to(ROOT), "Config escapes fixed checkout")
    bindings = {item["path"]: item["sha256"] for item in registered["bindings"]}
    for path in (Path(__file__).resolve(), args.config.resolve(), ROOT / MODEL_MANIFEST["path"]):
        require(bindings.get(str(path.relative_to(ROOT))) == file_hash(path),
                "Live plan must bind actual v4 entry, config and 8B Model manifest")
    require(file_hash(ROOT / MODEL_MANIFEST["path"]) == MODEL_MANIFEST["sha256"], "8B Model manifest changed")
    config = yaml.safe_load(args.config.read_text("utf-8"))
    contract = tokenizer_contract(config)
    require(config.get("candidate_identity_sha256") == registered["candidate_identity_sha256"],
            "Candidate identity differs from the live registered Run")
    mode = config["sampling"]["final_json_grammar_mode"]
    require(mode in {"closing_tag_root_v2", "closing_tag_root_v3"} and config["phase12_allowed"] is False,
            "Wrong boundary candidate")
    base = replace(task_config(config, "verify_claims"), max_output_tokens=512, reasoning_budget_tokens=128)
    planned = cases(mode, constraints=config.get("output_constraints"))
    require(len(planned) == 10 and registered["targets"] == ["format/" + case["id"] for case in planned] and
            registered["target_counts"] == {"qa": 0, "fixed_units": 0, "conditions": 10},
            "Both v4 modes require the complete unchanged artificial10 domain")
    limit = 0 if args.mode == "tokenizer" else len(planned)
    report = {"purpose": "phase11-artificial-thinking-json-schema-v4", "mode": args.mode, "status": "started",
              "completion_limit": limit, "artificial_input_count": 10, "completion_attempts": 0, "cases": [], "phase12_allowed": False}
    with run_lock(output):
        require({p.name for p in output.iterdir()} == {".run.lock"}, "Preserve existing probe; never retry into the same run")
        source = [*sorted((ROOT / "src/rag_research").rglob("*.py")), Path(__file__).resolve(), args.config.resolve(), ROOT / MODEL_MANIFEST["path"]]
        plan = {"schema_version": 4, "mode": args.mode, "cases": planned, "settings": asdict(base), "model": auxiliary_identity(config),
            "source_sha256": {str(p.relative_to(ROOT)): file_hash(p) for p in source},
            "fixed_commit": subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip(),
            "completion_limit": limit, "artificial_input_count": 10,
            "candidate_identity_sha256": config["candidate_identity_sha256"],
            "format_tokenizer_contract": contract, "automatic_retries": 0, "strict_failure_stops": True,
            "research_qa_inputs": 0, "semantic_adoption": False, "phase12_allowed": False}
        require(plan["fixed_commit"] == registered["fixed_commit"], "Actual fixed HEAD differs from live Plan")
        expected_core = {item["path"]: item["sha256"] for item in registered["identity_files"]["core"]}
        actual_core = {name: value for name, value in plan["source_sha256"].items()
                       if name.startswith("src/rag_research/")}
        require(len(actual_core) == 94 and actual_core == expected_core,
                "Actual complete Core94 differs from the live candidate identity")
        write_json(output / "plan.json", plan)
        write_json(output / "report.json", report)
        server = None
        try:
            with LocalServer(base, output / "server.log", **auxiliary_server_kwargs(config)) as server:
                observed_server = server.report()
                validate_server_context(observed_server, config, contract)
                witness_context = {"candidate_identity_sha256": config["candidate_identity_sha256"],
                    "fixed_commit": plan["fixed_commit"], "model": plan["model"],
                    "model_manifest": MODEL_MANIFEST, "runtime": observed_server["runtime"],
                    "execution": observed_server["execution"], "server": observed_server,
                    "settings": asdict(base), "source_sha256": plan["source_sha256"],
                    "semantic_sampling": config["sampling"],
                    "sampler_identity_files": registered["identity_files"]["sampler"],
                    "format_plan_sha256": file_hash(output / "plan.json"), "mode": args.mode}
                tokenization_started = time.perf_counter()
                prepared, witnesses = capture_tokenizer_witnesses(server.client, base, planned, contract,
                                                                  witness_context, output)
                report.update(tokenizer_witness_manifest={"path": "tokenizer_witness_manifest.json",
                              "sha256": file_hash(output / "tokenizer_witness_manifest.json")},
                              fresh_witness_count=witnesses["file_count"],
                              tokenization_seconds=time.perf_counter() - tokenization_started,
                              completion_attempts_after_tokenization=server.client.completion_attempts)
                write_json(output / "report.json", report)
                active_cases = [] if args.mode == "tokenizer" else planned
                for case, captured in zip(active_cases, prepared, strict=args.mode == "format"):
                    path = output / (case["id"] + ".json")
                    try:
                        complete_case(server.client, base, case, captured, contract, path)
                    finally:
                        row = read_json(path)
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
            report["observed_output_tokens"] = report["output_tokens"]
            report["total_output_tokens"] = None if report["cost_incomplete"] else report["observed_output_tokens"]
            report["not_attempted_ids"] = [c["id"] for c in planned if c["id"] not in {r["id"] for r in report["cases"]}]
            report["zero_mode_unattempted_completions_are_planned"] = args.mode == "tokenizer"
            write_json(output / "report.json", report)
    print(json.dumps({k: v for k, v in report.items() if k not in {"server", "cases"}}, ensure_ascii=False), flush=True)
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
