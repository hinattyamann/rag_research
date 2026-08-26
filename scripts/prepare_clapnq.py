"""Acquire CLAPNQ at the revision fixed by the research specification."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_research.data.clapnq_acquisition import (  # noqa: E402
    DEFAULT_RAW_ROOT,
    acquire_clapnq,
)
from rag_research.data.clapnq_source import (  # noqa: E402
    CLAPNQ_REPOSITORY_URL,
    CLAPNQ_REVISION,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CLAPNQを研究仕様で固定したCommitから安全に取得します。"
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=DEFAULT_RAW_ROOT,
        help=f"Revision別Directoryを作成する場所（Default: {DEFAULT_RAW_ROOT}）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(f"Repository: {CLAPNQ_REPOSITORY_URL}")
    print(f"Revision:   {CLAPNQ_REVISION}")
    print(f"Raw root:   {args.raw_root.resolve()}")

    result = acquire_clapnq(args.raw_root, progress=print)
    action = "既存Dataを検証して再利用" if result.reused_existing else "新規取得"
    print(f"完了: {action}")
    print(f"取得先: {result.checkout_path}")


if __name__ == "__main__":
    main()
