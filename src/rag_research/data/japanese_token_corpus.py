"""Build the common Japanese corpus from verified articles, without reading QA."""

import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

from rag_research.data.baobab_source import REVISION
from rag_research.data.japanese_dataset import read_complete_snapshot
from rag_research.data.japanese_passages import article_passages
from rag_research.data.source_availability import POLICY
from rag_research.experiments.frozen_trace import require
from rag_research.retrieval.common import ResourceMonitor, file_hash, read_json, write_json

ARTICLE_FIELDS = {"purpose", "requested_title", "plan_sha256", "text_version", "cutoff_utc",
                  "request_files_sha256", "canonical_title", "page_id", "normalized_titles",
                  "current_redirects", "revision_id", "revision_timestamp_utc", "source_url",
                  "status", "text", "text_sha256", "characters", "rendering_may_use_current_templates",
                  "result_sha256", "error"}


def validate_spec(spec):
    require(spec.get("schema_version") == 1 and
            spec.get("purpose") == "phase11-source-only-japanese-token-corpus" and
            spec.get("source_revision") == REVISION and
            re.fullmatch(rf"{REVISION[:7]}-e5-passages-v[1-9][0-9]*", spec.get("dataset_version", "")),
            "Unknown Japanese token corpus specification")
    require(re.fullmatch(r"[a-f0-9]{64}", spec.get("snapshot_plan_sha256", "")) and
            type(spec.get("expected_titles")) is int and spec["expected_titles"] > 0 and
            type(spec.get("expected_unique_articles")) is int and spec["expected_unique_articles"] > 0 and
            type(spec.get("max_input_tokens")) is int and 32 <= spec["max_input_tokens"] <= 512,
            "Invalid Japanese corpus identity/count/budget")
    counts = spec.get("expected_status_counts", {})
    require(set(counts) == {"ok", "unavailable", "error"} and
            all(type(v) is int and v >= 0 for v in counts.values()) and
            sum(counts.values()) == spec["expected_titles"], "Invalid Japanese source status counts")
    require(spec.get("terminal_source_unavailability_policy") == POLICY and
            spec.get("parent_identity") == "historical-page-revision-rendered-body-hash" and
            spec.get("parent_relevance_unit") == "source_article_not_each_child_entailment" and
            spec.get("preserve_all_source_characters") is True and
            spec.get("qa_or_reference_input") is False and spec.get("quality_or_coverage_filtering") is False
            and spec.get("phase12_allowed") is False, "Japanese corpus source/relevance boundary changed")


def parent_identity(article):
    """An article parent remains distinct from the text-bearing citation child IDs."""
    return f"jawiki:{article['page_id']}:{article['revision_id']}:{article['text_sha256']}"


def article_children(article, tokenizer, *, max_tokens=512):
    require(set(article) <= ARTICLE_FIELDS, "QA/Reference or unknown field in source-only article")
    children = article_passages(article, tokenizer, max_tokens=max_tokens)
    parent = parent_identity(article)
    return [{**child, "parent_passage_id": parent, "parent_relevance_unit": "source_article"}
            for child in children]


