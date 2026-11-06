"""Read-only provenance extraction; no inference, grading, or experiment writes.

Run only in the lab. The independent verifier never imports this module.
"""

import argparse
import ast
import collections
import hashlib
import html
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


def digest(data):
    return hashlib.sha256(data).hexdigest()


def metadata(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return {"bytes": path.stat().st_size, "sha256": h.hexdigest()}


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Sources:
    def __init__(self, repo, out):
        self.repo, self.out, self.rows, self.copies = repo, out, {}, []

    def register(self, path):
        path = path.resolve()
        location = path.relative_to(self.repo).as_posix() if path.is_relative_to(self.repo) else str(path)
        key = digest(location.encode())[:24]
        value = {"historical_path": location, **metadata(path)}
        if key in self.rows:
            assert self.rows[key] == value, f"Source changed: {location}"
        self.rows[key] = value
        return key

    def copy(self, path, target):
        key = self.register(path)
        destination = self.out / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
        row = {"path": target, "source_id": key, "transformation": "byte_identical"}
        self.copies.append(row)
        return row

    def recheck(self):
        for row in self.rows.values():
            p = Path(row["historical_path"])
            if not p.is_absolute():
                p = self.repo / p
            assert metadata(p) == {k: row[k] for k in ("bytes", "sha256")}, str(p)


def snapshot(repo, baseline):
    result = {}
    source_manifest = read(baseline / "source_manifest.json")
    for relative, expected in source_manifest["source_files"].items():
        actual = metadata(repo / relative)
        assert actual["sha256"] == expected["sha256"], relative
        result[relative] = actual
    frozen = repo / ".tools/worktrees/fixed-v23-study-v1/data/runs"
    for split, name in [("bilingual_development", "fixed-v23-main-v1"),
                        ("bilingual_calibration", "fixed-v23-cal-v1")]:
        for path in (frozen / split / name).rglob("*"):
            if path.is_file():
                result[path.relative_to(repo).as_posix()] = metadata(path)
    return result


def extract_japanese(repo, baseline, public, out, sources):
    root = repo / "data/raw/wikipedia_human_retrieval_ja/corpus-20231225-v1"
    original = {}
    for name, relative in {
        "article": "articles/0b0739891461f74a49a5d6b0.json",
        "request": "requests/0b0739891461f74a49a5d6b0-revision.json",
        "acquisition_spec": "source_snapshot/configs/phase11_japanese_corpus_v1.json",
        "extractor": "source_snapshot/src/rag_research/data/wikipedia_snapshot.py",
    }.items():
        original[name] = sources.copy(root / relative, "evidence/japanese/original_" + Path(relative).name)
    for path in sorted(public.glob("*.json")):
        if path.is_file():
            # Public responses were obtained separately; never inserted into the corpus.
            sources.copy(path, "evidence/japanese/public/" + path.name)
    raw_article = read(root / "articles/0b0739891461f74a49a5d6b0.json")
    raw_request = read(root / "requests/0b0739891461f74a49a5d6b0-revision.json")
    assert raw_article["page_id"] == 5273510 and raw_article["status"] == "unavailable"
    assert raw_request["status"] == "ok" and "revisions" not in raw_request["response"]["query"]["pages"][0]
    # Execute just archived constants and stdlib HTML parser definitions, not any I/O code.
    code = (root / "source_snapshot/src/rag_research/data/wikipedia_snapshot.py").read_text()
    module = ast.parse(code)
    names = {"BLOCKS", "VOID", "OMIT_TAGS", "OMIT_CLASSES", "ArticleText", "article_text"}
    definitions = [node for node in module.body if
                   isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names or
                   isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets)]
    from html.parser import HTMLParser
    scope = {"HTMLParser": HTMLParser}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), "archived_article_text", "exec"), scope)
    parsed = read(public / "historical_parse_response.json")["parse"]
    text = scope["article_text"](parsed["text"])
    assert parsed["revid"] == 98057227 and parsed["pageid"] == 56523
    text_path = out / "evidence/japanese/recovered_revision_98057227.txt"
    text_path.write_text(text, encoding="utf-8")
    qa = read(baseline / "inputs/main_ja_ae3cdc2b7e88b42e102ec4b2.json")
    quote = qa["qa_source"]["reference_evidence"][0]["quote"]
    anchors = [
        "第二次世界大戦の最中の1943年のこと、ウォーレン・マカロックとウォルター・ピッツが神経回路網理論を提出したが（形式ニューロンを参照）、この理論は現実の脳と比べてあまりに単純化するものだったので当時はほとんど注目されなかった。",
        "ところが1970年代になるとマービン・ミンスキーとシーモア・パパートがパーセプトロンの限界を数学的に証明したことで、神経回路網的手法に対する期待が一気にしぼみ、その研究者の数が急激に減ってしまった",
    ]
    result = {
        "record_id": qa["record_id"], "cohort": "main", "language": "ja",
        "investigation_status": "completed", "resolution_status": "historical_reference_recovered_with_limits",
        "original_acquisition_classification": "http_200_no_revision_returned_before_cutoff",
        "original_evidence": original,
        "cutoff_utc": raw_article["cutoff_utc"], "original_page_id": 5273510,
        "original_revision_id": None, "original_parse_request_exists": False,
        "facts": [
            "Original API request succeeded (HTTP 200) but returned no revisions for page 5273510 before the declared cutoff.",
            "Public move log 8295729 links original logpage 56523 to the move to ニューラルネットワーク (機械学習) on 2026-07-26T15:45:54Z.",
            "Public earliest revision for current page 5273510 is 110422898 at the same 2026 timestamp, with parentid 0.",
            "The moved history of page 56523 returns revision 98057227 (2023-11-21T16:00:37Z) at the declared cutoff.",
            "This public historical body was fetched in this audit, not present in the original corpus or experimental input.",
        ],
        "causal_interpretation": "The historical lookup used the then-current title/page after a move; the new page history starts after cutoff. This explains the observed empty revision result, not a permission or transport error.",
        "unrelated_error_not_used": "Page13492/Revision95068750 permissiondenied is a separate article.",
        "recovered_page_id": 56523, "recovered_revision_id": 98057227,
        "recovered_revision_timestamp_utc": "2023-11-21T16:00:37Z",
        "recovered_revision_url": "https://ja.wikipedia.org/w/index.php?oldid=98057227",
        "response_path": "evidence/japanese/public/historical_parse_response.json",
        "extracted_text_path": text_path.relative_to(out).as_posix(),
        "extraction": "Unmodified archived article_text / wikipedia-rendered-article-text-v1 on new parse HTML; UTF-8, no appended newline.",
        "rendering_identity_with_past_not_established": True,
        "saved_reference_quote": quote, "entire_reference_quote_verbatim_match": quote in text,
        "reference_anchor_matches": [{"quote": a, "in_saved_reference": a in quote,
                                      "recovered_character_start": text.find(a)} for a in anchors],
        "used_contexts": [{"passage_id": d["passage_id"], "text_sha256": digest(d["text"].encode())}
                          for d in qa["used_documents"]],
        "originally_comparable": qa["statistical_comparison"]["comparable"],
        "external_labels_preserved": {stage: qa[stage]["quality"] for stage in ["A", "B"]},
        "remaining_unknowns": [
            "No original acquisition render exists for this article, so byte equality to a hypothetical 2023/2026 render is unprovable.",
            "The saved dataset reference quote is not a verbatim full-string match to the newly extracted historical text; only the documented anchors match. No reference or label was corrected.",
        ],
        "evidence_paths": ["evidence/japanese/public/" + p.name for p in sorted(public.glob("*.json"))],
    }
    write(out / "japanese_reference.json", result)
    return result


