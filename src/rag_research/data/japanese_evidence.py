"""Offline mapping of native references to existing article parents and literal spans."""

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from rag_research.data.baobab_source import REVISION
from rag_research.data.japanese_dataset import SPLITS, json_bytes, publish_immutable
from rag_research.experiments.frozen_trace import require
from rag_research.retrieval.common import file_hash, read_json

QUOTE_POLICY = "exact-then-whitespace-only-all-occurrences-without-fuzzy-v1"
MAPPING_STATUS = "audited_cited_article_and_literal_quote_mapping_v1"


def validate_spec(spec):
    require(spec.get("schema_version") == 1 and
            spec.get("purpose") == "phase11-japanese-offline-reference-corpus-audit" and
            spec.get("source_revision") == REVISION and
            re.fullmatch(rf"{REVISION[:7]}-qa-corpus-v[1-9][0-9]*", spec.get("dataset_version", "")),
            "Unknown Japanese evidence dataset specification")
    require(all(re.fullmatch(r"[a-f0-9]{64}", spec.get(k, "")) for k in
                ("source_group_report_sha256", "source_corpus_report_sha256")) and
            type(spec.get("expected_qa_count")) is int and spec["expected_qa_count"] > 0,
            "Invalid Japanese evidence input identities/count")
    require(spec.get("quote_matching") == QUOTE_POLICY and
            spec.get("gold_parent_unit") == "available_cited_source_article" and
            spec.get("gold_child_unit") == "verified_literal_quote_overlap_children_only" and
            spec.get("human_summary") == "retain_as_non_literal_without_automatic_entailment" and
            spec.get("missing_body") == "retain_cited_source_units_without_qa_exclusion_or_unanswerable_relabel"
            and spec.get("uncited_references_are_gold") is False and
            spec.get("per_question_corpus_injection") is False and spec.get("model_calls") == 0 and
            spec.get("phase12_allowed") is False, "Japanese reference/evidence boundary changed")


def occurrences(text, needle):
    start = 0
    while True:
        position = text.find(needle, start)
        if position < 0:
            return
        yield position
        start = position + 1


def literal_spans(body, quote):
    """Whitespace tolerance only; retain all locations and the actual source span hash."""
    if quote is None:
        return {"status": "no_literal_quote", "mode": None, "spans": [], "ambiguous_location": False}
    require(isinstance(quote, str) and quote.strip(), "Nonblank literal quote required")
    if body is None:
        return {"status": "article_body_unavailable", "mode": None, "spans": [], "ambiguous_location": False}
    require(isinstance(body, str) and body.strip(), "Invalid article body")
    spans = [(p, p + len(quote)) for p in occurrences(body, quote)]
    mode = "exact"
    if not spans:
        positions = [i for i, char in enumerate(body) if not char.isspace()]
        compact = "".join(body[i] for i in positions)
        target = "".join(quote.split())
        spans = [(positions[p], positions[p + len(target) - 1] + 1)
                 for p in occurrences(compact, target)]
        mode = "whitespace_only"
    values = []
    for start, end in spans:
        actual = body[start:end]
        require(actual == quote if mode == "exact" else "".join(actual.split()) == "".join(quote.split()),
                "Literal span does not reconstruct the reference quote")
        values.append({"start": start, "end": end,
                       "source_span_sha256": hashlib.sha256(actual.encode()).hexdigest()})
    return {"status": "located" if values else "not_located", "mode": mode if values else None,
            "spans": values, "ambiguous_location": len(values) > 1}


