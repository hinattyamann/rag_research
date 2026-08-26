"""Build deterministic CLAPNQ retrieval Document JSONL."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_research.data.clapnq_acquisition import DEFAULT_RAW_ROOT  # noqa: E402
from rag_research.data.clapnq_corpus import (  # noqa: E402
    iter_clapnq_corpus,
    write_corpus_jsonl,
)
from rag_research.data.clapnq_records import (  # noqa: E402
    CLAPNQ_BASE_DATASET_VERSION,
    DEFAULT_PROCESSED_ROOT,
    load_clapnq_qa_records,
)
from rag_research.data.clapnq_source import CLAPNQ_REVISION  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="固定CLAPNQ Corpusを内部Document SchemaのJSONLへ変換します。"
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
            DEFAULT_PROCESSED_ROOT
            / CLAPNQ_BASE_DATASET_VERSION
            / "passages.jsonl"
        ),
        help="生成する内部Retrieval Document JSONL",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    qa_records = load_clapnq_qa_records(args.checkout)
    gold_passage_ids = {
        gold_id for record in qa_records for gold_id in record.gold_passage_ids
    }
    documents = iter_clapnq_corpus(args.checkout)
    summary = write_corpus_jsonl(
        documents,
        args.output,
        expected_gold_passage_ids=gold_passage_ids,
    )

    print(f"Output: {summary.output_path.resolve()}")
    print(f"Dataset version: {CLAPNQ_BASE_DATASET_VERSION}")
    print(f"Passage records: {summary.record_count}")
    print(f"Unique titles: {summary.unique_title_count}")
    print(
        "Verified unique Gold Passage IDs: "
        f"{summary.verified_gold_passage_id_count}"
    )
    print(f"Bytes: {summary.byte_count}")
    print(f"SHA-256: {summary.sha256}")


if __name__ == "__main__":
    main()
