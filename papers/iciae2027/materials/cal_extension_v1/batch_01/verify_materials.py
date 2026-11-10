"""Offline, standard-library verification of the self-contained writing materials.

No path from source_manifest/controller/report metadata is ever opened. Only
validated relative paths inside the materials folder are used for data access.
"""

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from urllib.parse import unquote

POLICIES = {"no_repair", "always_rewrite", "original", "reversed", "shuffle_1", "shuffle_2", "shuffle_3", "repeat_2", "repeat_3", "repeat_4", "repeat_5"}
Y = {"reliable": 1, "unreliable": 0, "indeterminate": None}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def path_in(root, relative):
    p = Path(relative)
    require(not p.is_absolute() and ".." not in p.parts, "Non-relative/escaping material path")
    result = (root / p).resolve()
    require(result.is_relative_to(root.resolve()), "Material path escapes root")
    return result


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def close(a, b, name):
    a = None if a == "" else a
    b = None if b == "" else b
    if a is None or b is None:
        require(a is b, "Unknown value was imputed: " + name)
    else:
        require(math.isclose(float(a), float(b), rel_tol=1e-11, abs_tol=1e-10), "Numeric mismatch: " + name)


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def csv_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def comparable_value(evaluation):
    if evaluation is None:
        return None, None, None, False
    trials = {t["trial_id"]: t for t in evaluation["trials"]}
    rates = []
    for group in (evaluation["plan"]["order_group"], evaluation["plan"]["repeat_group"]):
        values = [trials[name] for name in group if trials[name]["status"] == "ok"]
        pairs = list(combinations(values, 2))
        rates.append(sum(a["decision"] != b["decision"] for a, b in pairs) / len(pairs) if pairs else None)
    ok = all(t["status"] == "ok" for t in trials.values()) and all(v is not None for v in rates)
    return rates[0], rates[1], rates[0] - rates[1] if ok else None, ok


def task_cost(tasks):
    steps = []
    for task in tasks:
        steps.extend(task["subtask_costs"] if task.get("execution_mode") in {"claimwise-v1", "source-reading-v1"} else [task])
    attempted = [t for t in steps if t.get("completion_attempted", False)]
    unknown = sum(t.get("error_code") == "interrupted_unknown_outcome" for t in attempted)
    return {"completion_attempts": None if unknown else len(attempted), "recorded_completion_attempts": len(attempted),
        "unknown_outcome_steps": unknown, "input_tokens": sum(t.get("input_tokens") or 0 for t in attempted),
        "output_tokens": sum(t.get("output_tokens") or 0 for t in attempted),
        "summed_step_seconds": sum(t.get("elapsed_seconds", 0) for t in steps),
        "incomplete": bool(unknown) or any(t.get("cost_incomplete", False) for t in steps)}