def prepare_corpus(snapshot, output, spec, tokenizer, *, code_hashes):
    """Validate the whole snapshot, deduplicate page aliases, preserve full article text."""
    validate_spec(spec)
    snapshot, output = Path(snapshot), Path(output)
    require(file_hash(snapshot / "plan.json") == spec["snapshot_plan_sha256"], "Snapshot plan changed")
    plan = read_json(snapshot / "plan.json")
    require(len(plan["titles"]) == spec["expected_titles"], "Japanese source title count changed")
    plan, articles = read_complete_snapshot(snapshot, expected_titles=plan["titles"],
                                            unavailability_policy=spec["terminal_source_unavailability_policy"])
    require(dict(Counter(r["status"] for r in articles)) ==
            {k: v for k, v in spec["expected_status_counts"].items() if v}, "Japanese source status counts changed")
    require(all(set(a) <= ARTICLE_FIELDS for a in articles), "QA/Reference field in source-only snapshot")
    journals = {a["requested_title"]: file_hash(snapshot / "articles" /
                (hashlib.sha256(a["requested_title"].encode()).hexdigest()[:24] + ".json")) for a in articles}
    identity = {"spec": spec, "code_sha256": code_hashes, "tokenizer_model": tokenizer.model_manifest,
                "article_journal_sha256": journals}
    if output.exists():
        report = read_json(output / "report.json")
        require(report["execution_identity"] == identity, "Japanese corpus conditions changed; use a new version")
        for name, info in report["artifacts"].items():
            require(file_hash(output / name) == info["sha256"] and
                    (output / name).stat().st_size == info["bytes"], "Japanese corpus artifact changed")
        return report
    stage = output.with_name(output.name + ".building")
    require(not stage.exists(), "Incomplete Japanese corpus exists; preserve it and use a new output path")
    stage.mkdir(parents=True)
    by_page = defaultdict(list)
    for article in articles:
        if article["status"] == "ok":
            by_page[article["page_id"]].append(article)
    require(len(by_page) == spec["expected_unique_articles"], "Japanese unique article count changed")
    identifiers, maximum, total, characters = set(), 0, 0, 0
    with ResourceMonitor() as monitor:
        with (stage / "passages.jsonl").open("wb") as corpus, \
                (stage / "parent_map.jsonl").open("wb") as parents, \
                (stage / "article_catalog.jsonl").open("wb") as catalog:
            def emit(handle, value):
                handle.write((json.dumps(value, ensure_ascii=False, sort_keys=True,
                                         separators=(",", ":")) + "\n").encode())

            for page, aliases in sorted(by_page.items()):
                article = min(aliases, key=lambda a: a["requested_title"])
                require(all(parent_identity(a) == parent_identity(article) for a in aliases),
                        "Alias page revision/body differs")
                children = article_children(article, tokenizer, max_tokens=spec["max_input_tokens"])
                require("".join(c["text"] for c in children) == article["text"], "Japanese parent lost source text")
                for child in children:
                    require(child["passage_id"] not in identifiers, "Japanese child ID collision")
                    identifiers.add(child["passage_id"])
                    maximum = max(maximum, child["source_char_span"]["embedding_input_tokens"])
                    emit(corpus, child)
                total += len(children)
                characters += len(article["text"])
                emit(parents, {"parent_passage_id": parent_identity(article),
                               "parent_text_sha256": article["text_sha256"],
                               "wikipedia_page_id": page, "wikipedia_revision_id": article["revision_id"],
                               "canonical_title": article["canonical_title"],
                               "requested_titles": sorted(a["requested_title"] for a in aliases),
                               "child_passage_ids": [c["passage_id"] for c in children],
                               "relevance_unit": "source_article_not_each_child_entailment"})
                if len(by_page) > 100 and len(identifiers) % 1000 < len(children):
                    print(json.dumps({"output_passages": total, "source_characters": characters}), flush=True)
            for article in sorted(articles, key=lambda a: a["requested_title"]):
                emit(catalog, {"requested_title": article["requested_title"],
                               "canonical_title": article.get("canonical_title"),
                               "normalized_titles": article.get("normalized_titles", []),
                               "current_redirects": article.get("current_redirects", []),
                               "wikipedia_page_id": article.get("page_id"),
                               "wikipedia_revision_id": article.get("revision_id"),
                               "raw_status": article["status"],
                               "body_available": article["status"] == "ok",
                               "parent_passage_id": parent_identity(article) if article["status"] == "ok" else None,
                               "documented_deleted_text_absence": article["status"] == "error",
                               "article_journal_sha256": journals[article["requested_title"]]})
            for handle in (corpus, parents, catalog):
                handle.flush()
                os.fsync(handle.fileno())
    require(file_hash(snapshot / "plan.json") == spec["snapshot_plan_sha256"], "Snapshot changed during corpus preparation")
    for title, expected in journals.items():
        require(file_hash(snapshot / "articles" / (hashlib.sha256(title.encode()).hexdigest()[:24] + ".json")) == expected,
                "Article changed during corpus preparation")
    report = {"schema_version": 1, "purpose": "phase11-source-only-japanese-corpus-not-final-freeze",
              "execution_identity": identity, "source_title_count": len(articles),
              "source_status_counts": dict(Counter(a["status"] for a in articles)),
              "source_unique_article_count": len(by_page), "output_passage_count": total,
              "source_characters_preserved": characters, "maximum_embedding_input_tokens": maximum,
              "full_source_text_preserved_per_parent": True, "qa_or_reference_read": False,
              "parent_relevance_unit": "source_article_not_each_child_entailment",
              "gold_passage_mapping_status": "pending_qa_parent_and_quote_audit",
              "artifacts": {n: {"sha256": file_hash(stage / n), "bytes": (stage / n).stat().st_size}
                            for n in ("passages.jsonl", "parent_map.jsonl", "article_catalog.jsonl")},
              "resources": monitor.report(), "embedding_inference_calls": 0, "generative_model_calls": 0,
              "gate11_passed": False, "phase12_allowed": False}
    write_json(stage / "report.json", report)
    stage.rename(output)
    return report
