"""Pinned official GGUF and Windows CPU runtime, installed only in the workspace."""

import json
import platform
import urllib.request
import zipfile
from pathlib import Path

from huggingface_hub import hf_hub_download

from rag_research.retrieval.common import file_hash, read_json, write_json

MODEL_ID = "Qwen/Qwen2.5-3B-Instruct-GGUF"
MODEL_REVISION = "7dabda4d13d513e3e842b20f0d435c732f172cbe"
MODEL_FILE = "qwen2.5-3b-instruct-q4_k_m.gguf"
MODEL_SHA256 = "626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d"
MODEL_BYTES = 2104932768
RUNTIME_TAG = "b11433"
RUNTIME_ASSET = f"llama-{RUNTIME_TAG}-bin-win-cpu-x64.zip"
RUNTIME_URL = (
    f"https://github.com/ggml-org/llama.cpp/releases/download/{RUNTIME_TAG}/{RUNTIME_ASSET}"
)
RUNTIME_SHA256 = "301943380e45deae3991d42dddd03fae65c6a4963a5d882328a60208b43aa9e0"
MODEL_DIR = Path("data/models/Qwen2.5-3B-Instruct-GGUF") / MODEL_REVISION
RUNTIME_DIR = Path("data/runtimes/llama.cpp") / RUNTIME_TAG
MANIFEST_PATH = Path("data/manifests/phase5_generation_manifest.json")


def model_identity():
    return {
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "file": MODEL_FILE,
        "sha256": MODEL_SHA256,
        "bytes": MODEL_BYTES,
        "quantization": "Q4_K_M",
        "license": "qwen-research",
    }


def verify_model(directory=MODEL_DIR):
    path = directory / MODEL_FILE
    if path.stat().st_size != MODEL_BYTES or file_hash(path) != MODEL_SHA256:
        raise ValueError("Generator model size/hash mismatch")
    return path


def verify_runtime(directory=RUNTIME_DIR):
    manifest = read_json(directory / "runtime_manifest.json")
    if manifest["tag"] != RUNTIME_TAG or manifest["archive_sha256"] != RUNTIME_SHA256:
        raise ValueError("Runtime identity mismatch")
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
    if actual != set(manifest["files"]) | {"runtime_manifest.json"}:
        raise ValueError("Runtime file set mismatch")
    for name, digest in manifest["files"].items():
        if file_hash(directory / name) != digest:
            raise ValueError(f"Runtime file hash mismatch: {name}")
    server = directory / manifest["server"]
    if server.name != "llama-server.exe" or not server.is_file():
        raise ValueError("CPU server executable missing")
    return server, manifest


def prepare_model():
    if not (MODEL_DIR / MODEL_FILE).exists():
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        print("Downloading pinned Qwen GGUF (2.10 GB)...", flush=True)
        hf_hub_download(
            MODEL_ID, MODEL_FILE, revision=MODEL_REVISION, local_dir=MODEL_DIR, token=False
        )
    path = verify_model()
    for name in ("README.md", "LICENSE"):
        if not (MODEL_DIR / name).exists():
            hf_hub_download(
                MODEL_ID, name, revision=MODEL_REVISION, local_dir=MODEL_DIR, token=False
            )
    print(f"Verified model: {path}", flush=True)


def prepare_runtime():
    if platform.system() != "Windows" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise ValueError(
            "This pinned runtime is Windows x64 CPU only; record another runtime on Linux"
        )
    if (RUNTIME_DIR / "runtime_manifest.json").exists():
        verify_runtime()
        return
    stage = RUNTIME_DIR.with_name(RUNTIME_TAG + ".building")
    stage.mkdir(parents=True, exist_ok=True)
    archive = stage / RUNTIME_ASSET
    if not archive.exists():
        print(f"Downloading official runtime: {RUNTIME_TAG}", flush=True)
        request = urllib.request.Request(RUNTIME_URL, headers={"User-Agent": "rag-research"})
        with urllib.request.urlopen(request, timeout=120) as source, archive.open("wb") as target:
            while block := source.read(1024 * 1024):
                target.write(block)
    if file_hash(archive) != RUNTIME_SHA256:
        raise ValueError("Official runtime archive hash mismatch")
    extracted = stage / "extracted"
    extracted.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            destination = (extracted / member.filename).resolve()
            if not destination.is_relative_to(extracted.resolve()):
                raise ValueError("Archive path escapes runtime directory")
        source.extractall(extracted)
    servers = list(extracted.rglob("llama-server.exe"))
    if len(servers) != 1:
        raise ValueError("Expected one server in official archive")
    write_json(
        extracted / "runtime_manifest.json",
        {
            "tag": RUNTIME_TAG,
            "archive_url": RUNTIME_URL,
            "archive_sha256": RUNTIME_SHA256,
            "backend": "Windows-x64-CPU",
            "server": servers[0].relative_to(extracted).as_posix(),
            "files": {
                p.relative_to(extracted).as_posix(): file_hash(p)
                for p in sorted(extracted.rglob("*"))
                if p.is_file() and p.name != "runtime_manifest.json"
            },
        },
    )
    if RUNTIME_DIR.exists():
        raise ValueError("Refusing to overwrite runtime")
    extracted.rename(RUNTIME_DIR)
    # Keep the verified download archive as a local reproducibility artifact.
    verify_runtime()


def prepare_all():
    prepare_runtime()
    prepare_model()
    _, runtime = verify_runtime()
    manifest = {
        "schema_version": 1,
        "purpose": "phase5-development-only",
        "model": model_identity(),
        "runtime": runtime,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    if MANIFEST_PATH.exists():
        if read_json(MANIFEST_PATH) != manifest:
            raise ValueError("Existing generation manifest differs; use a new version")
    else:
        write_json(MANIFEST_PATH, manifest)
    print(json.dumps({"manifest": str(MANIFEST_PATH), "model": model_identity()}, indent=2))
