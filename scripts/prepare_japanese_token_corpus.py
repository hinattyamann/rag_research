"""Create Japanese token-bounded passages from a completed historical source snapshot."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.data.japanese_token_corpus import prepare_corpus  # noqa: E402
from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.storage import run_lock  # noqa: E402
from rag_research.retrieval.common import file_hash, read_json  # noqa: E402
from rag_research.retrieval.multilingual import MODEL_ROOT as E5_MODEL_ROOT  # noqa: E402
from rag_research.retrieval.multilingual import E5Tokenizer  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, default=E5_MODEL_ROOT)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/phase11_japanese_token_corpus_v1.json")
    args = parser.parse_args()
    output, config, snapshot = args.output_dir.resolve(), args.config.resolve(), args.snapshot_dir.resolve()
    require(output.is_relative_to(ROOT / "data/processed/wikipedia_human_retrieval_ja") and
            config.is_relative_to(ROOT), "Use a new Japanese processed corpus and repository config")
    files = [Path(__file__), config, ROOT / "configs/phase11_multilingual_embedding_v1.json",
             *(ROOT / f"src/rag_research/data/{n}.py" for n in
               ("japanese_token_corpus", "japanese_passages", "japanese_dataset", "source_availability", "wikipedia_snapshot")),
             ROOT / "src/rag_research/retrieval/multilingual.py"]
    hashes = {p.relative_to(ROOT).as_posix(): file_hash(p) for p in files}
    tokenizer = E5Tokenizer(args.model_root)
    with run_lock(output.with_name(output.name + ".prepare-lock")), run_lock(snapshot):
        report = prepare_corpus(snapshot, output, read_json(config), tokenizer, code_hashes=hashes)
    require(all(file_hash(p) == hashes[p.relative_to(ROOT).as_posix()] for p in files),
            "Corpus preparation code changed during execution")
    print(json.dumps({key: report[key] for key in ("source_title_count", "source_status_counts",
          "source_unique_article_count", "output_passage_count", "source_characters_preserved",
          "maximum_embedding_input_tokens", "resources", "gold_passage_mapping_status")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
