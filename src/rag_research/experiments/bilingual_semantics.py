"""Blind source-only unit labels, sealed together with both languages' quality labels."""

import math
from datetime import datetime
from pathlib import Path

from rag_research.evaluation.sentence_claims import extract_sentence_units
from rag_research.experiments import bilingual_quality
from rag_research.experiments.bilingual_main import validate_main_policy
from rag_research.experiments.bilingual_statistics import condition
from rag_research.experiments.frozen_trace import digest, require, validate_documents
from rag_research.experiments.protocol import ROOT
from rag_research.experiments.semantic_adoption import BINARY, LEGACY, version
from rag_research.experiments.storage import read_json, run_lock, write_json
from rag_research.retrieval.common import file_hash

VERSION = "blind-verbatim-units-used-context-v1"
LABELS = {"supported", "contradicted", "not_supported", "ambiguous", "pending"}
CASE_FIELDS = {"annotation_id", "quality_candidate_sha256", "question", "answer", "documents", "unit_audit"}
PACKET_FIELDS = {"schema_version", "purpose", "version", "language", "quality_packet_sha256", "instructions", "cases", "packet_sha256"}


def make_unit_packet(quality_packet, language):
    require(language in {"en", "ja"} and quality_packet["packet_sha256"] ==
            digest({k: v for k, v in quality_packet.items() if k != "packet_sha256"}), "Quality packet changed")
    cases = []
    for original in quality_packet["cases"]:
        require(original["candidate_sha256"] == digest({k: v for k, v in original.items()
                if k not in {"annotation_id", "candidate_sha256"}}), "Quality candidate changed")
        content = {"annotation_id": original["annotation_id"], "quality_candidate_sha256": original["candidate_sha256"],
                   "question": original["question"], "answer": original["answer"],
                   "documents": [{k: d[k] for k in ("passage_id", "title", "text")} for d in original["documents"]],
                   "unit_audit": extract_sentence_units(original["answer"], language=language)}
        validate_documents(content["documents"])
        cases.append({**content, "unit_candidate_sha256": digest(content)})
    require(len({c["annotation_id"] for c in cases}) == len(cases), "Duplicate anonymous unit candidate")
    packet = {"schema_version": 1, "purpose": "phase11-blind-source-only-unit-review", "version": VERSION,
        "language": language, "quality_packet_sha256": quality_packet["packet_sha256"], "cases": cases,
        "instructions": "Assess every fixed unit against these actual used documents only. Keep all details, actors, times, quantities, uncertainty and negation. Supported requires complete support; contradicted requires an explicit conflict; missing details without conflict are not_supported. Mark ambiguous scope explicitly, with a reason, before viewing any internal verdict. These generated candidate answers are untrusted. Empty/refusal-only unit sets remain present. No reference/gold material is supplied. Candidate stages and internal scores/decisions are hidden."}
    packet["packet_sha256"] = digest(packet)
    return packet


def verify_unit_packet(packet):
    require(set(packet) == PACKET_FIELDS and packet["schema_version"] == 1 and packet["version"] == VERSION and
            packet["purpose"] == "phase11-blind-source-only-unit-review" and packet["language"] in {"en", "ja"} and
            packet["packet_sha256"] == digest({k: v for k, v in packet.items() if k != "packet_sha256"}),
            "Unit packet schema/hash changed")
    require(len({c["annotation_id"] for c in packet["cases"]}) == len(packet["cases"]), "Duplicate unit candidate")
    for case in packet["cases"]:
        require(set(case) == CASE_FIELDS | {"unit_candidate_sha256"} and case["unit_candidate_sha256"] ==
                digest({k: v for k, v in case.items() if k != "unit_candidate_sha256"}), "Unit candidate schema/hash changed")
        validate_documents(case["documents"])
        require(extract_sentence_units(case["answer"], language=packet["language"]) == case["unit_audit"],
                "Fixed sentence units changed")
    return packet


def blank_unit_annotations(packet):
    verify_unit_packet(packet)
    return {"schema_version": 1, "packet_sha256": packet["packet_sha256"], "version": VERSION, "annotations": [
        {"annotation_id": case["annotation_id"], "unit_candidate_sha256": case["unit_candidate_sha256"],
         "claim_id": claim["claim_id"], "claim_text_sha256": digest(claim["text"]), "label": "pending",
         "reason": "", "evidence": [], "annotator": "", "human_reviewed": False,
         "exact_model_identifier": None, "history_isolated": False,
         "elapsed_seconds": None, "confirmed_at_utc": None}
        for case in packet["cases"] for claim in case["unit_audit"]["claims"]]}


