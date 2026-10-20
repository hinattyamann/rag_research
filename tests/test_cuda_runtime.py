import json
from pathlib import Path

import pytest

from rag_research.generation import cuda_runtime
from rag_research.generation.config import GenerationConfig
from rag_research.generation.local import LocalServer
from rag_research.retrieval.common import file_hash


def test_cuda_runtime_rejects_changed_bytes_and_external_symlinks(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    directory = root / "runtime"
    directory.mkdir()
    spec = root / "spec.json"
    spec.write_text(json.dumps({"schema_version": 1, "tag": "b11433",
                               "backend": "Ubuntu-x64-CUDA-12.8", "directory": "runtime"}))
    monkeypatch.setattr(cuda_runtime, "ROOT", root)
    monkeypatch.setattr(cuda_runtime, "SPEC", spec)
    server = directory / "llama-server"
    server.write_bytes(b"fixed server fixture")
    manifest = {"specification_sha256": file_hash(spec), "backend": "Ubuntu-x64-CUDA-12.8",
                "server": "llama-server", "files": {"llama-server": file_hash(server)}}
    (directory / "runtime_manifest.json").write_text(json.dumps(manifest))
    assert cuda_runtime.verify_cuda_runtime()[0] == server
    server.write_bytes(b"altered server fixture")
    with pytest.raises(ValueError, match="hash mismatch"):
        cuda_runtime.verify_cuda_runtime()
    server.unlink()
    outside = tmp_path / "outside"
    outside.write_bytes(b"fixed server fixture")
    server.symlink_to(outside)
    with pytest.raises(ValueError, match="hash mismatch"):
        cuda_runtime.verify_cuda_runtime()


def test_cpu_default_is_preserved_and_gpu_requires_explicit_conditions():
    assert cuda_runtime.execution_kwargs({}) == {}
    with pytest.raises(ValueError, match="explicit GPU"):
        cuda_runtime.execution_kwargs({"execution": {"gpu_layers": 0}})


@pytest.mark.parametrize("log,actual,full", [
    ("offloaded 33/33 layers to GPU", False, False),
    ("CUDA0 model buffer size = 2000 MiB\noffloaded 20/33 layers to GPU", True, False),
    ("using device CUDA0\noffloaded 33/33 layers to GPU", True, True),
    ("using device CUDA0\noffloaded 0/33 layers to GPU", False, False),
])
def test_offload_proof_requires_positive_cuda_layers(tmp_path, log, actual, full):
    path = tmp_path / "server.log"
    path.write_text(log)
    server = LocalServer(GenerationConfig(), path)
    with path.open("a") as server.log_file:
        assert server.offload_report()["actual_gpu_offload"] is actual
        assert server.offload_report()["full_gpu_offload"] is full


def test_gpu_preselection_is_preserved_and_never_replaced(tmp_path, monkeypatch):
    from rag_research.calibration import preparation
    from rag_research.calibration.preparation import load_config, prepare

    original_hash = preparation.file_hash
    monkeypatch.setattr(preparation, "file_hash", lambda path:
                        "identity-fixture" if path.name == "phase11_gpu_generation_manifest.json"
                        else original_hash(path))
    root = Path(__file__).resolve().parents[1]
    config_path = root / "configs/phase11_gpu_calibration.yaml"
    config = load_config(config_path)
    selection_path = root / config["preselected_manifest"]
    before = selection_path.read_bytes()
    selection, candidate = prepare(config_path, config, selection_path, tmp_path / "run")
    assert selection["count"] == 20 and candidate["gate11_passed"] is False
    assert selection_path.read_bytes() == before
    changed = dict(config, count=19)
    with pytest.raises(ValueError, match="preselection differs"):
        prepare(config_path, changed, selection_path, tmp_path / "other")
