"""Strict 9B-Q6 partial offload profile; all process/network observations are doubles."""

from copy import deepcopy
from pathlib import Path

import pytest
from test_cuda_execution_v2 import startup  # noqa: F401 -- reuse the unchanged no-Native fixture

from rag_research.generation import cuda_runtime, local
from rag_research.generation.config import GenerationConfig

PROFILE = {"runtime_spec": cuda_runtime.GRAPH_OFF_SPEC, "gpu_layers": 16,
           "device": "CUDA0", "require_full_offload": False,
           "version": cuda_runtime.PARTIAL_GPU_VERSION, "flash_attention": "off",
           "expected_total_layers": 33, "model_manifest": cuda_runtime.PARTIAL_GPU_MODEL_MANIFEST}
LOG = ("llama_model_loader: general.architecture str = qwen35\n"
       "llama_model_loader: qwen35.block_count u32 = 32\n"
       "print_info: n_layer_all = 32\nusing device CUDA0\n"
       "offloaded 16/33 layers to GPU\nllama_context: n_ctx = 12288\n"
       "llama_context: flash_attn = disabled\n")


@pytest.fixture
def q6_metadata(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    content = (root / cuda_runtime.PARTIAL_GPU_MODEL_MANIFEST).read_bytes()
    target = tmp_path / cuda_runtime.PARTIAL_GPU_MODEL_MANIFEST
    target.parent.mkdir(parents=True)
    target.write_bytes(content)
    monkeypatch.setattr(cuda_runtime, "ROOT", tmp_path)
    return tmp_path


def test_exact_profile_binds_small_model_metadata_without_mutation(q6_metadata):
    config = {"execution": deepcopy(PROFILE),
              "auxiliary_model_manifest": cuda_runtime.PARTIAL_GPU_MODEL_MANIFEST}
    before = deepcopy(config)
    assert cuda_runtime.execution_kwargs(config) == {"execution": PROFILE}
    assert config == before
    assert cuda_runtime.partial_gpu_model_path() == q6_metadata / cuda_runtime.PARTIAL_GPU_MODEL_ENTRYPOINT
    assert not cuda_runtime.partial_gpu_model_path().exists(), "Fixture must never contain a Model"


@pytest.mark.parametrize("key", list(PROFILE))
def test_v3_requires_every_field(q6_metadata, key):
    value = deepcopy(PROFILE)
    value.pop(key)
    with pytest.raises(ValueError, match="explicit GPU"):
        cuda_runtime.execution_kwargs({"execution": value})


@pytest.mark.parametrize("key,value", [
    ("runtime_spec", "configs/lab_cuda_runtime.json"), ("runtime_spec", []),
    ("gpu_layers", 99), ("gpu_layers", 15), ("gpu_layers", 16.0), ("gpu_layers", True),
    ("expected_total_layers", 32), ("expected_total_layers", 33.0), ("expected_total_layers", True),
    ("device", "CUDA1"), ("device", "CPU"),
    ("require_full_offload", True), ("require_full_offload", 0),
    ("flash_attention", "auto"), ("flash_attention", "on"),
    ("model_manifest", "data/manifests/phase11_auxiliary_qwen3_8b_manifest_v1.json"),
    ("version", "cuda-execution-v3"), ("extra_flags", ["--device", "CPU"]),
])
def test_v3_rejects_other_profile_values(q6_metadata, key, value):
    with pytest.raises(ValueError, match="explicit GPU"):
        cuda_runtime.execution_kwargs({"execution": {**PROFILE, key: value}})


def test_v3_rejects_outer_model_manifest_mismatch(q6_metadata):
    with pytest.raises(ValueError, match="explicit GPU"):
        cuda_runtime.execution_kwargs({"execution": PROFILE, "auxiliary_model_manifest": "another.json"})


def test_changed_small_model_metadata_fails_without_opening_model(q6_metadata):
    (q6_metadata / cuda_runtime.PARTIAL_GPU_MODEL_MANIFEST).write_text("{}\n")
    with pytest.raises(ValueError, match="manifest hash"):
        cuda_runtime.execution_kwargs({"execution": PROFILE})


@pytest.mark.parametrize("wrong", ["missing", "other_path", "no_jinja"])
def test_direct_constructor_rejects_wrong_model_or_jinja(q6_metadata, wrong, monkeypatch):
    monkeypatch.setattr(local.subprocess, "Popen", lambda *a, **kw: pytest.fail("Native forbidden"))
    path = None if wrong == "missing" else q6_metadata / cuda_runtime.PARTIAL_GPU_MODEL_ENTRYPOINT
    if wrong == "other_path":
        path = q6_metadata / "another.gguf"
    with pytest.raises(ValueError, match="fixed Q6 Model path and Jinja"):
        local.LocalServer(GenerationConfig(), q6_metadata / "server.log", model_path=path,
                          jinja=wrong != "no_jinja", execution=PROFILE)


@pytest.fixture
def partial_startup(request, q6_metadata):
    state, _ = request.getfixturevalue("startup")
    state["log"] = LOG
    config = GenerationConfig(context_tokens=12288, max_output_tokens=6144)

    def make():
        return local.LocalServer(config, q6_metadata / "server.log",
                                 model_path=q6_metadata / cuda_runtime.PARTIAL_GPU_MODEL_ENTRYPOINT,
                                 jinja=True, execution=PROFILE)

    return state, make


def test_valid_16_of_33_startup_command_and_session_proof(partial_startup):
    state, make = partial_startup
    with make() as server:
        report = server.report()
        proof = report["execution_profile_validation"]
        assert report["execution"] == PROFILE
        assert report["actual_gpu_offload"] is True and report["full_gpu_offload"] is False
        assert (report["offloaded_layers"], report["total_layers"]) == (16, 33)
        assert proof["version"] == cuda_runtime.PARTIAL_GPU_VERSION
        assert proof["actual_offload_records"] == [[16, 33]]
        assert proof["actual_devices"] == ["CUDA0"]
        assert proof["model_architecture"] == "qwen35" and proof["model_block_count"] == 32
        assert proof["flash_attention"] == "off" and proof["actual_context_tokens"] == [12288]
        for flag, value in [("--gpu-layers", "16"), ("--device", "CUDA0"),
                            ("--flash-attn", "off"), ("--batch-size", "128"), ("--ubatch-size", "128")]:
            assert state["command"][state["command"].index(flag) + 1] == value
        assert state["health"] == 1
    assert state["terminated"] and server.log_file.closed


@pytest.mark.parametrize("before,after", [
    (LOG, ""), ("16/33", "33/33"), ("16/33", "15/33"), ("16/33", "16/32"),
    ("using device CUDA0\n", ""), ("using device CUDA0", "using device CUDA1"),
    ("str = qwen35", "str = qwen3"), ("qwen35.block_count u32 = 32\n", ""),
    ("block_count u32 = 32", "block_count u32 = 31"),
    ("n_layer_all = 32", "n_layer_all = 31"),
    ("flash_attn = disabled", "flash_attn = auto"),
    ("flash_attn = disabled", "flash_attn = enabled"),
    ("n_ctx = 12288", "n_ctx = 4096"),
])
def test_actual_profile_mismatch_stops_owned_double_before_generation(partial_startup, before, after):
    state, make = partial_startup
    state["log"] = state["log"].replace(before, after)
    server = make()
    with pytest.raises(local.GenerationError):
        with server:
            pytest.fail("Unverified partial offload must never reach a caller")
    assert state["terminated"] and server.log_file.closed


@pytest.mark.parametrize("extra", ["offloaded 33/33 layers to GPU\n", "using device CUDA1\n",
    "llama_model_loader: general.architecture str = qwen3\n", "print_info: n_layer_all = 31\n",
    "llama_context: flash_attn = auto\n", "Flash Attention enabled\n"])
def test_contradictory_earlier_log_record_is_not_hidden_by_last_good_record(partial_startup, extra):
    state, make = partial_startup
    state["log"] = extra + state["log"]
    server = make()
    with pytest.raises(local.GenerationError):
        with server:
            pytest.fail("Every runtime record must agree")
    assert state["terminated"]
