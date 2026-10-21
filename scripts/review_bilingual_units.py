"""Export blind source-only units, or compare after both language label sets are sealed."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.bilingual_semantics import (  # noqa: E402
    analyze_semantics,
    export_units,
)
from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.storage import read_json, write_json  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("--quality-bundle", type=Path, required=True)
    export.add_argument("--output-dir", type=Path, required=True)
    export.add_argument("--language", choices=("en", "ja"), required=True)
    analyze = commands.add_parser("analyze")
    analyze.add_argument("--inputs", type=Path, required=True)
    analyze.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "export":
        print(json.dumps(export_units(args.quality_bundle, args.output_dir, args.language), ensure_ascii=False))
    else:
        output = args.output.resolve()
        require(output.is_relative_to(ROOT / "data/runs/bilingual_development") and not output.exists(),
                "Preserve old semantic results; use a new Development output")
        result = analyze_semantics(read_json(args.inputs))
        output.parent.mkdir(parents=True, exist_ok=True)
        write_json(output, result)
        print(json.dumps({k: result[k] for k in ("languages", "main_development_semantic_gate_passed", "gate11_passed")}, ensure_ascii=False))
