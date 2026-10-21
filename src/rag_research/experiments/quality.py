"""Blinded offline manual annotation, strict import and common-candidate routing."""

import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from rag_research.experiments.decisions import decide_with_refusal
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.protocol import ROOT
from rag_research.experiments.storage import (
    checkpoint,
    read_json,
    run_lock,
    verify_checkpoint,
    write_json,
)
from rag_research.retrieval.common import CORPUS_PATH, file_hash

CRITERIA = ("essential_answer", "no_major_error", "context_support")
LABELS = {"reliable": 1, "unreliable": 0, "indeterminate": None, "pending": None}


def read_run(run):
    manifest, report = read_json(run / "manifest.json"), read_json(run / "report.json")
    require(report["manifest_sha256"] == digest(manifest), "Phase 9 manifest binding differs")
    source = (ROOT / manifest["source_order_run"]).resolve()
    require(source.is_relative_to(ROOT / "data/runs/order_sensitivity"), "Unexpected source run")
    for name, expected in manifest["source_artifacts"].items():
        path = (source / name).resolve()
        require(path.is_relative_to(source) and file_hash(path) == expected,
                "Phase 8 source artifact changed")
    original_records = {r["record_id"]: r for r in read_json(source / "report.json")["records"]}
    source_manifest = read_json(source / "manifest.json")
    baseline_path = (ROOT / manifest["config"]["baseline_answers"]).resolve()
    require(baseline_path.is_relative_to(ROOT / "data/runs") and
            file_hash(baseline_path) == source_manifest["baseline_answers_sha256"], "Baseline cost source changed")
    baseline = {r["record_id"]: r for r in map(json.loads, baseline_path.read_text("utf-8").splitlines())}
    ids = [r["trace"]["record_id"] for r in report["records"]]
    require(len(ids) == len(set(ids)) and set(ids) == set(original_records), "Phase 9 record set differs")
    for row in report["records"]:
        trace, rewritten = row["trace"], row["rewrite"]
        require(digest({k: v for k, v in trace.items() if k != "trace_sha256"}) ==
                trace["trace_sha256"], "Trace hash differs")
        verify_checkpoint(rewritten)
        require(rewritten["binding"] == {"manifest_sha256": digest(manifest),
                                         "trace_sha256": trace["trace_sha256"]},
                "Rewrite trace binding differs")
        raw = run / digest(trace["record_id"])[:24] / "rewrite.json"
        require(read_json(raw) == rewritten, "Rewrite raw/report differs")
        require(row["evaluation"] == original_records[trace["record_id"]], "Saved Judge summary differs")
        require(row["baseline_cost"] == {k: baseline[trace["record_id"]].get(k) for k in
                                         ("input_tokens", "output_tokens", "generation_seconds",
                                          "context_seconds", "answer_generation_calls")},
                "Saved baseline cost differs")
        folder = source / digest(trace["record_id"])[:24]
        require(trace == read_json(folder / "trace.json") and
                row["tasks"]["extraction"] == read_json(folder / "claims.json"), "Source trace/claims differ")
        for trial in row["evaluation"]["trials"]:
            if "task_file" in trial:
                require(row["tasks"]["judges"][trial["trial_id"]] == read_json(source / trial["task_file"]),
                        "Source Judge task differs")
    return manifest, report


