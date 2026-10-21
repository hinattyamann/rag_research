"""Bind held-out execution to reverified main evidence and the original reservation."""

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import yaml

from rag_research.experiments.bilingual_certification import certify_main
from rag_research.experiments.bilingual_main import bound_path, validate_main_policy
from rag_research.experiments.calibration_selection import SOURCE_SPLITS, prepare
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.storage import (
    checkpoint,
    read_json,
    run_lock,
    verify_checkpoint,
    write_json,
)
from rag_research.retrieval.common import file_hash

ROOT = Path(__file__).resolve().parents[3]
SCOPE = "heldout_calibration_v1"
LIMITS = {"maximum_completion_attempts": 1660, "maximum_new_qa_per_stage_session": 5,
    "stop_on_any_task_error": True, "automatic_refill": False}
MAIN_FIELDS = ("status", "canonical_inputs", "source_runs", "main_execution_policy", "condition_sha256",
    "annotation_burden", "evidence_files_sha256", "bound_external_files_sha256", "certification_source_sha256")


def binding(path):
    path = Path(path).resolve()
    require(path.is_relative_to(ROOT) and path.is_file(), "Calibration binding must stay in repository")
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": file_hash(path)}


def bound(value):
    return bound_path(value, root=ROOT)


def rules(path):
    value = read_json(path)
    require(value["schema_version"] == 1 and value["purpose"] == "phase11-bilingual-calibration-execution-rules" and
            value["status"] == "preregistered_pending_main_evidence" and value["count_per_language"] == 20 and
            value["limits_per_language"] == LIMITS and value["main_full_certificate_required"] is True and
            value["both_language_all_labels_sealed_before_unblinding"] is True and value["phase12_allowed"] is False,
            "Preserve held-out Calibration rules and complete main evidence")
    validate_main_policy(value)
    resource = value["resource_policy"]
    require(resource["total_native_call_ceiling"] == 1660 and resource["unknown_outcome"] == "stop_without_retry" and
            resource["no_post_result_budget_or_criteria_relaxation"] is True and
            all(isinstance(resource[k], str) and resource[k].strip() for k in ("token_limits", "time_limits")) and
            all(isinstance(value[k], str) and value[k].strip() for k in ("revision_policy", "sample_size_policy")),
            "Calibration resource/revision rules must be explicit")
    return value


def verify_main(inputs_path, certificate_path):
    # Recompute/seal both language reviews BEFORE reading the private certificate.
    current = certify_main(inputs_path)
    certificate_path = Path(certificate_path).resolve()
    require(certificate_path.is_relative_to(ROOT / "data/runs/development_certification"),
            "Use a complete main Development certificate")
    saved = read_json(certificate_path)
    verify_checkpoint(saved)
    require(saved["purpose"] == "phase11-main-development-evidence-certificate" and saved["status"] == "verified" and
            all(saved[k] == current[k] for k in MAIN_FIELDS) and
            saved["inputs"] == binding(inputs_path), "Main certificate differs from reverified complete evidence")
    require(set(current["source_runs"]) == {"en", "ja"} and all(
            len(r["selected"]) == len({s["document_group_id"] for s in r["selected"]}) == 20
            for r in current["source_runs"].values()), "Both complete main20 group sets are required")
    return current


def unchanged_selection(reservation_path, policy_path, *, excluded_resume_runs=()):
    reserved = read_json(reservation_path)
    verify_checkpoint(reserved)
    fresh = prepare(policy_path, root=ROOT, excluded_resume_runs=excluded_resume_runs)
    keys = ("purpose", "method", "analysis_split", "source_splits", "seed", "policy_sha256", "inputs", "source_qa_sha256")
    require(all(reserved[k] == fresh[k] for k in keys) and reserved["source_splits"] == SOURCE_SPLITS and
            all(reserved["languages"][lang]["selected"] == fresh["languages"][lang]["selected"] and
                fresh["languages"][lang]["planned_qa"] == len(fresh["languages"][lang]["selected"]) == 20
                for lang in ("en", "ja")),
            "Reserved Calibration is no longer unused or its original IDs/groups changed; never refill")
    return reserved, fresh


def source_hashes(*, root=None):
    root = ROOT if root is None else root
    paths = [*sorted((root / "src/rag_research").rglob("*.py")),
        *[root / name for name in ("scripts/prepare_bilingual_calibration.py", "scripts/run_bilingual_calibration.py",
            "scripts/analyze_bilingual_calibration.py", "scripts/bilingual_quality.py", "scripts/review_bilingual_units.py",
            "docs/order_quality_rubric.md", "docs/phase11_statistical_plan.md")]]
    return {p.relative_to(root).as_posix(): file_hash(p) for p in paths}


def configuration(main_config, selected, language):
    config = deepcopy(main_config)
    require(config["execution_scope"] == "main_development_v1" and config["language"] == language and
            config["main_limits"] == LIMITS, "Use the actual completed main configuration")
    config.update(purpose="phase11-bilingual-calibration-candidate", execution_scope=SCOPE,
        analysis_split="calibration", data={"split": SOURCE_SPLITS[language], "record_ids": [s["record_id"] for s in selected]})
    for key in ("development_selection", "main_execution_policy", "main_limits"):
        config.pop(key)
    config["calibration_limits"] = deepcopy(LIMITS)
    return config