def annotation_bundle(root, cohort, language):
    base = root / "annotations" / cohort / language
    packet, mapping = read(base / "packet.json"), read(base / "mapping.private.json")
    annotations = read(base / "annotations.json")
    unit_packet, unit_labels = read(base / "units/packet.json"), read(base / "units/annotations.json")
    for p in (packet, unit_packet):
        require(p["packet_sha256"] == digest({k: v for k, v in p.items() if k != "packet_sha256"}), "Packet digest differs")
    require(unit_packet["quality_packet_sha256"] == packet["packet_sha256"], "Unit/quality packet mismatch")
    require(annotations["packet_sha256"] == packet["packet_sha256"] and unit_labels["packet_sha256"] == unit_packet["packet_sha256"], "Annotations bound to another packet")
    require(mapping["packet_sha256"] == packet["packet_sha256"], "Anonymous mapping packet mismatch")
    cases = {c["annotation_id"]: c for c in packet["cases"]}
    labels = {a["annotation_id"]: a for a in annotations["annotations"]}
    require(len(labels) == len(annotations["annotations"]) and set(cases) == set(labels) == set(mapping["assignments"]), "Missing/duplicate candidate annotations")
    by_stage = {}
    for cid, assignments in mapping["assignments"].items():
        case, label = cases[cid], labels[cid]
        require(case["candidate_sha256"] == digest({k: v for k, v in case.items() if k not in {"annotation_id", "candidate_sha256"}}), "Candidate digest differs")
        require(label["candidate_sha256"] == case["candidate_sha256"] and label["label"] in Y, "Unsealed quality/identity")
        require(label["reason"].strip() and label["annotator"].strip() and label["elapsed_seconds"] > 0, "Quality provenance missing")
        for evidence in label["evidence"]:
            require(any(evidence["passage_id"] == d["passage_id"] and evidence["quote"].strip() and evidence["quote"] in d["text"]
                for d in case["documents"] + case["gold_documents"]), "Quality evidence quote differs")
        criteria = set(label["criteria"].values())
        if label["label"] == "reliable":
            require(criteria == {"pass"} and any(e["passage_id"] == d["passage_id"] and e["quote"] in d["text"] for e in label["evidence"] for d in case["documents"]), "Reliable without actual context support")
        elif label["label"] == "unreliable":
            require("fail" in criteria, "Unreliable criteria mismatch")
        else:
            require("uncertain" in criteria and not criteria.intersection({"fail", "pending"}), "Unknown quality criteria mismatch")
        for slot in assignments:
            key = slot["record_id"], slot["stage"]
            require(key not in by_stage, "Duplicate stage assignment")
            by_stage[key] = (case, label)
    ucases = {c["annotation_id"]: c for c in unit_packet["cases"]}
    expected = {(c["annotation_id"], claim["claim_id"]): (c, claim) for c in unit_packet["cases"] for claim in c["unit_audit"]["claims"]}
    observed = {(a["annotation_id"], a["claim_id"]): a for a in unit_labels["annotations"]}
    require(len(observed) == len(unit_labels["annotations"]) and set(observed) == set(expected), "Unit identities/counts differ")
    for key, annotation in observed.items():
        case, claim = expected[key]
        require(case["unit_candidate_sha256"] == digest({k: v for k, v in case.items() if k != "unit_candidate_sha256"}), "Unit candidate digest differs")
        require(annotation["claim_text_sha256"] == digest(claim["text"]) and annotation["unit_candidate_sha256"] == case["unit_candidate_sha256"], "Fixed claim identity differs")
        require(annotation["label"] in {"supported", "contradicted", "not_supported", "ambiguous"} and annotation["human_reviewed"] is False, "Pending/invalid unit label")
        require(annotation["label"] not in {"supported", "contradicted"} or bool(annotation["evidence"]), "Missing unit support/conflict evidence")
        for e in annotation["evidence"]:
            require(any(e["passage_id"] == d["passage_id"] and e["quote"].strip() and e["quote"] in d["text"] for d in case["documents"]), "Unit quote is not actual verbatim context")
    return by_stage, ucases, observed