def make_packet(records, qa, gold, rubric, version, seed, binding, *, reference_metadata=None):
    cases, mapping, lookup = {}, {}, {}
    for row in records:
        trace = row["trace"]
        reference = qa[trace["record_id"]]
        candidates = {"initial": trace["answer"]}
        if row["rewrite"]["status"] == "ok":
            candidates["rewritten"] = row["rewrite"]["answer"]
        for stage, answer in candidates.items():
            content = {"question": trace["question"], "answer": answer,
                       "documents": trace["documents"],
                       "reference_answers": reference["reference_answers"],
                       "selected_sentences_by_reference": reference["selected_sentences_by_reference"],
                       "gold_documents": [gold[i] for i in reference["gold_passage_ids"]]}
            if reference_metadata is not None:
                content["reference_provenance"] = reference_metadata[trace["record_id"]]
            candidate_hash = digest(content)
            # Identical question/answer/context/reference is annotated once for both stages.
            anonymous = "Q-" + digest([seed, candidate_hash])[:20]
            case = {"annotation_id": anonymous, "candidate_sha256": candidate_hash, **content}
            require(anonymous not in cases or cases[anonymous] == case, "Anonymous ID collision")
            cases[anonymous] = case
            lookup.setdefault(anonymous, []).append({"record_id": trace["record_id"], "stage": stage})
    ordered = sorted(cases, key=lambda key: digest([seed, "display", key]))
    packet = {"schema_version": 1, "rubric_version": version, "rubric": rubric,
              "criteria": list(CRITERIA), "cases": [cases[k] for k in ordered]}
    packet["packet_sha256"] = digest(packet)
    mapping.update(schema_version=1, packet_sha256=packet["packet_sha256"],
                   run_manifest_sha256=binding, assignments=lookup)
    return packet, mapping


def blank_annotations(packet):
    return {"schema_version": 1, "packet_sha256": packet["packet_sha256"],
            "rubric_version": packet["rubric_version"], "annotations": [
                {"annotation_id": c["annotation_id"], "candidate_sha256": c["candidate_sha256"],
                 "label": "pending", "criteria": dict.fromkeys(CRITERIA, "pending"),
                 "essential_points": "", "reason": "", "evidence": [], "annotator": "",
                 "elapsed_seconds": None, "confirmed_at_utc": None} for c in packet["cases"]]}


def verify_packet(packet, mapping):
    require(packet["packet_sha256"] == digest({k: v for k, v in packet.items()
                                               if k != "packet_sha256"}), "Packet hash differs")
    verify_checkpoint(mapping)
    require(mapping["packet_sha256"] == packet["packet_sha256"], "Mapping belongs to another packet")
    ids = [c["annotation_id"] for c in packet["cases"]]
    require(len(ids) == len(set(ids)) and set(ids) == set(mapping["assignments"]),
            "Packet/mapping case set differs")
    for case in packet["cases"]:
        require(case["candidate_sha256"] == digest({k: v for k, v in case.items()
                if k not in {"annotation_id", "candidate_sha256"}}), "Candidate hash differs")


def validate_annotations(packet, value):
    require(set(value) == {"schema_version", "packet_sha256", "rubric_version", "annotations"},
            "Unexpected annotation fields")
    require(value["schema_version"] == 1 and value["packet_sha256"] == packet["packet_sha256"] and
            value["rubric_version"] == packet["rubric_version"], "Annotation packet/rubric differs")
    cases = {c["annotation_id"]: c for c in packet["cases"]}
    annotations = value["annotations"]
    require(isinstance(annotations, list), "Annotations must be a list")
    ids = [a["annotation_id"] for a in annotations]
    require(len(ids) == len(set(ids)) and set(ids) == set(cases), "Missing/duplicate/unknown annotation ID")
    for annotation in annotations:
        case = cases[annotation["annotation_id"]]
        expected = set(blank_annotations({**packet, "cases": [case]})["annotations"][0])
        require(set(annotation) == expected, "Unexpected annotation fields")
        require(annotation["candidate_sha256"] == case["candidate_sha256"], "Annotation candidate differs")
        label, criteria = annotation["label"], annotation["criteria"]
        require(label in LABELS and set(criteria) == set(CRITERIA), "Invalid label/criteria")
        require(all(v in {"pass", "fail", "uncertain", "pending"} for v in criteria.values()),
                "Invalid criterion value")
        for field in ("essential_points", "reason", "annotator"):
            require(isinstance(annotation[field], str), f"Invalid annotation {field}")
        require(isinstance(annotation["evidence"], list), "Evidence must be a list")
        documents = case["documents"] + case["gold_documents"]
        for evidence in annotation["evidence"]:
            require(set(evidence) == {"passage_id", "quote"}, "Invalid evidence fields")
            require(isinstance(evidence["quote"], str) and bool(evidence["quote"].strip()) and
                    any(evidence["passage_id"] == d["passage_id"] and evidence["quote"] in d["text"]
                        for d in documents), "Evidence quote is not verbatim")
        if label == "pending":
            require("pending" in criteria.values(), "Completed criteria require a completed label")
            continue
        seconds = annotation["elapsed_seconds"]
        require(type(seconds) in {int, float} and math.isfinite(seconds) and seconds > 0,
                "Completed annotation needs positive elapsed seconds")
        require(all(annotation[f].strip() for f in ("essential_points", "reason", "annotator")),
                "Completed annotation needs essential points/reason/annotator")
        when = datetime.fromisoformat(annotation["confirmed_at_utc"])
        require(when.utcoffset() is not None, "Annotation timestamp needs timezone")
        values = set(criteria.values())
        if label == "reliable":
            require(values == {"pass"} and bool(annotation["evidence"]),
                    "Reliable requires all criteria pass and supporting evidence")
        elif label == "unreliable":
            require("fail" in values, "Unreliable requires a definite failing criterion")
        else:
            require("uncertain" in values and not values.intersection({"fail", "pending"}),
                    "Indeterminate requires completed uncertain criteria without a definite failure")
    return {a["annotation_id"]: a for a in annotations}