def create(inputs_path, certificate_path, reservation_path, policy_path, rules_path, output):
    paths = [Path(p).resolve() for p in (inputs_path, certificate_path, reservation_path, policy_path, rules_path)]
    inputs_path, certificate_path, reservation_path, policy_path, rules_path = paths
    output = Path(output).resolve()
    parent = ROOT / "data/runs/bilingual_calibration_protocol"
    require(output.is_relative_to(parent) and output != parent and not output.exists(), "Use a new Calibration protocol")
    require(all(p.is_relative_to(ROOT) for p in paths), "Calibration inputs must stay in repository")
    require(reservation_path.is_relative_to(ROOT / "data/manifests") or reservation_path.is_relative_to(ROOT / "configs"),
            "Reservation must be a manifest/configuration, not Evaluation QA")
    require(policy_path.is_relative_to(ROOT / "configs") and rules_path.is_relative_to(ROOT / "configs"),
            "Calibration policies/rules must stay in configs; never parse Evaluation QA")
    source_before = source_hashes()
    main = verify_main(inputs_path, certificate_path)
    rules(rules_path)
    reserved, fresh = unchanged_selection(reservation_path, policy_path)
    configs, runs, estimates = {}, {}, {}
    for language in ("en", "ja"):
        main_run = ROOT / main["source_runs"][language]["run"]
        manifest = read_json(main_run / "manifest.json")
        chosen = fresh["languages"][language]["selected"]
        config = configuration(manifest["config"], chosen, language)
        require(config["assets"] == reserved["inputs"]["assets"]["path"], "Calibration assets must match main")
        require(not {s["document_group_id"] for s in chosen} & {
            s["document_group_id"] for s in main["source_runs"][language]["selected"]}, "Calibration overlaps main groups")
        configs[language] = config
        runs[language] = f"data/runs/bilingual_calibration/{output.name}-{language}"
        measured = main["source_runs"][language]["native_collection_cost"]
        estimates[language] = {"observed_main_calls": measured["completion_attempts"],
            "observed_main_input_tokens": measured["input_tokens"], "observed_main_output_tokens": measured["output_tokens"],
            "observed_main_step_seconds": measured["summed_step_seconds"],
            "largest_adopted_context_tokens": max(manifest["baseline"]["generation"]["context_tokens"], config["auxiliary_runtime"]["context_tokens"]),
            "largest_adopted_output_reservation": max(manifest["baseline"]["generation"]["max_output_tokens"],
                *(v["max_output_tokens"] for k, v in config["tasks"].items() if k != "extract_claims")),
            "baseline_timeout_seconds": manifest["baseline"]["generation"]["timeout_seconds"],
            "auxiliary_timeout_seconds": config["auxiliary_runtime"]["timeout_seconds"],
            "estimate_note": "Same 20 QA count; use measured main work for planning, not a guarantee for different QA. Native timeout is per call; retrieval/startup/review and wall-clock latency are separate."}
    protocol = {"schema_version": 1, "purpose": "phase11-bilingual-heldout-calibration-protocol", "status": "preregistered",
        "created_at_utc": datetime.now(UTC).isoformat(), "execution_scope": SCOPE,
        "main_inputs": binding(inputs_path), "main_certificate": binding(certificate_path),
        "reservation": binding(reservation_path), "reservation_policy": binding(policy_path), "rules": binding(rules_path),
        "condition_sha256": main["condition_sha256"], "source_splits": SOURCE_SPLITS, "analysis_split": "calibration",
        "selected": {lang: fresh["languages"][lang]["selected"] for lang in ("en", "ja")}, "runs": runs,
        "config_payload_sha256": {lang: digest(configs[lang]) for lang in configs},
        "unused_inventory_at_preparation_sha256": digest(fresh), "resource_estimates": estimates,
        "source_sha256": source_before, "new_model_calls": 0, "gate11_passed": False, "phase12_allowed": False}
    require(source_hashes() == source_before, "Calibration preparation sources changed")
    with run_lock(output):
        require({p.name for p in output.iterdir()} == {".run.lock"}, "Preserve existing protocol")
        write_json(output / "unused_inventory_before.json", fresh)
        protocol["unused_inventory_file"] = binding(output / "unused_inventory_before.json")
        checkpoint(output / "protocol.json", protocol)
        for language, config in configs.items():
            config["calibration_protocol"] = binding(output / "protocol.json")
            (output / ("config-" + language + ".yaml")).write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))
    return {"protocol": binding(output / "protocol.json"), "runs": runs, "new_model_calls": 0,
        "gate11_passed": False, "phase12_allowed": False}


