"""Freeze title-disjoint CLAPNQ research splits from the Phase 2 base QA."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_research.data.clapnq_split import (  # noqa: E402
    DEFAULT_BASE_QA_PATH,
    DEFAULT_SPLIT_MANIFEST_PATH,
    SPLIT_DATASET_VERSION,
    SPLIT_NAMES,
    SPLIT_SEED,
    SplitValidationError,
    generate_research_split,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLAPNQをTitle単位で65%/10%/25%に分割・固定します。"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_BASE_QA_PATH)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_SPLIT_MANIFEST_PATH)
    parser.add_argument("--seed", type=int, default=SPLIT_SEED)
    parser.add_argument("--dataset-version", default=SPLIT_DATASET_VERSION)
    args = parser.parse_args()
    try:
        manifest = generate_research_split(
            args.input,
            args.output_dir,
            args.manifest,
            seed=args.seed,
            dataset_version=args.dataset_version,
        )
    except (OSError, SplitValidationError) as error:
        parser.exit(1, f"Split failed: {error}\n")
    print(f"Dataset version: {manifest['dataset_version']}")
    print(f"Algorithm: {manifest['algorithm_version']}; seed: {manifest['seed']}")
    for name in SPLIT_NAMES:
        stats = manifest["splits"][name]
        print(
            f"{name}: {stats['record_count']} QA ({stats['record_ratio']:.2%}), "
            f"answerable/unanswerable={stats['answerable_count']}/{stats['unanswerable_count']}, "
            f"titles/groups={stats['title_count']}/{stats['group_count']}"
        )
    print(f"Title overlap: {manifest['validation']['title_overlap_count']}")
    print(f"QA SHA-256: {manifest['outputs']['qa.jsonl']['sha256']}")
    print(f"Manifest: {args.manifest.resolve()}")


if __name__ == "__main__":
    main()