def cost(tasks):
    """Summed measured model steps, never claimed to be end-to-end operational latency."""
    tasks = list(tasks)
    attempted = [t for t in tasks if t.get("completion_attempted", False)]
    unknown = [t for t in tasks if t.get("error_code") == "interrupted_unknown_outcome"]
    return {"completion_attempts": None if unknown else len(attempted),
            "recorded_completion_attempts": len(attempted),
            "unknown_outcome_steps": len(unknown),
            "input_tokens": sum(t.get("input_tokens") or 0 for t in attempted),
            "output_tokens": sum(t.get("output_tokens") or 0 for t in attempted),
            "summed_step_seconds": sum(t.get("elapsed_seconds", 0) for t in tasks),
            "incomplete": bool(unknown) or any(t.get("cost_incomplete", False) for t in tasks)}


def reconstruct(records, labels):
    """labels[(record_id, stage)] has manual status; absent labels stay pending."""
    rows = []
    transitions = Counter()
    for row in records:
        identifier = row["trace"]["record_id"]
        rewrite = row["rewrite"]
        statuses = {stage: labels.get((identifier, stage), "pending") for stage in ("initial", "rewritten")}
        yi, yr = [LABELS[statuses[s]] for s in ("initial", "rewritten")]
        pair_known = yi is not None and yr is not None and rewrite["status"] == "ok"
        transition = f"{yi}->{yr}" if pair_known else "unknown"
        transitions[transition] += 1
        b = row["baseline_cost"]
        initial_cost = {"completion_attempted": bool(b["answer_generation_calls"]),
                        "input_tokens": b["input_tokens"], "output_tokens": b["output_tokens"],
                        "elapsed_seconds": (b["generation_seconds"] or 0) + (b["context_seconds"] or 0)}
        routes = [{"route": "no_repair", "requested": False, "fallback": None,
                   "tasks": [initial_cost]},
                  {"route": "always_rewrite", "requested": True, "fallback": None,
                   "tasks": [initial_cost, rewrite]}]
        for trial in row["evaluation"]["trials"]:
            judge = row["tasks"]["judges"].get(trial["trial_id"])
            requested = trial["action"] == "rewrite_requested"
            tasks = [initial_cost, row["tasks"]["extraction"]]
            if judge:
                tasks.append(judge)
            if requested:
                tasks.append(rewrite)
            bare_refusal = (requested and trial["decision"] == "unscorable" and
                            decide_with_refusal(None, row["evaluation"]["threshold"], row["tasks"]["extraction"],
                                                policy="rewrite_once")["action"] == "rewrite_requested")
            routes.append({"route": trial["trial_id"], "requested": requested,
                           "fallback": ("bare_refusal_rewrite_once" if bare_refusal else "unscorable")
                           if trial["decision"] == "unscorable" else None,
                           "tasks": tasks})
        for route in routes:
            selected = "rewritten" if route["requested"] and rewrite["status"] == "ok" else "initial"
            fallback = "rewrite_failed" if route["requested"] and rewrite["status"] != "ok" else route["fallback"]
            rows.append({"record_id": identifier, "route": route["route"], "selected_stage": selected,
                         "selected_answer_sha256": digest(row["rewrite"]["answer"] if selected == "rewritten"
                                                          else row["trace"]["answer"]),
                         "rewrite_requested": route["requested"], "fallback": fallback,
                         "quality_status": statuses[selected], "quality_y": LABELS[statuses[selected]],
                         "quality_transition": transition,
                         "missed_improvement": (selected == "initial" and yi == 0 and yr == 1)
                         if pair_known else None,
                         "harmful_rewrite": (selected == "rewritten" and yi == 1 and yr == 0)
                         if pair_known else None,
                         "operational_cost": cost(route["tasks"])})
    collection_tasks = [t for r in records for t in
                        [r["tasks"]["extraction"], *r["tasks"]["judges"].values(), r["rewrite"]]]
    return {"schema_version": 1, "record_count": len(records), "routes": rows,
            "quality_transitions": {k: transitions[k] for k in ("0->0", "0->1", "1->0", "1->1", "unknown")},
            "auxiliary_collection_cost": cost(collection_tasks),
            "cost_notes": ["Collection includes saved Phase 8 and Phase 9; baseline collection excluded",
                           "Each route pays its own one Judge and requested rewrite even if collected once",
                           "No-repair/always-rewrite routes omit extraction/Judge",
                           "Step seconds exclude retrieval, startup, offline annotation; not measured route latency",
                           "Counterfactual rewrite is collected even when all routes accept or are unscorable"]}


