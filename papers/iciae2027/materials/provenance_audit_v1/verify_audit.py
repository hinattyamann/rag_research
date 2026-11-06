"""Offline integrity and evidence-correspondence checks, using only this folder."""

import argparse
import ast
import hashlib
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, urlsplit


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def confined(root, relative):
    p = PurePosixPath(relative)
    require(not p.is_absolute() and ".." not in p.parts and "\\" not in relative, "Unsafe relative path")
    path = root / relative
    require(path.resolve().is_relative_to(root.resolve()) and not path.is_symlink(), "Path escapes package")
    return path


def verify(root):
    root = root.resolve()
    def load(name):
        return json.loads(confined(root, name).read_bytes())
    manifest = load("artifact_manifest.json")
    files = manifest["files"]
    actual = set()
    for path in root.rglob("*"):
        require(not path.is_symlink(), "Symlink in package")
        if path.is_file() and path != root / "artifact_manifest.json" and "__pycache__" not in path.parts:
            actual.add(path.relative_to(root).as_posix())
    require(actual == set(files), "Manifest file inventory mismatch")
    for relative, expected in files.items():
        data = confined(root, relative).read_bytes()
        require(len(data) == expected["bytes"] and sha(data) == expected["sha256"], "Hash mismatch: " + relative)

    source_index = load("evidence/source_index.json")
    for row in source_index.values():
        require(re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None and row["bytes"] > 0,
                "Missing original source hash/size")
    for copy in load("evidence/copy_index.json"):
        data = confined(root, copy["path"]).read_bytes()
        original = source_index[copy["source_id"]]
        require(sha(data) == original["sha256"] and len(data) == original["bytes"], "Exact source copy mismatch")

    findings = load("findings.json")
    require(findings["fixed_material_tree"] == "5fb236667f6e4411a730187dc1e6ce80f27c710f", "Baseline tree changed")
    require(findings["new_research_inference_calls"] == findings["new_annotation_calls"] == 0 and
            findings["labels_or_results_changed"] is False, "Forbidden research changes")
    for item in ["japanese_reference", "annotation_model", "english_revisions"]:
        require(findings[item]["investigation_status"] == "completed" and findings[item]["resolution_status"], "Missing investigation/resolution state")
        confined(root, findings[item]["evidence_path"]).read_bytes()

    ja = load("japanese_reference.json")
    article = load(ja["original_evidence"]["article"]["path"])
    request = load(ja["original_evidence"]["request"]["path"])
    require(article["page_id"] == 5273510 and article["status"] == "unavailable", "Original acquisition identity")
    require(request["status"] == "ok" and request["attempts"][0]["http_status"] == 200 and
            "revisions" not in request["response"]["query"]["pages"][0], "Wrong original failure classification")
    for name in ["cutoff", "earliest", "move_log", "delete_log", "moved_cutoff", "historical_parse"]:
        record = load(f"evidence/japanese/public/{name}_request.json")
        data = confined(root, f"evidence/japanese/public/{name}_response.json").read_bytes()
        require(record["http_status"] == 200 and record["retrieved_at_utc"] and
                sha(data) == record["response_sha256"] and len(data) == record["bytes"], "Public response provenance mismatch")
    move = load("evidence/japanese/public/move_log_response.json")["query"]["logevents"]
    require(any(m["logid"] == 8295729 and m["logpage"] == 56523 and
                m["params"]["target_title"] == "ニューラルネットワーク (機械学習)" for m in move), "Move evidence absent")
    earliest = load("evidence/japanese/public/earliest_response.json")["query"]["pages"][0]
    require(earliest["pageid"] == 5273510 and earliest["revisions"][0]["parentid"] == 0 and
            earliest["revisions"][0]["timestamp"] == "2026-07-26T15:45:54Z", "New-page history evidence")
    historical = load("evidence/japanese/public/moved_cutoff_response.json")["query"]["pages"][0]
    require(historical["pageid"] == 56523 and historical["revisions"][0]["revid"] == 98057227, "Cutoff history evidence")
    parsed = load(ja["response_path"])["parse"]
    require(parsed["revid"] == ja["recovered_revision_id"] == 98057227 and parsed["pageid"] == 56523, "Recovered page identity")
    text = confined(root, ja["extracted_text_path"]).read_text(encoding="utf-8")
    archived_code = confined(root, ja["original_evidence"]["extractor"]["path"]).read_text(encoding="utf-8")
    names = {"BLOCKS", "VOID", "OMIT_TAGS", "OMIT_CLASSES", "ArticleText", "article_text"}
    definitions = [node for node in ast.parse(archived_code).body if
                   isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names or
                   isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets)]
    namespace = {"HTMLParser": HTMLParser}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), "archived_text_extractor", "exec"), namespace)
    require(namespace["article_text"](parsed["text"]) == text, "Historical HTML/text extraction mismatch")
    require(ja["rendering_identity_with_past_not_established"] is True, "Rendering limit suppressed")
    require(ja["entire_reference_quote_verbatim_match"] == (ja["saved_reference_quote"] in text) is False, "Quote mismatch suppressed")
    for anchor in ja["reference_anchor_matches"]:
        start = anchor["recovered_character_start"]
        require(start >= 0 and text[start:start + len(anchor["quote"]) ] == anchor["quote"] and
                anchor["quote"] in ja["saved_reference_quote"], "Reference anchor mismatch")
    require(len(ja["used_contexts"]) == 5 and ja["originally_comparable"] is True, "Actual input/reference distinction lost")

    jobs = load("annotation_jobs.json")
    require(len(jobs) == 84 and len({j["job_id"] for j in jobs}) == 84, "84 job coverage")
    for job in jobs:
        evidence = load(job["evidence_path"])
        require(evidence["job_id"] == job["job_id"] and evidence["investigation_status"] == "completed", "Job evidence correspondence")
        require(evidence["exact_serving_model_identifier"] is None and job["exact_serving_model_identifier"] is None and
                evidence["resolution_status"] == "exact_serving_identifier_not_observed_in_retained_logs", "Unsupported serving ID claim")
        require(evidence["configured_model"] == evidence["session_context_model"] == "gpt-6.1-sol" and
                evidence["configured_reasoning_effort"] == evidence["session_context_effort"] == "high", "Historical configuration mismatch")
        require(evidence["historical_cli_version"] == "0.164.0-alpha.11.1", "Missing historical version")
        for name, field in [("input.json", "input_sha256"), ("output.json", "output_sha256")]:
            require(source_index[evidence["source_ids"][name]]["sha256"] == evidence[field] == job[field], "Job input/output hash mismatch")
        require(source_index[evidence["packet_source_id"]]["sha256"] == evidence["retained_packet_file_sha256"], "Packet hash mismatch")
        session_source = source_index[evidence["source_ids"]["session_rollout"]]
        require(evidence["thread_id"] in session_source["historical_path"], "Session thread mismatch")
        require(evidence["cli_identifier_fields"] == [] and evidence["raw_log_bodies_distributed"] is False, "Unexpected raw/identifier data")
        for projection in evidence["session_projections"]:
            require(projection["source_id"] == evidence["source_ids"]["session_rollout"] and
                    projection["line"] > 0 and len(projection["line_sha256"]) == 64, "Session excerpt provenance missing")
        require(evidence["annotation_bindings"], "Missing anonymous packet mapping")
        for binding in evidence["annotation_bindings"]:
            require(binding["assignments"] and binding["candidate_hashes"] and binding["annotation_id"].startswith("Q-"), "Missing candidate/stage mapping")
    require(findings["annotation_model"]["jobs_audited"] == findings["annotation_model"]["sessions_audited"] == len(jobs) and
            findings["annotation_model"]["service_wide_nondisclosure_claimed"] is False, "Model audit scope overstated")

    qas, passages = load("english_qa_sources.json"), load("english_passage_revisions.json")
    require(len(qas) == 40 and len({q["qa_key"] for q in qas}) == 40, "English 40 QA coverage")
    require(len(passages) == 222 and len({p["passage_id"] for p in passages}) == 222, "English passage coverage")
    identified_qas = 0
    for qa in qas:
        require(qa["investigation_status"] == "completed" and qa["resolution_status"], "Missing QA investigation state")
        if qa["original_document"]:
            identified_qas += 1
            require(qa["original_document"]["source_id"] in source_index, "QA original source missing")
    counts = {"candidate_only": 0, "not_recovered_in_checked_sources": 0}
    by_id = {p["passage_id"]: p for p in passages}
    for passage in passages:
        require(passage["investigation_status"] == "completed" and passage["resolution_status"] in counts, "Missing passage investigation state")
        require(passage["identified_corpus_revision_oldid"] is None, "Candidate upgraded to identified revision")
        require(sha(passage["text"].encode()) == passage["text_sha256"], "Passage text hash mismatch")
        observed = set()
        for match in passage["matches"]:
            source = source_index[match["source_id"]]
            require(source.get("upstream_revision") == "c508d78d8c5c2eecbf172fcf5f789004206e11fb", "Upstream file version missing")
            require(match["matched_text"] == passage["text"] and match["matched_text_sha256"] == passage["text_sha256"], "Passage substring evidence mismatch")
            require(match["matched_utf8_byte_end"] - match["matched_utf8_byte_start"] == len(passage["text"].encode()), "Passage byte span mismatch")
            explicit = int(parse_qs(urlsplit(html.unescape(match["document_url"])).query)["oldid"][0])
            require(explicit == match["oldid_from_explicit_url"], "URL identifier mismatch")
            observed.add(explicit)
        require(sorted(observed) == passage["candidate_oldids"] and len(observed) == passage["candidate_count"], "Candidate correspondence mismatch")
        require(bool(observed) == (passage["resolution_status"] == "candidate_only"), "Passage state inconsistent with evidence")
        counts[passage["resolution_status"]] += 1
    en = findings["english_revisions"]
    require(identified_qas == en["qa_document_urls_identified"] == 36 and
            counts["candidate_only"] == en["candidate_only"] == 199 and
            counts["not_recovered_in_checked_sources"] == en["not_recovered"] == 23 and
            en["corpus_revision_identified"] == 0, "English summary mismatch")
    for case in load("english_case_passages.json"):
        require(case["qa_key"] in {q["qa_key"] for q in qas}, "Case QA absent")
        for identifier in case["used_passage_ids"] + case["reference_passage_ids"]:
            require(identifier in by_id, "Case passage absent")
    preservation = load("preservation.json")
    require(preservation["before_after_equal"] is True and
            len(preservation["original_files"]) == preservation["original_file_count"], "Source preservation record inconsistent")
    return {"status": "passed", "artifact_files": len(files), "japanese_historical_body_recovered": True,
            "original_render_identity_established": False, "annotation_jobs": len(jobs), "historical_sessions": len(jobs),
            "exact_serving_identifier_recovered": False, "english_selected_qa": len(qas),
            "english_qa_source_urls_identified": identified_qas, "english_passages": len(passages),
            "english_passage_candidates": counts["candidate_only"], "english_passages_not_recovered": counts["not_recovered_in_checked_sources"],
            "exact_corpus_revision_bindings_recovered": 0, "original_files_preserved": preservation["original_file_count"],
            "original_run_or_auth_required": False, "new_research_inference_calls": 0, "new_annotation_calls": 0}


def install_audit(root):
    root = root.resolve()

    def audit(event, args):
        if event == "open" and isinstance(args[0], (str, bytes)):
            path = Path(args[0].decode() if isinstance(args[0], bytes) else args[0]).resolve()
            require(path.is_relative_to(root), "Data access outside supplemental package")
        if event.startswith("socket."):
            raise ValueError("Network access forbidden during offline verification")
    sys.addaudithook(audit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-open", action="store_true")
    options = parser.parse_args()
    directory = Path(__file__).resolve().parent
    if options.audit_open:
        # All imports are completed before enforcing the data-access boundary.
        install_audit(directory)
    print(json.dumps(verify(directory), ensure_ascii=False, indent=2))
