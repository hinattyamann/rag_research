"""Generate the validated CLAPNQ source manifest."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_research.data.clapnq_acquisition import DEFAULT_RAW_ROOT  # noqa: E402
from rag_research.data.clapnq_manifest import (  # noqa: E402
    DEFAULT_MANIFEST_PATH,
    generate_source_manifest,
)
from rag_research.data.clapnq_source import CLAPNQ_REVISION  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="取得済みCLAPNQを検証し、Source Manifestを生成します。"
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
        default=DEFAULT_MANIFEST_PATH,
        help=f"Manifest出力先（Default: {DEFAULT_MANIFEST_PATH}）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(f"Checkout: {args.checkout.resolve()}")
    print(f"Output:   {args.output.resolve()}")
    print("Hash、件数、Schema、Gold Passage対応を検証しています。")
    manifest = generate_source_manifest(args.checkout, args.output)
    validation = manifest["validation"]
    print(f"完了: 必須File {validation['required_file_count']}件")
    print(f"Annotation: {validation['annotation_record_count']}件")
    print(f"Corpus: {validation['corpus_passage_count']}件")
    print(f"Manifest: {args.output.resolve()}")


if __name__ == "__main__":
    main()

