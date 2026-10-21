"""Connect sealed, source-verified bilingual Development runs to preregistered statistics."""

import yaml

from rag_research.data.study_assets import load_assets, load_rows
from rag_research.experiments import bilingual_quality
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.protocol import ROOT
from rag_research.experiments.quality import cost, reconstruct
from rag_research.experiments.statistics import analyze
from rag_research.experiments.storage import read_json
from rag_research.retrieval.common import file_hash


def condition(manifest):
    config = manifest["config"]
    prompts = yaml.safe_load((ROOT / config["prompts"]).read_text())
    return {"baseline_model": manifest["baseline_model"], "auxiliary_model": manifest["auxiliary_model"],
            "baseline": manifest["baseline"], "judge": {k: config.get(k) for k in
            ("trials", "decision", "auxiliary_runtime", "sampling", "tasks", "output_constraints", "execution", "verification_mode",
             "quality_rubric_version")},
            "judge_prompts": {k: prompts.get(k) for k in ("judge_layout", "judge_checks", "judge_payload",
                             "source_reading_schema", "source_reading_auxiliary")},
            "judge_tasks": {k: prompts["tasks"][k] for k in ("verify_claims", "read_sources") if k in prompts["tasks"]}}


def analyze_runs(inputs, *, analysis_split="development", unit_inputs=None, canonical_runs=None):
    require(analysis_split in {"development", "calibration"}, "Unknown statistical analysis split")
    require(isinstance(inputs, list) and len(inputs) >= 2, "At least two sealed language inputs required")
    paths = []
    for row in inputs:
        require(set(row) == {"run", "bundle", "annotations"}, "Unexpected statistical input fields")
        run, bundle, annotations = ((ROOT / row[k]).resolve() for k in ("run", "bundle", "annotations"))
        require(bilingual_quality.analysis_split(run, root=ROOT, allow_replay=canonical_runs is not None) == analysis_split and
                bundle.is_relative_to(run) and
                bundle != run and annotations.is_relative_to(bundle), "Unexpected sealed Development input paths")
        paths.append((run, bundle, annotations))
    require(len({p[0] for p in paths}) == len(paths), "Duplicate statistical run")
    unit_frozen = {}
    if analysis_split == "calibration":
        from rag_research.experiments.bilingual_semantics import sealed_inputs

        sealed, unit_frozen = sealed_inputs(unit_inputs, analysis_split="calibration", allow_replay=canonical_runs is not None)
        require({(r[0]["run"], r[0]["quality_bundle"], r[0]["quality_annotations"]) for r in sealed} == set(paths),
                "Statistical quality and sealed unit review cohorts differ")
    # Every language/run is sealed first, before any private F or decision is accessed.
    for _, bundle, annotations in paths:
        bilingual_quality.sealed_annotations(bundle, annotations)
    sealed_hashes = {annotations: file_hash(annotations) for _, _, annotations in paths}
    records, provenance, collections, conditions = [], [], [], []
    for run, bundle, annotations in paths:
        require(all(file_hash(p) == sha for p, sha in sealed_hashes.items()), "Sealed statistical annotations changed")
        manifest, report, assigned = bilingual_quality.validated_annotations(run, bundle, annotations)
        if analysis_split == "calibration":
            from rag_research.experiments.calibration_protocol import review_contract

            review_contract(run, manifest, canonical_runs=canonical_runs)
        language = manifest["language"]
        assets = load_assets(ROOT / manifest["config"]["assets"])
        allowed = assets["datasets"][language]["qa"]
        splits = [s for s in ("development", "calibration") if allowed[s]["path"] == manifest["qa_path"]]
        source = bilingual_quality.source_split(manifest, analysis_split)
        require(len(splits) == 1 and splits[0] == source,
                "Only verified Development runs or declared Calibration source splits are supported by this adapter")
        qa, _ = load_rows(assets, language, splits[0], root=ROOT)
        by_id = {r["record_id"]: r for r in qa}
        evaluated = {r["trace"]["record_id"]: r["evaluation"] for r in report["records"]}
        selected = [r["record_id"] for r in manifest["selection"]]
        require(set(selected) <= set(by_id), "Statistical selection differs from QA source")
        records.extend({"language": language, "record_id": i, "document_group_id": by_id[i]["document_group_id"],
                        "evaluation": evaluated.get(i)} for i in selected)
        conditions.append(condition(manifest))
        baseline_paths = [run / "baseline" / digest(i)[:24] / "record.json" for i in selected]
        baseline_costs = []
        for path in baseline_paths:
            saved = read_json(path)  # Already verified against manifest/trace/failure by validated_annotations.
            baseline_costs.append({"completion_attempted": saved.get("completion_attempted", bool(saved.get("answer_generation_calls"))),
                "input_tokens": saved.get("input_tokens"), "output_tokens": saved.get("output_tokens"),
                "elapsed_seconds": (saved.get("generation_seconds") or 0) + (saved.get("context_seconds") or 0),
                "error_code": saved.get("error_code"), "cost_incomplete": saved.get("cost_incomplete", False)})
        collections.append({"language": language, "run": run.relative_to(ROOT).as_posix(),
                            "selected_qa_count": report["selected_qa_count"], "baseline_failures": report["failures"],
                            "all_selected_baseline_cost": cost(baseline_costs),
                            "quality_and_costs": reconstruct(report["records"], assigned)})
        files = [run / "manifest.json", run / "report.private.json", bundle / "packet.json",
                 bundle / "mapping.private.json", bundle / "export_manifest.json", annotations, *baseline_paths]
        provenance.append({"language": language, "run_manifest_digest": digest(manifest),
                           "qa_sha256": manifest["qa_sha256"],
                           "files_sha256": {f.relative_to(ROOT).as_posix(): file_hash(f) for f in files}})
    require(all(c == conditions[0] for c in conditions), "Bilingual statistical conditions differ")
    require(all(file_hash(p) == sha for p, sha in sealed_hashes.items()), "Sealed statistical annotations changed")
    require(all(file_hash(p) == sha for p, sha in unit_frozen.items()), "Sealed statistical unit reviews changed")
    result = analyze(records, repetitions=10000, seed=42)
    result.update(purpose=f"sealed-bilingual-{analysis_split}-statistics-not-final-evaluation",
                  analysis_split=analysis_split,
                  source_runs=provenance, all_selected_quality_costs=collections,
                  statistical_plan_sha256=file_hash(ROOT / "docs/phase11_statistical_plan.md"),
                  condition_sha256=digest(conditions[0]), research_sample_size_frozen=False)
    if analysis_split == "calibration":
        result["sealed_review_files_sha256"] = {p.relative_to(ROOT).as_posix(): sha for p, sha in unit_frozen.items()}
    return result