def export_quality(run, output):
    run, output = Path(run).resolve(), Path(output).resolve()
    require(run.is_relative_to(ROOT / "data/runs/answer_rewrite"), "Unexpected Phase 9 run")
    require(output.is_relative_to(run) and output != run, "Annotation export must be a child of run")
    manifest, report = read_run(run)
    qa_path = ROOT / manifest["qa_path"]
    require(file_hash(qa_path) == manifest["qa_sha256"], "Quality QA source changed")
    qa = {r["record_id"]: r for r in map(json.loads, qa_path.read_text("utf-8").splitlines())}
    needed = {i for r in report["records"] for i in qa[r["trace"]["record_id"]]["gold_passage_ids"]}
    gold = {}
    with (ROOT / CORPUS_PATH).open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["passage_id"] in needed:
                gold[row["passage_id"]] = {k: row[k] for k in ("passage_id", "title", "text")}
    require(set(gold) == needed, "Missing Gold passages")
    config = manifest["config"]
    rubric_path = ROOT / config["quality_rubric"]
    require(file_hash(rubric_path) == manifest["rubric_sha256"], "Rubric changed")
    # Public rubric contains criteria only; historical worked examples reveal stage/Judge information.
    rubric = rubric_path.read_text("utf-8").split("## 3.")[0]
    packet, mapping = make_packet(report["records"], qa, gold, rubric,
                                  config["quality_rubric_version"], config["annotation_seed"], digest(manifest))
    from rag_research.experiments.quality_form import render_form

    with run_lock(output):
        require({p.name for p in output.iterdir()} == {".run.lock"}, "Export directory already used")
        write_json(output / "packet.json", packet)
        checkpoint(output / "mapping.private.json", mapping)
        write_json(output / "annotations.blank.json", blank_annotations(packet))
        (output / "採点画面.html").write_text(render_form(packet), encoding="utf-8")
        analysis = reconstruct(report["records"], {})
        write_json(output / "routes.pending.json", analysis)
        checkpoint(output / "export_manifest.json", {
            "run_manifest_sha256": digest(manifest), "packet_sha256": packet["packet_sha256"],
            "mapping_sha256": file_hash(output / "mapping.private.json"),
            "corpus_sha256": file_hash(ROOT / CORPUS_PATH),
            "source_sha256": {p.name: file_hash(p) for p in (Path(__file__),
                              ROOT / "src/rag_research/experiments/quality_form.py")}})
    return {"candidate_count": len(packet["cases"]), "quality_status": "pending", "output": str(output)}


