"""Load CLAPNQ annotations and print a normalization summary."""

import argparse
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_research.data.clapnq_acquisition import DEFAULT_RAW_ROOT  # noqa: E402
from rag_research.data.clapnq_queries import load_and_link_clapnq  # noqa: E402
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
    pairs = load_and_link_clapnq(args.checkout)
    records = [pair.annotation for pair in pairs]
    partitions = Counter((record.source_split, record.is_answerable) for record in records)
    valid_references = sum(len(record.references) for record in records)
    gold_assignments = sum(len(pair.gold_passage_ids) for pair in pairs)
    unique_gold_ids = {gold_id for pair in pairs for gold_id in pair.gold_passage_ids}
    multiline_query_answers = sum(
        "\n" in pair.retrieval_query.raw_row["answers"]
        or "\r" in pair.retrieval_query.raw_row["answers"]
        for pair in pairs
    )

    print(f"Checkout: {args.checkout.resolve()}")
    print(f"Records: {len(records)}")
    print(f"Linked queries: {len(pairs)}")
    print(f"Train Answerable: {partitions[('train', True)]}")
    print(f"Train Unanswerable: {partitions[('train', False)]}")
    print(f"Dev Answerable: {partitions[('dev', True)]}")
    print(f"Dev Unanswerable: {partitions[('dev', False)]}")
    print(f"Valid references: {valid_references}")
    print(f"Gold Passage assignments: {gold_assignments}")
    print(f"Unique Gold Passage IDs: {len(unique_gold_ids)}")
    print(f"Multiline Query answers: {multiline_query_answers}")


if __name__ == "__main__":
    main()