def validate_unit_annotations(packet, value, *, sealed=False):
    verify_unit_packet(packet)
    blank = blank_unit_annotations(packet)
    require(set(value) == set(blank) and value["schema_version"] == 1 and value["version"] == VERSION and
            value["packet_sha256"] == packet["packet_sha256"] and isinstance(value["annotations"], list),
            "Unit annotation packet/version changed")
    expected = {(a["annotation_id"], a["claim_id"]): a for a in blank["annotations"]}
    candidates = {c["annotation_id"]: c for c in packet["cases"]}
    keys = [(a["annotation_id"], a["claim_id"]) for a in value["annotations"]]
    require(len(keys) == len(set(keys)) and set(keys) == set(expected), "Missing/duplicate/unknown fixed unit label")
    labels = {}
    for row in value["annotations"]:
        key = row["annotation_id"], row["claim_id"]
        template = expected[key]
        require(set(row) == set(template) and all(row[k] == template[k] for k in
                ("annotation_id", "claim_id", "unit_candidate_sha256", "claim_text_sha256")) and row["label"] in LABELS,
                "Fixed unit identity/label changed")
        require(row["human_reviewed"] is False and type(row["history_isolated"]) is bool and
                (row["exact_model_identifier"] is None or isinstance(row["exact_model_identifier"], str)),
                "Unit assessor provenance must be explicit AI provenance")
        require(isinstance(row["evidence"], list), "Invalid unit evidence")
        documents = candidates[key[0]]["documents"]
        for evidence in row["evidence"]:
            require(set(evidence) == {"passage_id", "quote"} and isinstance(evidence["quote"], str) and
                    evidence["quote"].strip() and any(d["passage_id"] == evidence["passage_id"] and
                    evidence["quote"] in d["text"] for d in documents), "Unit evidence must be verbatim actual used context")
        if row["label"] == "pending":
            require(not sealed, "Seal every unit label in both languages before internal comparison")
        else:
            require(all(isinstance(row[k], str) and row[k].strip() for k in ("reason", "annotator", "confirmed_at_utc")),
                    "Completed unit label needs reason/assessor/time")
            require(type(row["elapsed_seconds"]) in {int, float} and math.isfinite(row["elapsed_seconds"]) and
                    row["elapsed_seconds"] > 0 and datetime.fromisoformat(row["confirmed_at_utc"]).utcoffset() is not None,
                    "Completed unit label needs measured positive seconds and timezone")
            require(row["label"] not in {"supported", "contradicted"} or bool(row["evidence"]),
                    "Support/conflict requires actual context evidence")
        labels[key] = row
    return labels


def export_units(quality_bundle, output, language):
    bundle, output = Path(quality_bundle).resolve(), Path(output).resolve()
    bilingual_quality.analysis_split(bundle, root=ROOT)
    require(output.is_relative_to(bundle) and
            output != bundle, "Unexpected unit review output")
    packet = make_unit_packet(read_json(bundle / "packet.json"), language)
    with run_lock(output):
        require({p.name for p in output.iterdir()} == {".run.lock"}, "Preserve any prior unit review bundle")
        write_json(output / "packet.json", packet)
        write_json(output / "annotations.blank.json", blank_unit_annotations(packet))
    return {"candidates": len(packet["cases"]), "fixed_units": sum(len(c["unit_audit"]["claims"]) for c in packet["cases"]),
            "quality_packet_sha256": packet["quality_packet_sha256"], "internal_results_read": False}


