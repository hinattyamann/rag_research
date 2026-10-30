"""Fixed-v23 adapters; original inference sources and legacy adoption gates stay sealed."""

import argparse
import importlib.util
import re
import signal
import sys
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from common import (
    cohort_run,
    immutable,
    load_config,
    now,
    progress,
    read,
    require,
    run_owned,
    sha,
    write,
)

CAL_VERSION = "fixed-v23-additional-calibration-v1"


def runtime(config):
    root = Path(config["checkout"])
    sys.path.insert(0, str(root / "src"))
    spec = importlib.util.spec_from_file_location("sealed_v23_recovery", root / "scripts/recover_fixed_v23_v2.py")
    recovery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recovery)
    recovery.verify_release()
    from rag_research.experiments import bilingual_quality

    original_source_split = bilingual_quality.source_split

    def source_split(manifest, split):
        if split == "calibration" and manifest["config"].get("execution_scope") == "fixed_v23_calibration_v1":
            protocol = verify_cal(config)
            language = manifest["language"]
            expected = protocol["configs"][language]
            expected = {**expected, "fixed_v23_calibration_protocol": {
                "path": str((Path(config["cal_run"]) / "protocol.json").relative_to(root)),
                "sha256": sha(Path(config["cal_run"]) / "protocol.json")}}
            require(manifest["config"] == expected and
                    [r["record_id"] for r in manifest["selection"]] == expected["data"]["record_ids"],
                    "Fixed-v23 Calibration configuration/selection changed")
            return protocol["source_splits"][language]
        return original_source_split(manifest, split)

    bilingual_quality.source_split = source_split
    return recovery


def verify_seal(run):
    seal = read(run / "all_annotations.seal.json")
    require(seal["all_both_languages_sealed"] is True and seal["human_reviewed"] is False,
            "Both languages' quality and Expected must be sealed first")
    require(all(sha(run / name) == value for name, value in seal["files"].items()), "Sealed annotation changed")
    return seal


def verify_cal(config):
    run = Path(config["cal_run"])
    protocol = read(run / "protocol.json")
    require(config["cal_launch_authorized"] is True and protocol["version"] == CAL_VERSION and protocol["phase12_allowed"] is False
            and protocol["automatic_retries"] == 0 and protocol["maximum_calls_per_language"] == 1660
            and protocol["minimum_comparable_main_per_language"] == 10
            and protocol["main_gate_passed"] is True
            and protocol["session_wall_seconds"] == 43200 and protocol["total_wall_seconds"] == 259200
            and protocol["source_splits"] == {"en": "development", "ja": "calibration"}
            and protocol["purpose"] == "additional_confirmation_not_tuning"
            and protocol["original_release_sha256"] == sha(Path(config["checkout"]) / "fixed-v23-release.json"),
            "Fixed-v23 Calibration protocol changed")
    for name, expected in protocol["inputs"].items():
        require(sha(name) == expected, "Calibration prerequisite changed: " + name)
    return protocol


def source_hashes(run):
    files = {}
    for language in ("en", "ja"):
        for path in (run / language).rglob("*"):
            if path.is_file() and path.name not in {".run.lock", "progress.json"}:
                require(path.resolve().is_relative_to(run.resolve()), "Source evidence escapes its registered run")
                files[str(path.relative_to(run))] = sha(path)
    return files


