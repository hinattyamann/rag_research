"""Artificial clients only: no real tokenizer, Native, Runtime, Model or QA."""

import ast
import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location(
    "format_v5_source_test", Path(__file__).resolve().parents[1] / "scripts/probe_thinking_json_schema_v5.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)

from rag_research.generation.auxiliary_config import AuxiliaryGenerationConfig  # noqa: E402


def config():
    return {"auxiliary_model_manifest": probe.MODEL_MANIFEST["path"],
        "format_tokenizer_contract": {"version": "phase11-tokenizer-v5", "model_manifest": probe.MODEL_MANIFEST,
            "open_token_id": 70001, "close_token_id": 70002, "single_token_tags": True,
            "fresh_witness_required": 11, "expected_model_block_count": 36, "expected_full_offload_layers": 37},
        "sampling": {"reasoning_budget_tokens": 4096, "final_json_grammar_mode": "closing_tag_root_v3",
                     "reasoning_prefill_mode": "chatml_think_suffix_v1"},
        "auxiliary_runtime": {"context_tokens": 12288}, "output_constraints": "thinking_json_passage_ids_v3",
        "phase12_allowed": False,
        "execution": {"runtime_spec": "configs/lab_cuda_graph_off_runtime_v1.json", "gpu_layers": 99,
            "device": "CUDA0", "require_full_offload": True, "version": "cuda-execution-v2", "flash_attention": "off"}}


def base():
    return AuxiliaryGenerationConfig(context_tokens=12288, max_output_tokens=512,
        temperature=0.2, reasoning_budget_tokens=128, reasoning_prefill_mode="chatml_think_suffix_v1",
        final_json_grammar=True, final_json_grammar_mode="closing_tag_root_v3")


class FakeClient:
    """Invented reversible character encoding; it is not a Model tokenizer."""

    def __init__(self, *, closing=70002, suffix=True):
        self.completion_attempts = 0
        self.closing = closing
        self.suffix = suffix
        self.tokenize_options = []

    def tokenize(self, text, *, special=False):
        self.tokenize_options.append(special)
        result = []
        while text:
            if text.startswith("<think>"):
                result.append(70001)
                text = text[len("<think>"):]
            elif text.startswith("</think>"):
                result.append(self.closing)
                text = text[len("</think>"):]
            else:
                result.append(ord(text[0]) + 1000)
                text = text[1:]
        return result

    def detokenize(self, tokens):
        return "".join("<think>" if token == 70001 else "</think>" if token == self.closing else
                       chr(token - 1000) for token in tokens)

    def render(self, messages):
        return json.dumps(messages, ensure_ascii=False) + (probe.CHATML_THINK_SUFFIX if self.suffix else "bad suffix")

    def complete(self, *args, **kwargs):
        pytest.fail("Witness capture must never call completion")


@pytest.fixture(autouse=True)
def deny_native_constructor(monkeypatch):
    monkeypatch.setattr(probe.LocalServer, "__init__",
                        lambda *a, **k: pytest.fail("No actual Runtime during Source preparation"))


def test_exact_fresh11_from_artificial_client_have_hash_context_and_no_generation(tmp_path):
    client = FakeClient()
    planned = probe.cases(constraints="thinking_json_passage_ids_v3")
    context = {"fixture_only": True, "model": "invented test client", "settings": asdict(base())}
    prepared, manifest = probe.capture_tokenizer_witnesses(
        client, base(), planned, probe.tokenizer_contract(config()), context, tmp_path)
    assert len(prepared) == 10 and len(manifest["files"]) == manifest["file_count"] == 11
    assert client.completion_attempts == manifest["completion_attempts_after"] == 0
    assert manifest["old_model_token_ids_or_witnesses_reused"] is False
    assert all(client.tokenize_options)
    for reference in manifest["files"]:
        path = tmp_path / reference["path"]
        assert probe.file_hash(path) == reference["sha256"]
        witness = json.loads(path.read_text())
        assert witness["context_sha256"] == probe.digest(context)
        assert witness["status"] == "validated" and witness["completion_attempts_after"] == 0
    for case, captured in zip(planned, prepared, strict=True):
        assert captured["schema"] == case["schema"]
        assert captured["messages"] == probe.messages_for(case)
        assert captured["settings"]["reasoning_budget_tokens"] == 128
        assert captured["settings"]["max_output_tokens"] == 512
        assert captured["reasoning_tag_tokens"] == {"open": [70001], "close": [70002]}
    assert sum(case["mode"] == "brace_trigger_v1" for case in planned) == 1


def test_root_reported_bare_template_shape_gets_fresh11_before_any_generation(tmp_path):
    class BareClient(FakeClient):
        def render(self, messages):
            return json.dumps(messages, ensure_ascii=False) + "<|im_start|>assistant\n"

    client = BareClient()
    prepared, manifest = probe.capture_tokenizer_witnesses(client, base(),
        probe.cases(constraints="thinking_json_passage_ids_v3"), probe.tokenizer_contract(config()),
        {"fixture_only": True, "tokenizer": "invented reversible IDs, not actual8B"}, tmp_path)
    assert manifest["schema_version"] == 5 and manifest["file_count"] == 11
    assert client.completion_attempts == 0
    for row in prepared:
        assert row["raw_rendered_prompt"].endswith("<|im_start|>assistant\n")
        assert row["rendered_prompt"] == row["raw_rendered_prompt"] + probe.THINK_PREFILL
        assert row["reasoning_prefill_audit"]["applied"] is True
        assert row["prompt_tokens"] == row["raw_prompt_tokens"] + client.tokenize(probe.THINK_PREFILL, special=True)


def test_original_format10_inputs_schemas_and_decisions_have_identical_ast():
    root = Path(__file__).resolve().parents[1]
    trees = [ast.parse((root / "scripts" / name).read_text()) for name in
        ("probe_thinking_json_schema_v4.py", "probe_thinking_json_schema_v5.py")]
    for name in ("cases", "conforms", "messages_for", "complete_case"):
        functions = [next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
                     for tree in trees]
        assert ast.dump(functions[0]) == ast.dump(functions[1])


@pytest.mark.parametrize("failure", ["wrong-tag", "bad-prefill", "overflow"])
def test_bad_tokenizer_evidence_is_saved_and_stops_before_native(tmp_path, failure):
    client = FakeClient(closing=70003 if failure == "wrong-tag" else 70002,
                        suffix=failure != "bad-prefill")
    planned = probe.cases(constraints="thinking_json_passage_ids_v3")
    if failure == "overflow":
        planned[0]["instruction"] = "x" * 13000
    with pytest.raises(ValueError):
        probe.capture_tokenizer_witnesses(client, base(), planned, probe.tokenizer_contract(config()),
                                          {"fixture_only": True}, tmp_path)
    assert client.completion_attempts == 0
    assert not (tmp_path / "tokenizer_witness_manifest.json").exists()
    saved = [json.loads(path.read_text()) for path in (tmp_path / "tokenizer_witnesses").glob("*.json")]
    assert any(row["status"] == "failed" and "error" in row for row in saved)


def test_input_domain_cannot_be_reduced_to_nine_witnesses(tmp_path):
    with pytest.raises(ValueError, match="unchanged artificial10"):
        probe.capture_tokenizer_witnesses(FakeClient(), base(), probe.cases()[:5],
                                          probe.tokenizer_contract(config()), {}, tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("failure", ["pending", "same-id", "boolean-id", "old-model", "semantic128", "old-layers", "ten-witnesses"])
def test_pending_or_inconsistent_model_contract_refuses(failure):
    candidate = config()
    contract = candidate["format_tokenizer_contract"]
    if failure == "pending":
        contract["close_token_id"] = None
    elif failure == "same-id":
        contract["close_token_id"] = contract["open_token_id"]
    elif failure == "boolean-id":
        contract["open_token_id"] = True
    elif failure == "old-model":
        candidate["auxiliary_model_manifest"] = "invented-other-model.json"
    elif failure == "semantic128":
        candidate["sampling"]["reasoning_budget_tokens"] = 128
    elif failure == "old-layers":
        contract["expected_full_offload_layers"] = 35
    else:
        contract["fresh_witness_required"] = 10
    with pytest.raises(ValueError):
        probe.tokenizer_contract(candidate)


def server_report():
    return {"execution": config()["execution"], "server_context_tokens": 12288,
        "actual_gpu_offload": True, "full_gpu_offload": True, "offloaded_layers": 37, "total_layers": 37,
        "command": ["invented-server", "--flash-attn", "off"],
        "execution_profile_validation": {"version": "cuda-execution-v2", "flash_attention": "off",
            "actual_context_flash_attn": ["disabled"], "actual_context_tokens": [12288],
            "enabled_or_auto_context_observed": False},
        "runtime": {"source_commit": "50569eb87df530daff11afda229ceb9ab8e6cae8",
            "backend": "Ubuntu-x64-CUDA-12.9-graph-off-source-v1", "cmake_options": {"GGML_CUDA_GRAPHS": "OFF"}}}


@pytest.mark.parametrize("failure", [None, "layers", "enabled", "auto", "context", "graph-on"])
def test_actual_server_profile_must_prove_new_model_and_faoff(failure):
    server = server_report()
    if failure == "layers":
        server["offloaded_layers"] = server["total_layers"] = 35
    elif failure == "enabled":
        server["execution_profile_validation"]["actual_context_flash_attn"] = ["enabled"]
    elif failure == "auto":
        server["execution_profile_validation"]["enabled_or_auto_context_observed"] = True
    elif failure == "context":
        server["execution_profile_validation"]["actual_context_tokens"] = [4096]
    elif failure == "graph-on":
        server["runtime"]["cmake_options"]["GGML_CUDA_GRAPHS"] = "ON"
    if failure:
        with pytest.raises(ValueError):
            probe.validate_server_context(server, config(), probe.tokenizer_contract(config()))
    else:
        probe.validate_server_context(server, config(), probe.tokenizer_contract(config()))


def test_no_live_supervisor_refuses_before_any_input_or_native_read(monkeypatch):
    monkeypatch.delenv("RAG_PHASE11_AUTONOMY_CONTEXT", raising=False)
    monkeypatch.setattr(probe, "read_json", lambda *a: pytest.fail("No data opens without live registration"))
    with pytest.raises(ValueError, match="preparation is not execution"):
        probe.verify_live_supervisor(SimpleNamespace(mode="tokenizer"))


@pytest.mark.parametrize("failure", [None, "argv", "budget", "pid", "create-time", "group", "deadline",
                                     "noncanonical-ledger", "main-checkout", "wrong-head"])
def test_live_metadata_exact_argv_budget_ownership_and_deadline(tmp_path, monkeypatch, failure):
    import psutil

    canonical = tmp_path / "canonical"
    worktree = canonical / ".tools/worktrees/fixture"
    admin = canonical / ".git/worktrees/fixture"
    worktree.mkdir(parents=True)
    admin.mkdir(parents=True)
    (worktree / ".git").write_text("gitdir: " + str(admin))
    (admin / "commondir").write_text("../..")
    (admin / "HEAD").write_text("a" * 40)
    script = worktree / "scripts/probe_thinking_json_schema_v5.py"
    arguments = [str(script), "--mode", "tokenizer", "--config", "configs/invented.yaml",
                 "--output-dir", "data/runs/runtime_screening/invented"]
    plan = {"stage": "preflight", "run_id": "fixture-only", "fixed_commit": "a" * 40,
            "budget": {"planned_calls": 0, "maximum_calls": 0,
            "maximum_wall_seconds": 1800}, "automatic_retries": 0, "phase12_allowed": False,
            "command": ["scripts/probe_thinking_json_schema_v5.py", *arguments[1:]]}
    row = {"run_id": "fixture-only", "state": "running", "plan": plan,
        "child_pid": 90002, "child_create_time": 200.0, "supervisor_pid": 90001,
        "supervisor_create_time": 100.0, "started_at_utc": probe.datetime.now(probe.UTC).isoformat()}
    if failure == "argv":
        plan["command"][2] = "format"
    elif failure == "budget":
        plan["budget"]["maximum_calls"] = 10
    elif failure == "pid":
        row["child_pid"] = 90003
    elif failure == "create-time":
        row["child_create_time"] = 201.0
    elif failure == "deadline":
        row["started_at_utc"] = "2000-01-01T00:00:00+00:00"
    elif failure == "wrong-head":
        plan["fixed_commit"] = "b" * 40
    row["plan_content_sha256"] = probe.digest(plan)
    ledger = {"version": "phase11-autonomy-v3", "runs": [row]}
    monkeypatch.setattr(probe, "ROOT", canonical if failure == "main-checkout" else worktree)
    monkeypatch.setattr(probe, "__file__", str(script))
    monkeypatch.setattr(probe.sys, "argv", arguments)
    monkeypatch.setattr(probe, "read_json", lambda path: ledger)
    shared = canonical / "data/runs/development_screening/phase11-autonomy-v3"
    monkeypatch.setenv("RAG_PHASE11_AUTONOMY_CONTEXT", json.dumps({
        "ledger_dir": str(tmp_path / "fake-ledger" if failure == "noncanonical-ledger" else shared), "run_id": "fixture-only"}))
    monkeypatch.setattr(psutil, "Process", lambda pid: SimpleNamespace(
        is_running=lambda: True, create_time=lambda: 100.0 if pid == 90001 else 200.0))
    with monkeypatch.context() as owned:
        owned.setattr(probe.os, "getpid", lambda: 90002)
        owned.setattr(probe.os, "getpgid", lambda pid: 90004 if failure == "group" else pid)
        if failure:
            with pytest.raises(ValueError):
                probe.verify_live_supervisor(SimpleNamespace(mode="tokenizer"))
        else:
            assert probe.verify_live_supervisor(SimpleNamespace(mode="tokenizer")) == plan


@pytest.mark.parametrize("failure", ["response-lost", "truncated", "bad-stop", "wrong-preserved", "budget"])
def test_legacy_native_health_failure_never_sends_the_next_request(tmp_path, monkeypatch, failure):
    contract = probe.tokenizer_contract(config())
    planned = probe.cases(constraints="thinking_json_passage_ids_v3")

    class CompletionFixture:
        completion_attempts = 0

        def complete(self, *args, **kwargs):
            self.completion_attempts += 1
            if failure == "response-lost":
                raise RuntimeError("invented HTTP unknown after submission")
            return {"tokens": [123, 70002, 124], "content": "invented response",
                    "truncated": failure == "truncated", "stop_type": "limit" if failure == "bad-stop" else "eos",
                    "generation_settings": {"preserved_tokens": [70001, 70003 if failure == "wrong-preserved" else 70002]}}

    client = CompletionFixture()
    monkeypatch.setattr(probe, "audit_reasoning_budget", lambda *a:
                        (_ for _ in ()).throw(ValueError("invented budget breach")))
    with pytest.raises((RuntimeError, ValueError)):
        for case in planned[:2]:
            captured = {"id": case["id"], "prompt_tokens": [70001, 1010], "input_tokens": 2, "fixture_only": True}
            probe.complete_case(client, base(), case, captured, contract, tmp_path / (case["id"] + ".json"))
    assert client.completion_attempts == 1
    assert not (tmp_path / (planned[1]["id"] + ".json")).exists()
    first = json.loads((tmp_path / (planned[0]["id"] + ".json")).read_text())
    assert first["status"] == "failed" and first["native_health_verified"] is False
    if failure == "response-lost":
        assert first["response_received"] is False and "output_tokens" not in first


def test_intended_legacy_format_failure_is_kept_after_native_health_passes(tmp_path, monkeypatch):
    case = probe.cases()[0]
    client = SimpleNamespace(complete=lambda *a, **k: {"tokens": [123, 70002, 124], "content": "invented array",
        "truncated": False, "stop_type": "eos", "generation_settings": {"preserved_tokens": [70001, 70002]}})
    monkeypatch.setattr(probe, "audit_reasoning_budget", lambda *a: {"fixture_only": True})
    monkeypatch.setattr(probe, "audit_final_json_grammar", lambda *a, **k:
                        (_ for _ in ()).throw(ValueError("invented intentional array outside object root")))
    captured = {"id": case["id"], "prompt_tokens": [70001, 1010], "input_tokens": 2, "fixture_only": True}
    result = probe.complete_case(client, base(), case, captured, probe.tokenizer_contract(config()), tmp_path / "legacy.json")
    assert result["status"] == "failed" and result["native_health_verified"] is True
    assert result["response_received"] is True and result["output_tokens"] == 3