def verify(root):
    root = root.resolve()
    manifest = read(root / "artifact_manifest.json")
    actual_files = set()
    for p in root.rglob("*"):
        require(not p.is_symlink(), "Symlink in materials")
        if p.is_file() and not any(v in {"__pycache__", ".pytest_cache", ".ruff_cache"} for v in p.parts) and p != root / "artifact_manifest.json" and p.suffix != ".pyc":
            actual_files.add(p.relative_to(root).as_posix())
    require(actual_files == set(manifest["files"]), "Missing/unlisted material files")
    for name, value in manifest["files"].items():
        p = path_in(root, name)
        require(p.stat().st_size == value["bytes"] and sha(p) == value["sha256"], "Artifact hash differs: " + name)
    source = read(root / "source_manifest.json")
    require(source["new_inference_calls"] == source["new_annotation_calls"] == 0, "Unexpected experiment/reannotation")
    for copy in source["copies"]:
        p = path_in(root, copy["destination"])
        require(sha(p) == copy["source"]["sha256"] == source["source_files"][copy["source"]["path"]]["sha256"], "Exact source copy changed")
    qa = [read(p) for p in sorted((root / "inputs").glob("*.json"))]
    require(len(qa) == 40 and len({q["qa_key"] for q in qa}) == 40 and len({q["record_id"] for q in qa}) == 40, "Expected all 40 unique selected QA")
    require(Counter((q["cohort"], q["language"]) for q in qa) == Counter({(cohort, language): 20 for cohort in ("cal",) for language in ("en", "ja")}), "Two 20-QA strata required")
    require([{k: q[k] for k in ("qa_key", "cohort", "language", "record_id", "document_group_id")} for q in qa] ==
        sorted(source["qa_correspondence"], key=lambda r: r["qa_key"]), "Source QA correspondence differs")
    index = {q["qa_key"]: q for q in qa}
    qtable = csv_rows(root / "qa_summary.csv")
    require(len(qtable) == 40 and {q["qa_key"] for q in qtable} == set(index), "QA summary missing rows")
    trials = rows(root / "trials.jsonl")
    trial_index = {(t["qa_key"], t["trial_id"]): t for t in trials}
    require(len(trial_index) == len(trials), "Duplicate trial")
    policies = csv_rows(root / "policy_outcomes.csv")
    policy_index = {(p["qa_key"], p["route"]): p for p in policies}
    require(len(policies) == len(policy_index) == 440 and set(policy_index) == {(key, name) for key in index for name in POLICIES}, "All QA/policy states required")
    observed_policy = []
    comparisons, semantics, transitions = {}, {}, {}
    planned_count, candidate_assignments = 0, 0
    for cohort in ("cal",):
        original_analysis = read(root / "analysis" / (cohort + ".private.json"))
        public = read(root / "published_results" / (cohort + "_summary.json"))
        require(public["source_analysis_sha256"] == sha(root / "analysis" / (cohort + ".private.json")), "Analysis/public source binding differs")
        seal = read(root / "provenance" / cohort / "all_annotations.seal.json")
        require(seal["all_both_languages_sealed"] and not seal["human_reviewed"], "Missing full annotation seal")
        for name, expected in seal["files"].items():
            require("/quality/" in name and name.split('/')[0] in {"en", "ja"}, "Unexpected annotation seal path")
            require(sha(path_in(root, "annotations/" + cohort + "/" + name.replace("/quality/", "/", 1))) == expected, "Original annotation seal differs")
        for language in ("en", "ja"):
            stem = root / "provenance" / cohort / language
            m, report = read(stem / "manifest.json"), read(stem / "report.private.json")
            local_qa = {q["record_id"]: q for q in qa if q["cohort"] == cohort and q["language"] == language}
            require(set(local_qa) == {r["record_id"] for r in m["selection"]}, "Selection IDs differ")
            groups = {r["record_id"]: r["document_group_id"] for r in m["selection"]}
            require(all(q["document_group_id"] == groups[rid] for rid, q in local_qa.items()), "Document group differs")
            require(all(q["source_qa_split"] == ("development" if cohort == "main" or language == "en" else "calibration") for q in local_qa.values()), "QA source/analysis role conflated")
            assigned, unit_cases, unit_labels = annotation_bundle(root, cohort, language)
            require({rid for rid, _ in assigned} <= set(local_qa), "Unselected QA in annotation mapping")
            candidate_assignments += len(assigned)
            recs = {r["trace"]["record_id"]: r for r in report["records"]}
            stats = {q["record_id"]: q for q in original_analysis["statistics"]["qa"] if q["language"] == language}
            expected_routes = {(r["record_id"], r["route"]): r for r in original_analysis["quality_routes"][language]["routes"]}
            mean_values = []
            semantic = Counter()
            transition_counts = Counter()
            for rid, q in local_qa.items():
                baseline = read(path_in(root, q["A"]["copy"]))
                require(digest(q["qa_source"]) == source["qa_source_row_sha256"][q["qa_key"]], "Selected source QA row changed")
                require(baseline["record_id"] == rid and baseline["question"] == q["question"] == q["qa_source"]["question"], "QA/baseline identity differs")
                require(q["A"]["status"] == baseline["status"] and q["A"]["answer"] == baseline.get("answer"), "Initial answer changed")
                corpus = {d["passage_id"]: d for d in q["corpus_documents"]}
                for d in corpus.values():
                    require(hashlib.sha256(d["text"].encode()).hexdigest() == d["source_metadata"]["text_sha256"], "Corpus source hash differs")
                for d in q["used_documents"] + q["gold_documents"]:
                    span = d["corpus_character_span"]
                    require(corpus[d["passage_id"]]["text"][span["start"]:span["end"]] == d["text"] and
                        hashlib.sha256(d["text"].encode()).hexdigest() == d["actual_text_sha256"], "Actual used context/source span differs")
                    require(d["source_metadata"]["source_url"].startswith("https://"), "Missing source attribution")
                for stage, letter in (("initial", "A"), ("rewritten", "B")):
                    a = assigned.get((rid, stage))
                    quality = q[letter]["quality"]
                    if a is None:
                        require(quality["annotation_id"] is None and quality["y"] is None, "Missing candidate quality imputed")
                    else:
                        case, label = a
                        require(case["answer"] == q[letter]["answer"] and quality["annotation_id"] == label["annotation_id"] and quality["annotation"] == label, "Candidate/stage annotation differs")
                        require(case["question"] == q["question"] and case["documents"] == [{k: d[k] for k in ("passage_id", "title", "text")} for d in q["used_documents"]], "Annotated actual context differs")
                        require(case["reference_answers"] == q["qa_source"]["reference_answers"], "QA Reference differs from annotation input")
                        require(quality["y"] == Y[label["label"]], "Quality Y differs")
                record = recs.get(rid)
                if record is None:
                    require(q["A"]["status"] != "ok" and not q["fixed_claims"] and q["trial_plan"] is None, "Absent record not represented as missing")
                    require(not any(key[0] == q["qa_key"] for key in trial_index), "Invented trial for unavailable initial answer")
                    evaluation = None
                else:
                    evaluation = record["evaluation"]
                    require(q["fixed_claims"] == evaluation["claims"] and q["trial_plan"] == evaluation["plan"], "Fixed units/plan differ")
                    require(q["A"]["answer"] == record["trace"]["answer"] and q["B"]["answer"] == record["rewrite"].get("answer") and q["B"]["status"] == record["rewrite"]["status"], "A/B differs from source report")
                    require([{k: d[k] for k in ("passage_id", "title", "text")} for d in q["used_documents"]] == record["trace"]["documents"], "Used context differs")
                    plan = evaluation["plan"]
                    planned = {t["trial_id"]: t for t in plan["trials"]}
                    require(set(plan["order_group"]) & set(plan["repeat_group"]) == {"original"}, "Shared original incorrectly counted")
                    require(len({tuple(planned[name]["document_ids"]) for name in plan["order_group"]}) == len(plan["order_group"]), "Duplicate orders not deduplicated")
                    require(all(planned[name]["document_ids"] == planned["original"]["document_ids"] for name in plan["repeat_group"]), "Repeat order differs")
                    require({name for key, name in trial_index if key == q["qa_key"]} == set(planned), "Planned/exported trials differ")
                    planned_count += len(planned)
                    cid = q["A"]["quality"]["annotation_id"]
                    require(unit_cases[cid]["unit_audit"]["claims"] == q["fixed_claims"], "Unit annotation claims differ")
                    for claim in q["fixed_claims"]:
                        semantic["unique_ambiguous_units" if unit_labels[cid, claim["claim_id"]]["label"] == "ambiguous" else "unique_definite_units"] += 1
                    semantic["no_unit_qa"] += not q["fixed_claims"]
                    for saved in evaluation["trials"]:
                        trial = trial_index[q["qa_key"], saved["trial_id"]]
                        require(all(trial[k] == v for k, v in saved.items()), "Trial differs from source report")
                        require(trial["document_ids"] == planned[trial["trial_id"]]["document_ids"] and set(trial["document_ids"]) == {d["passage_id"] for d in q["used_documents"]}, "Trial document order/set differs")
                        task = record["tasks"]["judges"].get(trial["trial_id"])
                        verdicts = (task.get("parsed") or {}).get("verdicts", []) if task else []
                        require(trial["verdicts"] == verdicts, "Exported fixed-unit verdicts differ")
                        require(trial["judge_task_present"] == bool(task) and trial["native_subtask_costs"] == (task.get("subtask_costs", []) if task else []), "Trial native cost binding differs")
                        require(all(value == (task.get(k) if task else None) for k, value in trial["cost"].items()), "Trial cost differs from source")
                        if trial["status"] == "ok":
                            require(set(v["claim_id"] for v in verdicts) == {c["claim_id"] for c in q["fixed_claims"]} and len(verdicts) == len(q["fixed_claims"]), "Verdict coverage differs")
                            f = sum(v["label"] == "supported" for v in verdicts) / len(q["fixed_claims"])
                            close(f, trial["score"], "F from fixed labels")
                            require(trial["decision"] == ("accept" if f >= evaluation["threshold"] else "rewrite"), "F/decision threshold mismatch")
                            require(trial["action"] == ("keep_initial" if f >= evaluation["threshold"] else "rewrite_requested"), "F/action mismatch")
                        else:
                            require(trial["score"] is None and trial["decision"] == "unscorable", "Unknown F imputed")
                            expected_action = "rewrite_requested" if q["extraction_audit"].get("exclusion") == "standalone_refusal" and m["config"]["decision"].get("bare_refusal_policy") == "rewrite_once" else "keep_initial_fallback"
                            require(trial["action"] == expected_action, "Unscorable/refusal action mismatch")
                        predicted = {v["claim_id"]: v["label"] for v in verdicts}
                        semantic["invalid_trial_conditions"] += bool(q["fixed_claims"] and (task is None or task["status"] != "ok"))
                        for claim in q["fixed_claims"]:
                            truth, actual = unit_labels[cid, claim["claim_id"]]["label"], predicted.get(claim["claim_id"])
                            if truth == "ambiguous":
                                semantic["ambiguous_unit_conditions_retained_in_F"] += 1
                                continue
                            semantic["planned_definite_unit_conditions"] += 1
                            semantic["exact_correct"] += truth == actual
                            if truth == "supported":
                                semantic["planned_supported_unit_conditions"] += 1
                                semantic["supported_exact_correct"] += actual == truth
                            else:
                                semantic["planned_definite_negative_unit_conditions"] += 1
                                semantic["false_support_count"] += actual == "supported"
                order, repeat, increment, comparable = comparable_value(evaluation)
                recorded = q["statistical_comparison"]
                require(recorded == stats[rid] and comparable == recorded["comparable"], "QA comparison differs")
                close(increment, recorded["increment"], "QA D")
                if evaluation:
                    close(order, recorded["order"]["rate"], "QA O")
                    close(repeat, recorded["repeat"]["rate"], "QA R")
                if comparable:
                    mean_values.append(increment)
                    semantic["complete_comparable_qa"] += 1
                exported = next(t for t in qtable if t["qa_key"] == q["qa_key"])
                require(exported["record_id"] == rid and exported["document_group_id"] == groups[rid] and exported["comparable"] == str(comparable), "QA CSV identity/state differs")
                require(exported["increment"] == "" if increment is None else math.isclose(float(exported["increment"]), increment), "QA CSV missing/number differs")
                expected_fields = {"cohort": cohort, "language": language, "source_qa_split": q["source_qa_split"],
                    "initial_status": q["A"]["status"], "rewrite_status": q["B"]["status"],
                    "comparison_reason": recorded["reason"], "fixed_claim_count": len(q["fixed_claims"]),
                    "order_rate": recorded.get("order", {}).get("rate"), "repeat_rate": recorded.get("repeat", {}).get("rate"),
                    "A_quality": q["A"]["quality"]["status"], "A_y": q["A"]["quality"]["y"],
                    "B_quality": q["B"]["quality"]["status"], "B_y": q["B"]["quality"]["y"],
                    "order_varies": recorded.get("order", {}).get("disagreeing_pairs", 0) > 0,
                    "repeat_varies": recorded.get("repeat", {}).get("disagreeing_pairs", 0) > 0,
                    "input_path": "inputs/" + q["qa_key"] + ".json"}
                require(all(exported[k] == (str(v) if v is not None else "") for k, v in expected_fields.items()), "QA summary columns differ")
                a, b = q["A"]["quality"]["y"], q["B"]["quality"]["y"]
                known = a is not None and b is not None and q["B"]["status"] == "ok"
                transition = f"{a}->{b}" if known else "unknown"
                if record:
                    transition_counts[transition] += 1
                aliases = evaluation["plan"].get("duplicate_order_aliases", {}) if evaluation else {}
                for name in POLICIES:
                    exported_policy = policy_index[q["qa_key"], name]
                    route = expected_routes.get((rid, name))
                    state = "observed" if route else "omitted_duplicate_order_alias" if name in aliases else "initial_unavailable"
                    require(exported_policy["policy_state"] == state and exported_policy["alias_of"] == (aliases.get(name) or ""), "Policy omission/alias differs")
                    if route is None:
                        require(exported_policy["quality_y"] == exported_policy["input_tokens"] == exported_policy["recorded_completion_attempts"] == "", "Missing policy outcome/cost imputed")
                        continue
                    observed_policy.append((cohort, language, route))
                    requested = name == "always_rewrite" or name not in {"no_repair", "always_rewrite"} and trial_index[q["qa_key"], name]["action"] == "rewrite_requested"
                    selected = "rewritten" if requested and q["B"]["status"] == "ok" else "initial"
                    require(route["selected_stage"] == selected and route["rewrite_requested"] == requested, "Action/candidate selection differs")
                    require(route["selected_answer_sha256"] == digest(q["B" if selected == "rewritten" else "A"]["answer"]), "Selected candidate digest differs")
                    status = q["B" if selected == "rewritten" else "A"]["quality"]["status"]
                    require(route["quality_status"] == status and route["quality_y"] == Y[status] and route["quality_transition"] == transition, "Selected quality/transition differs")
                    require(route["missed_improvement"] == ((selected == "initial" and a == 0 and b == 1) if known else None), "Missed improvement differs")
                    require(route["harmful_rewrite"] == ((selected == "rewritten" and a == 1 and b == 0) if known else None), "Harmful rewrite differs")
                    bc = record["baseline_cost"]
                    tasks = [{"completion_attempted": bool(bc["answer_generation_calls"]), "input_tokens": bc["input_tokens"], "output_tokens": bc["output_tokens"],
                        "elapsed_seconds": (bc["generation_seconds"] or 0) + (bc["context_seconds"] or 0)}]
                    if name not in {"no_repair", "always_rewrite"}:
                        tasks.append(record["tasks"]["extraction"])
                        if name in record["tasks"]["judges"]:
                            tasks.append(record["tasks"]["judges"][name])
                    if requested:
                        tasks.append(record["rewrite"])
                    cost = task_cost(tasks)
                    for field, value in cost.items():
                        close(value, route["operational_cost"][field], "Route cost " + field)
                    for field, value in {**{k: v for k, v in route.items() if k not in {"record_id", "route", "operational_cost"}}, **route["operational_cost"]}.items():
                        require(exported_policy[field] == (str(value) if value is not None else ""), "Policy CSV value differs: " + field)
            target = public["statistics"]["languages"][language]
            require(len(mean_values) == target["comparable_qa_count"], "Comparable denominator differs")
            close((sum(mean_values) / len(mean_values) if mean_values else None), target["mean_increment"], "Mean D")
            require(public["statistics"] == {k: v for k, v in original_analysis["statistics"].items() if k != "qa"}, "Bootstrap/original statistics differ")
            for key, value in semantic.items():
                require(value == public["semantics"][language][key], "Semantic audit differs: " + key)
            require(dict(transition_counts) == {k: v for k, v in original_analysis["quality_routes"][language]["quality_transitions"].items() if v}, "Quality transitions differ")
            comparisons[cohort + "/" + language] = len(mean_values)
            semantics[cohort + "/" + language] = dict(semantic)
            transitions[cohort + "/" + language] = dict(transition_counts)
    require(planned_count == len(trials), "Unselected/unplanned trial in export")
    verify_public_tables(root, qa, observed_policy)
    proof_files = list((root / "provenance/annotation_jobs").glob("*/attempt-*/provenance.json"))
    require(bool(proof_files) or candidate_assignments == 0, "Missing completed annotation job provenance")
    for p in proof_files:
        proof = read(p)
        require(sha(p.with_name("input.json")) == proof["input_sha256"] and sha(p.with_name("output.json")) == proof["output_sha256"], "Annotation job input/output hash differs")
        if proof.get("stdin_sha256"):
            require(sha(p.with_name("stdin.json")) == proof["stdin_sha256"], "Annotation stdin provenance differs")
        payload = read(p.with_name("input.json"))
        allowed = read(root / "annotations" / payload["cohort"] / payload["language"] / ("units/packet.json" if payload["kind"] == "units" else "packet.json"))
        require(payload["full_packet_sha256"] == allowed["packet_sha256"] and {c["annotation_id"] for c in payload["cases"]} <= {c["annotation_id"] for c in allowed["cases"]}, "Unselected/foreign annotation job")
    cases = read(root / "cases/index.json")["cases"]
    require(2 <= len(cases) <= 4 and {c["language"] for c in cases} == {"en", "ja"}, "Missing bilingual explanatory cases")
    for case in cases:
        q = index[case["qa_key"]]
        require(read(root / "cases" / (case["case_id"] + ".json")) == case and case["record_id"] == q["record_id"], "Case binding differs")
        require(case["input_path"] == "inputs/" + q["qa_key"] + ".json", "Case input path differs")
        require(case["post_outcome_explanatory_selection"] is True, "Case selection disclosure missing")
        require(case["trials"] == [t for t in trials if t["qa_key"] == case["qa_key"]], "Case trials differ")
        require([{k: str(v) if v is not None else "" for k, v in row.items()} for row in case["policy_outcomes"]] ==
            [r for r in policies if r["qa_key"] == case["qa_key"]], "Case quality/cost/policy outcomes differ")
        for t in case["trials"]:
            for v in t["verdicts"]:
                for e in v.get("evidence", []):
                    require(any(e["passage_id"] == d["passage_id"] and e["quote"] in d["text"] for d in q["used_documents"]), "Case internal evidence differs")
    for p in root.rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", p.read_text(encoding="utf-8")):
            if "://" in target or target.startswith(("#", "mailto:")):
                continue
            relative = unquote(target.split("#", 1)[0])
            destination = (p.parent / relative).resolve()
            require(destination.is_relative_to(root) and destination.exists(), "Broken/nonlocal materials link: " + target)
    return {"status": "passed", "qa": len(qa), "strata": 2, "comparable_qa": comparisons,
        "planned_trials": len(trials), "candidate_stage_assignments": candidate_assignments,
        "annotation_jobs": len(proof_files),
        "policy_slots": len(policies), "observed_policy_outcomes": len(observed_policy), "cases": len(cases),
        "artifact_files": len(manifest["files"]), "semantic_audit": "recomputed", "route_costs": "recomputed", "published_tables": "matched",
        "bootstrap": "original implementation/version/seed/replicates and exact result retained; not regenerated with a different RNG",
        "original_run_access_required": False, "new_inference_calls": 0, "new_annotation_calls": 0}


