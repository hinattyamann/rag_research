"""Export a blinded manual-quality form or import researcher-completed JSON."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.quality import export_quality, import_quality  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export")
    export.add_argument("--run-dir", type=Path, required=True)
    export.add_argument("--output-dir", type=Path, required=True)
    load = sub.add_parser("import")
    load.add_argument("--run-dir", type=Path, required=True)
    load.add_argument("--bundle-dir", type=Path, required=True)
    load.add_argument("--annotations", type=Path, required=True)
    args = parser.parse_args()
    result = (export_quality(args.run_dir, args.output_dir) if args.command == "export" else
              import_quality(args.run_dir, args.bundle_dir, args.annotations))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
