"""Source-only English passage subdivision, retaining original IDs and relevance units."""

import hashlib
import json
import os
import re
from pathlib import Path

from rag_research.data.clapnq_source import CLAPNQ_REVISION
from rag_research.data.japanese_passages import VERSION, split_spans
from rag_research.experiments.frozen_trace import digest, require
from rag_research.retrieval.common import ResourceMonitor, file_hash, read_json, write_json


def validate_spec(spec):
    require(spec.get("schema_version") == 1 and spec.get("purpose") == "phase11-token-bounded-english-corpus"
            and spec.get("source_dataset") == "CLAPNQ" and spec.get("source_revision") == CLAPNQ_REVISION,
            "Unknown English token-bounded corpus specification")
    require(re.fullmatch(rf"{CLAPNQ_REVISION[:7]}-e5-passages-v[1-9][0-9]*", spec.get("dataset_version", "")),
            "Invalid token-bounded corpus version")
    require(type(spec.get("expected_parent_passages")) is int and spec["expected_parent_passages"] > 0 and
            type(spec.get("max_input_tokens")) is int and 32 <= spec["max_input_tokens"] <= 512,
            "Invalid corpus count/token bounds")
    require(re.fullmatch(r"[a-f0-9]{64}", spec.get("source_corpus_sha256", "")) and
            spec.get("preserve_within_budget_ids") is True and
            spec.get("gold_relevance_unit") == "original_source_parent_passage" and
            spec.get("quality_or_question_filtering") is False and spec.get("phase12_allowed") is False,
            "Source corpus identity/relevance boundary changed")


def source_passages(row, tokenizer, *, max_tokens=512):
    """Keep short parents byte-for-byte in text; long parents get source-span children."""
    require(set(row) == {"source_dataset", "source_revision", "passage_id", "title", "text", "text_sha256"},
            "Unexpected field in source-only passage; QA/Reference metadata is forbidden")
    require(row.get("source_dataset") == "CLAPNQ" and row.get("source_revision") == CLAPNQ_REVISION and
            isinstance(row.get("passage_id"), str) and row["passage_id"].strip() and
            isinstance(row.get("title"), str) and row["title"].strip() and
            isinstance(row.get("text"), str) and row["text"].strip(), "Invalid English source passage")
    text = row["text"]
    require(hashlib.sha256(text.encode()).hexdigest() == row["text_sha256"], "Source passage hash changed")
    require(type(max_tokens) is int and 32 <= max_tokens <= 512, "Invalid passage token budget")
    count = tokenizer.count(text)
    spans = ([{"start": 0, "end": len(text), "embedding_input_tokens": count}]
             if count <= max_tokens else split_spans(text, tokenizer, max_tokens=max_tokens))
    parent = str(int(digest(["CLAPNQ", CLAPNQ_REVISION, row["passage_id"], row["text_sha256"], VERSION])[:24], 16))
    result = []
    for span in spans:
        value = text[span["start"]:span["end"]]
        identifier = row["passage_id"] if len(spans) == 1 else f"{parent}_{span['start']}-{span['end']}"
        result.append({**row, "passage_id": identifier, "language": "en", "text": value,
                       "text_sha256": hashlib.sha256(value.encode()).hexdigest(),
                       "parent_passage_id": row["passage_id"], "parent_text_sha256": row["text_sha256"],
                       "source_char_span": span, "passage_version": VERSION,
                       "embedding_token_budget": max_tokens})
    require("".join(r["text"] for r in result) == text, "English child passages lose source text")
    return result


def normalize_corpus(source, output, spec, tokenizer, *, code_hashes):
    """Stream a deterministic new corpus and parent map; never read QA/Reference data."""
    validate_spec(spec)
    source, output = Path(source), Path(output)
    require(file_hash(source) == spec["source_corpus_sha256"], "English source corpus hash mismatch")
    identity = {"spec": spec, "code_sha256": code_hashes, "tokenizer_model": tokenizer.model_manifest}
    if output.exists():
        report = read_json(output / "report.json")
        require(report["execution_identity"] == identity, "Corpus preparation conditions changed; use a new version")
        for name, info in report["artifacts"].items():
            require(file_hash(output / name) == info["sha256"] and
                    (output / name).stat().st_size == info["bytes"], "Prepared corpus artifact changed")
        return report
    stage = output.with_name(output.name + ".building")
    require(not stage.exists(), "Incomplete corpus preparation exists; preserve it and use a new output path")
    stage.mkdir(parents=True)
    parents, identifiers = set(), set()
    total, split_parents, maximum = 0, 0, 0
    with ResourceMonitor() as monitor:
        with source.open(encoding="utf-8") as incoming, (stage / "passages.jsonl").open("wb") as outgoing, \
                (stage / "parent_map.jsonl").open("wb") as mapping:
            for line in incoming:
                row = json.loads(line)
                require(row["passage_id"] not in parents, "Duplicate source parent Passage ID")
                parents.add(row["passage_id"])
                children = source_passages(row, tokenizer, max_tokens=spec["max_input_tokens"])
                split_parents += len(children) > 1
                for child in children:
                    require(child["passage_id"] not in identifiers, "Child/parent Passage ID collision")
                    identifiers.add(child["passage_id"])
                    maximum = max(maximum, child["source_char_span"]["embedding_input_tokens"])
                    outgoing.write((json.dumps(child, ensure_ascii=False, sort_keys=True,
                                               separators=(",", ":")) + "\n").encode())
                    total += 1
                parent_row = {"parent_passage_id": row["passage_id"], "parent_text_sha256": row["text_sha256"],
                              "child_passage_ids": [c["passage_id"] for c in children]}
                mapping.write((json.dumps(parent_row, sort_keys=True, separators=(",", ":")) + "\n").encode())
                if len(parents) % 10000 == 0:
                    print(json.dumps({"source_parents": len(parents), "output_passages": total,
                                      "subdivided_parents": split_parents}), flush=True)
            for handle in (outgoing, mapping):
                handle.flush()
                os.fsync(handle.fileno())
    require(len(parents) == spec["expected_parent_passages"] and
            file_hash(source) == spec["source_corpus_sha256"], "English source count/content changed")
    report = {"schema_version": 1, "purpose": "phase11-token-bounded-english-corpus-not-final-retrieval-freeze",
              "execution_identity": identity, "source_parent_count": len(parents),
              "output_passage_count": total, "subdivided_parent_count": split_parents,
              "unchanged_parent_id_count": len(parents) - split_parents,
              "maximum_embedding_input_tokens": maximum,
              "full_source_text_preserved_per_parent": True,
              "gold_relevance_unit": "original_source_parent_passage", "qa_or_reference_read": False,
              "artifacts": {name: {"sha256": file_hash(stage / name), "bytes": (stage / name).stat().st_size}
                            for name in ("passages.jsonl", "parent_map.jsonl")},
              "resources": monitor.report(), "embedding_inference_calls": 0, "generative_model_calls": 0,
              "gate11_passed": False, "phase12_allowed": False}
    write_json(stage / "report.json", report)
    stage.rename(output)
    return report


def parent_relevance(child_ids, parent_of, gold_parent_ids):
    """One original Gold parent can contribute relevance at most once per ranking."""
    require(len(set(child_ids)) == len(child_ids), "Duplicate retrieved child Passage ID")
    require(all(identifier in parent_of for identifier in child_ids), "Unknown child Passage ID")
    gold = set(gold_parent_ids)
    seen, relevance = set(), []
    for identifier in child_ids:
        parent = parent_of[identifier]
        relevance.append(int(parent in gold and parent not in seen))
        seen.add(parent)
    return relevance
