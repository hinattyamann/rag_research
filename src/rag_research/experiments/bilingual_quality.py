"""Blind bilingual quality packets with explicit offline source provenance."""

import json
from collections import defaultdict
from pathlib import Path

from rag_research.data.study_assets import load_assets, parent_map
from rag_research.evaluation.order import trial_plan
from rag_research.experiments.decisions import decide
from rag_research.experiments.frozen_trace import digest, freeze_record, require
from rag_research.experiments.protocol import ROOT
from rag_research.experiments.quality import (
    blank_annotations,
    make_packet,
    reconstruct,
    validate_annotations,
    verify_packet,
)
from rag_research.experiments.storage import (
    checkpoint,
    read_json,
    run_lock,
    verify_checkpoint,
    write_json,
)
from rag_research.retrieval.common import file_hash


def read_run(run):
    require(run.is_relative_to(ROOT / "data/runs/bilingual_development"), "Unexpected bilingual run path")
    manifest, report = read_json(run / "manifest.json"), read_json(run / "report.private.json")
    require(report["manifest_sha256"] == digest(manifest), "Bilingual report binding differs")
    for name, expected in manifest["source_sha256"].items():
        require(file_hash(ROOT / name) == expected, "Bilingual source changed: " + name)
    selection = {r["record_id"] for r in manifest["selection"]}
    ids = [r["trace"]["record_id"] for r in report["records"]]
    failed_ids = [r["record_id"] for r in report["failures"]]
    require(len(set(ids + failed_ids)) == len(ids + failed_ids) and set(ids + failed_ids) == selection and
            report["selected_qa_count"] == len(selection),
            "Selected/failed/candidate record set differs")
    internal = read_json(run / "internal/manifest.json")
    require(internal == {"manifest_sha256": digest(manifest), "traces": [
        {"record_id": row["trace"]["record_id"], "directory": digest(row["trace"]["record_id"])[:24],
         "trace_sha256": row["trace"]["trace_sha256"], "plan": trial_plan(row["trace"], manifest["config"])}
        for row in report["records"]]}, "Internal run plan differs")
    for failure in report["failures"]:
        baseline = read_json(run / "baseline" / digest(failure["record_id"])[:24] / "record.json")
        verify_checkpoint(baseline)
        require(baseline["binding"] == {"manifest_sha256": digest(manifest)} and
                failure["status"] == baseline["status"] and failure["error"] == baseline.get("error") and
                (baseline["status"] != "ok" or not baseline.get("used_context")), "Failure provenance differs")
    for row in report["records"]:
        trace = row["trace"]
        baseline = read_json(run / "baseline" / digest(trace["record_id"])[:24] / "record.json")
        verify_checkpoint(baseline)
        require(baseline["binding"] == {"manifest_sha256": digest(manifest)} and
                freeze_record(baseline) == trace, "Baseline/trace binding differs")
        require(row["baseline_cost"] == {k: baseline.get(k) for k in
                ("input_tokens", "output_tokens", "generation_seconds", "context_seconds", "answer_generation_calls")},
                "Baseline cost changed")
        folder = run / "internal" / digest(trace["record_id"])[:24]
        require(read_json(folder / "trace.json") == trace and
                read_json(folder / "summary.json") == row["evaluation"], "Trace/evaluation changed")
        require(trace["trace_sha256"] == digest({k: v for k, v in trace.items() if k != "trace_sha256"}),
                "Frozen trace hash differs")
        require(row["rewrite"] == read_json(folder / "rewrite.json"), "Rewrite changed")
        require(row["tasks"]["extraction"] == read_json(folder / "claims.json"), "Extraction changed")
        entry = next(e for e in internal["traces"] if e["record_id"] == trace["record_id"])
        task_binding = {"manifest_sha256": digest({**internal, "traces": [entry]}),
                        "trace_sha256": trace["trace_sha256"]}
        extraction = row["tasks"]["extraction"]
        claims = extraction["parsed"]["claims"] if extraction["status"] == "ok" else []
        require(row["rewrite"]["binding"] == task_binding and extraction["binding"] == task_binding and
                row["evaluation"]["claims"] == claims and row["evaluation"]["threshold"] ==
                manifest["config"]["decision"]["threshold"] and row["evaluation"]["plan"] == entry["plan"],
                "Internal task/claim/threshold binding differs")
        expected_tasks = {t["trial_id"] for t in row["evaluation"]["trials"] if "task_file" in t}
        require(set(row["tasks"]["judges"]) == expected_tasks, "Judge task set differs")
        for task in [row["rewrite"], row["tasks"]["extraction"], *row["tasks"]["judges"].values()]:
            verify_checkpoint(task)
        for name, task in row["tasks"]["judges"].items():
            require(task == read_json(folder / (name + ".json")) and task["binding"] == {
                    **task_binding, "trial_id": name, "claims_sha256": digest(claims)}, "Saved Judge changed")
        for trial in row["evaluation"]["trials"]:
            task = row["tasks"]["judges"].get(trial["trial_id"])
            score = task["parsed"]["score"] if task and task["status"] == "ok" else None
            require(trial["score"] == score and all(trial[k] == v for k, v in
                    decide(score, row["evaluation"]["threshold"]).items()), "Saved score/decision changed")
    return manifest, report


