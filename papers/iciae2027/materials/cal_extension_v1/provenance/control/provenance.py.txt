"""Resolve original Gold parent IDs through the frozen passage map, offline."""

import hashlib
import json
from pathlib import Path
from urllib.parse import quote


def check(value, message):
    if not value:
        raise ValueError(message)


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def selected_sources(fixed, assets, wanted, source):
    """Retain child IDs and reconstruct parents only from hash-bound full spans."""
    fixed = Path(fixed)
    metadata, bodies = {}, {}
    for language in ("en", "ja"):
        spec = assets["datasets"][language]
        mapping_path = fixed / spec["parent_map"]["path"]
        check(hashlib.sha256(mapping_path.read_bytes()).hexdigest() == spec["parent_map"]["sha256"],
              "Frozen parent map changed")
        parents = {}
        for line in mapping_path.open(encoding="utf-8"):
            row = json.loads(line)
            if row["parent_passage_id"] in wanted[language]:
                check(row["parent_passage_id"] not in parents, "Duplicate selected parent ID")
                parents[row["parent_passage_id"]] = row
        required = wanted[language] | {pid for p in parents.values() for pid in p["child_passage_ids"]}
        path = fixed / spec["corpus"]["path"]
        check(hashlib.sha256(path.read_bytes()).hexdigest() == spec["corpus"]["sha256"], "Corpus changed")
        binding = source(path, "selected_passage_metadata_only")
        for line in path.open(encoding="utf-8"):
            row = json.loads(line)
            if row["passage_id"] not in required:
                continue
            body = row.pop("text")
            check(row["text_sha256"] == digest(body), "Passage text checksum differs")
            if language == "en":
                row["source_url"] = "https://en.wikipedia.org/wiki/" + quote(row["title"].replace(" ", "_"), safe="")
                row["source_url_precision"] = "title-based attribution URL; original Wikipedia revision not recorded by the CLAPNQ passage asset"
                row["license"] = "CC-BY-SA-3.0 (Natural Questions lineage); dataset annotations Apache-2.0"
            else:
                row["license"] = "CC-BY-SA-4.0; Wikipedia contributors; see oldid and page history"
            row["contributors_history_url"] = row["source_url"] + ("&action=history" if "?" in row["source_url"] else "?action=history")
            row["transformation"] = "Existing contiguous character-span passage; no new text normalization"
            row["corpus_source"] = binding
            check((language, row["passage_id"]) not in metadata, "Duplicate selected corpus ID")
            metadata[language, row["passage_id"]], bodies[language, row["passage_id"]] = row, body
        for pid in sorted(wanted[language]):
            if (language, pid) in metadata:
                continue
            check(pid in parents, "Missing selected passage provenance: " + language + ":" + pid)
            parent = parents[pid]
            ids = parent["child_passage_ids"]
            check(bool(ids) and len(ids) == len(set(ids)), "Invalid selected parent children")
            check(all((language, child) in metadata for child in ids), "Missing parent child passage")
            children = [metadata[language, child] for child in ids]
            cursor, parts = 0, []
            for child in children:
                span = child["source_char_span"]
                body = bodies[language, child["passage_id"]]
                check(child["parent_passage_id"] == pid and child["parent_text_sha256"] == parent["parent_text_sha256"],
                      "Parent/child identity or checksum differs")
                check(span["start"] == cursor and span["end"] == cursor + len(body), "Parent spans have gap, overlap, or wrong order")
                check(child["title"] == children[0]["title"] and child["source_url"] == children[0]["source_url"],
                      "Parent children have different attribution")
                parts.append(body)
                cursor = span["end"]
            body = "".join(parts)
            check(digest(body) == parent["parent_text_sha256"], "Reconstructed parent checksum differs")
            row = {k: v for k, v in children[0].items()
                   if k not in {"passage_id", "source_char_span", "text_sha256", "embedding_token_budget", "passage_version"}}
            row.update(passage_id=pid, text_sha256=digest(body), provenance_kind="original_parent_reconstructed_from_fixed_children",
                       child_passage_ids=ids, parent_map_entry=parent,
                       parent_map_source=source(mapping_path, "selected_parent_mapping_only"),
                       transformation="Exact concatenation of frozen child spans, checked against original parent SHA-256; offline Reference only")
            metadata[language, pid], bodies[language, pid] = row, body
    return metadata, bodies