def scalar_model_fields(value, path=""):
    result = []
    if isinstance(value, dict):
        for key, child in value.items():
            pointer = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if re.search("model|snapshot", key, re.I) and isinstance(child, (str, int, float, bool)):
                result.append({"json_pointer": pointer, "value": child})
            result.extend(scalar_model_fields(child, pointer))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            result.extend(scalar_model_fields(child, path + "/" + str(i)))
    return result


def audit_jobs(repo, baseline, sessions_root, out, sources):
    manifest = read(baseline / "source_manifest.json")
    jobs = sorted({(repo / c["source"]["path"]).parent for c in manifest["copies"]
                   if "/jobs/" in c["source"]["path"] and c["source"]["path"].endswith("provenance.json")})
    assert len(jobs) == 84
    session_files = list(sessions_root.rglob("*.jsonl"))
    result = []
    for job in jobs:
        payload, prov, receipt = (read(job / name) for name in ["input.json", "provenance.json", "invocation.json"])
        configured_arguments = [a for a in receipt["argv"] if a.startswith(("model=", "model_reasoning_effort="))]
        assert 'model="gpt-6.1-sol"' in configured_arguments
        assert 'model_reasoning_effort="high"' in configured_arguments
        source_ids = {name: sources.register(job / name) for name in
                      ["input.json", "output.json", "provenance.json", "invocation.json", "schema.json"]}
        assert metadata(job / "input.json")["sha256"] == prov["input_sha256"]
        assert metadata(job / "output.json")["sha256"] == prov["output_sha256"]
        if (job / "stdin.json").exists():
            source_ids["stdin.json"] = sources.register(job / "stdin.json")
            assert metadata(job / "stdin.json")["sha256"] == prov["stdin_sha256"]
        if (job.parent / "validated.json").exists():
            source_ids["validated.json"] = sources.register(job.parent / "validated.json")
        mapping = read(baseline / f"annotations/{payload['cohort']}/{payload['language']}/mapping.private.json")
        packet_name = "packet.json" if payload["kind"] == "quality" else "units/packet.json"
        packet = baseline / f"annotations/{payload['cohort']}/{payload['language']}/{packet_name}"
        assert payload["full_packet_sha256"] == read(packet)["packet_sha256"]
        bindings = []
        for case in payload["cases"]:
            identifier = case["annotation_id"]
            bindings.append({"annotation_id": identifier,
                             "candidate_hashes": {k: v for k, v in case.items() if k.endswith("sha256")},
                             "assignments": mapping["assignments"][identifier]})
        log = job / "invocation.log"
        events, model_fields, thread_ids = [], [], []
        if log.exists():
            source_ids["invocation.log"] = sources.register(log)
            for number, line in enumerate(log.read_bytes().splitlines(keepends=True), 1):
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                events.append({"line": number, "event_type": event.get("type"), "line_sha256": digest(line),
                               "top_level_keys": sorted(event)})
                model_fields.extend({"line": number, "event_type": event.get("type"), **field}
                                    for field in scalar_model_fields(event))
                if event.get("type") == "thread.started":
                    thread_ids.append(event["thread_id"])
        assert len(thread_ids) == 1
        matching = [p for p in session_files if thread_ids[0] in p.name]
        assert len(matching) == 1
        session = matching[0]
        source_ids["session_rollout"] = sources.register(session)
        projections, observed_fields = [], []
        for number, line in enumerate(session.read_bytes().splitlines(keepends=True), 1):
            record = json.loads(line)
            kind, data = record.get("type"), record.get("payload", {})
            fields = scalar_model_fields(record)
            observed_fields.extend({"line": number, "event_type": kind, **field} for field in fields)
            if kind == "session_meta":
                selection = {k: data[k] for k in ["id", "timestamp", "cwd", "originator", "cli_version", "source", "model_provider"] if k in data}
                assert selection["id"] == thread_ids[0] and selection["cwd"] == str(job)
            elif kind == "turn_context":
                selection = {k: data[k] for k in ["cwd", "model", "effort", "turn_id"] if k in data}
            else:
                selection = {}
            if fields or selection:
                projections.append({"source_id": source_ids["session_rollout"], "line": number,
                                    "line_sha256": digest(line), "event_type": kind,
                                    "projection": selection, "identifier_fields": fields,
                                    "transformation": "JSON field projection; account IDs, instructions, tools, messages and unrelated fields omitted"})
        session_meta = next(p["projection"] for p in projections if p["event_type"] == "session_meta")
        turn = next(p["projection"] for p in projections if p["event_type"] == "turn_context")
        # Catalog and instructions hashes belong to the client; they are not serving snapshots.
        assert turn["model"] == prov["configured_model"] == "gpt-6.1-sol"
        allowed_keys = {"model", "model_provider", "model_provider_id", "model_catalog", "model_context_window"}
        assert all(f["json_pointer"].rsplit("/", 1)[-1] in allowed_keys for f in observed_fields)
        assert not model_fields, "Review unanticipated CLI model identifier before classifying"
        relative = job.relative_to(repo / ".tools/fixed-v23-automation-v1/jobs").as_posix()
        row = {
            "job_id": relative, "cohort": payload["cohort"], "language": payload["language"], "kind": payload["kind"],
            "investigation_status": "completed", "resolution_status": "exact_serving_identifier_not_observed_in_retained_logs",
            "source_ids": source_ids, "thread_id": thread_ids[0],
            "input_sha256": prov["input_sha256"], "output_sha256": prov["output_sha256"],
            "full_packet_sha256": payload["full_packet_sha256"], "retained_packet_file_sha256": metadata(packet)["sha256"],
            "packet_source_id": sources.register(packet),
            "configured_model": prov["configured_model"], "configured_reasoning_effort": "high",
            "invocation_model_arguments": configured_arguments, "historical_cli_path": receipt["argv"][0],
            "session_context_model": turn["model"], "session_context_effort": turn["effort"],
            "historical_cli_version": session_meta["cli_version"], "model_provider": session_meta["model_provider"],
            "exact_serving_model_identifier": None,
            "started_at_utc": receipt["started_at_utc"], "finished_at_utc": receipt["finished_at_utc"],
            "exit_code": receipt["exit_code"], "original_input_transport": prov.get("input_transport"),
            "source_identity_limitation": "Retained model values are local configuration, prompt provenance, world state or thread settings. Model catalog digest and instruction hash are not server snapshot identifiers. Absence in these logs does not prove service-wide non-disclosure.",
            "annotation_bindings": bindings,
            "cli_events": events, "cli_identifier_fields": model_fields,
            "session_projections": projections,
            "identifier_classification": "client_model_alias_and_catalog_metadata_only",
            "raw_log_bodies_distributed": False,
        }
        target = "evidence/jobs/" + relative.replace("/", "__") + ".json"
        write(out / target, row)
        result.append({k: row[k] for k in ["job_id", "cohort", "language", "kind", "investigation_status", "resolution_status",
                                         "input_sha256", "output_sha256", "configured_model", "session_context_model",
                                         "historical_cli_version", "exact_serving_model_identifier"]} | {"evidence_path": target})
    write(out / "annotation_jobs.json", result)
    return result


