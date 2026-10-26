"""The isolated rebuild is an explicit identity, never a replacement of the old runtime."""

import json

import pytest

from rag_research.generation import cuda_runtime
from rag_research.retrieval.common import file_hash


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def graph_off(tmp_path, monkeypatch):
    monkeypatch.setattr(cuda_runtime, "ROOT", tmp_path)
    options = {"GGML_CUDA_GRAPHS": "OFF", "GGML_CUDA": "ON",
               "LLAMA_BUILD_COMMIT": cuda_runtime.FIXED_SOURCE_COMMIT,
               "LLAMA_BUILD_NUMBER": "11433"}
    run = tmp_path / "build-evidence"
    run.mkdir()
    registration = run / "registration.json"
    write(registration, {"source_commit": cuda_runtime.FIXED_SOURCE_COMMIT,
                         "cmake_options": options})
    provenance = run / "source.json"
    write(provenance, {"source_commit": cuda_runtime.FIXED_SOURCE_COMMIT,
                       "registration_sha256": file_hash(registration),
                       "saved_source_checks": {"common.h": {
                           "saved_sha256": "a" * 64, "source_sha256": "a" * 64}}})
    cache = run / "CMakeCache.txt"
    cache.write_text("".join(f"{key}:BOOL={value}\n" for key, value in options.items()))
    spec = {"schema_version": 2, "tag": "b11433",
            "backend": cuda_runtime.GRAPH_OFF_BACKEND,
            "source_commit": cuda_runtime.FIXED_SOURCE_COMMIT,
            "directory": "new-runtime", "cmake_options": options,
            "build": {key: {"path": str(path.relative_to(tmp_path)), "sha256": file_hash(path)}
                      for key, path in (("registration", registration),
                                        ("source_provenance", provenance), ("cmake_cache", cache))}}
    spec_path = tmp_path / cuda_runtime.GRAPH_OFF_SPEC
    write(spec_path, spec)
    server = tmp_path / "new-runtime/llama-server"
    server.parent.mkdir()
    server.write_bytes(b"isolated-server-fixture")
    manifest = {**spec, "specification_sha256": file_hash(spec_path),
                "server": "llama-server", "files": {"llama-server": file_hash(server)}}
    write(server.parent / "runtime_manifest.json", manifest)
    return tmp_path, spec, spec_path, server, manifest


def test_new_runtime_requires_explicit_spec_and_proves_source_build(graph_off):
    _, spec, _, server, manifest = graph_off
    assert cuda_runtime.verify_cuda_runtime(cuda_runtime.GRAPH_OFF_SPEC) == (server, manifest)
    config = {"execution": {"runtime_spec": cuda_runtime.GRAPH_OFF_SPEC, "gpu_layers": 99,
                            "device": "CUDA0", "require_full_offload": True}}
    assert cuda_runtime.execution_identity(config)["runtime"]["build"] == spec["build"]
    with pytest.raises(ValueError, match="specification path"):
        cuda_runtime.verify_cuda_runtime("../unapproved-runtime.json")
    with pytest.raises(ValueError, match="explicit GPU"):
        cuda_runtime.execution_kwargs({"execution": {**config["execution"], "gpu_layers": 20}})


def test_changed_build_evidence_is_rejected_even_when_runtime_bytes_match(graph_off):
    root, _, _, _, _ = graph_off
    (root / "build-evidence/CMakeCache.txt").write_text(
        "GGML_CUDA_GRAPHS:BOOL=ON\nGGML_CUDA:BOOL=ON\n")
    with pytest.raises(ValueError, match="evidence hash mismatch"):
        cuda_runtime.verify_cuda_runtime(cuda_runtime.GRAPH_OFF_SPEC)


def test_graph_on_cannot_be_blessed_by_rehashing_its_cache(graph_off):
    root, spec, spec_path, _, _ = graph_off
    cache = root / "build-evidence/CMakeCache.txt"
    cache.write_text("GGML_CUDA_GRAPHS:BOOL=ON\nGGML_CUDA:BOOL=ON\n")
    spec["build"]["cmake_cache"]["sha256"] = file_hash(cache)
    write(spec_path, spec)
    with pytest.raises(ValueError, match="does not prove Graph OFF"):
        cuda_runtime.verify_cuda_runtime(cuda_runtime.GRAPH_OFF_SPEC)


def test_manifest_cannot_substitute_a_different_source_or_runtime(graph_off):
    _, _, _, server, manifest = graph_off
    manifest["source_commit"] = "0" * 40
    write(server.parent / "runtime_manifest.json", manifest)
    with pytest.raises(ValueError, match="manifest provenance mismatch"):
        cuda_runtime.verify_cuda_runtime(cuda_runtime.GRAPH_OFF_SPEC)


def test_parent_repository_commit_cannot_become_the_build_identity(graph_off):
    root, spec, spec_path, _, _ = graph_off
    cache = root / "build-evidence/CMakeCache.txt"
    cache.write_text(cache.read_text().replace(cuda_runtime.FIXED_SOURCE_COMMIT, "50374e8"))
    spec["build"]["cmake_cache"]["sha256"] = file_hash(cache)
    write(spec_path, spec)
    with pytest.raises(ValueError, match="actual CMake options differ"):
        cuda_runtime.verify_cuda_runtime(cuda_runtime.GRAPH_OFF_SPEC)


def test_runtime_bytes_are_verified_after_provenance(graph_off):
    _, _, _, server, _ = graph_off
    server.write_bytes(b"changed-server")
    with pytest.raises(ValueError, match="file hash mismatch"):
        cuda_runtime.verify_cuda_runtime(cuda_runtime.GRAPH_OFF_SPEC)