def import_quality(run, bundle, annotations):
    run, bundle, annotations = map(lambda p: Path(p).resolve(), (run, bundle, annotations))
    require(run.is_relative_to(ROOT / "data/runs/answer_rewrite"), "Unexpected Phase 9 run")
    require(bundle.is_relative_to(run) and bundle != run, "Unexpected annotation bundle")
    manifest, report = read_run(run)
    packet, mapping = read_json(bundle / "packet.json"), read_json(bundle / "mapping.private.json")
    verify_packet(packet, mapping)
    exported = read_json(bundle / "export_manifest.json")
    verify_checkpoint(exported)
    require(exported["mapping_sha256"] == file_hash(bundle / "mapping.private.json") and
            exported["packet_sha256"] == packet["packet_sha256"] and
            exported["run_manifest_sha256"] == digest(manifest), "Export provenance differs")
    require(mapping["run_manifest_sha256"] == digest(manifest), "Bundle belongs to another run")
    # Rebuild assignment/content hashes from the run to detect edited private mapping.
    expected = {}
    for row in report["records"]:
        for stage in ("initial", "rewritten"):
            if stage == "rewritten" and row["rewrite"]["status"] != "ok":
                continue
            expected[(row["trace"]["record_id"], stage)] = row
    observed = []
    cases = {c["annotation_id"]: c for c in packet["cases"]}
    for anonymous, assignments in mapping["assignments"].items():
        for assignment in assignments:
            key = (assignment["record_id"], assignment["stage"])
            require(key in expected, "Unknown private assignment")
            row, case = expected[key], cases[anonymous]
            answer = row["trace"]["answer"] if key[1] == "initial" else row["rewrite"]["answer"]
            require(case["answer"] == answer and case["question"] == row["trace"]["question"] and
                    case["documents"] == row["trace"]["documents"], "Private assignment content differs")
            observed.append(key)
    require(len(observed) == len(set(observed)) and set(observed) == set(expected), "Assignment set differs")
    value = read_json(annotations)
    validated = validate_annotations(packet, value)
    labels = {(a["record_id"], a["stage"]): validated[anonymous]["label"]
              for anonymous, assignments in mapping["assignments"].items() for a in assignments}
    analysis = reconstruct(report["records"], labels)
    analysis["manual_annotation_status_counts"] = dict(Counter(a["label"] for a in validated.values()))
    analysis["offline_annotation_seconds"] = sum(a["elapsed_seconds"] or 0 for a in validated.values()
                                                if a["label"] != "pending")
    with run_lock(bundle):
        imports = bundle / "imports"
        imports.mkdir(exist_ok=True)
        destination = imports / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        destination.mkdir()
        write_json(destination / "annotations.json", value)
        write_json(destination / "analysis.json", analysis)
        checkpoint(destination / "import_manifest.json", {
            "created_at_utc": datetime.now(UTC).isoformat(), "annotations_sha256": file_hash(annotations),
            "packet_sha256": packet["packet_sha256"], "mapping_sha256": file_hash(bundle / "mapping.private.json"),
            "run_report_sha256": file_hash(run / "report.json"),
            "analysis_sha256": file_hash(destination / "analysis.json"),
            "import_source_sha256": file_hash(Path(__file__))})
    return {"output": str(destination), "manual_annotation_status_counts":
            analysis["manual_annotation_status_counts"], "quality_transitions": analysis["quality_transitions"]}