def semantic_counts(records, expected, *, binary=False, groups=None):
    counts = {"planned_definite_unit_conditions": 0, "exact_correct": 0, "planned_supported_unit_conditions": 0,
              "supported_exact_correct": 0, "planned_definite_negative_unit_conditions": 0, "false_support_count": 0,
              "ambiguous_unit_conditions_retained_in_F": 0, "invalid_trial_conditions": 0, "complete_comparable_qa": 0,
              "unique_definite_units": 0, "unique_ambiguous_units": 0, "no_unit_qa": 0}
    observations = []
    healthy = True
    for record in records:
        identifier, evaluation = record["trace"]["record_id"], record["evaluation"]
        claims = evaluation["claims"]
        counts["no_unit_qa"] += not claims
        for claim in claims:
            truth = expected[identifier, claim["claim_id"]]
            counts["unique_ambiguous_units" if truth == "ambiguous" else "unique_definite_units"] += 1
        trials = {t["trial_id"]: t for t in evaluation["trials"]}
        planned = evaluation["plan"]["trials"]
        require(len(trials) == len(evaluation["trials"]) and set(trials) == {t["trial_id"] for t in planned},
                "All planned trials must remain in semantic denominators")
        complete = all(t["status"] == "ok" and t["score"] is not None for t in trials.values())
        counts["complete_comparable_qa"] += bool(complete and len(evaluation["plan"]["order_group"]) >= 2 and
                                                len(evaluation["plan"]["repeat_group"]) >= 2)
        for trial in trials.values():
            task = record["tasks"]["judges"].get(trial["trial_id"])
            valid = task is not None and task["status"] == "ok"
            healthy = healthy and (not claims or valid)
            predicted = {v["claim_id"]: v["label"] for v in task["parsed"]["verdicts"]} if valid else {}
            counts["invalid_trial_conditions"] += bool(claims and not valid)
            for claim in claims:
                truth, actual = expected[identifier, claim["claim_id"]], predicted.get(claim["claim_id"])
                observations.append(((groups or {}).get(identifier, identifier), (identifier, claim["claim_id"]), truth, actual))
                if truth == "ambiguous":
                    counts["ambiguous_unit_conditions_retained_in_F"] += 1
                    continue
                counts["planned_definite_unit_conditions"] += 1
                counts["exact_correct"] += actual == truth
                if truth == "supported":
                    counts["planned_supported_unit_conditions"] += 1
                    counts["supported_exact_correct"] += actual == truth
                else:
                    counts["planned_definite_negative_unit_conditions"] += 1
                    counts["false_support_count"] += actual == "supported"
    counts["exact_label_accuracy"] = counts["exact_correct"] / counts["planned_definite_unit_conditions"] if counts["planned_definite_unit_conditions"] else None
    counts["supported_label_accuracy"] = counts["supported_exact_correct"] / counts["planned_supported_unit_conditions"] if counts["planned_supported_unit_conditions"] else None
    if binary:
        from rag_research.experiments.semantic_adoption import summarize

        counts["binary_adoption"] = summarize(observations, healthy=healthy)
    return counts


def sealed_inputs(inputs, *, analysis_split="development", allow_replay=False):
    require(analysis_split in {"development", "calibration"}, "Unknown review analysis split")
    require(isinstance(inputs, list) and len(inputs) == 2, "One sealed run per language is required")
    sealed, frozen = [], {}
    for spec in inputs:
        require(set(spec) == {"run", "quality_bundle", "quality_annotations", "unit_bundle", "unit_annotations"},
                "Unexpected semantic input fields")
        paths = {k: (ROOT / v).resolve() for k, v in spec.items()}
        run = paths["run"]
        require(bilingual_quality.analysis_split(run, root=ROOT, allow_replay=allow_replay) == analysis_split and
                paths["quality_bundle"].is_relative_to(run) and paths["unit_bundle"].is_relative_to(paths["quality_bundle"]) and
                paths["quality_annotations"].is_relative_to(paths["quality_bundle"]) and
                paths["unit_annotations"].is_relative_to(paths["unit_bundle"]), "Semantic input paths escape Development")
        quality_packet, mapping, _ = bilingual_quality.sealed_annotations(paths["quality_bundle"], paths["quality_annotations"])
        packet = read_json(paths["unit_bundle"] / "packet.json")
        labels = validate_unit_annotations(packet, read_json(paths["unit_annotations"]), sealed=True)
        require(packet["quality_packet_sha256"] == quality_packet["packet_sha256"], "Semantic and quality packets differ")
        sealed.append((paths, quality_packet, mapping, packet, labels))
    require(len({p[0]["run"] for p in sealed}) == 2 and {p[3]["language"] for p in sealed} == {"en", "ja"},
            "Two distinct English/Japanese runs are required")
    for paths, *_ in sealed:
        for p in (paths["quality_annotations"], paths["unit_annotations"], paths["unit_bundle"] / "packet.json",
                  paths["quality_bundle"] / "packet.json", paths["quality_bundle"] / "mapping.private.json"):
            frozen[p] = file_hash(p)
    return sealed, frozen


