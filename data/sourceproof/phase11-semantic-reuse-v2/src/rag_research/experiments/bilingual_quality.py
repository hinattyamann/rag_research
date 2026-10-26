"""Blind bilingual quality packets with explicit offline source provenance."""

import json
from collections import defaultdict
from pathlib import Path

import yaml

from rag_research.data.study_assets import load_assets, parent_map
from rag_research.evaluation.claimwise import verify_once
from rag_research.evaluation.order import trial_plan
from rag_research.experiments.decisions import decide_with_refusal
from rag_research.experiments.frozen_trace import digest, freeze_record, require
from rag_research.experiments.phase11_autonomy import validate_chain_identity
from rag_research.experiments.protocol import ROOT, task_config
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


def analysis_split(run, *, root=None, allow_replay=False):
    root = ROOT if root is None else root
    run = Path(run).resolve()
    folders = {"development": ["data/runs/bilingual_development"], "calibration": ["data/runs/bilingual_calibration"]}
    if allow_replay:
        folders["calibration"].append("data/runs/bilingual_calibration_replay")
    matched = [split for split, names in folders.items() for name in names
               if run.is_relative_to(root / name) and run != root / name]
    require(len(matched) == 1, "Unexpected bilingual Development/Calibration run path")
    return matched[0]


def source_split(manifest, split):
    if split == "development":
        require(manifest["config"].get("execution_scope") != "heldout_calibration_v1" and
                manifest["config"].get("analysis_split") != "calibration" and
                manifest["config"].get("purpose") != "phase11-bilingual-calibration-candidate",
                "Calibration cannot be relabelled as Development")
        return "development"
    require(split == "calibration" and manifest["config"]["purpose"] == "phase11-bilingual-calibration-candidate" and
            manifest["config"]["execution_scope"] == "heldout_calibration_v1" and
            manifest["config"]["analysis_split"] == "calibration" and manifest["language"] in {"en", "ja"},
            "Use the declared held-out Calibration role")
    source = "development" if manifest["language"] == "en" else "calibration"
    require(manifest["config"]["data"]["split"] == source, "Calibration source split changed")
    return source


def read_run(run):
    split = analysis_split(run, allow_replay=True)
    manifest, report = read_json(run / "manifest.json"), read_json(run / "report.private.json")
    validate_chain_identity(manifest["config"], manifest, report, root=ROOT)
    source_split(manifest, split)
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
            if task.get("execution_mode") in {"claimwise-v1", "source-reading-v1"}:
                prompts = yaml.safe_load((ROOT / manifest["config"]["prompts"]).read_text())
                spec = next(t for t in entry["plan"]["trials"] if t["trial_id"] == name)
                documents = {d["passage_id"]: d for d in trace["documents"]}
                verified = verify_once(None, task_config(manifest["config"], "verify_claims"), prompts,
                    {"question": trace["question"], "answer": trace["answer"], "claims": claims,
                     "documents": [documents[i] for i in spec["document_ids"]]}, folder / (name + ".json"),
                    task["binding"], constraints=manifest["config"]["output_constraints"], mode=task["execution_mode"],
                    reader_generation=task_config(manifest["config"], "read_sources") if task["execution_mode"] == "source-reading-v1" else None)
                require(verified == task, "Claimwise raw/report differs")
        for trial in row["evaluation"]["trials"]:
            task = row["tasks"]["judges"].get(trial["trial_id"])
            score = task["parsed"]["score"] if task and task["status"] == "ok" else None
            require(trial["score"] == score and all(trial[k] == v for k, v in
                    decide_with_refusal(score, row["evaluation"]["threshold"], extraction,
                        policy=manifest["config"]["decision"].get("bare_refusal_policy", "keep_initial")).items()),
                    "Saved score/decision changed")
    return manifest, report


def build_packet(run):
    manifest, report = read_run(run)
    config, language = manifest["config"], manifest["language"]
    assets = load_assets(ROOT / config["assets"])
    source = source_split(manifest, analysis_split(run, allow_replay=True))
    declared = assets["datasets"][language]["qa"][source]
    qa_path = (ROOT / manifest["qa_path"]).resolve()
    require(qa_path == (ROOT / declared["path"]).resolve() and manifest["qa_sha256"] == declared["sha256"],
            "Quality QA must match the declared source split; never load Evaluation rows")
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
    analysis_split(run)
    require(output.is_relative_to(run) and output != run,
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


def sealed_annotations(bundle, annotations):
    """Check all labels before accessing private scores or reconstructing any routes."""
    bundle, annotations = Path(bundle).resolve(), Path(annotations).resolve()
    packet, mapping = read_json(bundle / "packet.json"), read_json(bundle / "mapping.private.json")
    verify_packet(packet, mapping)
    labels = validate_annotations(packet, read_json(annotations))
    require(all(a["label"] != "pending" for a in labels.values()), "Seal all external labels before revealing internal routes")
    return packet, mapping, labels


def validated_annotations(run, bundle, annotations):
    run, bundle, annotations = map(lambda p: Path(p).resolve(), (run, bundle, annotations))
    require(bundle.is_relative_to(run) and bundle != run, "Annotation bundle escapes run")
    packet, mapping, labels = sealed_annotations(bundle, annotations)
    manifest, report, expected_packet, expected_mapping = build_packet(run)
    require(packet == expected_packet and {k: v for k, v in mapping.items() if k != "result_sha256"} == expected_mapping,
            "Quality packet/mapping differs from source candidates")
    exported = read_json(bundle / "export_manifest.json")
    verify_checkpoint(exported)
    require(exported["mapping_sha256"] == file_hash(bundle / "mapping.private.json") and
            exported["run_manifest_sha256"] == digest(manifest), "Quality export binding differs")
    assigned = {(a["record_id"], a["stage"]): labels[identifier]["label"]
                for identifier, slots in mapping["assignments"].items() for a in slots}
    return manifest, report, assigned


def import_annotations(run, bundle, annotations):
    run, bundle, annotations = map(lambda p: Path(p).resolve(), (run, bundle, annotations))
    require(analysis_split(run) == "development", "Calibration requires both languages' quality and unit labels in the batch analysis")
    manifest, report, assigned = validated_annotations(run, bundle, annotations)
    result = reconstruct(report["records"], assigned)
    result.update(selected_qa_count=report["selected_qa_count"], baseline_failures=report["failures"],
                  language=manifest["language"], quality_annotation_sha256=file_hash(annotations),
                  gate11_passed=False, phase12_allowed=False)
    path = bundle / "routes.scored.json"
    require(not path.exists(), "Scored routes already exist")
    write_json(path, result)
    labels = read_json(annotations)["annotations"]
    return {"sealed_candidates": len(labels), "route_rows": len(result["routes"]), "gate11_passed": False}
