"""Offline Japanese QA adaptation and leakage-preserving connected-component splits.

Reference answers/quotes/summaries are offline metadata, never retrieval documents.
Unsuccessful search records contribute to the corpus, not unanswerable QA labels.
"""

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from rag_research.data.baobab_source import DATASET_ID, REVISION, SOURCE_FILES, validate_rows
from rag_research.data.clapnq_records import InternalQARecord
from rag_research.data.wikipedia_snapshot import TEXT_VERSION, article_text
from rag_research.data.wikipedia_snapshot import validate_spec as validate_snapshot_spec
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.storage import read_json, verify_checkpoint
from rag_research.retrieval.common import file_hash

SPLITS = ("development", "calibration", "evaluation")
GROUPING = "all-retrieved-articles-aliases-pageids-identical-text-and-exact-qa-components-v1"
ASSIGNMENT = "reserved-development-then-size-desc-sha256-greedy-squared-error-v1"


def title_key(title):
    return "title:" + unicodedata.normalize("NFC", " ".join(title.replace("_", " ").split()).casefold())


def text_key(kind, text):
    normalized = unicodedata.normalize("NFC", "".join(text.split()))
    return kind + ":" + hashlib.sha256(normalized.encode()).hexdigest()


def validate_spec(spec):
    require(spec.get("schema_version") == 1 and
            spec.get("purpose") == "phase11-japanese-qa-group-split-preparation",
            "Unknown Japanese dataset specification")
    require(spec.get("source_revision") == REVISION and
            spec.get("dataset_version", "").startswith(REVISION[:7] + "-groups-v"),
            "Japanese dataset source/version mismatch")
    require(spec.get("grouping") == GROUPING and spec.get("assignment") == ASSIGNMENT,
            "Unknown Japanese grouping/assignment rule")
    percentages = spec.get("split_percentages", {})
    require(set(percentages) == set(SPLITS) and
            all(type(x) is int and 0 < x < 100 for x in percentages.values()) and
            sum(percentages.values()) == 100, "Invalid Japanese split percentages")
    require(type(spec.get("seed")) is int and spec["seed"] >= 0, "Invalid Japanese split seed")
    require(spec.get("qa_population") == "all_838_answered_records_without_quality_or_coverage_filtering"
            and spec.get("unsuccessful_searches_are_unanswerable_qa") is False and
            spec.get("gold_passage_mapping") == "pending_passage_build_not_fabricated_from_reference_quotes"
            and spec.get("model_calls") == 0 and spec.get("phase12_allowed") is False,
            "Japanese dataset population/evidence boundary changed")


def normalize_answered(row, *, raw_line, line_index):
    """Retain literal reference quotes and human summaries in distinct fields."""
    validate_rows([row], answered=True)
    require(json.loads(raw_line) == row and type(line_index) is int and line_index >= 0,
            "Japanese source line/record mismatch")
    cited_by = defaultdict(list)
    for index, sentence in enumerate(row["answer"]["sentences"]):
        for reference in sentence["citations"]:
            cited_by[reference].append(index)
    evidence, quotes = [], []
    for index, reference in enumerate(row["references"]):
        page = reference.get("page")
        if not page:
            continue
        quote = page.get("quote", {}).get("text") if page.get("quote") else None
        summary = page.get("summary", {}).get("text") if page.get("summary") else None
        evidence.append({"reference_index": index, "title": page["title"], "url": page["url"],
                         "quote": quote, "human_summary_not_literal_source": summary,
                         "cited_by_answer_sentence_indices": cited_by.get(index, [])})
        if index in cited_by and quote is not None and quote not in quotes:
            quotes.append(quote)
    primary_index = row["answer"]["sentences"][0]["citations"][0]
    record = InternalQARecord(
        record_id=f"whrja:{REVISION[:7]}:answered:{row['id']}", source_dataset=DATASET_ID,
        source_revision=REVISION, source_split="answered", research_split=None,
        source_id=str(row["id"]), source_line_index=line_index,
        source_record_sha256=hashlib.sha256(raw_line).hexdigest(),
        source_title=row["references"][primary_index]["page"]["title"], question=row["question"],
        reference_answers=[row["answer"]["text"]], selected_sentences_by_reference=[quotes],
        is_answerable=True, gold_passage_ids=[], provided_passage=None, dataset_type="normal",
        derived_from_id=None, derivation=None).to_dict()
    record.update(language="ja", reference_evidence=evidence,
                  reference_answer_sentences=deepcopy(row["answer"]["sentences"]),
                  gold_passage_mapping_status="pending_passage_build",
                  answerability_scope="human_answer_in_source_not_verified_common_corpus_coverage")
    return record


