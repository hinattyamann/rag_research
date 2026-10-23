"""Prepare both main Development configs only after complete known-regression adoption.

This command runs no model. It replays immutable evidence on a private copy and
uses the existing runner's full contract before publishing either configuration.
The execution policy is a separate, prior input; this command cannot adopt one.
"""

import argparse
import json
import shutil
import sys
import tempfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.bilingual_main import (  # noqa: E402
    bound_path,
    passing_known_regression,
    validate_main_policy,
)
from rag_research.experiments.bilingual_runner import load_config  # noqa: E402
from rag_research.experiments.development_selection import prepare as select  # noqa: E402
from rag_research.experiments.frozen_trace import digest, require  # noqa: E402
from rag_research.experiments.storage import (  # noqa: E402
    read_json,
    run_lock,
    verify_checkpoint,
    write_json,
)
from rag_research.retrieval.common import file_hash  # noqa: E402


def local(path):
    path = Path(path).resolve()
    require(path.is_relative_to(ROOT), "Main preparation paths must stay in the repository")
    return path


def binding(path):
    path = local(path)
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": file_hash(path)}


def snapshot(run):
    files = {}
    for path in sorted(run.rglob("*")):
        if path.is_file():
            require(path.resolve().is_relative_to(run), "Known evidence escapes its run")
            files[path.relative_to(run).as_posix()] = file_hash(path)
    return files


def terminal_gate(report_path):
    """Reject before policy, templates, selection or previously unused QA are read."""
    report_path = local(report_path)
    require(report_path.is_relative_to(ROOT / "data/runs/semantic_diagnostics") and
            report_path.name == "report.json", "Use canonical known-regression evidence")
    require(report_path.is_file(), "Complete and audit the whole known regression before main preparation")
    report = read_json(report_path)
    require(report.get("diagnostic_gate_passed") is True and
            report.get("completed_conditions") == report.get("planned_conditions") == 30 and
            report.get("completion_attempts_recorded") == 84 and
            report.get("not_attempted_ids") == [] and report.get("cost_incomplete") is False,
            "Main preparation requires passing 30-condition/84-call direct known regression")
    run = report_path.parent
    require(all((run / name).is_file() for name in ("audit_check.json", "resume_check.json", ".run.lock")),
            "Complete the terminal audit and zero-call resume check before main preparation")
    audit, resume = (read_json(run / name) for name in ("audit_check.json", "resume_check.json"))
    require(audit.get("aggregate_conditions") == 30 and audit.get("actual_leaf_calls") == 84 and
            resume.get("new_calls") == resume.get("new_server_files") == 0 and
            resume.get("unchanged_files") == len(resume.get("sha256", {})) > 0,
            "Whole known-regression audit or zero-call replay is missing")
    for name, sha in resume["sha256"].items():
        path = (run / name).resolve()
        require(path.is_relative_to(run) and path.is_file() and file_hash(path) == sha,
                "Previously audited known evidence changed")
    return run


def configuration(template, prior, selected, language, assets, policy, selection, adoption, version):
    """Copy adopted model/task conditions; retain baseline, rewrite and blind review contracts."""
    require(template["purpose"] == "phase11-bilingual-development-candidate" and
            template["language"] == language and template["execution_scope"] == "connection_smoke_only",
            "Use the matching existing Development connection template")
    config = deepcopy(template)
    for key, value in prior.items():
        if key not in {"study_version", "purpose", "diagnostics", "prompts"}:
            config[key] = deepcopy(value)
    config.update(study_version=f"{version}-{language}", execution_scope="main_development_v1",
        language=language, assets=assets, prompts=prior["prompts"][language],
        data={"split": "development", "answerable_only": True,
              "record_ids": [row["record_id"] for row in selected]},
        main_execution_policy=deepcopy(policy), development_selection=deepcopy(selection),
        adopted_known_regression=deepcopy(adoption))
    config["decision"]["bare_refusal_policy"] = "rewrite_once"
    return config


