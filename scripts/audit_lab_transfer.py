"""Read-only transfer/hash audit; Evaluation is hashed, never parsed for tuning."""

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.retrieval.common import file_hash, read_json, write_json  # noqa: E402


def audit(root):
    checks = []
    cache = {}

    def check(path, sha, source):
        path = Path(path)
        if not path.is_absolute():
            path = root / path
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Audit path escapes repository")
        name = path.relative_to(root).as_posix()
        if name not in cache:
            cache[name] = file_hash(path) if path.is_file() else None
        actual = cache[name]
        checks.append({"path": name, "manifest": source, "expected_sha256": sha,
                       "actual_sha256": actual,
                       "status": "missing" if actual is None else "ok" if actual == sha else "mismatch"})

    manifests = root / "data/manifests"
    source = read_json(manifests / "clapnq_source_manifest.json")
    for entry in source["files"]:
        check(Path(source["dataset"]["checkout_layout"]) / entry["relative_path"],
              entry["sha256"], "clapnq_source_manifest.json")
    split = read_json(manifests / "clapnq_split_manifest.json")
    for name, entry in split["outputs"].items():
        check(Path("data/processed/clapnq") / split["dataset_version"] / name,
              entry["sha256"], "clapnq_split_manifest.json")
    retrieval = read_json(manifests / "clapnq_retrieval_manifest.json")
    check("data/processed/clapnq/c508d78-base-v1/passages.jsonl", retrieval["corpus"]["sha256"],
          "clapnq_retrieval_manifest.json")
    check("data/processed/clapnq/c508d78-base-v1/qa.jsonl", retrieval["gold_coverage"]["qa_sha256"],
          "clapnq_retrieval_manifest.json")
    for kind, index in retrieval["indexes"].items():
        directory = Path("data/indexes/clapnq") / retrieval["index_version"] / kind
        check(directory / "manifest.json", index["manifest_sha256"], "clapnq_retrieval_manifest.json")
        for name, entry in index["files"].items():
            check(directory / name, entry["sha256"], "clapnq_retrieval_manifest.json")

    def walk(value, source):
        if isinstance(value, dict):
            for key, item in value.items():
                if (key.startswith("data/runs/") and isinstance(item, str) and len(item) == 64
                        and all(c in "0123456789abcdef" for c in item)):
                    check(key, item, source)
                walk(item, source)
        elif isinstance(value, list):
            for item in value:
                walk(item, source)

    for path in sorted(manifests.glob("*.json")):
        walk(read_json(path), path.name)
    # Local inventory also preserves unmanifested failure/log files for subsequent comparisons.
    inventory = {p.relative_to(root).as_posix(): file_hash(p)
                 for folder in ("raw", "processed", "indexes", "runs")
                 for p in sorted((root / "data" / folder).rglob("*")) if p.is_file()}
    issues = [c for c in checks if c["status"] != "ok"]
    return {"purpose": "lab-transfer-audit-not-calibration", "schema_version": 1,
            "recorded_at_utc": datetime.now(UTC).isoformat(),
            "checks": checks, "summary": dict(Counter(c["status"] for c in checks)),
            "unique_checked_paths": len(cache), "issues": issues,
            "requires_source_PC_transfer": sorted({c["path"] for c in issues
                                                   if c["path"].startswith("data/runs/")}),
            "reacquirable_or_regenerable": sorted({c["path"] for c in issues
                                                   if not c["path"].startswith("data/runs/")}),
            "inventory_sha256": inventory, "evaluation_content_parsed": False,
            "note": "Unmanifested files have only a local baseline hash, not a source-PC comparison."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or not args.output.resolve().is_relative_to(ROOT / "data/runs/lab"):
        raise ValueError("Choose a new audit output under data/runs/lab")
    report = audit(ROOT)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, report)
    print(json.dumps({k: report[k] for k in ("summary", "unique_checked_paths", "issues")}, indent=2))