def connected_groups(rows, *, reserved_source_ids, articles=()):
    """Unite all retrieved pages, aliases, duplicate article text and exact QA text."""
    validate_rows(rows, answered=True)
    ids = {row["id"] for row in rows}
    require(set(reserved_source_ids) <= ids and
            all(type(x) is int for x in reserved_source_ids), "Unknown reserved Japanese QA ID")
    parent = {}

    def find(node):
        parent.setdefault(node, node)
        root = node
        while parent[root] != root:
            root = parent[root]
        while parent[node] != node:
            previous = parent[node]
            parent[node] = root
            node = previous
        return root

    def join(nodes):
        first = find(nodes[0])
        for node in nodes[1:]:
            other = find(node)
            if other != first:
                parent[other] = first

    for article in articles:
        nodes = [title_key(article["requested_title"])]
        if article.get("canonical_title"):
            nodes.append(title_key(article["canonical_title"]))
        if type(article.get("page_id")) is int and article["page_id"] > 0:
            nodes.append(f"page:{article['page_id']}")
        for mapping in (*article.get("normalized_titles", []), *article.get("current_redirects", [])):
            nodes.extend([title_key(mapping["from"]), title_key(mapping["to"])])
        if article["status"] == "ok":
            nodes.append("article-text:" + article["text_sha256"])
        join(nodes)
    for row in sorted(rows, key=lambda r: r["id"]):
        nodes = [f"qa:{row['id']}", text_key("question", row["question"]),
                 text_key("answer", row["answer"]["text"])]
        nodes.extend(title_key(r["page"]["title"]) for r in row["references"] if r.get("page"))
        join(nodes)
    members, keys = defaultdict(list), defaultdict(list)
    for identifier in sorted(ids):
        members[find(f"qa:{identifier}")].append(identifier)
    for node in sorted(parent):
        component = find(node)
        if component in members and not node.startswith("qa:"):
            keys[component].append(node)
    groups = []
    reserved = set(reserved_source_ids)
    for component, source_ids in members.items():
        group_id = "whrja-group:" + digest({"revision": REVISION, "source_ids": source_ids})[:24]
        groups.append({"group_id": group_id, "source_ids": source_ids,
                       "identity_keys": keys[component],
                       "development_reserved": bool(reserved.intersection(source_ids))})
    return sorted(groups, key=lambda g: g["group_id"])


def assign_splits(groups, spec):
    """Minimize fixed target count error, preserving indivisible reserved groups."""
    validate_spec(spec)
    total = sum(len(g["source_ids"]) for g in groups)
    counts = dict.fromkeys(SPLITS, 0)
    assignments = {}
    require(len({g["group_id"] for g in groups}) == len(groups), "Duplicate Japanese Group ID")
    for group in groups:
        if group["development_reserved"]:
            assignments[group["group_id"]] = "development"
            counts["development"] += len(group["source_ids"])
    remaining = (g for g in groups if not g["development_reserved"])
    def order(g):
        return -len(g["source_ids"]), digest([spec["seed"], g["group_id"]]), g["group_id"]
    for group in sorted(remaining, key=order):
        size = len(group["source_ids"])

        def change(name):
            before = 100 * counts[name] - total * spec["split_percentages"][name]
            return (before + 100 * size) ** 2 - before ** 2

        chosen = min(SPLITS, key=lambda name: (change(name), SPLITS.index(name)))
        assignments[group["group_id"]] = chosen
        counts[chosen] += size
    validate_assignments(groups, assignments)
    require(all(counts.values()), "Japanese grouping produced an empty split")
    return assignments


def validate_assignments(groups, assignments):
    require(set(assignments) == {g["group_id"] for g in groups}, "Japanese Group assignment mismatch")
    owners, ids = {}, set()
    for group in groups:
        name = assignments[group["group_id"]]
        require(name in SPLITS and
                (not group["development_reserved"] or name == "development"),
                "Reserved Japanese development Group escaped")
        require(bool(group["source_ids"]) and len(set(group["source_ids"])) == len(group["source_ids"])
                and not ids.intersection(group["source_ids"]),
                "Missing/duplicate Japanese Group source ID")
        ids.update(group["source_ids"])
        for key in group["identity_keys"]:
            require(key not in owners or owners[key] == group["group_id"],
                    "Japanese source identity occurs in multiple Groups")
            owners[key] = group["group_id"]
    return {"record_count": len(ids), "group_count": len(groups),
            "identity_key_count": len(owners), "cross_group_identity_overlap": 0}


