"""Build deterministic CLAPNQ base QA JSONL in the internal schema."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_research.data.clapnq_acquisition import DEFAULT_RAW_ROOT  # noqa: E402
from rag_research.data.clapnq_records import (  # noqa: E402
    CLAPNQ_BASE_DATASET_VERSION,
    DEFAULT_PROCESSED_ROOT,
    load_clapnq_qa_records,
    write_qa_records_jsonl,
)
from rag_research.data.clapnq_source import CLAPNQ_REVISION  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="固定CLAPNQを最終内部QA SchemaのJSONLへ変換します。"
    )
    parser.add_argument(
        "--checkout",
        type=Path,
        default=DEFAULT_RAW_ROOT / CLAPNQ_REVISION,
        help="固定RevisionをCheckoutしたDirectory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            DEFAULT_PROCESSED_ROOT / CLAPNQ_BASE_DATASET_VERSION / "qa.jsonl"
        ),
        help="生成する内部QA JSONL",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_clapnq_qa_records(args.checkout)
    summary = write_qa_records_jsonl(records, args.output)

    answerable_count = sum(record.is_answerable for record in records)
    provided_count = sum(record.provided_passage is not None for record in records)
    print(f"Output: {summary.output_path.resolve()}")
    print(f"Dataset version: {CLAPNQ_BASE_DATASET_VERSION}")
    print(f"Records: {summary.record_count}")
    print(f"Answerable with Gold Passage: {answerable_count}")
    print(f"Unanswerable with Provided Passage: {provided_count}")
    print(f"Bytes: {summary.byte_count}")
    print(f"SHA-256: {summary.sha256}")


if __name__ == "__main__":
    main()