def resource_audit(run, manifest, recovery, *, cohort):
    """Check actual CUDA headers; explicitly retain missing reports from known Main failures."""
    checked = []
    for stage, declared, context in (
            ("baseline", manifest["baseline"], manifest["baseline"]["generation"]["context_tokens"]),
            ("internal", manifest["config"], manifest["config"]["auxiliary_runtime"]["context_tokens"])):
        folder = run / stage
        logs = sorted(folder.glob("server-*.log"))
        sessions = {p.name.replace("session-", "server-").replace(".json", ".log"): p
                    for p in folder.glob("session-*.json")}
        require(logs and set(sessions) <= {p.name for p in logs}, "Missing CUDA resource log")
        expected = recovery.runner.execution_identity(declared)
        snapshot = recovery.reserve(run, 1660)
        allowed_unpaired = sum(name.startswith(stage + "/") for name in snapshot["error_paths"]) if cohort == "main" else 0
        require(len(logs) - len(sessions) <= allowed_unpaired, "Unexplained missing session report")
        for path in logs:
            text = path.read_text(encoding="utf-8", errors="replace")
            layers = [tuple(map(int, pair)) for pair in re.findall(r"offloaded (\d+)/(\d+) layers to GPU", text)]
            contexts = [int(value) for value in re.findall(r"llama_context:\s+n_ctx\s*=\s*(\d+)", text)]
            require(layers and all(a == b and a > 0 for a, b in layers) and contexts and
                    all(value == context for value in contexts) and re.search(r"using device CUDA\d+|CUDA\d+.*model buffer", text),
                    "Actual CUDA/context proof differs from the fixed full-offload condition")
            saved = read(sessions[path.name]) if path.name in sessions else None
            if saved:
                require(all(saved.get(k) == v for k, v in expected.items()) and saved.get("server_context_tokens") == context
                        and saved.get("full_gpu_offload") is True and saved.get("actual_gpu_offload") is True
                        and (saved.get("offloaded_layers"), saved.get("total_layers")) == layers[-1],
                        "Saved session differs from actual fixed runtime")
            checked.append({"stage": stage, "log_sha256": sha(path), "context_tokens": context,
                "offloaded_layers": layers[-1][0], "total_layers": layers[-1][1],
                "session_report_present": saved is not None,
                "missing_report_reason": None if saved else "known Main length failure interrupted report publication; log retained"})
    return checked


def annotation_results(run, language):
    from rag_research.experiments.bilingual_semantics import (
        make_unit_packet,
        validate_unit_annotations,
    )
    from rag_research.experiments.quality import validate_annotations

    bundle = run / language / "quality"
    packet, units = read(bundle / "packet.json"), read(bundle / "units/packet.json")
    require(make_unit_packet(packet, language) == units, "Expected packet differs from actual anonymous candidates")
    quality = validate_annotations(packet, read(bundle / "annotations.json"))
    labels = validate_unit_annotations(units, read(bundle / "units/annotations.json"), sealed=True)
    require(all(a["label"] != "pending" for a in quality.values()), "Quality still pending")
    return quality, units, labels