def group_statistics(groups, assignments=None):
    report = {"qa_count": sum(len(g["source_ids"]) for g in groups), "group_count": len(groups),
              "largest_group_sizes": sorted((len(g["source_ids"]) for g in groups), reverse=True)[:10],
              "reserved_development_qa": sum(len(g["source_ids"]) for g in groups if g["development_reserved"])}
    if assignments is not None:
        report["split_qa_counts"] = dict(Counter(
            {name: sum(len(g["source_ids"]) for g in groups if assignments[g["group_id"]] == name)
             for name in SPLITS}))
    return report


def read_complete_snapshot(directory, *, expected_titles):
    """Fail closed on partial acquisition, changed archives or inconsistent bodies."""
    plan = read_json(directory / "plan.json")
    verify_checkpoint(plan)
    validate_snapshot_spec(plan["spec"])
    require(plan["purpose"] == "phase11-historical-japanese-corpus-plan" and
            plan["source_dataset"] == DATASET_ID and plan["source_revision"] == REVISION and
            plan["source_files_sha256"] == SOURCE_FILES and plan["titles"] == sorted(expected_titles),
            "Historical snapshot differs from Japanese source")
    execution = read_json(directory / "execution.json")
    verify_checkpoint(execution)
    require(execution["plan_sha256"] == digest(plan) and
            re.fullmatch(r"[a-f0-9]{40}", execution["repository_commit"]),
            "Historical execution identity mismatch")
    complete = None
    for path in sorted(directory.glob("progress-*.json")):
        progress = read_json(path)
        verify_checkpoint(progress)
        require(progress["plan_sha256"] == digest(plan), "Historical progress plan mismatch")
        if progress["status"] == "finished" and progress["articles_seen_this_session"] == len(expected_titles):
            complete = progress
    require(complete is not None, "Historical acquisition is incomplete; no final Group split")
    for relative, expected in plan["source_code_sha256"].items():
        path = directory / "source_snapshot" / relative
        require(path.resolve().is_relative_to((directory / "source_snapshot").resolve()) and
                file_hash(path) == expected, "Historical acquisition source archive changed")
    articles, identities = [], {}
    for title in expected_titles:
        key = hashlib.sha256(title.encode()).hexdigest()[:24]
        row = read_json(directory / "articles" / f"{key}.json")
        verify_checkpoint(row)
        require(row["requested_title"] == title and row["plan_sha256"] == digest(plan) and
                row["text_version"] == TEXT_VERSION and row["cutoff_utc"] == plan["spec"]["cutoff_utc"] and
                row["status"] in {"ok", "unavailable", "error"}, "Historical article metadata mismatch")
        requests = {}
        for relative, expected in row["request_files_sha256"].items():
            path = directory / relative
            require(path.resolve().is_relative_to((directory / "requests").resolve()) and
                    file_hash(path) == expected, "Historical request archive changed")
            request = read_json(path)
            verify_checkpoint(request)
            requests[path.name] = request
        if row["status"] == "ok":
            require(hashlib.sha256(row["text"].encode()).hexdigest() == row["text_sha256"] and
                    len(row["text"]) == row["characters"] and row["text"].strip() and
                    row["revision_timestamp_utc"] <= row["cutoff_utc"], "Historical article body changed")
            parsed = requests[f"{key}-parse.json"]["response"]["parse"]
            require(parsed["revid"] == row["revision_id"] and parsed["pageid"] == row["page_id"] and
                    article_text(parsed["text"]) == row["text"], "Historical rendered source differs")
            query = requests[f"{key}-revision.json"]
            page = query["response"]["query"]["pages"][0]
            revision = page["revisions"][0]
            require(query["status"] == "ok" and query["parameters"]["titles"] == title and
                    query["parameters"]["rvstart"] == row["cutoff_utc"] and
                    page["pageid"] == row["page_id"] and revision["revid"] == row["revision_id"] and
                    revision["timestamp"] == row["revision_timestamp_utc"],
                    "Historical revision source differs")
            identity = (row["revision_id"], row["text_sha256"])
            require(row["page_id"] not in identities or identities[row["page_id"]] == identity,
                    "Historical aliases resolve to inconsistent revisions/bodies")
            identities[row["page_id"]] = identity
        articles.append(row)
    require(complete["expected_articles"] == len(articles) and
            complete["statuses"] == dict(Counter(r["status"] for r in articles)),
            "Historical progress counts differ from article journals")
    return plan, articles


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def publish_immutable(artifacts):
    """Check all conflicts before writing anything; retries reuse only identical bytes."""
    for path, payload in artifacts.items():
        require(not path.exists() or path.read_bytes() == payload,
                "Japanese dataset artifact differs; use a new output version")
    for path, payload in artifacts.items():
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            require(path.read_bytes() == payload, "Concurrent Japanese dataset artifact conflict")
        finally:
            temporary.unlink()
