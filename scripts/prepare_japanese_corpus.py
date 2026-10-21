"""Prepare and acquire a fixed historical Japanese Wikipedia corpus, without inference."""

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.data.baobab_source import (  # noqa: E402
    DATASET_ID,
    REVISION,
    SOURCE_FILES,
    article_titles,
    download_source,
    load_source,
)
from rag_research.data.wikipedia_snapshot import (  # noqa: E402
    MediaWikiClient,
    fetch_article,
    validate_spec,
)
from rag_research.experiments.frozen_trace import digest, require  # noqa: E402
from rag_research.experiments.storage import (  # noqa: E402
    checkpoint,
    read_json,
    run_lock,
    verify_checkpoint,
)
from rag_research.retrieval.common import file_hash  # noqa: E402


def prepare(source_dir, output, spec_path):
    spec = read_json(spec_path)
    validate_spec(spec)
    require(spec["dataset_id"] == DATASET_ID and spec["source_revision"] == REVISION,
            "Japanese source differs from selected release")
    require(spec["article_selection"] == "all_page_titles_in_answered_and_unsuccessful_human_search_logs"
            and spec["per_question_gold_injection"] is False, "Source corpus selection changed")
    chunks = load_source(source_dir)
    source_paths = [Path(__file__), ROOT / "src/rag_research/data/baobab_source.py",
                    ROOT / "src/rag_research/data/wikipedia_snapshot.py", spec_path]
    plan = {"schema_version": 1, "purpose": "phase11-historical-japanese-corpus-plan",
            "source_dataset": DATASET_ID, "source_revision": REVISION, "spec": spec,
            "source_files_sha256": SOURCE_FILES, "titles": article_titles(chunks),
            "source_code_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in source_paths},
            "model_calls": 0, "phase12_allowed": False}
    require(bool(plan["titles"]), "Japanese corpus has no source article titles")
    output.mkdir(parents=True, exist_ok=True)
    path = output / "plan.json"
    if path.exists():
        saved = read_json(path)
        verify_checkpoint(saved)
        require(digest(plan) == digest({k: v for k, v in saved.items() if k != "result_sha256"}),
                "Japanese corpus plan/source code changed; use a new version")
        for name, expected in saved["source_code_sha256"].items():
            require(file_hash(output / "source_snapshot" / name) == expected,
                    "Archived acquisition source changed/missing")
        return saved
    saved = checkpoint(path, plan)
    # Preserve the executable source alongside provenance before any HTTP request.
    for path in source_paths:
        destination = output / "source_snapshot" / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    checkpoint(output / "execution.json", {
        "purpose": "source-acquisition-execution-not-model-experiment", "plan_sha256": digest(saved),
        "repository_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                     text=True).strip(),
        "started_at_utc": datetime.now(UTC).isoformat(), "model_calls": 0})
    return saved


def acquire(plan, output, maximum_new=None):
    spec = plan["spec"]
    client = MediaWikiClient(spec)
    results = []
    new = 0
    network_failures = 0
    stopped = False
    for title in plan["titles"]:
        requests_before = client.network_requests
        row = fetch_article(client, spec, title, output, digest(plan))
        results.append(row)
        if client.network_requests > requests_before:
            new += 1
            network_failures = network_failures + 1 if row["status"] == "error" else 0
            if new % 10 == 0:
                print(json.dumps({"articles_seen": len(results), "new_articles": new,
                                  "statuses": dict(Counter(r["status"] for r in results)),
                                  "network_requests": client.network_requests}), flush=True)
        if network_failures >= spec["maximum_consecutive_network_failures"]:
            stopped = True
            break
        if maximum_new is not None and new >= maximum_new:
            break
    status = "finished" if len(results) == len(plan["titles"]) else "stopped" if stopped else "partial"
    summary = {"schema_version": 1, "purpose": "historical-japanese-corpus-acquisition-progress",
               "plan_sha256": digest(plan), "status": status,
               "recorded_at_utc": datetime.now(UTC).isoformat(), "expected_articles": len(plan["titles"]),
               "articles_seen_this_session": len(results), "statuses": dict(Counter(r["status"] for r in results)),
               "new_articles_this_session": new, "network_requests_this_session": client.network_requests,
               "model_calls": 0, "phase12_allowed": False}
    session = len(list(output.glob("progress-*.json"))) + 1
    checkpoint(output / f"progress-{session:03d}.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["plan", "fetch"])
    parser.add_argument("--source-dir", type=Path,
                        default=ROOT / "data/raw/wikipedia_human_retrieval_ja" / f"source-{REVISION}")
    parser.add_argument("--download-source", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/phase11_japanese_corpus_v1.json")
    parser.add_argument("--max-new-articles", type=int)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    require(output.is_relative_to(ROOT / "data/raw/wikipedia_human_retrieval_ja"),
            "Choose a new version under data/raw/wikipedia_human_retrieval_ja")
    require(args.config.resolve().is_relative_to(ROOT), "Config escapes repository")
    require(args.max_new_articles is None or args.max_new_articles > 0, "Invalid acquisition limit")
    with run_lock(output):
        if args.download_source:
            require(args.source_dir.resolve().is_relative_to(ROOT / "data/raw/wikipedia_human_retrieval_ja"),
                    "Download source into the Japanese raw data directory")
            download_source(args.source_dir.resolve())
        plan = prepare(args.source_dir.resolve(), output, args.config.resolve())
        result = ({"planned_articles": len(plan["titles"]), "model_calls": 0}
                  if args.stage == "plan" else acquire(plan, output, args.max_new_articles))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