def analyze_cohort(config, cohort):
    recovery = runtime(config)
    from rag_research.data.study_assets import load_assets, load_rows
    from rag_research.experiments.bilingual_quality import validated_annotations
    from rag_research.experiments.bilingual_semantics import semantic_counts
    from rag_research.experiments.bilingual_statistics import condition
    from rag_research.experiments.decisions import decide_with_refusal
    from rag_research.experiments.quality import reconstruct
    from rag_research.experiments.statistics import analyze, qa_increment

    run = cohort_run(config, cohort)
    seal = verify_seal(run)
    # Validate ALL external labels before any private mapping or score is read.
    reviewed = {language: annotation_results(run, language) for language in ("en", "ja")}
    before = source_hashes(run)
    records, semantics, routes, costs, conditions, ranges, sensitivity = [], {}, {}, {}, [], [], []
    resources = {}
    for language in ("en", "ja"):
        bundle = run / language / "quality"
        manifest, report, assigned = validated_annotations(run / language, bundle, bundle / "annotations.json")
        resources[language] = resource_audit(run / language, manifest, recovery, cohort=cohort)
        _, unit_packet, unit_labels = reviewed[language]
        mapping = read(bundle / "mapping.private.json")
        expected = {(slot["record_id"], claim["claim_id"]):
            unit_labels[case["annotation_id"], claim["claim_id"]]["label"]
            for case in unit_packet["cases"] for slot in mapping["assignments"][case["annotation_id"]]
            if slot["stage"] == "initial" for claim in case["unit_audit"]["claims"]}
        fixed = {slot["record_id"]: case["unit_audit"]["claims"] for case in unit_packet["cases"]
            for slot in mapping["assignments"][case["annotation_id"]] if slot["stage"] == "initial"}
        require(all(row["evaluation"]["claims"] == fixed[row["trace"]["record_id"]] for row in report["records"]),
                "Annotated fixed units differ from internal evaluation units")
        assets = load_assets(Path(config["checkout"]) / manifest["config"]["assets"])
        source = "development" if cohort == "main" or language == "en" else "calibration"
        qa, qa_path = load_rows(assets, language, source)
        require(sha(qa_path) == manifest["qa_sha256"], "Analysis QA provenance differs")
        groups = {r["record_id"]: r["document_group_id"] for r in qa}
        evaluations = {r["trace"]["record_id"]: r["evaluation"] for r in report["records"]}
        require(all(r["document_group_id"] == groups[r["record_id"]] for r in manifest["selection"]),
                "Selection group provenance differs")
        records.extend({"language": language, "record_id": r["record_id"],
            "document_group_id": groups[r["record_id"]], "evaluation": evaluations.get(r["record_id"])}
            for r in manifest["selection"])
        semantics[language] = semantic_counts(report["records"], expected, binary=True, groups=groups)
        conditions.append(condition(manifest))
        routes[language] = reconstruct(report["records"], assigned)
        snapshot = recovery.reserve(run / language, 1660)
        leaves = [read(run / language / leaf["path"]) for leaf in snapshot["raw_calls"]]
        costs[language] = {"selected_qa": 20, "native_attempts": len(leaves),
            "failed_native_records": len(snapshot["error_paths"]), "unknown": len(snapshot["unknown_or_interrupted_paths"]),
            "input_tokens": sum(v.get("input_tokens") or 0 for v in leaves),
            "output_tokens": sum(v.get("output_tokens") or 0 for v in leaves),
            "summed_observed_task_seconds": sum(v.get("elapsed_seconds") or v.get("generation_seconds") or 0 for v in leaves),
            "baseline_missing_qa": len(report["failures"]),
            "rewrite_missing_qa": sum(r["rewrite"]["status"] != "ok" for r in report["records"]),
            "time_scope": "sum of observed task steps; excludes startup/retrieval/annotation and is not route wall time"}
        for row in report["records"]:
            evaluation = row["evaluation"]
            scores = [t["score"] for t in evaluation["trials"] if t["status"] == "ok"]
            ranges.append({"language": language, "record_id": row["trace"]["record_id"],
                "F_range": max(scores) - min(scores) if scores else None})
        for threshold in manifest["config"]["decision"]["sensitivity_thresholds"]:
            increments = []
            for row in report["records"]:
                evaluation = deepcopy(row["evaluation"])
                evaluation["threshold"] = threshold
                for trial in evaluation["trials"]:
                    trial.update(decide_with_refusal(trial["score"], threshold, row["tasks"]["extraction"],
                        policy=manifest["config"]["decision"].get("bare_refusal_policy", "keep_initial")))
                value = qa_increment(evaluation)
                if value["comparable"]:
                    increments.append(value["increment"])
            sensitivity.append({"language": language, "threshold": threshold,
                "comparable_qa": len(increments), "mean_increment": sum(increments) / len(increments) if increments else None})
    require(conditions[0] == conditions[1], "Scientific conditions differ across languages")
    statistics = analyze(records, repetitions=10000, seed=42)
    require(all(statistics["languages"][lang]["comparable_qa_count"] == semantics[lang]["complete_comparable_qa"]
                for lang in ("en", "ja")), "Statistical/semantic comparable denominators differ")
    gate = all(statistics["languages"][lang]["comparable_qa_count"] >= 10 and
               semantics[lang]["invalid_trial_conditions"] == 0 and costs[lang]["unknown"] == 0 for lang in ("en", "ja"))
    result = {"cohort": cohort, "created_at_utc": now(), "statistics": statistics, "semantics": semantics,
        "quality_routes": routes, "collection_costs": costs, "F_ranges": ranges, "threshold_sensitivity": sensitivity,
        "condition_sha256": recovery.digest(conditions[0]), "all_annotations_seal": seal, "source_files_sha256": before,
        "resource_audit": resources,
        "progression_gate_passed": gate, "gate11_passed": False, "phase12_allowed": False,
        "human_reviewed": False, "history_independence_not_assumed": True,
        "limitations": ["two post-outcome Main stopping-rule amendments", "length-dependent missingness",
            "AI annotations are not human ground truth", "language comparison includes dataset differences",
            "group-bootstrap CI is conditional on comparable observed QA; no seed/model/annotator variability",
            "known v23 negative specificity 87.5% did not meet the old 90% adoption criterion"]}
    # Timestamp is first-publication provenance, never a reason to overwrite analysis on resume.
    destination = Path(config["state_dir"]) / cohort / "analysis.private.json"
    if destination.exists():
        result["created_at_utc"] = read(destination)["created_at_utc"]
    immutable(destination, result)
    require(all(sha(run / name) == expected for name, expected in seal["files"].items()), "Labels changed during analysis")
    require(source_hashes(run) == before, "Source run changed during analysis")
    progress(config, "analyzed", cohort=cohort, codex_running=False)
    return result