def prepare(known_report, known_config, policy_path, selection_policy, assets, templates, output):
    output = local(output)
    parent = ROOT / "data/runs/bilingual_main_protocol"
    require(output.is_relative_to(parent) and output != parent and not output.exists(),
            "Use a new main protocol directory; preserve existing outputs")
    run = terminal_gate(known_report)
    # No path below this line is opened for an incomplete/failed known regression.
    known_config, policy_path, selection_policy, assets = map(local,
        (known_config, policy_path, selection_policy, assets))
    require(all(p.is_relative_to(ROOT / "configs") for p in
                (known_config, policy_path, selection_policy, assets)), "Use versioned configs as main inputs")
    templates = {language: local(path) for language, path in templates.items()}
    require(set(templates) == {"en", "ja"} and all(p.is_relative_to(ROOT / "configs")
            for p in templates.values()), "Both language templates are required")
    with run_lock(run):
        before = snapshot(run)
        inputs = {"known_config": binding(known_config), "execution_policy": binding(policy_path),
            "selection_policy": binding(selection_policy), "assets": binding(assets),
            **{f"template_{lang}": binding(path) for lang, path in templates.items()}}
        adoption = {**binding(run / "report.json"), "config": inputs["known_config"]}
        # The copy remains under diagnostics to exercise the exact production adoption guard.
        with tempfile.TemporaryDirectory(prefix=".main-preparation-", dir=run.parent) as temporary:
            staging = Path(temporary)
            copied = staging / "known"
            shutil.copytree(run, copied)
            require(snapshot(copied) == before, "Copy every known-regression byte before replay")
            copied_adoption = {**adoption, "path": (copied / "report.json").relative_to(ROOT).as_posix()}
            prior, _ = passing_known_regression(copied_adoption)
            require(prior.get("verification_mode") == "claimwise-v1", "Use the adopted direct fixed-unit candidate")
            policy = read_json(policy_path)
            require(policy.get("purpose") == "phase11-main-development-execution-policy" and
                    policy.get("status") == "preregistered" and policy.get("phase12_allowed") is False and
                    policy.get("count_per_language") == 20,
                    "A separately preregistered current main execution policy is required")
            validate_main_policy(policy)
            candidate = yaml.safe_load(bound_path(policy.get("candidate_config"), root=ROOT).read_text("utf-8"))
            ignored = {"study_version", "diagnostics"}
            require(isinstance(candidate, dict) and
                    {k: v for k, v in candidate.items() if k not in ignored} ==
                    {k: v for k, v in prior.items() if k not in ignored},
                    "Main policy candidate must match the completely adopted known conditions")
            selection_binding = policy["selection_manifest"]
            selection_path = local(ROOT / selection_binding["path"])
            require(selection_path.is_relative_to(ROOT / "data/manifests") and
                    file_hash(selection_path) == selection_binding["sha256"], "Main selection binding changed")
            selection = read_json(selection_path)
            verify_checkpoint(selection)
            fresh = select(selection_policy)
            require(selection["policy_sha256"] == file_hash(selection_policy) and
                    selection["assets_sha256"] == file_hash(assets) and
                    fresh["used_baseline_input_sha256"] == selection["used_baseline_input_sha256"] and
                    all(fresh["languages"][lang]["selected"] == selection["languages"][lang]["selected"]
                        for lang in ("en", "ja")),
                    "Keep every original selected ID/group/order and unused status; never refill")
            configs = {}
            for language, template in templates.items():
                config = configuration(yaml.safe_load(template.read_text("utf-8")), prior,
                    selection["languages"][language]["selected"], language, inputs["assets"]["path"],
                    inputs["execution_policy"], selection_binding, adoption, output.name)
                config["main_limits"] = deepcopy(policy["limits_per_language"])
                checked = deepcopy(config)
                checked["adopted_known_regression"] = copied_adoption
                staged_path = staging / f"{language}.yaml"
                staged_path.write_text(yaml.safe_dump(checked, sort_keys=False, allow_unicode=True), "utf-8")
                # Load/validate only; the runner, retrieval and Native execution are never called.
                loaded = load_config(staged_path)
                require(loaded[0] == checked and len(loaded[2]) == 20,
                        "Both prepared configs must satisfy the production main contract")
                configs[language] = config
            require(snapshot(copied) == before and snapshot(run) == before,
                    "Replay must leave every original and copied known byte unchanged")
            require(all(binding(ROOT / b["path"]) == b for b in inputs.values()) and
                    binding(selection_path) == selection_binding, "Main inputs changed during preparation")
        # All checks precede output creation. An interrupted publication stays incomplete.
        output.mkdir(parents=True, exist_ok=False)
        for language, config in configs.items():
            with (output / f"main-{language}.yaml").open("x", encoding="utf-8") as stream:
                stream.write(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))
        receipt = {"schema_version": 1, "purpose": "phase11-bilingual-main-preparation-not-results",
            "created_at_utc": datetime.now(UTC).isoformat(), "inputs": inputs,
            "selection_manifest": selection_binding, "adopted_known_regression": adoption,
            "known_evidence_sha256": before, "known_files_unchanged": len(before),
            "known_replayed_on_copy": True, "both_configs_validated_by_main_runner": True,
            "configs": {lang: binding(output / f"main-{lang}.yaml") for lang in configs},
            "config_payload_sha256": {lang: digest(config) for lang, config in configs.items()},
            "preparer": binding(Path(__file__)), "new_model_calls": 0, "new_servers": 0,
            "main_experiment_completed": False, "gate11_passed": False, "phase12_allowed": False}
        write_json(output / "preparation.json", receipt)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("known-report", "known-config", "policy", "selection-policy", "assets", "template-en",
                  "template-ja", "output-dir"):
        parser.add_argument("--" + field, required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.known_report, args.known_config, args.policy, args.selection_policy, args.assets,
                     {"en": args.template_en, "ja": args.template_ja}, args.output_dir)
    print(json.dumps({"configs": result["configs"], "new_model_calls": 0, "new_servers": 0,
                      "main_experiment_completed": False, "phase12_allowed": False}))
