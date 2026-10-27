"""Versioned explicit FA-off execution; all process/HTTP observations are doubles."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from rag_research.generation import cuda_runtime, local
from rag_research.generation.config import GenerationConfig

LEGACY = {"runtime_spec": cuda_runtime.GRAPH_OFF_SPEC, "gpu_layers": 99,
          "device": "CUDA0", "require_full_offload": True}
PROFILE = {**LEGACY, "version": "cuda-execution-v2", "flash_attention": "off"}
OFF_LOG = "llama_context: n_ctx = 12288\nllama_context: flash_attn            = disabled\nusing device CUDA0\noffloaded 33/33 layers to GPU\n"


@pytest.mark.parametrize("execution", [None, LEGACY, {**LEGACY, "runtime_spec": "configs/lab_cuda_runtime.json"}, PROFILE])
def test_supported_contracts_are_returned_without_mutation(execution):
    config = {} if execution is None else {"execution": deepcopy(execution)}
    before = deepcopy(config)
    assert cuda_runtime.execution_kwargs(config) == ({} if execution is None else config)
    assert config == before


@pytest.mark.parametrize("key", list(PROFILE))
def test_v2_requires_every_declared_field(key):
    config = deepcopy(PROFILE)
    config.pop(key)
    with pytest.raises(ValueError, match="explicit GPU"):
        cuda_runtime.execution_kwargs({"execution": config})


@pytest.mark.parametrize("key,value", [
    ("runtime_spec", "../unapproved.json"), ("runtime_spec", []),
    ("version", "cuda-execution-v3"), ("version", None),
    ("flash_attention", "auto"), ("flash_attention", "on"), ("flash_attention", False),
    ("gpu_layers", 20), ("gpu_layers", 99.0), ("gpu_layers", True),
    ("device", "CPU"), ("require_full_offload", False), ("require_full_offload", 1),
    ("extra_flags", ["--flash-attn", "on"]), ("CUDA_LAUNCH_BLOCKING", "1"),
])
def test_v2_rejects_other_values_extra_flags_or_unrecorded_env(key, value):
    config = {**PROFILE, key: value}
    with pytest.raises(ValueError, match="explicit GPU"):
        cuda_runtime.execution_kwargs({"execution": config})


@pytest.mark.parametrize("log", [OFF_LOG,
    OFF_LOG + "resolve_fused_ops: fused Gated Delta Net enabled\n"])
def test_real_pinned_explicit_off_log_needs_no_auto_resolution_message(tmp_path, log):
    path = tmp_path / "server.log"
    path.write_text(log)
    server = local.LocalServer(GenerationConfig(context_tokens=12288, max_output_tokens=6144), path,
                               execution=PROFILE)
    with path.open("a") as server.log_file:
        proof = server.execution_profile_report()
    assert proof["actual_context_flash_attn"] == ["disabled"]
    assert proof["version"] == "cuda-execution-v2" and proof["flash_attention"] == "off"


@pytest.mark.parametrize("log", ["", "Flash Attention disabled\n",
    OFF_LOG.replace("disabled", "auto"), OFF_LOG.replace("disabled", "enabled"),
    OFF_LOG + "resolve_fused_ops: Flash Attention enabled\n",
    OFF_LOG + "llama_context: flash_attn = auto\n",
    OFF_LOG + "llama_new_context: enabling flash_attn since it is required\n"])
def test_missing_auto_enabled_or_contradictory_runtime_log_fails_closed(tmp_path, log):
    path = tmp_path / "server.log"
    path.write_text(log)
    server = local.LocalServer(GenerationConfig(), path, execution=PROFILE)
    with path.open("a") as server.log_file, pytest.raises(local.GenerationError, match="prove Flash Attention off"):
        server.execution_profile_report()


@pytest.mark.parametrize("log", [OFF_LOG.replace("n_ctx = 12288", "n_ctx = 4096"),
    OFF_LOG.replace("llama_context: n_ctx = 12288\n", "")])
def test_explicit_off_cannot_hide_missing_or_changed_actual_context(tmp_path, log):
    path = tmp_path / "server.log"
    path.write_text(log)
    server = local.LocalServer(GenerationConfig(context_tokens=12288), path, execution=PROFILE)
    with path.open("a") as server.log_file, pytest.raises(local.GenerationError, match="actual context log"):
        server.execution_profile_report()


@pytest.fixture
def startup(tmp_path, monkeypatch):
    """No runtime/version process, GPU, network, Model or tokenizer is started."""
    state = {"log": OFF_LOG, "context": 12288, "poll": None, "terminated": False,
             "env": None, "command": None, "health": 0}
    monkeypatch.setattr(local, "verify_cuda_runtime", lambda *_: (Path("/synthetic/llama-server"), {"synthetic": True}))
    monkeypatch.setattr(local.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout="synthetic version", stderr=""))

    class Process:
        pid = 12345

        def poll(self):
            return state["poll"]

        def terminate(self):
            state.update(terminated=True, poll=0)

        def wait(self, **kwargs):
            return state["poll"]

    def popen(command, **kwargs):
        state.update(command=command, env=kwargs["env"])
        kwargs["stdout"].write(state["log"])
        kwargs["stdout"].flush()
        return Process()

    class Port:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def bind(self, *args):
            pass

        def getsockname(self):
            return ("127.0.0.1", 1234)

    class Thread:
        def __init__(self, **kwargs):
            pass

        def start(self):
            pass

        def join(self, **kwargs):
            pass

    def request(self, route, payload=None, **kwargs):
        if route == "/health":
            state["health"] += 1
            return {"status": "ok"}
        assert route == "/props", "No generation or tokenizer request in this test"
        return {"default_generation_settings": {"n_ctx": state["context"]}}

    monkeypatch.setattr(local.subprocess, "Popen", popen)
    monkeypatch.setattr(local.socket, "socket", lambda: Port())
    monkeypatch.setattr(local.threading, "Thread", Thread)
    monkeypatch.setattr(local.LlamaClient, "request", request)
    config = GenerationConfig(context_tokens=12288, max_output_tokens=6144)

    def make(execution):
        return local.LocalServer(config, tmp_path / "server.log", model_path=tmp_path / "invented.gguf",
                                 jinja=True, execution=execution)

    return state, make


@pytest.mark.parametrize("execution", [LEGACY, PROFILE])
def test_startup_command_and_session_keep_legacy_or_capture_explicit_off(startup, execution):
    state, make = startup
    with make(execution) as server:
        report = server.report()
        assert report["execution"] == execution and report["server_context_tokens"] == 12288
        assert report["full_gpu_offload"] is True
        assert state["command"].count("--flash-attn") == (execution == PROFILE)
        if execution == PROFILE:
            assert state["command"][state["command"].index("--flash-attn") + 1] == "off"
            assert report["execution_profile_validation"]["flash_attention"] == "off"
        else:
            assert "execution_profile_validation" not in report
        assert state["command"][state["command"].index("--batch-size") + 1] == "128"
        assert state["command"][state["command"].index("--ubatch-size") + 1] == "128"
        assert state["env"]["LD_LIBRARY_PATH"] == "/synthetic"
        assert state["health"] == 1
    assert state["terminated"] and server.log_file.closed


@pytest.mark.parametrize("failure", ["FA_auto", "FA_enabled", "context", "offload"])
def test_bad_actual_profile_stops_owned_server_before_caller_can_generate(startup, failure):
    state, make = startup
    if failure == "context":
        state["context"] = 4096
    elif failure == "offload":
        state["log"] = OFF_LOG.replace("33/33", "20/33")
    else:
        state["log"] = OFF_LOG.replace("disabled", failure.removeprefix("FA_"))
    server = make(PROFILE)
    with pytest.raises(local.GenerationError):
        with server:
            pytest.fail("An unverified profile must not reach generation")
    assert state["terminated"] and server.log_file.closed