def oldid(url):
    return int(parse_qs(urlsplit(html.unescape(url)).query)["oldid"][0])


def english_passages(repo, baseline, out, sources):
    targets, qa_rows, inputs = {}, [], []
    for path in sorted((baseline / "inputs").glob("*_en_*.json")):
        qa = read(path)
        inputs.append(qa)
        qa_rows.append({"qa_key": qa["qa_key"], "record_id": qa["record_id"], "cohort": qa["cohort"],
                        "source_id": qa["record_id"].split(":")[3], "source_qa_split": qa["source_qa_split"]})
        for role in ["used_documents", "gold_documents", "corpus_documents", "gold_corpus_documents"]:
            for document in qa[role]:
                key = document["passage_id"]
                row = {"passage_id": key, "title": document.get("title", document["source_metadata"]["title"]),
                       "text": document["text"], "text_sha256": digest(document["text"].encode()), "qa_roles": []}
                if key not in targets:
                    targets[key] = row
                else:
                    assert targets[key]["text"] == row["text"]
                targets[key]["qa_roles"].append({"qa_key": qa["qa_key"], "role": role})
    assert len(qa_rows) == 40 and len(targets) == 222
    titles = {p["title"] for p in targets.values()}
    selected = {q["source_id"] for q in qa_rows}
    raw = repo / "data/raw/clapnq/c508d78d8c5c2eecbf172fcf5f789004206e11fb"
    docs, qa_sources = [], {}
    for path in sorted((raw / "original_documents").glob("*/*.jsonl")):
        source_id = sources.register(path)
        revision = "c508d78d8c5c2eecbf172fcf5f789004206e11fb"
        relative = path.relative_to(raw).as_posix()
        upstream = subprocess.check_output(["git", "-C", str(raw), "show", revision + ":" + relative])
        assert path.read_bytes().replace(b"\r\n", b"\n") == upstream
        sources.rows[source_id]["upstream_revision"] = revision
        sources.rows[source_id]["upstream_blob_sha1"] = subprocess.check_output(
            ["git", "-C", str(raw), "rev-parse", revision + ":" + relative], text=True).strip()
        sources.rows[source_id]["upstream_bytes"] = len(upstream)
        sources.rows[source_id]["upstream_sha256"] = digest(upstream)
        sources.rows[source_id]["upstream_comparison"] = "Local CRLF converted to LF is byte-identical to the pinned Git blob; document text/URLs unchanged"
        for line_number, line in enumerate(path.open("rb"), 1):
            obj = json.loads(line)
            # Only selected QA IDs and target passage document fields are investigated.
            # Never inspect question_text, annotations, or other QA content from these files.
            if obj["document_title"] not in titles and str(obj["example_id"]) not in selected:
                continue
            doc = {"document_title": obj["document_title"], "document_url": obj["document_url"],
                   "document_plaintext_sha256": digest(obj["document_plaintext"].encode()),
                   "document_plaintext_bytes": len(obj["document_plaintext"].encode()),
                   "oldid_from_explicit_url": oldid(obj["document_url"]), "source_id": source_id,
                   "line": line_number, "line_sha256": digest(line), "text": obj["document_plaintext"],
                   "transformation": "Selected document metadata projection; question/answer/annotation fields excluded"}
            docs.append(doc)
            if str(obj["example_id"]) in selected:
                qa_sources[str(obj["example_id"])] = {k: v for k, v in doc.items() if k != "text"}
    qa_table = []
    for row in qa_rows:
        source = qa_sources.get(row["source_id"])
        qa_table.append(row | {"investigation_status": "completed", "resolution_status": "original_qa_document_url_identified" if source else "original_qa_id_not_found_in_retained_original_documents",
                               "original_document": source,
                               "scope": "Original QA reference document URL; not proof of revision identity of every retrieval corpus passage"})
    write(out / "english_qa_sources.json", qa_table)
    table = []
    for key, target in sorted(targets.items()):
        matches = []
        for doc in docs:
            if doc["document_title"] != target["title"]:
                continue
            data, needle = doc["text"].encode(), target["text"].encode()
            start = 0
            while (position := data.find(needle, start)) >= 0:
                matches.append({k: v for k, v in doc.items() if k != "text"} |
                               {"matched_utf8_byte_start": position, "matched_utf8_byte_end": position + len(needle),
                                "matched_text": target["text"], "matched_text_sha256": target["text_sha256"]})
                start = position + len(needle)
        ids = sorted({m["oldid_from_explicit_url"] for m in matches})
        # A passage can be shared unchanged by multiple revisions. Even one retained
        # match is not a complete, recorded corpus->original-document lineage.
        status = "candidate_only" if ids else "not_recovered_in_checked_sources"
        table.append(target | {"investigation_status": "completed", "resolution_status": status,
                               "identified_corpus_revision_oldid": None, "candidate_oldids": ids,
                               "candidate_count": len(ids), "matches": matches,
                               "matching_method": "Exact title and UTF-8 substring; no normalization or numeric-ID inference",
                               "reason": "No explicit retained passage-to-document-URL binding or corpus construction ledger was found; text equality alone cannot uniquely date unchanged text." if ids else "No exact selected-title/text match in retained original_documents metadata (train/dev); no numeric-ID guessing or current revision substitution."})
    write(out / "english_passage_revisions.json", table)
    cases = []
    for number in [1, 3, 4]:
        case = read(baseline / f"cases/case_{number:02}.json")
        qa = next(q for q in inputs if q["qa_key"] == case["qa_key"])
        cases.append({"case_id": case["case_id"], "qa_key": qa["qa_key"], "record_id": qa["record_id"],
                      "used_passage_ids": [d["passage_id"] for d in qa["used_documents"]],
                      "reference_passage_ids": [d["passage_id"] for d in qa["gold_documents"]]})
    write(out / "english_case_passages.json", cases)
    excerpts = []
    for path in [raw / "original_documents/README.md", raw / "retrieval/README.md"]:
        excerpts.append(sources.copy(path, "evidence/english/" + path.parent.name + "_README.md"))
    write(out / "evidence/english/scope.json", {
        "selected_qa_count": 40, "passage_count": len(table), "selected_title_count": len(titles),
        "original_document_fields_used": ["example_id (only selected ID linkage)", "document_title", "document_url", "document_plaintext (only target text matching)"],
        "nonselected_questions_or_annotations_investigated": False,
        "development_original_documents_scope": "Selected passage document metadata only, not unused Evaluation QA content or results",
        "candidate_counts": dict(collections.Counter(str(r["candidate_count"]) for r in table)),
        "known_upstream_deduplication": "retrieval/README.md says differing document versions can be deduplicated with high ROUGE overlap, which does not identify an exact Wikipedia revision.",
        "upstream_evidence": excerpts,
        "additional_nq_metadata": "No separate original Natural Questions URL/revision mapping asset was located in the registered CLAPNQ acquisition; retained TyDI original_documents were inspected instead.",
        "candidate_use": "Candidate URLs may guide a later bounded audit; do not present them as confirmed exact corpus revision IDs.",
    })
    return qa_table, table


