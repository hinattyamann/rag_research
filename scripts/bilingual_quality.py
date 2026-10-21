"""Export blind bilingual candidates or import all sealed labels before route disclosure."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.experiments.bilingual_quality import export, import_annotations  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("export", "import"))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--annotations", type=Path)
    args = parser.parse_args()
    if args.stage == "import" and args.annotations is None:
        parser.error("Import requires all sealed --annotations")
    value = export(args.run, args.bundle) if args.stage == "export" else import_annotations(args.run, args.bundle, args.annotations)
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