def prepare_cal(config):
    recovery = runtime(config)
    from rag_research.experiments.calibration_selection import prepare

    main = Path(config["state_dir"]) / "main/analysis.private.json"
    result = read(main)
    require(config["cal_launch_authorized"] is True, "Calibration auto-start was not authorized")
    verify_seal(Path(config["main_run"]))
    require(source_hashes(Path(config["main_run"])) == result["source_files_sha256"], "Main source changed after analysis")
    require(result["progression_gate_passed"] is True, "Main does not meet the fixed Cal progression conditions")
    selection_path = Path(config["repo"]) / "data/manifests/phase11_bilingual_calibration_selection_v1.json"
    reservation = read(selection_path)
    current = prepare(Path(config["repo"]) / "configs/phase11_bilingual_calibration_selection_policy_v1.json",
                      root=Path(config["repo"]))
    require(all(current["languages"][lang]["selected"] == reservation["languages"][lang]["selected"]
                for lang in ("en", "ja")), "Reserved Cal IDs are no longer unused; do not replace them")
    root, run = Path(config["checkout"]), Path(config["cal_run"])
    configs = {}
    for language in ("en", "ja"):
        main_manifest = read(Path(config["main_run"]) / language / "manifest.json")
        chosen = reservation["languages"][language]["selected"]
        require(len(chosen) == len({r["record_id"] for r in chosen}) == len({r["document_group_id"] for r in chosen}) == 20,
                "Preserve all 20 reserved Cal groups")
        require(not {r["document_group_id"] for r in chosen} & {r["document_group_id"] for r in main_manifest["selection"]},
                "Main/Cal groups overlap")
        value = deepcopy(main_manifest["config"])
        value.pop("fixed_v23_protocol")
        value.update(purpose="phase11-bilingual-calibration-candidate", execution_scope="fixed_v23_calibration_v1",
            analysis_split="calibration", study_version="fixed-v23-additional-cal-v1-" + language)
        value["data"].update(split=reservation["source_splits"][language], record_ids=[r["record_id"] for r in chosen])
        configs[language] = value
    protocol_path = run / "protocol.json"
    protocol = {"version": CAL_VERSION, "configs": configs, "source_splits": reservation["source_splits"],
        "main_gate_passed": True, "main_analysis_sha256": sha(main),
        "original_release_sha256": sha(root / "fixed-v23-release.json"),
        "minimum_comparable_main_per_language": 10, "maximum_calls_per_language": 1660,
        "maximum_new_qa_per_stage": 5, "session_wall_seconds": 43200, "total_wall_seconds": 259200,
        "automatic_retries": 0, "replacement_qa": False, "token_limit_failure_policy": "same_as_main_recovery_v2",
        "purpose": "additional_confirmation_not_tuning", "gate11_passed": False, "phase12_allowed": False,
        "inputs": {str(p): sha(p) for p in [main, Path(config["main_run"]) / "all_annotations.seal.json",
            selection_path, root / "fixed-v23-release.json", root / "fixed-v23-recovery-v2.json",
            *[Path(p) for p in config["sealed_files"]]]}}
    immutable(protocol_path, protocol)
    immutable(run / "unused_reservation_recheck.json", current)
    for language in ("en", "ja"):
        value = {**configs[language], "fixed_v23_calibration_protocol": {
            "path": str(protocol_path.relative_to(root)), "sha256": sha(protocol_path)}}
        immutable(run / "configs" / (language + ".json"), value)
    # Reading reserved QA occurs only after the complete Main seal, analysis and gate.
    for language in ("en", "ja"):
        contract = cal_contract(config, language, recovery)
        cfg, _, rows, qa_path, baseline, _, _, _ = contract
        selection = [{k: r[k] for k in ("record_id", "question", "document_group_id")} for r in rows]
        release = recovery.verify_release()
        sources = {**release["files"], str(protocol_path.relative_to(root)): sha(protocol_path),
            str((run / "configs" / (language + ".json")).relative_to(root)): sha(run / "configs" / (language + ".json"))}
        for name in config["sealed_files"]:
            path = Path(name)
            if path.is_relative_to(root):
                sources[path.relative_to(root).as_posix()] = sha(path)
        manifest = {"schema_version": 1, "purpose": cfg["purpose"], "status": "candidate_not_frozen",
            "language": language, "config": cfg, "baseline": baseline,
            "baseline_model": recovery.runner.model_identity(), "auxiliary_model": recovery.runner.auxiliary_identity(cfg),
            **recovery.runner.execution_identity(baseline), "qa_path": str(qa_path.relative_to(root)),
            "qa_sha256": sha(qa_path), "selection": selection, "selection_scope": "preselected_heldout_calibration",
            "source_sha256": sources, "gate11_passed": False, "phase12_allowed": False}
        immutable(run / language / "manifest.json", manifest)
        (run / language / "baseline").mkdir(exist_ok=True)
    progress(config, "cal_prepared", codex_running=False)