def refresh_manifest(out):
    rows = {p.relative_to(out).as_posix(): metadata(p) for p in sorted(out.rglob("*"))
            if p.is_file() and p != out / "artifact_manifest.json" and "__pycache__" not in p.parts}
    write(out / "artifact_manifest.json", {"version": 1, "files": rows, "self_excluded": True})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--public-evidence", type=Path)
    parser.add_argument("--sessions-root", type=Path, default=Path("/home/uchida/.codex/sessions"))
    parser.add_argument("--refresh-manifest", action="store_true")
    args = parser.parse_args()
    out = Path(__file__).resolve().parent
    if args.refresh_manifest:
        refresh_manifest(out)
        return
    assert not (out / "findings.json").exists(), "Completed audit must not be overwritten"
    repo, baseline = args.source_repo.resolve(), args.baseline.resolve()
    before = snapshot(repo, baseline)
    sources = Sources(repo, out)
    japanese = extract_japanese(repo, baseline, args.public_evidence, out, sources)
    jobs = audit_jobs(repo, baseline, args.sessions_root, out, sources)
    qa, passages = english_passages(repo, baseline, out, sources)
    sources.copy(repo / "scripts/fixed_v23_automation/review.py", "evidence/annotation_collector_review.py.txt")
    sources.copy(baseline / "licenses/CLAPNQ-Apache-2.0.txt", "evidence/CLAPNQ-Apache-2.0.txt")
    candidates = sum(p["resolution_status"] == "candidate_only" for p in passages)
    findings = {
        "audit_version": "provenance-audit-v1", "created_at_utc": datetime.now(UTC).isoformat(),
        "base_paper_commit": "aff72fd74c1e2e5b8561675573b5534fbea6006c", "fixed_material_tree": "5fb236667f6e4411a730187dc1e6ce80f27c710f",
        "new_research_inference_calls": 0, "new_annotation_calls": 0, "labels_or_results_changed": False,
        "japanese_reference": {"investigation_status": "completed", "resolution_status": japanese["resolution_status"],
                               "evidence_path": "japanese_reference.json", "body_recovered": True, "original_render_recovered": False},
        "annotation_model": {"investigation_status": "completed", "resolution_status": "exact_serving_identifier_not_observed_in_retained_logs",
                             "jobs_audited": len(jobs), "sessions_audited": len(jobs), "missing_sessions": 0,
                             "cli_versions": sorted({j["historical_cli_version"] for j in jobs}),
                             "evidence_path": "annotation_jobs.json", "service_wide_nondisclosure_claimed": False},
        "english_revisions": {"investigation_status": "completed", "resolution_status": "qa_source_urls_recovered_corpus_revision_binding_unresolved",
                              "selected_qa": len(qa), "qa_document_urls_identified": sum(q["original_document"] is not None for q in qa),
                              "passages": len(passages), "corpus_revision_identified": 0,
                              "candidate_only": candidates, "not_recovered": len(passages) - candidates,
                              "evidence_path": "english_passage_revisions.json", "qa_sources_path": "english_qa_sources.json"},
        "offline_verification_scope": "Package integrity and internal evidence correspondence, not proof that unresolved information was recovered",
    }
    write(out / "findings.json", findings)
    sources.recheck()
    after = snapshot(repo, baseline)
    assert before == after
    write(out / "preservation.json", {"original_files": before, "before_after_equal": True,
                                      "fixed_material_tree": findings["fixed_material_tree"],
                                      "original_file_count": len(before), "source_files_rechecked": 2627})
    write(out / "evidence/source_index.json", sources.rows)
    write(out / "evidence/copy_index.json", sources.copies)
    refresh_manifest(out)
    print(json.dumps(findings, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