def bind_record(record, catalog, children, bodies):
    """Reference metadata stays offline; only cited sources define available parent Gold."""
    require(record.get("language") == "ja" and record.get("research_split") in SPLITS and
            record.get("source_revision") == REVISION and record.get("is_answerable") is True and
            record.get("gold_passage_ids") == [] and
            record.get("gold_passage_mapping_status") == "pending_passage_build",
            "Expected original split Japanese QA with pending evidence mapping")
    cited = {i for sentence in record["reference_answer_sentences"] for i in sentence["citations"]}
    references = record["reference_evidence"]
    indices = [r["reference_index"] for r in references]
    require(len(set(indices)) == len(indices) and cited <= set(indices), "Missing/duplicate cited reference index")
    mapped, gold_parents, gold_children, missing_units = [], set(), set(), set()
    for reference in references:
        title = unicodedata.normalize("NFC", reference["title"])
        require(title in catalog, "Reference title has no exact declared source catalog entry")
        source = catalog[title]
        parent = source["parent_passage_id"]
        available = source["body_available"]
        require(available == (parent is not None) and
                (not available or (parent in bodies and parent in children)), "Reference corpus parent is unavailable")
        audit = literal_spans(bodies[parent] if available else None, reference["quote"])
        child_ids = sorted({c["passage_id"] for c in children.get(parent, [])
                            if any(c["start"] < s["end"] and s["start"] < c["end"] for s in audit["spans"])})
        require(not audit["spans"] or bool(child_ids), "Located source quote has no corpus child overlap")
        used = reference["reference_index"] in cited
        expected_sentences = [i for i, sentence in enumerate(record["reference_answer_sentences"])
                              if reference["reference_index"] in sentence["citations"]]
        require(reference["cited_by_answer_sentence_indices"] == expected_sentences,
                "Reference answer citation correspondence changed")
        page = source["wikipedia_page_id"]
        unit = (f"jawiki-page:{page}" if type(page) is int and page > 0 else
                "unresolved-jawiki-title:" + hashlib.sha256(title.encode()).hexdigest())
        mapped.append({"reference_index": reference["reference_index"], "cited": used,
                       "cited_by_answer_sentence_indices": expected_sentences,
                       "source_reference_unit_id": unit, "raw_article_status": source["raw_status"],
                       "body_available": available, "parent_passage_id": parent,
                       "literal_quote_audit": audit, "literal_overlap_child_ids": child_ids,
                       "has_human_summary_not_literal_source": reference["human_summary_not_literal_source"] is not None})
        if used:
            if available:
                gold_parents.add(parent)
            else:
                missing_units.add(unit)
            gold_children.update(child_ids)
    result = deepcopy(record)
    result.update(gold_passage_ids=sorted(gold_children), gold_parent_ids=sorted(gold_parents),
                  unavailable_cited_reference_ids=sorted(missing_units), reference_corpus_mapping=mapped,
                  gold_passage_mapping_status=MAPPING_STATUS,
                  gold_relevance_unit="available_cited_source_article",
                  gold_passage_ids_scope="verified_literal_quote_overlap_children_only_not_metric_gold",
                  reference_corpus_metadata_offline_only=True,
                  corpus_answerability="not_annotated_no_relabel_from_body_or_quote_availability")
    require(gold_parents or missing_units, "Cited source mapping has no available or missing unit")
    require(all(result[k] == value for k, value in record.items()
                if k not in {"gold_passage_ids", "gold_passage_mapping_status"}), "Original Japanese QA field changed")
    return result


def load_context(corpus, snapshot, report):
    """Read verified source bodies and existing child spans; never modify the corpus."""
    parents = [json.loads(line) for line in (corpus / "parent_map.jsonl").read_text().splitlines()]
    parent_of = {c: p["parent_passage_id"] for p in parents for c in p["child_passage_ids"]}
    require(len(parent_of) == sum(len(p["child_passage_ids"]) for p in parents), "Duplicate corpus child ID")
    children = defaultdict(list)
    with (corpus / "passages.jsonl").open() as stream:
        seen = set()
        for line in stream:
            child = json.loads(line)
            identifier, parent = child["passage_id"], child["parent_passage_id"]
            require(identifier not in seen and parent_of.get(identifier) == parent, "Corpus child/parent mapping changed")
            seen.add(identifier)
            children[parent].append({"passage_id": identifier, "start": child["source_char_span"]["start"],
                                     "end": child["source_char_span"]["end"]})
    require(seen == set(parent_of), "Corpus child coverage differs")
    bodies = {}
    for title, expected in report["execution_identity"]["article_journal_sha256"].items():
        path = snapshot / "articles" / (hashlib.sha256(title.encode()).hexdigest()[:24] + ".json")
        require(file_hash(path) == expected, "Raw article journal changed after corpus audit")
        article = read_json(path)
        if article["status"] != "ok":
            continue
        require(hashlib.sha256(article["text"].encode()).hexdigest() == article["text_sha256"], "Raw article body changed")
        parent = f"jawiki:{article['page_id']}:{article['revision_id']}:{article['text_sha256']}"
        require(parent in children and (parent not in bodies or bodies[parent] == article["text"]),
                "Historical body differs from corpus parent")
        bodies[parent] = article["text"]
    catalog = {}
    for line in (corpus / "article_catalog.jsonl").read_text().splitlines():
        value = json.loads(line)
        title = unicodedata.normalize("NFC", value["requested_title"])
        require(title not in catalog, "Duplicate normalized catalog title")
        catalog[title] = value
    require(len(bodies) == len(parents), "Corpus parent has no verified source body")
    return catalog, children, bodies


