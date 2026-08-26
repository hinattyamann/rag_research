"""Load CLAPNQ annotations and print a normalization summary."""

import argparse
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_research.data.clapnq_acquisition import DEFAULT_RAW_ROOT  # noqa: E402
from rag_research.data.clapnq_annotations import load_clapnq_annotations  # noqa: E402
from rag_research.data.clapnq_source import CLAPNQ_REVISION  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CLAPNQ AnnotationをLoadし、Reference正規化結果を確認します。"
    )
    parser.add_argument(
        "--checkout",
        type=Path,
        default=DEFAULT_RAW_ROOT / CLAPNQ_REVISION,
        help="固定RevisionをCheckoutしたDirectory",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_clapnq_annotations(args.checkout)
    partitions = Counter((record.source_split, record.is_answerable) for record in records)
    valid_references = sum(len(record.references) for record in records)

    print(f"Checkout: {args.checkout.resolve()}")
    print(f"Records: {len(records)}")
    print(f"Train Answerable: {partitions[('train', True)]}")
    print(f"Train Unanswerable: {partitions[('train', False)]}")
    print(f"Dev Answerable: {partitions[('dev', True)]}")
    print(f"Dev Unanswerable: {partitions[('dev', False)]}")
    print(f"Valid references: {valid_references}")


if __name__ == "__main__":
    main()

