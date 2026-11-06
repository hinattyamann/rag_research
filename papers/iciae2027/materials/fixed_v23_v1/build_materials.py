"""Read-only export of the registered, already sealed 80-QA experiment.

Run with uv; requires the lab source repository only at extraction time.
The separate verifier uses only this output directory and the standard library.
"""

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
VERSION = "fixed-v23-paper-materials-v1"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def table(path, rows):
    require(bool(rows), "Cannot export an empty table")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def artifact_manifest(folder):
    ignored = {"artifact_manifest.json"}
    files = {}
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or any(p in {"__pycache__", ".pytest_cache", ".ruff_cache"} for p in path.parts):
            continue
        name = path.relative_to(folder).as_posix()
        if name in ignored or name.endswith(".pyc"):
            continue
        require(not path.is_symlink(), "Symlink in materials")
        files[name] = {"sha256": sha(path), "bytes": path.stat().st_size}
    save(folder / "artifact_manifest.json", {"version": VERSION, "files": files,
        "self_reference_excluded": True, "encoding": "UTF-8; exact copies retain their original bytes"})


class Export:
    def __init__(self, repo, output):
        self.repo, self.out = repo.resolve(), output.resolve()
        self.state = self.repo / ".tools/fixed-v23-automation-v1"
        self.config = read(self.state / "config.json")
        self.fixed = Path(self.config["checkout"])
        self.sources = {}
        self.copies = []
        self.qa_inputs, self.qa_rows, self.trials, self.policies = [], [], [], []
        self.runs = {}
        self.before = {}

    def source(self, path, role):
        path = Path(path).resolve()
        require(path.is_relative_to(self.repo), "Source outside the registered repository")
        key = path.relative_to(self.repo).as_posix()
        if key not in self.sources:
            self.sources[key] = {"sha256": sha(path), "bytes": path.stat().st_size, "roles": []}
        if role not in self.sources[key]["roles"]:
            self.sources[key]["roles"].append(role)
        return {"path": key, "sha256": self.sources[key]["sha256"]}

    def copy(self, source, destination, role="exact_copy"):
        binding = self.source(source, role)
        target = self.out / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            require(sha(target) == binding["sha256"], "Existing different copy: " + destination)
        else:
            shutil.copyfile(source, target)
        self.copies.append({"destination": destination, "source": binding, "transformation": "byte_identical"})
        return destination

    def preflight(self):
        require(sha(self.state / "config.json") == (self.state / "config.sha256").read_text().strip(), "Controller checksum changed")
        for path, expected in self.config["sealed_files"].items():
            require(sha(path) == expected, "Sealed controller prerequisite changed: " + path)
        release = read(self.fixed / "fixed-v23-release.json")
        changed = {name for name, expected in release["original_source_sha256"].items() if sha(self.fixed / name) != expected}
        require(changed == set(release["changed_original_sources"]), "Unregistered change from the base inference commit")
        for name, expected in release["files"].items():
            require(sha(self.fixed / name) == expected, "Frozen inference source changed")
        for cohort in ("main", "cal"):
            run = Path(self.config[cohort + "_run"])
            self.runs[cohort] = run
            seal = read(run / "all_annotations.seal.json")
            require(seal["all_both_languages_sealed"] and not seal["human_reviewed"], "Unsealed annotations")
            for name, expected in seal["files"].items():
                require(sha(run / name) == expected, "Annotation seal changed")
            analysis = read(self.state / cohort / "analysis.private.json")
            summary = read(self.repo / "reports/fixed_v23_order_study_v1" / (cohort + "_summary.json"))
            require(summary["source_analysis_sha256"] == sha(self.state / cohort / "analysis.private.json"), "Public analysis binding differs")
            for name, expected in analysis["source_files_sha256"].items():
                require(sha(run / name) == expected, "Scientific run changed: " + name)
                self.before[str(run / name)] = expected
            self.copy(run / "all_annotations.seal.json", f"provenance/{cohort}/all_annotations.seal.json")
            self.copy(self.state / cohort / "analysis.private.json", f"analysis/{cohort}.private.json")
            for language in ("en", "ja"):
                manifest = read(run / language / "manifest.json")
                for name, expected in manifest["source_sha256"].items():
                    require(sha(self.fixed / name) == expected, "Manifest input changed: " + name)
                require(len(manifest["selection"]) == 20 and len({q["record_id"] for q in manifest["selection"]}) == 20, "Wrong selection")
                for name in ("manifest.json", "report.private.json"):
                    self.copy(run / language / name, f"provenance/{cohort}/{language}/{name}")
                for name in ("packet.json", "mapping.private.json", "annotations.json", "units/packet.json", "units/annotations.json"):
                    self.copy(run / language / "quality" / name, f"annotations/{cohort}/{language}/{name}")
        protocol = read(self.runs["cal"] / "protocol.json")
        for name, expected in protocol["inputs"].items():
            require(sha(name) == expected, "Cal registration prerequisite changed")
        self.copy(self.runs["cal"] / "protocol.json", "provenance/cal/protocol.json")
        for source in (self.fixed.glob("fixed-v23-*.json")):
            self.copy(source, "provenance/registrations/" + source.name)
        self.copy(self.state / "config.json", "provenance/controller/config.json")
        self.copy(self.state / "cli_ledger.json", "provenance/controller/cli_ledger.json")
        self.copy(self.repo / "data/manifests/fixed_v23_prewriting_completion_v1.json", "provenance/prewriting_completion.json")

    def supporting_files(self):
        wanted = set()
        for cohort, run in self.runs.items():
            for language in ("en", "ja"):
                manifest = read(run / language / "manifest.json")
                cfg = manifest["config"]
                wanted.update(cfg[k] for k in ("assets", "prompts", "baseline_prompts", "baseline_config", "identity_manifest", "auxiliary_model_manifest"))
                wanted.add(cfg["execution"]["runtime_spec"])
        for name in sorted(wanted):
            self.copy(self.fixed / name, "provenance/frozen_files/" + name)
        for name in ("order_quality_rubric.md", "ai_quality_protocol.md", "phase11_statistical_plan.md",
                     "phase11_fixed_v23_recovery_v1.md", "phase11_fixed_v23_recovery_v2.md", "phase11_fixed_v23_recovery_v3.md",
                     "phase11_fixed_v23_annotation_recovery_v2.md", "phase11_fixed_v23_annotation_citations_v3.md"):
            self.copy(self.repo / "docs" / name, "provenance/protocol_text/" + name + ".txt")
        for name in ("phase11_japanese_source_selection.json", "clapnq_source_manifest.json", "phase11_japanese_token_corpus_manifest.json",
                     "phase11_japanese_reference_projection_v2.json", "phase11_bilingual_calibration_selection_v1.json"):
            self.copy(self.repo / "data/manifests" / name, "provenance/dataset_records/" + name)
        for name in ("pipeline.py", "review.py", "citations.py", "figures.py", "common.py", "gpu_guard.py", "service.py"):
            self.copy(Path(self.config["frozen_scripts"]) / name, "provenance/analysis_code/" + name + ".txt")
        for cohort in ("main", "cal"):
            for name in ("collection_completed.json", "failure_inventory.json", "startup_recovery/ledger.json", "external_interruptions/ledger.json"):
                path = self.runs[cohort] / name
                if path.exists():
                    self.copy(path, f"provenance/{cohort}/{name}")
        for name in ("request.started.json", "reexecution.json", "snapshot_manifest.json"):
            path = self.runs["main"] / "external_interruptions/monitor-cancellation-v1" / name
            self.copy(path, "provenance/main/external_interruptions/" + name)
        bibliography_source = HERE.parents[1] / "manuscript/draft_content.json"
        self.source(bibliography_source, "references_field_only_no_manuscript_change")
        save(self.out / "provenance/reference_bibliography.json", read(bibliography_source)["references"])
        for job in sorted((self.state / "jobs").glob("*")):
            if not job.name.startswith(("main-", "cal-")):
                continue
            for path in sorted(job.glob("attempt-*/*")):
                if path.name in {"provenance.json", "prompt.json", "schema.json", "invocation.json", "validation_error.json", "format_repair.json", "citation_binding.json",
                                 "input.json", "output.json", "stdin.json", "canonical_output.json"}:
                    self.copy(path, "provenance/annotation_jobs/" + path.relative_to(self.state / "jobs").as_posix())
        for source in sorted((self.repo / "reports/fixed_v23_order_study_v1").iterdir()):
            if source.is_file():
                self.copy(source, "published_results/" + source.name)
        self.copy(HERE.parents[1] / "notes/lab_pc_git_materials_prompt.md", "provenance/extraction_instructions.md.txt")
        self.copy(self.repo / "papers/iciae2027/references/source_review.md" if (self.repo / "papers/iciae2027/references/source_review.md").exists()
                  else HERE.parents[1] / "references/source_review.md", "provenance/reference_review.md.txt")

    def selected_sources(self):
        assets = read(self.fixed / "configs/phase11_bilingual_assets_v2.json")
        qa_by = {}
        for language in ("en", "ja"):
            for cohort in ("main", "cal"):
                split = "development" if cohort == "main" or language == "en" else "calibration"
                spec = assets["datasets"][language]["qa"][split]
                source = self.fixed / spec["path"]
                require(sha(source) == spec["sha256"], "QA asset changed")
                self.source(source, "selected_rows_only_no_other_QA_exported")
                manifest = read(self.runs[cohort] / language / "manifest.json")
                require(manifest["qa_sha256"] == spec["sha256"], "Manifest QA source differs")
                selected = {r["record_id"] for r in manifest["selection"]}
                rows = {}
                with source.open(encoding="utf-8") as stream:
                    for line in stream:
                        row = json.loads(line)
                        if row["record_id"] in selected:
                            rows[row["record_id"]] = row
                require(set(rows) == selected, "Selected QA unavailable")
                qa_by[cohort, language] = (split, rows)
        return assets, qa_by

    def extract_qa(self, cohort, language, split, qa):
        run = self.runs[cohort] / language
        manifest, report = read(run / "manifest.json"), read(run / "report.private.json")
        analysis = read(self.state / cohort / "analysis.private.json")
        packet = read(run / "quality/packet.json")
        mapping = read(run / "quality/mapping.private.json")
        labels = {a["annotation_id"]: a for a in read(run / "quality/annotations.json")["annotations"]}
        candidates = {x["annotation_id"]: x for x in packet["cases"]}
        stage_to_candidate = {(slot["record_id"], slot["stage"]): key for key, slots in mapping["assignments"].items() for slot in slots}
        records = {r["trace"]["record_id"]: r for r in report["records"]}
        qstats = {x["record_id"]: x for x in analysis["statistics"]["qa"] if x["language"] == language}
        routes = analysis["quality_routes"][language]["routes"]
        by_route = {(r["record_id"], r["route"]): r for r in routes}
        baselines = {read(p)["record_id"]: p for p in (run / "baseline").glob("*/record.json")}
        failures = {r["record_id"]: r for r in report["failures"]}
        policy_names = ["no_repair", "always_rewrite", "original", "reversed", "shuffle_1", "shuffle_2", "shuffle_3", "repeat_2", "repeat_3", "repeat_4", "repeat_5"]
        for selection in manifest["selection"]:
            rid = selection["record_id"]
            key = f"{cohort}_{language}_{digest(rid)[:24]}"
            row = records.get(rid)
            baseline = read(baselines[rid])
            baseline_copy = self.copy(baselines[rid], "provenance/baselines/" + key + ".json")
            summary = qstats[rid]
            quality = {}
            for stage in ("initial", "rewritten"):
                cid = stage_to_candidate.get((rid, stage))
                label = labels[cid] if cid else None
                quality[stage] = {"annotation_id": cid, "status": label["label"] if label else "candidate_unavailable",
                    "y": {"reliable": 1, "unreliable": 0, "indeterminate": None}.get(label["label"]) if label else None,
                    "annotation": label}
            documents = row["trace"]["documents"] if row else baseline.get("used_context", [])
            if documents and "passage_id" not in documents[0]:
                raise ValueError("Unknown used-context representation")
            rewrite = row["rewrite"] if row else None
            payload = {"qa_key": key, "cohort": cohort, "language": language, "analysis_role": cohort,
                "source_qa_split": split, "record_id": rid, "document_group_id": selection["document_group_id"],
                "qa_source": qa[rid], "source_selection": selection, "question": qa[rid]["question"],
                "used_documents": documents,
                "gold_documents": candidates[quality["initial"]["annotation_id"]]["gold_documents"] if quality["initial"]["annotation_id"] else [],
                "A": {"status": baseline["status"], "answer": baseline.get("answer"), "answer_sha256": digest(baseline["answer"]) if baseline.get("answer") is not None else None,
                    "quality": quality["initial"], "source": self.source(baselines[rid], "initial_answer"), "copy": baseline_copy},
                "B": {"status": rewrite["status"] if rewrite else "not_attempted_initial_missing", "answer": rewrite.get("answer") if rewrite else None,
                    "answer_sha256": digest(rewrite["answer"]) if rewrite and rewrite.get("answer") is not None else None,
                    "quality": quality["rewritten"]},
                "fixed_claims": row["evaluation"]["claims"] if row else [],
                "extraction_audit": row["tasks"]["extraction"].get("unit_audit") if row else None,
                "trial_plan": row["evaluation"]["plan"] if row else None,
                "statistical_comparison": summary, "failure": failures.get(rid),
                "report_source": self.source(run / "report.private.json", "selected_record"),
                "attribution_note": "See references_and_attributions.md and per-document source_metadata; Reference/Gold is offline evaluation material, not generation context."}
            self.qa_inputs.append(payload)
            save(self.out / "inputs" / (key + ".json"), payload)
            self.qa_rows.append({"qa_key": key, "cohort": cohort, "language": language, "source_qa_split": split,
                "record_id": rid, "document_group_id": selection["document_group_id"], "initial_status": baseline["status"],
                "rewrite_status": payload["B"]["status"], "comparable": summary["comparable"],
                "comparison_reason": summary["reason"], "fixed_claim_count": len(payload["fixed_claims"]),
                "order_rate": summary.get("order", {}).get("rate"), "repeat_rate": summary.get("repeat", {}).get("rate"),
                "increment": summary["increment"], "A_quality": quality["initial"]["status"], "A_y": quality["initial"]["y"],
                "B_quality": quality["rewritten"]["status"], "B_y": quality["rewritten"]["y"],
                "order_varies": summary.get("order", {}).get("disagreeing_pairs", 0) > 0,
                "repeat_varies": summary.get("repeat", {}).get("disagreeing_pairs", 0) > 0,
                "input_path": "inputs/" + key + ".json"})
            if row:
                for trial in row["evaluation"]["trials"]:
                    task = row["tasks"]["judges"].get(trial["trial_id"], {})
                    cost_keys = ("completion_attempted", "completion_attempts_recorded", "input_tokens", "output_tokens", "elapsed_seconds", "generation_seconds", "cost_incomplete")
                    self.trials.append({"qa_key": key, "cohort": cohort, "language": language, "record_id": rid,
                        **trial, "in_order_group": trial["trial_id"] in row["evaluation"]["order_group"],
                        "in_repeat_group": trial["trial_id"] in row["evaluation"]["repeat_group"],
                        "fixed_claims": row["evaluation"]["claims"], "verdicts": (task.get("parsed") or {}).get("verdicts", []),
                        "judge_task_present": bool(task),
                        "cost": {k: task.get(k) for k in cost_keys}, "native_subtask_costs": task.get("subtask_costs", []),
                        "task_result_sha256": task.get("result_sha256"), "shared_original_not_two_calls": trial["trial_id"] == "original"})
            aliases = row["evaluation"]["plan"].get("duplicate_order_aliases", {}) if row else {}
            for name in policy_names:
                route = by_route.get((rid, name))
                state = "observed" if route else "omitted_duplicate_order_alias" if name in aliases else "initial_unavailable"
                require(route is not None or name in aliases or row is None, "Unexplained absent policy")
                value = {"qa_key": key, "cohort": cohort, "language": language, "record_id": rid, "route": name,
                    "policy_state": state, "alias_of": aliases.get(name),
                    **{k: route.get(k) if route else None for k in ("selected_stage", "selected_answer_sha256", "rewrite_requested", "fallback", "quality_status", "quality_y", "quality_transition", "missed_improvement", "harmful_rewrite")},
                    **{k: route["operational_cost"].get(k) if route else None for k in ("completion_attempts", "recorded_completion_attempts", "unknown_outcome_steps", "input_tokens", "output_tokens", "summed_step_seconds", "incomplete")}}
                self.policies.append(value)

    def document_sources(self, assets):
        wanted = {lang: set() for lang in ("en", "ja")}
        for q in self.qa_inputs:
            wanted[q["language"]].update(d["passage_id"] for d in q["used_documents"] + q["gold_documents"])
            wanted[q["language"]].update(q["qa_source"]["gold_passage_ids"])
        metadata, bodies = {}, {}
        for language in ("en", "ja"):
            spec = assets["datasets"][language]["corpus"]
            path = self.fixed / spec["path"]
            require(sha(path) == spec["sha256"], "Corpus changed")
            binding = self.source(path, "selected_passage_metadata_only")
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    d = json.loads(line)
                    if d["passage_id"] not in wanted[language]:
                        continue
                    body = d.pop("text")
                    require(d["text_sha256"] == hashlib.sha256(body.encode()).hexdigest(), "Passage text checksum differs")
                    if language == "en":
                        d["source_url"] = "https://en.wikipedia.org/wiki/" + quote(d["title"].replace(" ", "_"), safe="")
                        d["source_url_precision"] = "title-based attribution URL; original Wikipedia revision not recorded by the CLAPNQ passage asset"
                        d["license"] = "CC-BY-SA-3.0 (Natural Questions lineage); dataset annotations Apache-2.0"
                    else:
                        d["license"] = "CC-BY-SA-4.0; Wikipedia contributors; see oldid and page history"
                    d["contributors_history_url"] = d["source_url"] + ("&action=history" if "?" in d["source_url"] else "?action=history")
                    d["transformation"] = "Existing contiguous character-span passage; no new text normalization"
                    d["corpus_source"] = binding
                    metadata[language, d["passage_id"]] = d
                    bodies[language, d["passage_id"]] = body
        require(all((lang, pid) in metadata for lang, ids in wanted.items() for pid in ids), "Missing selected passage provenance")
        for q in self.qa_inputs:
            for d in q["used_documents"] + q["gold_documents"]:
                source = metadata[q["language"], d["passage_id"]]
                d["source_metadata"] = source
                body = bodies[q["language"], d["passage_id"]]
                start = body.find(d["text"])
                require(start >= 0, "Actual context is not a contiguous corpus substring")
                d["actual_text_sha256"] = hashlib.sha256(d["text"].encode()).hexdigest()
                d["corpus_character_span"] = {"start": start, "end": start + len(d["text"])}
            local_ids = {d["passage_id"] for d in q["used_documents"] + q["gold_documents"]} | set(q["qa_source"]["gold_passage_ids"])
            q["corpus_documents"] = [{"passage_id": pid, "text": bodies[q["language"], pid],
                "source_metadata": metadata[q["language"], pid]} for pid in sorted(local_ids)]
            q["gold_passage_source_metadata"] = {pid: metadata[q["language"], pid] for pid in q["qa_source"]["gold_passage_ids"]}
            q["gold_corpus_documents"] = [{"passage_id": pid, "text": bodies[q["language"], pid],
                "source_metadata": metadata[q["language"], pid]} for pid in q["qa_source"]["gold_passage_ids"]]
            save(self.out / "inputs" / (q["qa_key"] + ".json"), q)
        save(self.out / "provenance/document_attributions.json", {f"{lang}:{pid}": v for (lang, pid), v in metadata.items()})

    def finish(self):
        self.native_metadata()
        table(self.out / "qa_summary.csv", self.qa_rows)
        jsonl(self.out / "trials.jsonl", self.trials)
        table(self.out / "policy_outcomes.csv", self.policies)
        self.cases()
        self.licenses()
        self.documentation()
        for name, expected in self.before.items():
            require(sha(name) == expected, "Original scientific file changed during extraction")
        for name, expected in self.sources.items():
            require(sha(self.repo / name) == expected["sha256"], "Extraction input changed")
        save(self.out / "source_manifest.json", {"version": VERSION, "exported_at_utc": datetime.now(UTC).isoformat(),
            "source_repository": "https://github.com/hinattyamann/rag_research.git",
            "source_root_head": subprocess.check_output(["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True).strip(),
            "writing_branch_base": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "frozen_inference_commit": subprocess.check_output(["git", "-C", str(self.fixed), "rev-parse", "HEAD"], text=True).strip(),
            "source_files": self.sources, "copies": self.copies,
            "qa_correspondence": [{k: q[k] for k in ("qa_key", "cohort", "language", "record_id", "document_group_id")} for q in self.qa_inputs],
            "qa_source_row_sha256": {q["qa_key"]: digest(q["qa_source"]) for q in self.qa_inputs},
            "scientific_files_rechecked_unchanged": len(self.before), "new_inference_calls": 0, "new_annotation_calls": 0,
            "transformations": ["Selected 80 QA only from registered source splits", "Exact provenance and published-result copies", "JSON/CSV projection of existing sealed records; no outcome imputation", "Source URLs absent in English asset are explicitly title-derived; no exact oldid invented"],
            "omissions": ["Model weights, corpus/index and unrelated/evaluation QA", "Authentication files and CLI event logs", "Unreceived externally cancelled response/cost", "Exact remote annotation serving model identifier not exposed in retained provenance", "Human author identity and full-paper literature review are separate author work"]})
        artifact_manifest(self.out)

    def native_metadata(self):
        """Keep cost evidence, not the thousands of original native response files."""
        rows = []
        for cohort, run in self.runs.items():
            for language in ("en", "ja"):
                folder = run / language
                paths = [*(folder / "baseline").glob("*/record.json"), *(folder / "internal").rglob("*.json")]
                for path in sorted(paths):
                    value = read(path)
                    baseline = path.name == "record.json" and path.is_relative_to(folder / "baseline")
                    if not baseline and value.get("task") not in {"extract_claims", "read_sources", "verify_claims", "rewrite_answer"}:
                        continue
                    if value.get("execution_mode") in {"source-reading-v1", "claimwise-v1"} or not value.get("completion_attempted"):
                        continue
                    require(value["status"] != "started", "Unfinished native call")
                    rows.append({"cohort": cohort, "language": language, "source": self.source(path, "numeric_native_cost_metadata_only"),
                        "run_relative_path": path.relative_to(folder).as_posix(),
                        **{k: value.get(k) for k in ("task", "status", "error_code", "completion_attempted", "input_tokens", "output_tokens", "elapsed_seconds", "generation_seconds", "cost_incomplete", "result_sha256")}})
        jsonl(self.out / "analysis/native_calls.jsonl", rows)
        old = read(self.runs["main"] / "external_interruptions/monitor-cancellation-v1/request.started.json")
        save(self.out / "analysis/external_attempts.json", [{"cohort": "main", "language": "ja", "status": "archived_response_unknown",
            "input_tokens": old["input_tokens"], "output_tokens": None, "elapsed_seconds": None, "cost_incomplete": True,
            "source_copy": "provenance/main/external_interruptions/request.started.json"}])

    def cases(self):
        candidates = []
        used = set()
        rules = [("en", "different_quality"), ("ja", "different_quality"), (None, "same_quality"), (None, "refusal")]
        for language, mode in rules:
            pool = []
            for q in self.qa_inputs:
                if q["qa_key"] in used or language and q["language"] != language:
                    continue
                s = q["statistical_comparison"]
                a, b = q["A"]["quality"]["y"], q["B"]["quality"]["y"]
                varied = s["comparable"] and s["order"]["disagreeing_pairs"] > 0
                eligible = (varied and a is not None and b is not None and a != b if mode == "different_quality" else
                    varied and a is not None and a == b if mode == "same_quality" else
                    q["A"]["status"] == "ok" and not q["fixed_claims"])
                if eligible:
                    pool.append(q)
            if not pool:
                continue
            q = sorted(pool, key=lambda v: (v["cohort"], v["language"], v["record_id"]))[0]
            used.add(q["qa_key"])
            index = len(candidates) + 1
            case = {"case_id": f"case_{index:02d}", "qa_key": q["qa_key"], "record_id": q["record_id"],
                "cohort": q["cohort"], "language": q["language"], "selection_rule": f"First lexicographic unused {language or 'any language'} QA satisfying {mode}",
                "post_outcome_explanatory_selection": True, "mode": mode,
                "input_path": "inputs/" + q["qa_key"] + ".json",
                "trials": [t for t in self.trials if t["qa_key"] == q["qa_key"]],
                "policy_outcomes": [r for r in self.policies if r["qa_key"] == q["qa_key"]]}
            case["original_file_copies"] = []
            folder = self.runs[q["cohort"]] / q["language"] / "internal" / digest(q["record_id"])[:24]
            for name in ("trace.json", "summary.json", "rewrite.json"):
                require((folder / name).is_file(), "Case source file missing: " + str(folder / name))
                case["original_file_copies"].append(self.copy(folder / name, f"provenance/cases/{case['case_id']}/{name}"))
            for task in sorted(folder.glob("*.claims/*.json")):
                case["original_file_copies"].append(self.copy(task, f"provenance/cases/{case['case_id']}/" + task.relative_to(folder).as_posix()))
            candidates.append(case)
            save(self.out / "cases" / (case["case_id"] + ".json"), case)
            lines = [f"# {case['case_id']} — {q['cohort']}/{q['language']}", "", f"QA: `{q['record_id']}`", "",
                f"選定: {case['selection_rule']}。結果閲覧後の説明例であり、頻度の推定に使わない。", "",
                f"[全文・Referenceと実使用根拠・A/B・来歴](../inputs/{q['qa_key']}.json)", "",
                "## 質問", "", q["question"], "", "## 初回回答 A", "", q["A"]["answer"] or "生成失敗・完成回答なし", "",
                f"外部AI品質: {q['A']['quality']['status']} / Y={q['A']['quality']['y']}", "",
                "## 書換え B", "", q["B"]["answer"] or "候補欠測・完成回答なし", "",
                f"状態: {q['B']['status']} / 外部AI品質: {q['B']['quality']['status']} / Y={q['B']['quality']['y']}", "",
                "## 順序別の対応", "", "| Trial | 根拠ID列 | F | 判断 | Action |", "|---|---|---|---|---|"]
            lines += [f"| {t['trial_id']} | {', '.join(t['document_ids'])} | {t['score']} | {t['decision']} | {t['action']} |" for t in case["trials"]]
            lines += ["", "Fは固定文の支持割合であり、回答全体の正答率ではない。Label・根拠引用・経路費用は同名JSONとリンク先へ保存。", "",
                "## 根拠の表示用抜粋", "", "全文とは別の機械的な先頭抜粋。意味の説明に必要な範囲は元の全文で確認する。"]
            for d in q["used_documents"]:
                lines += ["", f"### {d['passage_id']} — {d['title']}", "",
                    f"出典: {d['source_metadata']['source_url']} / 範囲0:{min(240, len(d['text']))}文字", "", "```text", d["text"][:240], "```"]
            (self.out / "cases" / (case["case_id"] + ".md")).write_text("\n".join(lines) + "\n", encoding="utf-8")
        require(len(candidates) >= 2 and {c["language"] for c in candidates} == {"en", "ja"}, "Insufficient real explanatory examples")
        save(self.out / "cases/index.json", {"selection": "post-outcome deterministic explanatory selection, not a representative sample", "cases": candidates})

    def licenses(self):
        for source, target in [
            (self.repo / "data/raw/clapnq/c508d78d8c5c2eecbf172fcf5f789004206e11fb/LICENSE", "licenses/CLAPNQ-Apache-2.0.txt"),
            (self.repo / "data/models/Qwen2.5-3B-Instruct-GGUF/7dabda4d13d513e3e842b20f0d435c732f172cbe/LICENSE", "licenses/Qwen2.5-3B-model-license.txt")]:
            self.copy(source, target)
        card = self.repo / "data/runs/dataset_screening/phase11-ja-source-v1/huggingface--baobab-trees--wikipedia-human-retrieval-ja/README.md"
        text = card.read_text(encoding="utf-8")
        prefix = text.split('Example ("answered" data ID=1):')[0]
        self.source(card, "dataset_card_preface_without_unselected_example")
        (self.out / "licenses/Japanese-dataset-card-preface.txt").write_text(prefix, encoding="utf-8")
        save(self.out / "licenses/source_notices.json", {"checked_at_utc": datetime.now(UTC).isoformat(),
            "clapnq": {"revision": "c508d78d8c5c2eecbf172fcf5f789004206e11fb", "dataset_license": "Apache-2.0",
                "upstream_content_license": "CC-BY-SA-3.0", "source": "https://github.com/primeqa/clapnq", "upstream": "https://ai.google.com/research/NaturalQuestions/download"},
            "japanese": {"dataset": "baobab-trees/wikipedia-human-retrieval-ja", "revision": "02e85c83a64f345aee62fba3a35af99c075a331f", "annotation_license": "Apache-2.0", "content_license": "CC-BY-SA-4.0", "contributors": ["Yusuke Oda", "Baobab, Inc.", "Wikipedia contributors"]},
            "license_urls": ["https://creativecommons.org/licenses/by-sa/3.0/legalcode", "https://creativecommons.org/licenses/by-sa/4.0/legalcode", "https://www.apache.org/licenses/LICENSE-2.0"],
            "wikimedia_reuse_terms": "https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use/en#7._Licensing_of_Content",
            "changes": "Existing corpus passage extraction/reference projection retained; selected-row JSON formatting and analysis-derived tables added. Article URLs/oldid/history attribution accompany passages. No claim that dataset annotation license replaces source-text rights.",
            "share_alike_notice": "Quoted Wikipedia-derived passages and adapted text retain the indicated CC BY-SA license and attribution; this does not relicense model weights or unrelated third-party material."})

    def documentation(self):
        # This function is extended below with the human-readable guide texts.
        write_docs(self)


def write_docs(export):
    documents = {
        "README.md": """# 固定v23 Main/Calの検証済み執筆資料 v1

対象は既存Main/Cal×日英各20問、計80選定のみ。新規推論0・再採点0。元Run/GPU/モデル/Index/認証/ネット接続なしで、ここにある資料から本文・図表・実例を追跡できる。

## ノートPCで最初に実行

Repository Rootから `uv run --no-project python -I papers/iciae2027/materials/fixed_v23_v1/verify_materials.py --audit-open` を実行する。Python標準ライブラリのみ使用する。資料フォルダ単体を任意の場所へ移した場合も `uv run --no-project python -I verify_materials.py --audit-open` で動く。成功時のJSONに80 QA、全4区分、全予定Trial、採点対応、方策行、全Hashと集計の検証件数が出る。認証・モデル取得・推論は行わない。

## 索引と章への対応

| 資料 | 使う章/用途 |
|---|---|
| [実験条件](experiment_conditions.md) | 方法・実験条件。実設定本文はprovenance/frozen_files/ |
| [結果の読み方](results_explanation.md) | 結果・考察。既存表との対応と列名の注意 |
| [限界/事後変更](limitations_and_deviations.md) | 条件・考察・限界 |
| [採点来歴](annotation_provenance.md) | AI採点・遮蔽・実モデルIDの取得範囲 |
| [出典/利用条件](references_and_attributions.md) | 文献・Dataset・モデル・原文の帰属 |
| [80問の要約](qa_summary.csv) | 全選定/比較可能/対象外、A/B品質、O/R/D |
| [予定Trial](trials.jsonl) | 実提示順序、F/判定/Action、固定文Label/根拠/費用 |
| [全方策](policy_outcomes.csv) | 80×11枠。未実施・重複省略を明示、nullを0へ補完しない |
| [質問別全文](inputs/) | 質問/Reference・実使用根拠・A/B・固定文・日本語参照来歴 |
| [確定採点](annotations/) | 匿名Packet・対応表・品質/Expected。共用候補を保存 |
| [具体例](cases/) | 結果閲覧後に規則で選んだ2～4例。JSONでF/Y/費用を追跡 |
| [詳細解析](analysis/) | 元詳細解析の同一バイト複製と数値費用台帳 |
| [公開成果](published_results/) | 元図表/CSV/集計/Manifestと同一バイト |
| [来歴](provenance/) | 元Manifest/Seal/Report、設定・Prompt・採点Job来歴 |
| [元ファイル対応](source_manifest.json) | 元Repository/Commit・各入力の位置/Hash、変換、80問対応 |
| [資料Hash一覧](artifact_manifest.json) | 自己参照以外の全成果・Byte数・SHA-256 |

qa_keyは集合/言語/元IDのHashから作る資料内のキー。qa_summary.csvのinput_pathで質問別JSONへ進み、record_idとtrial_idでtrials.jsonl、routeでpolicy_outcomes.csvを結合する。匿名IDはannotations内のmapping.private.jsonでQA/initial・rewrittenへ結合する。同じ文章の採点共用を独立候補へ水増ししない。

## 抽出と再現

研究室での抽出コマンドは `uv run python build_materials.py --source-repo /path/to/lab/repo --output /path/to/new/materials`。この抽出だけは元Runが必要で、完成版への上書きを拒否する。通常のノート検証ではverify_materials.pyだけを使う。build_materials.py/test_verify_materials.pyも同梱し、処理と反証検証を追跡できる。

元の4つのreport.private.jsonは必要な確定資料としてByte不変で複製し、巨大なServer/Eventログ・全Run/Corpus・モデルを複製していない。provenance/protocol_textとanalysis_codeの*.txtは原文の証拠コピーで、元文書内のリンク/絶対パスは歴史的記録。検証器はそのパスを開かない。資料内の案内リンクはこのフォルダ内で完結する。

## 完了範囲と残件

本資料は抽出時の元Hash・封印・解析Sourceを検証したもの。Git再取得後の実検証結果と取込元Commitは、執筆Branchのnotes/materials_handoff.mdも参照する。原稿の著者情報確認、関連研究本文の精読、人手による採点妥当性確認、教員確認と提出は別工程。初回生成失敗1件と書換え失敗2件、既知の外的中断の応答/最終費用不明、未特定の採点Serving Model IDを補完していない。
""",
        "experiment_conditions.md": """# 実験条件と各集合の役割

Mainは開発集合として日英20問ずつ、Calは調整に使わない追加確認として日英20問ずつ。英語CalのQA Sourceはdevelopment、日本語Calはcalibration。入力のqa_source、source_qa_split、provenanceの元Manifestで確認できる。未使用Evaluationの本文は含めない。

初回生成はQwen/Qwen2.5-3B-Instruct-GGUF Q4_K_M、評価/共通書換えはunsloth/Qwen3.5-9B-GGUF Q6_K。固定Revision、モデルHash、Sampler・Context・CUDA全層条件はprovenanceの各manifest.jsonとfrozen_filesのモデル/Runtime/Prompt設定を正本とする。モデルWeightsは同梱しない。

初回: Context4096、出力上限512、温度0、Seed42。補助: Context12288、Batch128、Threads6、温度0.2、Seed42、Top-k20/Top-p0.95/Min-p0、Presence penalty1.5、Reasoning予約4096、出力予約6144。実験のBudgetと停止規則は元Manifest、固定Release/Recovery/Cal登録を参照する。GPU Graph OFF・FA OFF・全層Offloadの実証は元解析resource_auditへ保存されている。

検索はBM25とmultilingual-e5-smallのHybrid、候補50、RRF定数60、Top-k5。Reference/Goldと通常検索の実使用文書はinputsで別Fieldに保持する。Referenceを生成やJudgeへ注入した設計ではない。

初回Aと実使用Context・文単位を固定し、元/逆/Shuffle3候補と元順序計5反復を比較する。originalは両群で共用し、原則9論理試行。重複順列はplan.duplicate_order_aliasesで省略する。試行ごとの再検索・A再生成・文再抽出・切詰め・同順序Cache代用は行わない。

Fは支持とされた固定文の割合。F>=0.7で採用、未満で一回書換え。F=nullの判断不能と、bare-refusal時のrewrite_once Actionを区別する。Bは元順序の同じ根拠/Aから一回だけ生成し、Judge Feedback/F/Goldを渡さず全方策で共用する。B失敗時はA保持で費用を残す。

外部AI品質Yは必須要点・重大な誤りなし・実使用文書による支持の3基準。Expectedは実使用文書だけで全文固定単位を評価する。条件/F/判断/段階を匿名採点時に遮蔽し、Main・Calそれぞれの日英全品質/Expected封印後に内部結果と結合した。基準全文とPrompt/Schemaはprovenanceとannotationsに同梱した。
""",
        "results_explanation.md": """# 結果の読み方・公開表への対応

主指標はQAごとのO=順序群の全判断ペア不一致率、R=同順序反復群の同率、D=O-R。必要な全試行が有効なQAだけでDを等重み平均する。qa_summaryとinputsのstatistical_comparisonから再確認できる。文/ペア/Callは独立QAではない。

主比較はMain/en16/20・ja13/20、Cal/en16/20・ja12/20。平均増分は順に0.0875、0.04615384615384615、0.125、0.08333333333333333。95%区間は[0,0.1875]、[0,0.13846153846153844]、[0.05,0.225]、[0,0.20000000000000004]。日英差はMain -0.041346153846153845、Cal -0.04166666666666667で区間は双方0を含む。

CIは元のNumPy2.5.3・Seed42・文書Group Bootstrap10000回・linear percentileによる結果をByte不変で保持する。標準ライブラリ検証器は点推定・Group/分母とCIの元コピー一致を確認し、別RNGでCIを生成して同一実装と主張しない。

順序で判断が分かれたQAはMain/en3/16・ja1/13、Cal/en5/16・ja2/12。同順序反復は比較可能QAの全てで0。対象外23 QAはstandalone refusal/no_claims22件と初回生成失敗1件であり、順序効果0として補完しない。

品質Y=1件数は修復なし/元順序評価/常時書換えの順にMain/en9/12/14、Main/ja5/10/14、Cal/en6/9/10、Cal/ja4/6/9（各20選定）。A/Bの改善・悪化は対応のある品質遷移で確認し、不明Yはunknownのまま保持する。policy_outcomesにmissed_improvement/harmful_rewriteとQA内の選択/費用を保持した。単に判断が反転しただけで品質が変わったと解釈しない。

公開quality_and_operational_cost.csvのbaseline_missingは、実装上20-そのrouteの記録数である。shuffle_2等では重複順列の省略もここに含まれ、初回生成失敗件数そのものではない。元CSVを直さず、この資料のpolicy_state=omitted_duplicate_order_aliasとinitial_unavailableで区別する。省略Trialを新規実行したことにせず、alias_ofで元対応を残す。

collection_cost.csvは全収集の試行、policy_outcomesは単一方策を運用した場合の保存済み経路費用、annotation_cost.jsonは外部AI採点の費用で、相互加算・混同しない。保存秒の和は実測応答時間ではなく、外的取消の最終Token不明は既知分の下限。意味監査は同じ固定文×試行の反復を含み、人手正解の独立標本精度ではない。

閾値感度は事前の0.5/0.6/0.7/0.8/0.9で全て同じ元結果を再判定した補助分析。閾値を選び直していない。図表と詳細値は[published_results](published_results/)・[analysis](analysis/)を参照する。
""",
        "limitations_and_deviations.md": """# 限界と事後変更

- Main/Cal・日英は別集合。英語と日本語はDataset/領域/参照構造/検索Corpusが異なり、言語単独の因果効果を識別していない。
- 主比較は各12～16 QA。22拒否回答と初回長さ欠測1を除いた、比較可能な観測QAへの条件付き推定。区間はモデル/Seed/採点者を変えた変動を含まない。原文に本当に答えがなかったかは拒否文だけでは断定しない。
- Mainには初回/書換え長さ欠測各1、Calに書換え長さ欠測1。失敗結果/費用を保存し補充・0補完していない。書換え失敗そのものは初回評価の主比較除外条件ではない。
- Main停止規則は初回と書換えの長さ失敗後に事後変更。別の外的監視中断1要求は同一入力で一回再実行し、元要求の応答/最終費用不明は別保存した。詳細はprovenanceの元Recovery文書と解析collection_costsを参照。
- 採点CLIの資料読取エラー後に標準入力方式へ変更し、Cal途中では逐語引用不一致/根拠なし支持を防ぐ資料番号選択・原文転記へ変更した。過去の失敗/消費を保持し、成功採点を再送していない。Main/Calで採点手続が完全同一という主張はしない。
- 品質/Expectedは外部AI判定であり人手正解ではない。全てhuman_reviewed=false。履歴の完全独立や実Serving Model IDは未実証。
- 初回3Bと評価/書換え9Bではモデル/予算も異なる。常時書換えによる品質増加を、書換え操作だけの因果効果としない。
- 開発用既知v23の旧意味採用基準未達を知った上で固定した観察研究。旧Gate11/Phase12の達成へ読み替えない。
- 具体例は結果閲覧後に規則で選んだ説明例。見つからない型は作らず、例から頻度や原因を一般化しない。
""",
        "annotation_provenance.md": """# AI採点の条件と来歴

configured model=gpt-6.1-sol、reasoning effort=high、ChatGPT認証。保持されたprovenanceのexact_model_identifierはnullであり、別の実Serving Model名を推測しない。履歴の完全隔離も主張しない。研究採点のCLI予約は84で、失敗や形式修正を含む。人工輸送検証のJobは研究台帳へ混ぜていない。

provenance/annotation_jobsに各実Jobのモデル設定、測定wall、開始/終了時刻、入力/出力/標準入力Hash、利用Tokenと形式修正履歴、指示とSchemaを保存した。認証ファイル、環境変数、CLIの巨大Eventログは共有しない。実験の論理試行と採点Jobは別単位である。

各candidate/固定文はannotationsのPacket、各Label/理由/逐語引用はannotations.json、匿名IDと元QA/initial・rewrittenの対応はmapping.private.jsonで確認する。同じ候補内容に同じ注釈を共用した対応を残した。日英全品質/全文Expectedを封印してから内部Fと結合したことはprovenanceのSealで確認する。

品質採点ではReference/Goldと実使用Contextを区別し、Expectedは実使用Contextだけを渡した。遮蔽したものは順序条件/F/判断/候補段階/内部Judge理由であり、完全なモデル学習歴の独立を意味しない。

旧file読取失敗2 Job、inline_stdin_v2、inline_citations_v3を分ける。v3は候補ごとに元Passage全文の番号を選び、プログラムが元文字列を引用へ展開する。支持/矛盾の根拠必須・Slot/ID/Hash検証を追加した。成功済みLabelを再採点せず、無効Job全体を別名で再開した。元Rubricの全文・来歴・Schemaは同梱テキストとJobファイルを参照。

注釈ごとの秒はCLI Job wallの件数等配分で、純読解時間や人手時間ではない。採点者の正しさや人手一致率が実証されたと書かない。
""",
        "references_and_attributions.md": """# 出典・利用条件・帰属表示

## 原文の出典と利用条件

CLAPNQはprimeqa/clapnqの固定c508d78d8c5c2eecbf172fcf5f789004206e11fb。注釈のApache-2.0原文をlicensesへ複製し、Natural Questions由来本文のCC BY-SA 3.0を別に維持する。元取得記録はprovenance/dataset_records/clapnq_source_manifest.json。Dataset著者とWikipedia contributorsに帰属する。URL: https://github.com/primeqa/clapnq ・ https://ai.google.com/research/NaturalQuestions/download ・ https://creativecommons.org/licenses/by-sa/3.0/legalcode 。

日本語注釈はbaobab-trees/wikipedia-human-retrieval-jaの固定02e85c83a64f345aee62fba3a35af99c075a331f、カードにApache-2.0と宣言。Yusuke OdaとBaobab, Inc.へ帰属する。Wikipedia本文は注釈ライセンスと別で、CC BY-SA 4.0とWikipedia contributorsへの帰属を保持する。URL: https://huggingface.co/datasets/baobab-trees/wikipedia-human-retrieval-ja/tree/02e85c83a64f345aee62fba3a35af99c075a331f ・ https://creativecommons.org/licenses/by-sa/4.0/legalcode 。カードの例示QAは今回の選定外なのでコピーせず、前半の条件/構造説明をlicensesに保存した。

実使用/Goldの各PassageにTitle/ID/元本文SHA/Source Revision/URL/親・文字Spanを付け、provenance/document_attributions.jsonにも一意索引を保存した。日本語は保存済みoldid・Page ID・Revision日時を保持する。英語資産には元WikipediaのRevision IDが記録されていないため、Title由来の記事URLと固定CLAPNQ/元NQ Passage IDを併記し、存在しないoldidは作らない。帰属用URLは著者一覧を含む記事履歴へ戻るための参照である。

原文は既存のPassage分割/日本語脚注投影を保持し、ここでは選定行の抽出・JSON/CSV整形・表示用の先頭抜粋を行った。改変/抽出箇所・全文への対応を記録する。Wikipedia由来の原文/翻案には該当CC BY-SAと帰属・変更表示を維持する。Git/出版物で再利用する際も出典と適用ライセンスを添える。資料の著作権表示を、モデルWeightsや無関係な第三者資料へ一律適用しない。

利用条件の確認元: https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use/en#7._Licensing_of_Content 。2026-11-06に公式の再利用・帰属・変更表示条件とCC公式3.0/4.0の条件を確認した。記事別の第三者表示や参照本文の欠測/要約はqa_source.reference_evidence/reference_corpus_mappingに保持し、利用許諾や本文を捏造しない。

## モデル等

初回Qwen2.5-3B-Instructの元LICENSEはQwen Research LicenseでありApacheとは記さない。元LICENSEをlicensesへ同梱し、Weightsは配布しない。評価/書換えQwen3.5-9B Q6_KはUnslothの固定配布版で、保存ManifestのApache-2.0宣言を記録。モデル名/Revision/量子化/Hashを各manifestで照合する。Embeddingはintfloat/multilingual-e5-smallの固定614241f622f53c4eeff9890bdc4f31cfecc418b3。配布元 https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF ・ https://huggingface.co/unsloth/Qwen3.5-9B-GGUF ・ https://huggingface.co/intfloat/multilingual-e5-small 。

## 関連研究の引用候補と確認範囲

執筆Branchで既に確認した書誌/URL/確認範囲はprovenance/reference_review.md.txtをByte不変で保存した。Lewis et al. (RAG), Lost in the Middle, ConsJudge, RAGVUE, When the Judge Should Not Decide、Dataset/モデルカードが候補。既存の原稿referencesを正本にし、今回、関連論文の全本文を精読・新規性調査したとは主張しない。未確定の著者名/所属・取得不能な実モデル識別子は埋めない。論文本体と日英初稿は本作業で変更しない。
""",
    }
    for name, text in documents.items():
        (export.out / name).write_text(text, encoding="utf-8")
    for name in ("README.md", "limitations_and_deviations.md"):
        target = export.out / name
        target.write_text(target.read_text(encoding="utf-8") + '\n## 元から未取得・未特定の情報\n\n- Main日本語のwhrja:02e85c8:answered:857は引用元jawiki-page:5273510のCorpus本文を元取得段階で確保できていない。保存されたReference引用/URL・欠測状態はinputsに保持し、本文を捏造していない。実使用根拠の全文とは別の参照側の不足である。\n- 英語の元Wikipedia oldidはCLAPNQ加工資産に記録されていない。Title由来URLと固定Dataset Revision/Passage ID/本文Hashへ追跡する。\n- 採点Serving Modelの厳密な実識別子は未取得で、configured modelと来歴を保存する。\n- 人手確認・著者情報・関連研究本文の精読は本資料の完了範囲に含めない。\n\n## 保存した粒度\n\nA成功79件、B成功77件、匿名品質候補156件、外部固定文注釈460件。初回欠測1問はTrial計画未作成。残る79問の通常9条件から重複順列5条件を省き、実計画Trialは706件。これらをNative呼出し数や独立QA数へ読み替えない。方策表は80×11=880枠で、実記録864・初回欠測による未実施11・重複省略5を区別する。\n\n実使用文書のうち1件は、初回のContext PackingでCorpus Passageの先頭645文字が使われたもの。used_documentsに実際の645文字を無変更で保持し、corpus_documentsに元Passage全文、corpus_character_spanと両方のHashを保存した。順序試行では実使用本文を固定しており、Corpus全文へ置換していない。\n', encoding="utf-8")

    save(export.out / "missing_information.json", {'unavailable_reference_body': [{'cohort': 'main', 'language': 'ja', 'record_id': 'whrja:02e85c8:answered:857', 'source_article': 'jawiki-page:5273510', 'status': 'unavailable_in_original_corpus_acquisition', 'reference_annotation_retained': True}], 'unrecorded_information': ['original English Wikipedia revision IDs', 'exact remote annotation serving model identifier'], 'separate_author_work': ['human annotation review', 'author identity confirmation', 'full related-work reading', 'supervisor review', 'submission'], 'recorded_experiment_can_be_audited_offline': True})
    target = export.out / "references_and_attributions.md"
    target.write_text(target.read_text(encoding="utf-8") + '\n引用候補の著者・題名・年・会議/誌・URLの既存書誌は[reference_bibliography.json](provenance/reference_bibliography.json)、前回の確認範囲はprovenance/reference_review.md.txtを参照。今回の資料共有で文献内容を新たに認定したものではない。\n', encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path)
    parser.add_argument("--output", type=Path, default=HERE)
    parser.add_argument("--refresh-artifact-manifest", action="store_true")
    args = parser.parse_args()
    if args.refresh_artifact_manifest:
        artifact_manifest(args.output)
        return
    require(args.source_repo is not None, "--source-repo is required only for lab extraction")
    require(not (args.output / "artifact_manifest.json").exists(), "Preserve a completed version; use another version for different exports")
    if args.output.resolve() != HERE:
        args.output.mkdir(parents=True, exist_ok=True)
        for name in ("build_materials.py", "verify_materials.py", "test_verify_materials.py", ".gitattributes"):
            shutil.copyfile(HERE / name, args.output / name)
    export = Export(args.source_repo, args.output)
    export.preflight()
    export.supporting_files()
    assets, qa = export.selected_sources()
    for (cohort, language), (split, rows) in qa.items():
        export.extract_qa(cohort, language, split, rows)
    export.document_sources(assets)
    export.finish()


if __name__ == "__main__":
    main()
