"""Bind all original Japanese QA to existing corpus parents/quotes, without filtering."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.data.japanese_evidence import prepare_dataset  # noqa: E402
from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.storage import run_lock  # noqa: E402
from rag_research.retrieval.common import file_hash, read_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups-dir", type=Path, required=True)
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/phase11_japanese_evidence_v1.json")
    args = parser.parse_args()
    output, config = args.output_dir.resolve(), args.config.resolve()
    require(output.is_relative_to(ROOT / "data/processed/wikipedia_human_retrieval_ja") and
            config.is_relative_to(ROOT), "Use a new Japanese evidence dataset and repository config")
    require(output not in {args.groups_dir.resolve(), args.corpus_dir.resolve()}, "Do not overwrite source dataset/corpus")
    files = [Path(__file__), config, ROOT / "src/rag_research/data/japanese_evidence.py",
             ROOT / "src/rag_research/data/japanese_dataset.py",
             ROOT / "src/rag_research/data/wikipedia_reference_projection.py",
             ROOT / "src/rag_research/data/wikipedia_snapshot.py"]
    hashes = {p.relative_to(ROOT).as_posix(): file_hash(p) for p in files}
    with run_lock(output.with_name(output.name + ".prepare-lock")):
        report = prepare_dataset(args.groups_dir.resolve(), args.corpus_dir.resolve(), args.snapshot_dir.resolve(),
                                 output, read_json(config), code_hashes=hashes)
    require(all(file_hash(p) == hashes[p.relative_to(ROOT).as_posix()] for p in files),
            "Evidence preparation code changed during execution")
    print(json.dumps(report["statistics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