def validate(config, output):
    protocol_path = bound(config.get("calibration_protocol"))
    require(protocol_path.is_relative_to(ROOT / "data/runs/bilingual_calibration_protocol") and
            protocol_path.name == "protocol.json", "Dedicated Calibration protocol required")
    protocol = read_json(protocol_path)
    verify_checkpoint(protocol)
    require(protocol["purpose"] == "phase11-bilingual-heldout-calibration-protocol" and protocol["status"] == "preregistered" and
            protocol["execution_scope"] == SCOPE and protocol["analysis_split"] == "calibration" and
            protocol["source_splits"] == SOURCE_SPLITS and protocol["phase12_allowed"] is False,
            "Invalid held-out protocol")
    language = config["language"]
    require(language in SOURCE_SPLITS and Path(output).resolve() == ROOT / protocol["runs"][language] and
            digest({k: v for k, v in config.items() if k != "calibration_protocol"}) == protocol["config_payload_sha256"][language] and
            config["purpose"] == "phase11-bilingual-calibration-candidate" and config["execution_scope"] == SCOPE and
            config["data"]["split"] == SOURCE_SPLITS[language] and config["calibration_limits"] == LIMITS,
            "Calibration configuration, source split or exact output changed")
    require(source_hashes() == protocol["source_sha256"], "Calibration source changed after preregistration")
    rules(bound(protocol["rules"]))
    unused_path = bound(protocol["unused_inventory_file"])
    require(digest(read_json(unused_path)) == protocol["unused_inventory_at_preparation_sha256"], "Pre-inference usage proof changed")
    certificate_path = (ROOT / protocol["main_certificate"]["path"]).resolve()
    main = verify_main(bound(protocol["main_inputs"]), certificate_path)
    require(binding(certificate_path) == protocol["main_certificate"], "Bound main certificate changed")
    require(main["condition_sha256"] == protocol["condition_sha256"], "Main conditions changed")
    main_manifest = read_json(ROOT / main["source_runs"][language]["run"] / "manifest.json")
    require({k: v for k, v in config.items() if k != "calibration_protocol"} ==
            configuration(main_manifest["config"], protocol["selected"][language], language),
            "Calibration must use the actual adopted main conditions, even with updated protocol hashes")
    own = []
    for lang in ("en", "ja"):
        path = (ROOT / protocol["runs"][lang]).resolve()
        require(path.is_relative_to(ROOT / "data/runs/bilingual_calibration") and
                path != ROOT / "data/runs/bilingual_calibration", "Calibration run escapes its root")
        if path.exists():
            manifest_path = path / "manifest.json"
            require(manifest_path.is_file(), "Existing Calibration journal has no validated own manifest")
            manifest = read_json(manifest_path)
            own_config = manifest["config"]
            require(manifest["language"] == lang and own_config["calibration_protocol"] == config["calibration_protocol"] and
                    digest({k: v for k, v in own_config.items() if k != "calibration_protocol"}) == protocol["config_payload_sha256"][lang] and
                    [r["record_id"] for r in manifest["selection"]] == [r["record_id"] for r in protocol["selected"][lang]],
                    "Only this protocol's exact original runs may resume; do not hide external usage")
        own.append(path.relative_to(ROOT).as_posix())
    reserved, fresh = unchanged_selection(bound(protocol["reservation"]), bound(protocol["reservation_policy"]), excluded_resume_runs=own)
    require(all(fresh["languages"][lang]["selected"] == protocol["selected"][lang] for lang in ("en", "ja")) and
            [r["record_id"] for r in protocol["selected"][language]] == config["data"]["record_ids"], "Calibration selection drifted")
    return protocol, fresh, reserved


def review_contract(run, manifest, *, canonical_runs=None):
    """Only byte-identical isolated replays may stand in for the original Cal runs."""
    run = Path(run).resolve()
    original = run
    if canonical_runs is not None:
        aliases = {Path(k).resolve(): Path(v).resolve() for k, v in canonical_runs.items()}
        require(run in aliases and len(aliases) == len(set(aliases.values())) == 2,
                "Calibration replay needs the complete distinct original run mapping")
        for copied, source in aliases.items():
            require(copied.is_relative_to(ROOT / "data/runs/bilingual_calibration_replay") and
                    copied != ROOT / "data/runs/bilingual_calibration_replay" and
                    source.is_relative_to(ROOT / "data/runs/bilingual_calibration") and
                    source != ROOT / "data/runs/bilingual_calibration", "Unexpected isolated Cal replay")

            def snapshot(folder):
                paths = [p for p in folder.rglob("*") if p.is_file()]
                require(paths and all(p.resolve().is_relative_to(folder) for p in paths), "Replay file escapes run")
                return {p.relative_to(folder).as_posix(): file_hash(p) for p in paths}

            require(snapshot(copied) == snapshot(source), "Isolated Calibration replay differs from original evidence")
        original = aliases[run]
    protocol, _, _ = validate(manifest["config"], original)
    from rag_research.experiments.bilingual_statistics import condition

    require(digest(condition(manifest)) == protocol["condition_sha256"],
            "Calibration model/baseline/analysis conditions differ from the actual main proof")
    if canonical_runs is not None:
        require({(ROOT / p).resolve() for p in protocol["runs"].values()} ==
                {Path(p).resolve() for p in canonical_runs.values()}, "Replay original cohort differs from protocol")
    return protocol
