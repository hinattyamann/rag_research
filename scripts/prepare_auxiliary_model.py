"""Download a pinned official 7B candidate for Development Judge/rewrite diagnostics."""

import os
import sys
import time
import urllib.request
from pathlib import Path

from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.storage import read_json, write_json  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402

REPOSITORY = "Qwen/Qwen2.5-7B-Instruct-GGUF"
REVISION = "bb5d59e06d9551d752d08b292a50eb208b07ab1f"
FILES = [
    ("qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf", 3993201344,
     "dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db"),
    ("qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf", 689872288,
     "539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a"),
]


def download_gguf(folder, name, size, sha):
    path = folder / name
    if path.exists():
        require(path.stat().st_size == size and file_hash(path) == sha, "Existing model differs")
        return path
    temporary = path.with_suffix(".gguf.partial")
    offset = temporary.stat().st_size if temporary.exists() else 0
    require(offset <= size, "Partial download exceeds official size")
    if offset < size:
        # A cache-busting query avoids stale signed redirects; the commit stays pinned.
        url = (f"https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{name}"
               f"?download=true&transfer={time.time_ns()}")
        request = urllib.request.Request(url, headers={"Range": f"bytes={offset}-",
                                                       "User-Agent": "rag-research"})
        with urllib.request.urlopen(request, timeout=90) as source:
            content_range = source.headers.get("Content-Range", "")
            require(source.status == 206 and content_range.startswith(f"bytes {offset}-") and
                    content_range.endswith(f"/{size}"), "Unexpected range response")
            progress = offset
            next_notice = offset + 64 * 1024 * 1024
            with temporary.open("ab") as target:
                while block := source.read(4 * 1024 * 1024):
                    target.write(block)
                    progress += len(block)
                    if progress >= next_notice:
                        print(f"Downloaded {progress}/{size} bytes", flush=True)
                        next_notice = progress + 64 * 1024 * 1024
                target.flush()
                os.fsync(target.fileno())
    require(temporary.stat().st_size == size and file_hash(temporary) == sha, "Official model hash mismatch")
    temporary.replace(path)
    return path


def main():
    folder = ROOT / "data/models/Qwen2.5-7B-Instruct-GGUF" / REVISION
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for name, size, sha in FILES:
        print(f"Preparing {name} ({size} bytes)", flush=True)
        path = download_gguf(folder, name, size, sha)
        require(path.stat().st_size == size and file_hash(path) == sha, "Official model hash mismatch")
        files.append({"path": path.relative_to(ROOT).as_posix(), "bytes": size, "sha256": sha})
    for name in ("README.md", "LICENSE"):
        hf_hub_download(REPOSITORY, name, revision=REVISION, local_dir=folder, token=False)
    manifest = {"schema_version": 1, "purpose": "development-auxiliary-model",
                "model_id": REPOSITORY, "revision": REVISION, "quantization": "Q4_K_M",
                "license": "Apache-2.0", "source": f"https://huggingface.co/{REPOSITORY}/tree/{REVISION}",
                "entrypoint": files[0]["path"], "files": files}
    target = ROOT / "data/manifests/phase10_auxiliary_model_manifest.json"
    if target.exists():
        require(read_json(target) == manifest, "Existing auxiliary manifest differs")
    else:
        write_json(target, manifest)
    print("Pinned auxiliary candidate ready; baseline model unchanged", flush=True)


if __name__ == "__main__":
    main()
