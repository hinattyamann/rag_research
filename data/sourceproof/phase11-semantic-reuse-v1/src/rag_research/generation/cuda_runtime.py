"""Explicit Linux CUDA runtime; the historical Windows CPU identity stays unchanged."""

import platform
import shutil
import tarfile
import urllib.request
from pathlib import Path

from rag_research.generation.artifacts import model_identity
from rag_research.retrieval.common import file_hash, read_json, write_json

ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT / "configs/lab_cuda_runtime.json"
GRAPH_OFF_SPEC = "configs/lab_cuda_graph_off_runtime_v1.json"
GRAPH_OFF_BACKEND = "Ubuntu-x64-CUDA-12.9-graph-off-source-v1"
FIXED_SOURCE_COMMIT = "50569eb87df530daff11afda229ceb9ab8e6cae8"


def _spec_path(spec_path=None):
    if spec_path is None or spec_path == "configs/lab_cuda_runtime.json":
        return SPEC
    if spec_path != GRAPH_OFF_SPEC:
        raise ValueError("Unsupported CUDA runtime specification path")
    return ROOT / GRAPH_OFF_SPEC


def _verify_graph_off_provenance(spec):
    if (spec.get("schema_version") != 2 or spec.get("tag") != "b11433"
            or spec.get("source_commit") != FIXED_SOURCE_COMMIT
            or spec.get("backend") != GRAPH_OFF_BACKEND
            or spec.get("cmake_options", {}).get("GGML_CUDA_GRAPHS") != "OFF"
            or spec.get("cmake_options", {}).get("GGML_CUDA") != "ON"
            or spec.get("cmake_options", {}).get("LLAMA_BUILD_COMMIT") != FIXED_SOURCE_COMMIT
            or spec.get("cmake_options", {}).get("LLAMA_BUILD_NUMBER") != "11433"):
        raise ValueError("Graph OFF runtime specification/provenance mismatch")
    evidence = {}
    for key in ("registration", "source_provenance", "cmake_cache"):
        entry = spec.get("build", {}).get(key, {})
        path = ROOT / entry.get("path", "")
        if (not path.resolve().is_relative_to(ROOT.resolve()) or not path.is_file()
                or file_hash(path) != entry.get("sha256")):
            raise ValueError(f"Graph OFF runtime build evidence hash mismatch: {key}")
        evidence[key] = path
    registration = read_json(evidence["registration"])
    provenance = read_json(evidence["source_provenance"])
    if (registration.get("source_commit") != FIXED_SOURCE_COMMIT
            or registration.get("cmake_options") != spec["cmake_options"]
            or provenance.get("source_commit") != FIXED_SOURCE_COMMIT
            or provenance.get("registration_sha256") != spec["build"]["registration"]["sha256"]
            or not provenance.get("saved_source_checks")
            or any(c["saved_sha256"] != c["source_sha256"]
                   for c in provenance["saved_source_checks"].values())):
        raise ValueError("Graph OFF runtime source/options identity mismatch")
    cache = evidence["cmake_cache"].read_text(encoding="utf-8")
    cache_lines = set(cache.splitlines())
    if not {"GGML_CUDA_GRAPHS:BOOL=OFF", "GGML_CUDA:BOOL=ON"}.issubset(cache_lines):
        raise ValueError("Graph OFF runtime CMakeCache does not prove Graph OFF/CUDA ON")
    cache_values = {line.split(":", 1)[0]: line.split("=", 1)[1]
                    for line in cache_lines if ":" in line and "=" in line
                    and not line.startswith(("//", "#"))}
    if any(cache_values.get(key) != str(value) for key, value in spec["cmake_options"].items()):
        raise ValueError("Graph OFF runtime actual CMake options differ from registration")


def specification(spec_path=None):
    path = _spec_path(spec_path)
    spec = read_json(path)
    if spec_path == GRAPH_OFF_SPEC:
        _verify_graph_off_provenance(spec)
    elif (spec["schema_version"] != 1 or spec["tag"] != "b11433"
            or spec["backend"] not in {"Ubuntu-x64-CUDA-12.8", "Ubuntu-x64-CUDA-12.8-system12.9"}):
        raise ValueError("Unsupported CUDA runtime specification")
    return spec


