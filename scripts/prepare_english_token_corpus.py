"""Create a token-bounded English Corpus without inspecting QA or inference outcomes."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.data.token_bounded_corpus import normalize_corpus  # noqa: E402
from rag_research.retrieval.common import file_hash, read_json  # noqa: E402
from rag_research.retrieval.multilingual import MODEL_ROOT as E5_MODEL_ROOT  # noqa: E402
from rag_research.retrieval.multilingual import E5Tokenizer  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/phase11_english_token_corpus_v1.json")
    parser.add_argument("--source-corpus", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, default=E5_MODEL_ROOT)
    args = parser.parse_args()
    config = args.config.resolve()
    if not config.is_relative_to(ROOT):
        parser.error("Corpus config must be inside repository")
    spec = read_json(config)
    source = (args.source_corpus or ROOT / spec["source_corpus_path"]).resolve()
    output = args.output_dir.resolve()
    if not output.is_relative_to(ROOT / "data/processed/clapnq") or output == source.parent:
        parser.error("Use a new English processed corpus directory")
    files = [Path(__file__), ROOT / "src/rag_research/data/token_bounded_corpus.py",
             ROOT / "src/rag_research/data/japanese_passages.py", ROOT / "src/rag_research/retrieval/multilingual.py",
             ROOT / "configs/phase11_multilingual_embedding_v1.json", config]
    code_hashes = {p.relative_to(ROOT).as_posix(): file_hash(p) for p in files}
    tokenizer = E5Tokenizer(args.model_root)
    result = normalize_corpus(source, output, spec, tokenizer, code_hashes=code_hashes)
    for p in files:
        if file_hash(p) != code_hashes[p.relative_to(ROOT).as_posix()]:
            raise ValueError("Corpus preparation source changed during execution")
    print(json.dumps({key: result[key] for key in ("source_parent_count", "output_passage_count",
          "subdivided_parent_count", "maximum_embedding_input_tokens", "resources")}, indent=2))


if __name__ == "__main__":
    main()
