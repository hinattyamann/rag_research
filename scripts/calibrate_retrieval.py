"""Run the predeclared Phase 6 search grid, then freeze its selected conditions."""

import argparse
import json
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.retrieval.calibration import (  # noqa: E402
    CALIBRATION_PATH,
    SPLIT_MANIFEST,
    evaluate_grid,
    frozen_bytes,
    frozen_json,
    load_calibration,
    load_protocol,
    select_condition,
)
from rag_research.retrieval.common import (  # noqa: E402
    ResourceMonitor,
    file_hash,
    read_json,
    write_json,
)
from rag_research.retrieval.factory import (  # noqa: E402
    CALIBRATION_PROTOCOL,
    CALIBRATION_REPORT,
    COMMON_MANIFEST,
    HYBRID_MANIFEST,
    load_indexes,
)
from rag_research.retrieval.hybrid import HybridRetriever  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="CalibrationだけでHybrid検索条件を固定")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    protocol = load_protocol(CALIBRATION_PROTOCOL)
    split = read_json(SPLIT_MANIFEST)
    rows, excluded = load_calibration(CALIBRATION_PATH, split)
    output = args.output_dir or Path("data/runs/phase6/calibration") / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    )
    output.mkdir(parents=True, exist_ok=False)
    status = {
        "status": "running",
        "purpose": "calibration-not-final-evaluation",
        "protocol_sha256": file_hash(CALIBRATION_PROTOCOL),
        "sample_count": len(rows),
        "excluded_unanswerable": excluded,
    }
    write_json(output / "run_status.json", status)
    print(f"Calibration run: {output}", flush=True)
    try:
        with ResourceMonitor() as monitor:
            bm25, embedding = load_indexes()
            started = time.perf_counter()
            result = evaluate_grid(
                rows,
                bm25,
                embedding,
                protocol,
                progress=lambda count, total: print(f"Grid search: {count}/{total}", flush=True),
            )
            grid_seconds = time.perf_counter() - started
            selection = select_condition(result["grid"], protocol)
            print(f"Selected: {json.dumps(selection)}", flush=True)
            retriever = HybridRetriever(
                bm25,
                embedding,
                candidate_count=selection["candidate_count"],
                rrf_constant=selection["rrf_constant"],
            )
            timings = []
            condition = f"{selection['candidate_count']}:{selection['rrf_constant']}"
            for index, (row, query) in enumerate(zip(rows, result["queries"], strict=True), 1):
                started = time.perf_counter()
                hits = retriever.search(row["question"], top_k=selection["top_k"])
                elapsed = time.perf_counter() - started
                if [hit.passage_id for hit in hits] != query["hybrid_top_10"][condition][
                    : selection["top_k"]
                ]:
                    raise RuntimeError("Live Hybrid search differs from cached-grid selection")
                timings.append(
                    {
                        "record_id": row["record_id"],
                        "seconds": elapsed,
                        **retriever.last_search_details,
                    }
                )
                if index % 25 == 0 or index == len(rows):
                    print(f"Live selected search: {index}/{len(rows)}", flush=True)
        write_json(output / "query_rankings.json", result["queries"])
        write_json(
            output / "measurements.json",
            {
                **monitor.report(),
                "grid_seconds_with_reused_candidates": grid_seconds,
                "live_timing_scope": "warm-process-no-result-cache-index-and-model-load-excluded",
                "latency_p50_seconds": float(np.percentile([r["seconds"] for r in timings], 50)),
                "latency_p95_seconds": float(np.percentile([r["seconds"] for r in timings], 95)),
                "live_selected_reproducibility_matches": len(timings),
                "queries": timings,
            },
        )
        report = {
            "schema_version": 1,
            "purpose": "calibration-not-final-evaluation",
            "split": "calibration",
            "qa_sha256": file_hash(CALIBRATION_PATH),
            "split_manifest_sha256": file_hash(SPLIT_MANIFEST),
            "sample_count": len(rows),
            "excluded_unanswerable": excluded,
            "record_ids": [row["record_id"] for row in rows],
            "protocol": protocol,
            "protocol_sha256": file_hash(CALIBRATION_PROTOCOL),
            "standalone": result["standalone"],
            "grid": result["grid"],
            "selection": selection,
            "retriever": retriever.manifest,
            "live_selected_reproducibility_matches": len(timings),
            "calibration_implementation_sha256": {
                str(path): file_hash(path)
                for path in (Path(__file__), Path("src/rag_research/retrieval/calibration.py"))
            },
        }
        frozen_json(CALIBRATION_REPORT, report)
        manifest = {
            "schema_version": 1,
            "purpose": "phase6-fixed-hybrid-retriever",
            "selection": selection,
            "retriever": retriever.manifest,
            "common_manifest_sha256": file_hash(COMMON_MANIFEST),
            "protocol_sha256": file_hash(CALIBRATION_PROTOCOL),
            "calibration_report_sha256": file_hash(CALIBRATION_REPORT),
            "hybrid_implementation_sha256": file_hash(Path("src/rag_research/retrieval/hybrid.py")),
        }
        frozen_json(HYBRID_MANIFEST, manifest)
        config = read_phase5_with_hybrid(selection)
        frozen_bytes(
            Path("configs/phase6.yaml"),
            yaml.safe_dump(config, sort_keys=False, allow_unicode=True).encode("utf-8"),
        )
        status["status"] = "completed"
        status["selection"] = selection
        print(
            json.dumps(
                {
                    "selection": selection,
                    "standalone": result["standalone"],
                    "calibration_report": str(CALIBRATION_REPORT),
                    "hybrid_manifest": str(HYBRID_MANIFEST),
                },
                ensure_ascii=False,
                indent=2,
            ),
            flush=True,
        )
    except Exception as error:
        status["status"] = "failed"
        status["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        write_json(output / "run_status.json", status)


def read_phase5_with_hybrid(selection):
    config = yaml.safe_load(Path("configs/phase5.yaml").read_text(encoding="utf-8"))
    config["purpose"] = "phase6-hybrid-baseline"
    config["retrieval"] = selection
    return config


if __name__ == "__main__":
    main()