def verify_cuda_runtime(spec_path=None):
    spec = specification(spec_path)
    directory = ROOT / spec["directory"]
    if not directory.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("CUDA runtime directory escapes repository")
    manifest = read_json(directory / "runtime_manifest.json")
    if (manifest["specification_sha256"] != file_hash(_spec_path(spec_path))
            or manifest["backend"] != spec["backend"]):
        raise ValueError("CUDA runtime identity mismatch")
    if spec_path == GRAPH_OFF_SPEC and any(manifest.get(key) != spec.get(key)
                                           for key in ("source_commit", "build", "cmake_options")):
        raise ValueError("Graph OFF runtime manifest provenance mismatch")
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
    if actual != set(manifest["files"]) | {"runtime_manifest.json"}:
        raise ValueError("CUDA runtime file set mismatch")
    for name, digest in manifest["files"].items():
        path = directory / name
        if not path.resolve().is_relative_to(directory.resolve()) or file_hash(path) != digest:
            raise ValueError(f"CUDA runtime file hash mismatch: {name}")
    server = directory / manifest["server"]
    if (server.name != "llama-server" or not server.is_file()
            or manifest["server"] not in manifest["files"]
            or not server.resolve().is_relative_to(directory.resolve())):
        raise ValueError("Linux CUDA server executable missing")
    return server, manifest


def execution_kwargs(config):
    execution = config.get("execution")
    if execution is None:
        return {}
    if (not isinstance(execution, dict)
            or execution.get("runtime_spec") not in {"configs/lab_cuda_runtime.json", GRAPH_OFF_SPEC}
            or execution != {"runtime_spec": execution.get("runtime_spec"), "gpu_layers": 99,
                             "device": "CUDA0", "require_full_offload": True}):
        raise ValueError("Unsupported explicit GPU execution conditions")
    return {"execution": execution}


def execution_identity(config):
    if not execution_kwargs(config):
        return {}
    runtime_spec = config["execution"]["runtime_spec"]
    _, manifest = (verify_cuda_runtime() if runtime_spec == "configs/lab_cuda_runtime.json"
                   else verify_cuda_runtime(runtime_spec))
    return {"execution": config["execution"], "runtime": manifest}


def prepare_cuda_runtime():
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("This runtime requires Linux x86_64")
    spec = specification()
    directory = ROOT / spec["directory"]
    if directory.exists():
        return verify_cuda_runtime()
    stage = directory.with_name(directory.name + ".building")
    stage.mkdir(parents=True, exist_ok=True)
    extracted = stage / "extracted"
    extracted.mkdir(exist_ok=True)
    for artifact in spec["archives"]:
        archive = stage / artifact["name"]
        if not archive.exists():
            temporary = archive.with_suffix(archive.suffix + ".partial")
            url = (f"https://github.com/ggml-org/llama.cpp/releases/download/"
                   f"{spec['tag']}/{artifact['name']}")
            print(f"Downloading {artifact['name']}", flush=True)
            with urllib.request.urlopen(url, timeout=120) as source, temporary.open("wb") as target:
                while block := source.read(4 * 1024 * 1024):
                    target.write(block)
            temporary.rename(archive)
        if archive.stat().st_size != artifact["bytes"] or file_hash(archive) != artifact["sha256"]:
            raise ValueError("Official CUDA runtime archive hash mismatch")
        with tarfile.open(archive) as source:
            source.extractall(extracted, filter="data")
    servers = list(extracted.rglob("llama-server"))
    if len(servers) != 1:
        raise ValueError("Expected one Linux server")
    for library in spec.get("system_libraries", []):
        source = Path(library["source"])
        if Path(library["name"]).name != library["name"] or file_hash(source) != library["sha256"]:
            raise ValueError("System CUDA library identity differs from pinned lab specification")
        shutil.copyfile(source, servers[0].parent / library["name"])
    manifest = {"schema_version": 1, "tag": spec["tag"], "backend": spec["backend"],
                "source_commit": spec["source_commit"], "specification_sha256": file_hash(SPEC),
                "archives": spec["archives"], "server": servers[0].relative_to(extracted).as_posix(),
                "system_libraries": spec.get("system_libraries", []),
                "files": {p.relative_to(extracted).as_posix(): file_hash(p)
                          for p in sorted(extracted.rglob("*")) if p.is_file()}}
    write_json(extracted / "runtime_manifest.json", manifest)
    extracted.rename(directory)
    server, verified = verify_cuda_runtime()
    identity = ROOT / "data/manifests/phase11_gpu_generation_manifest.json"
    value = {"schema_version": 1, "purpose": "phase11-ubuntu-cuda-candidate",
             "model": model_identity(), "runtime": verified}
    if identity.exists() and read_json(identity) != value:
        raise ValueError("Preserve the previous GPU identity")
    if not identity.exists():
        write_json(identity, value)
    return server, verified