def cal_contract(config, language, recovery):
    import yaml

    from rag_research.data.study_assets import load_assets, load_rows
    from rag_research.generation.config import load_config as load_baseline
    from rag_research.generation.context import PromptSpec

    protocol = verify_cal(config)
    root, run = Path(config["checkout"]), Path(config["cal_run"])
    value = read(run / "configs" / (language + ".json"))
    require({k: v for k, v in value.items() if k != "fixed_v23_calibration_protocol"} == protocol["configs"][language],
            "Calibration conditions changed")
    require(value["fixed_v23_calibration_protocol"] == {"path": str((run / "protocol.json").relative_to(root)),
            "sha256": sha(run / "protocol.json")}, "Calibration registration binding changed")
    assets = load_assets(root / value["assets"])
    rows, qa_path = load_rows(assets, language, value["data"]["split"])
    by_id = {r["record_id"]: r for r in rows}
    chosen = [by_id[i] for i in value["data"]["record_ids"]]
    require(len(chosen) == 20 and all(r["is_answerable"] for r in chosen), "Use all original answered Cal QA")
    baseline, generation = load_baseline(root / value["baseline_config"])
    prompt = PromptSpec(**yaml.safe_load((root / value["baseline_prompts"]).read_text()))
    prompts = yaml.safe_load((root / value["prompts"]).read_text())
    recovery.runner.validate_task_contract(value, prompts)
    return value, assets, chosen, qa_path, baseline, generation, prompt, prompts


def cal_stage(config, language, phase):
    recovery = runtime(config)
    recovery.REGISTRATION = str((Path(config["cal_run"]) / "protocol.json").relative_to(config["checkout"]))
    recovery.VERSION = CAL_VERSION
    from rag_research.experiments.storage import run_lock

    run = Path(config["cal_run"])
    contract = cal_contract(config, language, recovery)
    manifest = read(run / language / "manifest.json")
    require(manifest["config"] == contract[0], "Calibration stage manifest changed")
    with run_lock(run / language):
        result = (recovery.baseline_stage if phase == "baseline" else recovery.internal_stage)(
            run / language, contract, manifest)
        write(run / f"result-{language}-{phase}.json", result)


