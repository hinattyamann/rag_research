"""Scoped adapter around the sealed, already exercised Cal collection functions."""

import argparse
import importlib.util
import json
import signal
import sys
from datetime import datetime
from pathlib import Path

VERSION = "fixed-v23-cal-extension-v1"


def attach(config):
    legacy = Path(config["frozen_scripts"])
    sys.path.insert(0, str(legacy))
    import common
    import pipeline

    def verify(cfg):
        common.require(cfg["extension_version"] == VERSION and cfg["cal_launch_authorized"] is True,
                       "Extension authorization changed")
        protocol = common.read(Path(cfg["cal_run"]) / "protocol.json")
        common.require(protocol["version"] == VERSION and protocol["batch_id"] == cfg["batch_id"] and
            protocol["maximum_calls_per_language"] == 1660 and protocol["automatic_retries"] == 0 and
            protocol["purpose"] == "additional_confirmation_not_tuning" and protocol["phase12_allowed"] is False and
            protocol["source_splits"] == {"en": "development", "ja": "calibration"} and
            protocol["original_release_sha256"] == common.sha(Path(cfg["checkout"]) / "fixed-v23-release.json"),
            "Extension scientific protocol changed")
        for path, expected in protocol["inputs"].items():
            common.require(common.sha(path) == expected, "Extension prerequisite changed")
        for language in ["en", "ja"]:
            chosen = protocol["selection"][language]
            common.require(len(chosen) == len({q["record_id"] for q in chosen}) ==
                len({q["document_group_id"] for q in chosen}) == 20, "Preserve all selected extension groups")
        return protocol

    pipeline.verify_cal = verify
    return common, pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--action", choices=["preflight", "stage", "finish-collection", "review", "analyze", "export"], required=True)
    parser.add_argument("--language", choices=["en", "ja"])
    parser.add_argument("--phase", choices=["baseline", "internal"])
    args = parser.parse_args()
    initial = json.loads(args.config.read_text())
    common, pipeline = attach(initial)
    config = common.load_config(args.config)
    common.require(datetime.now().timestamp() < datetime.fromisoformat(config["deadline_utc"]).timestamp(), "Workflow deadline reached")
    pipeline.verify_cal(config)
    if args.action == "preflight":
        recovery = pipeline.runtime(config)
        fingerprints = {}
        from rag_research.experiments.bilingual_statistics import condition
        for language in ["en", "ja"]:
            contract = pipeline.cal_contract(config, language, recovery)
            manifest = common.read(Path(config["cal_run"]) / language / "manifest.json")
            common.require(manifest["config"] == contract[0] and len(contract[2]) == 20,
                           "Manifest/contract mismatch")
            for name, expected in manifest["source_sha256"].items():
                common.require(common.sha(Path(config["checkout"]) / name) == expected, "Fixed source changed")
            fingerprints[language] = recovery.digest(condition(manifest))
        common.require(fingerprints["en"] == fingerprints["ja"], "Scientific conditions differ")
        print(json.dumps({"status": "passed", "new_native_calls": 0, "condition_sha256": fingerprints}))
    elif args.action == "stage":
        common.require(args.language and args.phase, "Stage identity required")
        pipeline.cal_stage(config, args.language, args.phase)
    elif args.action == "finish-collection":
        recovery = pipeline.runtime(config)
        run = Path(config["cal_run"])
        recovery.export_packets(run)
        for lang in ["en", "ja"]:
            recovery.reserve(run / lang, 1660)
        missing, rewrite = recovery.missing_count(run), recovery.rewrite_missing_count(run)
        totals = recovery.legacy.totals(run)
        common.require(totals["completed_qa"] + missing + rewrite == 40, "Incomplete extension collection")
        common.immutable(run / "collection_completed.json", {"processed_qa": 40, "state": "awaiting_scoring",
            "successful_qa": totals["completed_qa"], "baseline_failed_qa": missing, "rewrite_failed_qa": rewrite,
            "includes_missing": bool(missing + rewrite), "gate11_passed": False, "phase12_allowed": False})
    elif args.action == "review":
        import review
        review.complete_annotations(config, Path(config["cal_run"]), "cal")
    elif args.action == "analyze":
        pipeline.analyze_cohort(config, "cal")
    else:
        spec = importlib.util.spec_from_file_location("extension_material_export", Path(__file__).with_name("materials.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.export_batch(config)


if __name__ == "__main__":
    def stop(signum, frame):
        raise KeyboardInterrupt("Extension process interrupted")
    signal.signal(signal.SIGTERM, stop)
    main()