def prepare_dataset(groups, corpus, snapshot, output, spec, *, code_hashes):
    validate_spec(spec)
    groups, corpus, snapshot, output = map(Path, (groups, corpus, snapshot, output))
    reports = {}
    for name, directory in (("group", groups), ("corpus", corpus)):
        require(file_hash(directory / "report.json") == spec[f"source_{name}_report_sha256"],
                "Japanese evidence input report changed")
        report = read_json(directory / "report.json")
        for relative, info in report["artifacts"].items():
            require(file_hash(directory / relative) == info["sha256"] and
                    (directory / relative).stat().st_size == info["bytes"], "Japanese evidence input artifact changed")
        reports[name] = report
    original = [json.loads(line) for line in (groups / "qa.jsonl").read_text().splitlines()]
    require(len(original) == spec["expected_qa_count"] and
            len({r["record_id"] for r in original}) == len(original), "Japanese QA population changed")
    catalog, children, bodies = load_context(corpus, snapshot, reports["corpus"])
    rows = [bind_record(r, catalog, children, bodies) for r in original]
    all_references = [m for r in rows for m in r["reference_corpus_mapping"]]
    cited = [m for m in all_references if m["cited"]]
    statistics = {"qa_count": len(rows), "split_counts": dict(Counter(r["research_split"] for r in rows)),
                  "reference_count": len(all_references), "cited_reference_count": len(cited),
                  "all_reference_quote_statuses": dict(Counter(m["literal_quote_audit"]["status"] for m in all_references)),
                  "cited_reference_quote_statuses": dict(Counter(m["literal_quote_audit"]["status"] for m in cited)),
                  "qa_with_unavailable_cited_source_units": sum(bool(r["unavailable_cited_reference_ids"]) for r in rows),
                  "qa_without_any_available_cited_parent": sum(not r["gold_parent_ids"] for r in rows),
                  "qa_with_cited_unlocated_literal_quote": sum(any(m["cited"] and
                      m["literal_quote_audit"]["status"] == "not_located" for m in r["reference_corpus_mapping"]) for r in rows),
                  "qa_with_cited_human_summary": sum(any(m["cited"] and m["has_human_summary_not_literal_source"]
                                                       for m in r["reference_corpus_mapping"]) for r in rows)}
    def encode(values):
        return b"".join((json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
                        for r in values)
    artifacts = {output / "qa.jsonl": encode(rows), output / "groups.json": (groups / "groups.json").read_bytes()}
    for name in SPLITS:
        artifacts[output / f"{name}.jsonl"] = encode(r for r in rows if r["research_split"] == name)
    report = {"schema_version": 1, "purpose": "phase11-offline-japanese-reference-audit-not-final-freeze",
              "execution_identity": {"spec": spec, "code_sha256": code_hashes}, "statistics": statistics,
              "gold_passage_mapping_status": MAPPING_STATUS, "source_qa_and_splits_preserved": True,
              "gold_relevance_unit": "available_cited_source_article",
              "unavailable_reference_units_retained_not_relabelled_unanswerable": True,
              "gold_child_ids_are_only_literal_overlap_not_every_child_entailment": True,
              "corpus_changed_or_qa_injected": False, "quality_or_evaluation_results_used": False,
              "artifacts": {p.name: {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}
                            for p, b in artifacts.items()},
              "model_calls": 0, "gate11_passed": False, "phase12_allowed": False}
    artifacts[output / "report.json"] = json_bytes(report)
    publish_immutable(artifacts)
    return report