def collect_cal(config, config_path):
    recovery = runtime(config)
    from rag_research.experiments.storage import run_lock

    run = Path(config["cal_run"])
    protocol = verify_cal(config)
    receipts = Path(config["state_dir"]) / "cal-sessions"
    spent = sum(read(p).get("elapsed_seconds", 0) for p in receipts.glob("*.json")) if receipts.exists() else 0
    with run_lock(run):
        for language in ("en", "ja"):
            for phase in ("baseline", "internal"):
                for index in range(4):
                    require(not (Path(config["state_dir"]) / "stop.request").exists(), "Workflow stop requested")
                    receipt = receipts / f"{language}-{phase}-{index}.json"
                    progress(config, "collect_cal", cohort="cal", language=language, phase=phase, codex_running=False)
                    limit = min(protocol["session_wall_seconds"], protocol["total_wall_seconds"] - spent)
                    require(limit > 0, "Original finite Calibration wall budget exhausted")
                    run_owned([sys.executable, str(Path(__file__).resolve()), "--config", str(config_path),
                        "--action", "cal-stage", "--language", language, "--phase", phase],
                        cwd=config["checkout"], receipt=receipt, timeout=limit)
                    spent = sum(read(p).get("elapsed_seconds", 0) for p in receipts.glob("*.json"))
                    if read(run / f"result-{language}-{phase}.json")["stage_complete"]:
                        break
                else:
                    raise ValueError("Finite Calibration schedule did not complete")
        recovery.export_packets(run)
        for language in ("en", "ja"):
            recovery.reserve(run / language, 1660)
        missing = recovery.missing_count(run)
        rewrite_missing = recovery.rewrite_missing_count(run)
        totals = recovery.legacy.totals(run)
        require(totals["completed_qa"] + missing + rewrite_missing == 40,
                "Every selected Cal QA must be complete or an explicitly retained length failure")
        immutable(run / "collection_completed.json", {"processed_qa": 40, "state": "awaiting_scoring",
            "successful_qa": totals["completed_qa"], "baseline_failed_qa": missing,
            "rewrite_failed_qa": rewrite_missing, "includes_missing": bool(missing + rewrite_missing),
            "gate11_passed": False, "phase12_allowed": False})
    progress(config, "cal_awaiting_scoring", cohort="cal", codex_running=False)


def public_tables(result):
    routes = []
    for language, collection in result["quality_routes"].items():
        for route in sorted({r["route"] for r in collection["routes"]}):
            rows = [r for r in collection["routes"] if r["route"] == route]
            statuses = Counter(r["quality_status"] for r in rows)
            routes.append({"cohort": result["cohort"], "language": language, "route": route,
                "selected_qa": 20, "available_initial_qa": len(rows), "baseline_missing": 20 - len(rows),
                **{name: statuses[name] for name in ("reliable", "unreliable", "indeterminate", "pending")},
                "rewrite_failed_fallbacks": sum(r["fallback"] == "rewrite_failed" for r in rows),
                "native_attempts_sum": sum(r["operational_cost"]["recorded_completion_attempts"] for r in rows),
                "input_tokens_sum": sum(r["operational_cost"]["input_tokens"] for r in rows),
                "output_tokens_sum": sum(r["operational_cost"]["output_tokens"] for r in rows)})
    return routes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--action", required=True, choices=("review-main", "review-cal", "analyze-main", "analyze-cal",
        "prepare-cal", "collect-cal", "cal-stage"))
    parser.add_argument("--language", choices=("en", "ja"))
    parser.add_argument("--phase", choices=("baseline", "internal"))
    args = parser.parse_args()
    config = load_config(args.config)
    require(datetime.fromisoformat(config["deadline_utc"]).timestamp() > datetime.now().timestamp(), "Workflow deadline passed")
    if args.action.startswith("review-"):
        from review import complete_annotations

        complete_annotations(config, cohort_run(config, args.action.split("-")[1]), args.action.split("-")[1])
    elif args.action.startswith("analyze-"):
        analyze_cohort(config, args.action.split("-")[1])
    elif args.action == "prepare-cal":
        prepare_cal(config)
    elif args.action == "collect-cal":
        collect_cal(config, args.config)
    else:
        require(args.language and args.phase, "Specify the registered Calibration stage")
        cal_stage(config, args.language, args.phase)


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt("Workflow process interrupted")

    signal.signal(signal.SIGTERM, interrupted)
    main()
