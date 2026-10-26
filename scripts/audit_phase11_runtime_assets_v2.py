"""Preserve existing runs and stream-check pinned Phase 11 assets without inference."""

import argparse
import fcntl
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.generation.artifacts import (  # noqa: E402
    MODEL_BYTES,
    MODEL_DIR,
    MODEL_FILE,
    MODEL_SHA256,
)
from rag_research.retrieval.common import file_hash, read_json, write_json  # noqa: E402


def audit(root, output, host_proof=None):
    if output.exists() or not output.resolve().is_relative_to(root / "data/runs/lab"):
        raise ValueError("Choose a new audit directory under data/runs/lab")
    # Take this inventory before creating the destination, so its own snapshot is excluded.
    old_files = sorted(p for p in (root / "data/runs").rglob("*") if p.is_file())
    output.mkdir(parents=True)
    cache, checks, sources = {}, [], {}

    def check(path, expected, source, expected_bytes=None):
        path = Path(path)
        if not path.is_absolute():
            path = root / path
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Audit input escapes repository: {path}")
        name = path.relative_to(root).as_posix()
        if name not in cache:
            cache[name] = file_hash(path) if path.is_file() else None
        actual = cache[name]
        size = path.stat().st_size if path.is_file() else None
        status = ("missing" if actual is None else "ok"
                  if actual == expected and (expected_bytes is None or size == expected_bytes)
                  else "mismatch")
        checks.append({"path": name, "source": source, "expected_sha256": expected,
                       "actual_sha256": actual, "bytes": size, "status": status})

    def walk(value, source):
        if isinstance(value, dict):
            if (isinstance(value.get("path"), str) and value["path"].startswith("data/")
                    and isinstance(value.get("sha256"), str)):
                check(value["path"], value["sha256"], source, value.get("bytes"))
            for key, item in value.items():
                if isinstance(key, str) and key.startswith("data/"):
                    digest = item.get("sha256") if isinstance(item, dict) else item
                    if (isinstance(digest, str) and len(digest) == 64
                            and all(c in "0123456789abcdef" for c in digest)):
                        check(key, digest, source)
                walk(item, source)
        elif isinstance(value, list):
            for item in value:
                walk(item, source)

    for manifest in sorted((root / "data/manifests").glob("*.json")):
        sources[manifest.relative_to(root).as_posix()] = file_hash(manifest)
        walk(read_json(manifest), manifest.relative_to(root).as_posix())

    assets = read_json(root / "configs/phase11_bilingual_assets_v2.json")
    walk(assets, "configs/phase11_bilingual_assets_v2.json")
    for dataset in assets["datasets"].values():
        for entry in dataset["indexes"].values():
            manifest = root / entry["path"]
            data = read_json(manifest)
            for name, detail in data["files"].items():
                check(manifest.parent / name, detail["sha256"], entry["path"],
                      detail.get("bytes"))
            if "embedding" in manifest.parts:
                model = data["config"]["model"]
                model_dir = root / assets["embedding"]["model_root"] / model["revision"]
                for name, detail in model["files"].items():
                    check(model_dir / name, detail["sha256"], entry["path"],
                          detail.get("bytes"))
    check(MODEL_DIR / MODEL_FILE, MODEL_SHA256, "generation.artifacts baseline identity", MODEL_BYTES)
    runtime_spec = read_json(root / "configs/lab_cuda_runtime.json")
    runtime_dir = root / runtime_spec["directory"]
    runtime = read_json(runtime_dir / "runtime_manifest.json")
    for name, digest in runtime["files"].items():
        check(runtime_dir / name, digest, "old-runtime-manifest")

    inventory, lock_checks = {}, []
    preserved = output / "previous-runs"
    for path in old_files:
        name = path.relative_to(root).as_posix()
        digest = cache.get(name) or file_hash(path)
        inventory[name] = {"sha256": digest, "bytes": path.stat().st_size}
        destination = preserved / path.relative_to(root / "data/runs")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        if file_hash(destination) != digest or file_hash(path) != digest:
            raise ValueError(f"Run changed during preservation: {name}")
        if path.name == ".run.lock":
            with path.open("rb") as stream:
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(stream, fcntl.LOCK_UN)
                    held = False
                except BlockingIOError:
                    held = True
            lock_checks.append({"path": name, "held": held,
                                "content": path.read_text(errors="replace")})
    write_json(output / "old-run-inventory.json", inventory)
    write_json(output / "manifest-comparisons.json", checks)
    write_json(output / "lock-checks.json", lock_checks)
    latest = "data/manifests/phase11_known_trace_result_v10.json"
    v10_checks = [c for c in checks if c["source"] == latest]
    payload_checks = [c for c in checks if c["source"].startswith("data/indexes/")]
    active = [c for c in checks if c["source"] in {
        "configs/phase11_bilingual_assets_v2.json", "old-runtime-manifest",
        "generation.artifacts baseline identity",
        "data/manifests/phase11_auxiliary_qwen35_9b_q6_manifest_v1.json"}]
    report = {
        "schema_version": 2, "purpose": "phase11-zero-completion-preservation-and-asset-audit",
        "recorded_at_jst": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                                text=True).strip(),
        "completion_calls": 0, "server_starts": 0,
        "evaluation_body_parsed": False, "evaluation_files_hashed_only": True,
        "historical_manifests": sources,
        "all_manifest_comparisons": dict(Counter(c["status"] for c in checks)),
        "historical_note": "Earlier running snapshots may differ from terminal mutable logs; "
        "all differences are preserved, never repaired or regenerated.",
        "historical_issues": [c for c in checks if c["status"] != "ok"],
        "v10_comparisons": dict(Counter(c["status"] for c in v10_checks)),
        "active_assets_comparisons": dict(Counter(c["status"] for c in active)),
        "index_and_embedding_payload_comparisons":
            dict(Counter(c["status"] for c in payload_checks)),
        "old_runs": {"files": len(inventory), "bytes": sum(v["bytes"] for v in inventory.values()),
                     "inventory_sha256": file_hash(output / "old-run-inventory.json"),
                     "copy_path": preserved.relative_to(root).as_posix(),
                     "all_copies_and_originals_match": True},
        "lock_files": len(lock_checks), "held_locks": [v for v in lock_checks if v["held"]],
        "process_scope_note": "Do not infer host process absence from a sandbox PID namespace.",
        "host_process_proof": ({"path": host_proof.relative_to(root).as_posix(),
                                "sha256": file_hash(host_proof)} if host_proof else None),
        "old_budget": read_json(root /
            "data/runs/development_screening/phase11-review-budget-recovery-v1/ledger.json"),
        "old_cumulative_trials": 909, "old_unknown_responses": 3,
        "old_unused_calls_preserved": {"review_v1": 130, "v9": 69,
                                       "earlier_runs": [42, 42, 81, 42]},
        "phase12_allowed": False, "gate11_passed": False,
        "inputs_available": bool(v10_checks) and all(c["status"] == "ok"
            for c in v10_checks + active + payload_checks) and not any(v["held"] for v in lock_checks),
    }
    write_json(output / "report.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--host-proof", type=Path)
    args = parser.parse_args()
    result = audit(ROOT, args.output.resolve(), args.host_proof.resolve() if args.host_proof else None)
    print(json.dumps({k: result[k] for k in (
        "inputs_available", "all_manifest_comparisons", "v10_comparisons",
        "active_assets_comparisons", "index_and_embedding_payload_comparisons", "old_runs",
        "held_locks")}, ensure_ascii=False, indent=2))