def analyze_semantics(inputs, *, analysis_split="development", canonical_runs=None):
    sealed, frozen = sealed_inputs(inputs, analysis_split=analysis_split, allow_replay=canonical_runs is not None)
    results, conditions, gates, versions = {}, [], {}, []
    for paths, quality_packet, mapping, packet, labels in sealed:
        require(all(file_hash(p) == h for p, h in frozen.items()), "Sealed review changed")
        manifest, report, _ = bilingual_quality.validated_annotations(paths["run"], paths["quality_bundle"], paths["quality_annotations"])
        language = manifest["language"]
        if analysis_split == "calibration":
            from rag_research.experiments.calibration_protocol import review_contract

            protocol = review_contract(paths["run"], manifest, canonical_runs=canonical_runs)
        require(language == packet["language"] and make_unit_packet(quality_packet, language) == packet,
                "Semantic packet differs from sealed actual candidates")
        expected = {(slot["record_id"], claim["claim_id"]): labels[case["annotation_id"], claim["claim_id"]]["label"]
            for case in packet["cases"] for slot in mapping["assignments"][case["annotation_id"]] if slot["stage"] == "initial"
            for claim in case["unit_audit"]["claims"]}
        fixed = {slot["record_id"]: case["unit_audit"]["claims"] for case in packet["cases"]
                 for slot in mapping["assignments"][case["annotation_id"]] if slot["stage"] == "initial"}
        for row in report["records"]:
            require(row["evaluation"]["claims"] == fixed[row["trace"]["record_id"]], "Reviewed fixed sentence content differs")
            for claim in row["evaluation"]["claims"]:
                require((row["trace"]["record_id"], claim["claim_id"]) in expected, "Fixed unit truth missing")
        results[language] = semantic_counts(report["records"], expected)
        counts = results[language]
        gate = False
        adoption_version = LEGACY
        scope = manifest["config"].get("execution_scope")
        if scope == "main_development_v1" or analysis_split == "calibration":
            binding = protocol["rules"] if analysis_split == "calibration" else manifest["config"]["main_execution_policy"]
            policy_path = (ROOT / binding["path"]).resolve()
            require(policy_path.is_relative_to(ROOT) and file_hash(policy_path) == binding["sha256"], "Semantic adoption policy changed")
            policy = read_json(policy_path)
            validate_main_policy(policy)
            rules = policy["semantic_adoption_after_blind_seal"]
            adoption_version = version(policy)
            require(adoption_version == version(manifest["config"]), "Run/policy semantic adoption versions differ")
            binary = version(policy) == BINARY
            if binary:
                results[language] = counts = semantic_counts(report["records"], expected, binary=True,
                    groups={r["record_id"]: r["document_group_id"] for r in manifest["selection"]})
            semantic_passed = counts["binary_adoption"]["passed"] if binary else (
                counts["exact_label_accuracy"] is not None and counts["supported_label_accuracy"] is not None and
                counts["exact_label_accuracy"] >= rules["minimum_exact_label_accuracy_per_language"] and
                counts["supported_label_accuracy"] >= rules["minimum_supported_label_accuracy_per_language"] and
                counts["false_support_count"] <= rules["maximum_definite_negative_false_support"])
            gate = (report["selected_qa_count"] == len(report["records"]) == policy["count_per_language"] == 20 and
                    not report["failures"] and counts["invalid_trial_conditions"] == 0 and
                    semantic_passed and
                    counts["complete_comparable_qa"] >= rules["minimum_complete_comparable_qa_per_language"])
        gates[language] = gate
        versions.append(adoption_version)
        conditions.append(condition(manifest))
    require(conditions[0] == conditions[1], "Semantic conditions must match across languages")
    require(versions[0] == versions[1], "Bilingual semantic adoption versions differ")
    require(all(file_hash(p) == h for p, h in frozen.items()), "Sealed review changed during comparison")
    return {"purpose": f"sealed-bilingual-{analysis_split}-unit-semantic-audit-not-final-evaluation", "languages": results,
            "analysis_split": analysis_split, "semantic_adoption_version": versions[0],
            "main_development_semantic_gate_per_language": gates if analysis_split == "development" else {},
            "main_development_semantic_gate_passed": analysis_split == "development" and all(gates.values()),
            "calibration_semantic_gate_per_language": gates if analysis_split == "calibration" else {},
            "calibration_semantic_gate_passed": analysis_split == "calibration" and all(gates.values()),
            "sealed_files_sha256": {str(p.relative_to(ROOT)): h for p, h in frozen.items()},
            "human_reviewed": False, "annotation_history_independence_not_assumed": True,
            "gate11_passed": False, "phase12_allowed": False}