def build_packet(run):
    manifest, report = read_run(run)
    config, language = manifest["config"], manifest["language"]
    assets = load_assets(ROOT / config["assets"])
    qa_path = ROOT / manifest["qa_path"]
    require(file_hash(qa_path) == manifest["qa_sha256"], "Quality QA changed")
    qa = {r["record_id"]: r for r in map(json.loads, qa_path.read_text().splitlines())}
    parent_of = parent_map(assets, language)
    children = defaultdict(list)
    for child, parent in parent_of.items():
        children[parent].append(child)
    needed, references, provenance = set(), {}, {}
    for row in report["records"]:
        identifier = row["trace"]["record_id"]
        original = qa[identifier]
        require(row["trace"]["question"] == original["question"], "Quality question differs from QA")
        child_ids = (list(original["gold_passage_ids"]) if language == "ja" else
                     [c for p in original["gold_passage_ids"] for c in children[p]])
        references[identifier] = {**original, "gold_passage_ids": child_ids}
        needed.update(child_ids)
        provenance[identifier] = {"language": language,
                                  "gold_parent_unit": assets["datasets"][language]["gold_parent_unit"],
                                  "gold_documents_scope": "verified_reference_quote_overlap_children" if language == "ja" else "all_children_of_original_gold_parent",
                                  "missing_cited_source_units": original.get("unavailable_cited_reference_ids", [])}
        if language == "ja":
            mapping = {m["reference_index"]: m for m in original["reference_corpus_mapping"]}
            provenance[identifier]["cited_references"] = [
                {**e, "corpus_body_available": mapping[e["reference_index"]]["body_available"],
                 "literal_quote_audit": mapping[e["reference_index"]]["literal_quote_audit"]}
                for e in original["reference_evidence"] if mapping[e["reference_index"]]["cited"]]
    gold = {}
    corpus = ROOT / assets["datasets"][language]["corpus"]["path"]
    with corpus.open() as stream:
        for line in stream:
            row = json.loads(line)
            if row["passage_id"] in needed:
                gold[row["passage_id"]] = {k: row[k] for k in ("passage_id", "title", "text")}
    require(set(gold) == needed, "Missing verified quality reference documents")
    rubric = (ROOT / "docs/order_quality_rubric.md").read_text().split("## 3.")[0]
    rubric += ("\nReference provenance is offline annotation metadata. Human summaries are not literal source quotations. "
               "A missing source or unmatched quote does not automatically label a QA unanswerable. "
               "Gold material cannot replace support from the actual used context.\n")
    packet, mapping = make_packet(report["records"], references, gold, rubric, config["quality_rubric_version"],
                                  42, digest(manifest), reference_metadata=provenance)
    return manifest, report, packet, mapping


def export(run, output):
    run, output = Path(run).resolve(), Path(output).resolve()
    require(run.is_relative_to(ROOT / "data/runs/bilingual_development") and output.is_relative_to(run) and output != run,
            "Unexpected bilingual annotation output")
    manifest, report, packet, mapping = build_packet(run)
    with run_lock(output):
        require({p.name for p in output.iterdir()} == {".run.lock"}, "Quality bundle already exists")
        write_json(output / "packet.json", packet)
        checkpoint(output / "mapping.private.json", mapping)
        write_json(output / "annotations.blank.json", blank_annotations(packet))
        checkpoint(output / "export_manifest.json", {"run_manifest_sha256": digest(manifest),
                   "packet_sha256": packet["packet_sha256"], "mapping_sha256": file_hash(output / "mapping.private.json"),
                   "selected_qa_count": report["selected_qa_count"], "baseline_failure_count": len(report["failures"])})
    return {"candidate_count": len(packet["cases"]), "quality_status": "pending_external_blinded_annotation"}


def import_annotations(run, bundle, annotations):
    run, bundle, annotations = map(lambda p: Path(p).resolve(), (run, bundle, annotations))
    require(bundle.is_relative_to(run) and bundle != run, "Annotation bundle escapes run")
    manifest, report, expected_packet, expected_mapping = build_packet(run)
    packet, mapping = read_json(bundle / "packet.json"), read_json(bundle / "mapping.private.json")
    verify_packet(packet, mapping)
    require(packet == expected_packet and {k: v for k, v in mapping.items() if k != "result_sha256"} == expected_mapping,
            "Quality packet/mapping differs from source candidates")
    exported = read_json(bundle / "export_manifest.json")
    verify_checkpoint(exported)
    require(exported["mapping_sha256"] == file_hash(bundle / "mapping.private.json") and
            exported["run_manifest_sha256"] == digest(manifest), "Quality export binding differs")
    values = read_json(annotations)
    labels = validate_annotations(packet, values)
    require(all(a["label"] != "pending" for a in labels.values()), "Seal all external labels before revealing internal routes")
    assigned = {(a["record_id"], a["stage"]): labels[identifier]["label"]
                for identifier, slots in mapping["assignments"].items() for a in slots}
    result = reconstruct(report["records"], assigned)
    result.update(selected_qa_count=report["selected_qa_count"], baseline_failures=report["failures"],
                  language=manifest["language"], quality_annotation_sha256=file_hash(annotations),
                  gate11_passed=False, phase12_allowed=False)
    path = bundle / "routes.scored.json"
    require(not path.exists(), "Scored routes already exist")
    write_json(path, result)
    return {"sealed_candidates": len(labels), "route_rows": len(result["routes"]), "gate11_passed": False}