def verify_public_tables(root, qa, observed):
    trial_rows = rows(root / "trials.jsonl")
    for row in csv_rows(root / "published_results/primary_comparison.csv"):
        selected = [q for q in qa if q["cohort"] == row["cohort"] and q["language"] == row["language"]]
        good = [q for q in selected if q["statistical_comparison"]["comparable"]]
        require(int(row["selected_qa"]) == len(selected) and int(row["comparable_qa"]) == len(good) and int(row["missing_qa"]) == len(selected) - len(good), "Published primary denominator differs")
        close((sum(q["statistical_comparison"]["increment"] for q in good) / len(good) if good else None), row["mean_increment"], "Published primary mean")
        original = read(root / "published_results" / (row["cohort"] + "_summary.json"))["statistics"]["languages"][row["language"]]
        close(row["ci95_low"], (original["ci95"][0] if original["ci95"] else None), "Original CI low")
        close(row["ci95_high"], (original["ci95"][1] if original["ci95"] else None), "Original CI high")
    for row in csv_rows(root / "published_results/quality_and_operational_cost.csv"):
        selected = [r for cohort, language, r in observed if cohort == row["cohort"] and language == row["language"] and r["route"] == row["route"]]
        counts = Counter(r["quality_status"] for r in selected)
        for label in ("reliable", "unreliable", "indeterminate", "pending"):
            require(int(row[label]) == counts[label], "Published quality count differs")
        require(int(row["available_initial_qa"]) == len(selected) and int(row["baseline_missing"]) == 20 - len(selected), "Published legacy omission column differs")
        for field, key in (("native_attempts_sum", "recorded_completion_attempts"), ("input_tokens_sum", "input_tokens"), ("output_tokens_sum", "output_tokens")):
            close(sum(r["operational_cost"][key] for r in selected), row[field], "Published route cost")
    native = rows(root / "analysis/native_calls.jsonl")
    external = read(root / "analysis/external_attempts.json")
    for old in external:
        original = read(path_in(root, old["source_copy"]))
        require(original["status"] == "started" and original.get("output_tokens") is None and not original.get("runtime_response"), "Historical unknown response changed")
        require(old["input_tokens"] == original["input_tokens"] and old["output_tokens"] is old["elapsed_seconds"] is None and old["cost_incomplete"] is True, "Unknown historical cost imputed")
    for row in csv_rows(root / "published_results/collection_cost.csv"):
        values = [v for v in native if v["cohort"] == row["cohort"] and v["language"] == row["language"]]
        require(len(values) == int(row["active_native_attempts"]), "Native cost count differs")
        close(sum(v["output_tokens"] or 0 for v in values), row["output_tokens"], "Known collection output tokens")
        old = [v for v in external if v["cohort"] == row["cohort"] and v["language"] == row["language"]]
        require(len(old) == int(row["archived_external_attempts"]) and len(values) + len(old) == int(row["native_attempts"]), "Historical/active native counts differ")
        close(sum(v["input_tokens"] or 0 for v in values + old), row["input_tokens"], "Collection input tokens including archived attempts")
        close(sum(v.get("elapsed_seconds") or v.get("generation_seconds") or 0 for v in values), row["summed_observed_task_seconds"], "Observed collection step seconds")
        require(not old or row["native_cost_complete"] == "False" and row["total_output_tokens"] == "", "Unknown historical cost was imputed")
        require(sum(v["status"] == "error" for v in values) == int(row["failed_native_records"]), "Native failures differ")
    for cohort in ("cal",):
        summary = read(root / "published_results" / (cohort + "_summary.json"))
        actual = {(r["language"], r["threshold"]): r for r in summary["threshold_sensitivity"]}
        for row in csv_rows(root / "published_results/threshold_sensitivity.csv"):
            if row["cohort"] == cohort:
                expected = actual[row["language"], float(row["threshold"])]
                close(row["mean_increment"], expected["mean_increment"], "Threshold sensitivity")
                require(int(row["comparable_qa"]) == expected["comparable_qa"], "Sensitivity denominator differs")
                increments = []
                for q in qa:
                    if q["cohort"] != cohort or q["language"] != row["language"] or q["trial_plan"] is None:
                        continue
                    threshold = float(row["threshold"])
                    local = [{**t, "decision": "unscorable" if t["score"] is None else "accept" if t["score"] >= threshold else "rewrite"}
                        for t in trial_rows if t["qa_key"] == q["qa_key"]]
                    _, _, d, ok = comparable_value({"plan": q["trial_plan"], "trials": local})
                    if ok:
                        increments.append(d)
                require(len(increments) == int(row["comparable_qa"]), "Recomputed sensitivity denominator differs")
                close((sum(increments) / len(increments) if increments else None), row["mean_increment"], "Recomputed sensitivity mean")
    figure = read(root / "published_results/artifact_manifest.json")
    require(all(sha(path_in(root / "published_results", name)) == expected for name, expected in figure["files"].items()), "Original figure artifact changed")


def restrict_io(root):
    def audit(event, arguments):
        if event == "open" and isinstance(arguments[0], (str, bytes)):
            path = Path(arguments[0].decode() if isinstance(arguments[0], bytes) else arguments[0]).resolve()
            require(path.is_relative_to(root), "Verifier tried to open data outside materials: " + str(path))
        require(not event.startswith("socket."), "Verifier attempted network access")
    sys.addaudithook(audit)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-open", action="store_true", help="Reject data reads outside this material directory and socket access")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if args.audit_open:
        restrict_io(root)
    try:
        result = verify(root)
    except (ValueError, KeyError, OSError, TypeError) as failure:
        print(json.dumps({"status": "failed", "error": str(failure)}, ensure_ascii=False), file=sys.stderr)
        return 1
    result["all_data_reads_confined_to_materials"] = args.audit_open
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