def verify_parent_sources(q):
    """Self-contained so the generated standard-library verifier can embed it."""
    import hashlib

    corpus = {d["passage_id"]: d for d in q["corpus_documents"]}
    for parent in corpus.values():
        meta = parent["source_metadata"]
        if meta.get("provenance_kind") != "original_parent_reconstructed_from_fixed_children":
            continue
        ids = meta["child_passage_ids"]
        entry = meta["parent_map_entry"]
        if not ids or len(set(ids)) != len(ids) or ids != entry["child_passage_ids"] or entry["parent_passage_id"] != parent["passage_id"]:
            raise ValueError("Invalid reconstructed parent mapping")
        cursor, parts = 0, []
        for pid in ids:
            child = corpus[pid]
            cm = child["source_metadata"]
            span = cm["source_char_span"]
            if (cm["parent_passage_id"] != parent["passage_id"] or cm["parent_text_sha256"] != entry["parent_text_sha256"] or
                    span["start"] != cursor or span["end"] != cursor + len(child["text"]) or
                    hashlib.sha256(child["text"].encode()).hexdigest() != cm["text_sha256"] or
                    cm["title"] != meta["title"] or cm["source_url"] != meta["source_url"]):
                raise ValueError("Reconstructed parent child provenance differs")
            parts.append(child["text"])
            cursor = span["end"]
        body = "".join(parts)
        if body != parent["text"] or hashlib.sha256(body.encode()).hexdigest() != entry["parent_text_sha256"] or meta["text_sha256"] != entry["parent_text_sha256"]:
            raise ValueError("Reconstructed parent checksum differs")


def document_sources(export, assets):
    wanted = {lang: set() for lang in ("en", "ja")}
    for q in export.qa_inputs:
        wanted[q["language"]].update(d["passage_id"] for d in q["used_documents"] + q["gold_documents"])
        wanted[q["language"]].update(q["qa_source"]["gold_passage_ids"])
    metadata, bodies = selected_sources(export.fixed, assets, wanted, export.source)
    for q in export.qa_inputs:
        language = q["language"]
        for d in q["used_documents"] + q["gold_documents"]:
            d["source_metadata"] = metadata[language, d["passage_id"]]
            body = bodies[language, d["passage_id"]]
            start = body.find(d["text"])
            check(start >= 0, "Actual context is not a contiguous corpus substring")
            d["actual_text_sha256"] = digest(d["text"])
            d["corpus_character_span"] = {"start": start, "end": start + len(d["text"])}
        ids = {d["passage_id"] for d in q["used_documents"] + q["gold_documents"]} | set(q["qa_source"]["gold_passage_ids"])
        for pid in list(ids):
            ids.update(metadata[language, pid].get("child_passage_ids", []))
        def document(pid):
            return {"passage_id": pid, "text": bodies[language, pid], "source_metadata": metadata[language, pid]}
        q["corpus_documents"] = [document(pid) for pid in sorted(ids)]
        q["gold_passage_source_metadata"] = {pid: metadata[language, pid] for pid in q["qa_source"]["gold_passage_ids"]}
        q["gold_corpus_documents"] = [document(pid) for pid in q["qa_source"]["gold_passage_ids"]]
        verify_parent_sources(q)
        export.out.joinpath("inputs", q["qa_key"] + ".json").write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n")
    output = {f"{lang}:{pid}": value for (lang, pid), value in metadata.items()}
    export.out.joinpath("provenance/document_attributions.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
