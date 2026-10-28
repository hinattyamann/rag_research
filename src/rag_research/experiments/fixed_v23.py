"""Explicit fixed-v23 study, separate from the historical scientific adoption gates."""

import subprocess
from copy import deepcopy
from pathlib import Path

import yaml

from rag_research.experiments.frozen_trace import require
from rag_research.experiments.protocol import ROOT
from rag_research.experiments.storage import read_json, verify_checkpoint
from rag_research.retrieval.common import file_hash

VERSION = "fixed-v23-order-study-v1"
BASE = "f0b7c71c4375a617c7142c67e3aa0610f73edb14"
CANDIDATE = "91f50601299a8e9b1399b3925acddc36ffb6af9a46032e2adad631770a12d1b5"
INFERENCE_KEYS = ("auxiliary_model_manifest", "auxiliary_runtime", "sampling", "execution",
                  "verification_mode", "output_constraints", "tasks", "trials", "errors")


def bound(root, binding):
    require(isinstance(binding, dict) and set(binding) == {"path", "sha256"}, "Invalid fixed-study binding")
    name = binding["path"]
    require(isinstance(name, str) and not Path(name).is_absolute(), "Use a relative study path")
    path = (root / name).resolve()
    require(path.is_relative_to(root) and path.is_file() and file_hash(path) == binding["sha256"],
            "Fixed-study file changed: " + name)
    return path


def load_study(path, *, root=ROOT):
    study = read_json(Path(path))
    require(study["version"] == VERSION and study["base_commit"] == BASE and
            study["candidate_identity_sha256"] == CANDIDATE and study["mode"] == "main" and
            study["phase12_allowed"] is False and study["old_gate11_passed"] is False and
            study["known_limit_acknowledged"] is True and study["automatic_retries"] == 0,
            "Use the explicit fixed-v23 Main study; preserve known rejection")
    require(study["limits_per_language"] == {
        "maximum_completion_attempts": 1660, "maximum_new_qa_per_stage_session": 5,
        "stop_on_any_task_error": True, "automatic_refill": False}, "Preserve original finite call ceiling")
    require(study["count_per_language"] == 20 and study["minimum_comparable_per_language"] == 10 and
            study["quality_and_expected_seal"] == "all_both_languages_before_internal_unblinding",
            "Preserve both-language selection, comparison and seal requirements")
    for key in ("pilot_wall_seconds", "session_wall_seconds", "total_wall_seconds"):
        require(type(study[key]) is int and study[key] > 1200, "Finite wall deadline required")
    rejection = read_json(bound(root, study["known_result"]))
    require(rejection["fixed_commit"] == BASE and rejection["candidate_identity_sha256"] == CANDIDATE
            and rejection["binary_adoption"]["passed"] is False
            and rejection["binary_adoption"]["negative_specificity"] == .875
            and rejection["counts"]["returned"] == 84
            and rejection["counts"]["failed"] == rejection["counts"]["unknown"] == 0,
            "Retain the complete rejected known result without rewriting history")
    prior = yaml.safe_load(bound(root, study["candidate"]).read_text("utf-8"))
    require(prior["candidate_identity_sha256"] == CANDIDATE, "Original candidate identity differs")
    selection = read_json(bound(root, study["selection"]))
    verify_checkpoint(selection)
    require(selection["assets_sha256"] == study["assets"]["sha256"], "Original selection/assets differ")
    bound(root, study["assets"])
    for binding in study["fixed_inputs"]:
        bound(root, binding)
    return study, prior, selection


def verify_release(root=ROOT):
    """The deployed checkout seals every original source plus the control-only overlay."""
    root = Path(root).resolve()
    require((root / "fixed-v23-release.json").is_file(), "Use the sealed original-v23 checkout")
    release = read_json(root / "fixed-v23-release.json")
    require(release["base_commit"] == BASE and release["new_native_calls"] == 0,
            "Missing fixed source release")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    require(head == BASE, "Run only from the original v23 checkout")
    for name, sha in release["files"].items():
        bound(root, {"path": name, "sha256": sha})
    actual = {p.relative_to(root).as_posix() for p in (root / "src/rag_research").rglob("*.py")}
    require(actual == {p for p in release["files"] if p.startswith("src/")},
            "Unexpected or missing deployed Python source")
    return release


def validate_fixed(config, rows, qa_path, *, root=ROOT):
    verify_release(root)
    study_path = bound(root, config["fixed_v23_protocol"])
    study, prior, selection = load_study(study_path, root=root)
    require(config["execution_scope"] == "fixed_v23_main_v1" and
            config["purpose"] == "phase11-bilingual-development-candidate" and
            config["data"]["split"] == "development" and config["phase12_allowed"] is False,
            "Fixed-v23 Main cannot access Calibration or Evaluation")
    require(not {"autonomy_protocol", "autonomy_protocol_version", "candidate_identity_sha256",
                 "adopted_known_regression", "main_execution_policy"}.intersection(config),
            "Do not masquerade as an adopted historical Main chain")
    for key in INFERENCE_KEYS:
        require(config.get(key) == prior[key], "Fixed-v23 inference condition changed: " + key)
    decision = deepcopy(prior["decision"])
    decision["bare_refusal_policy"] = "rewrite_once"
    require(config["decision"] == decision and config["main_limits"] == study["limits_per_language"],
            "Preserve threshold, refusal policy and limits")
    lang = config["language"]
    require(config["prompts"] == prior["prompts"][lang] and config["assets"] == study["assets"]["path"]
            and config["baseline_config"] == study["baseline"]["path"]
            and config["baseline_prompts"] == study["initial_prompts"][lang]["path"],
            "Preserve exact baseline/Judge prompt and model separation")
    selected = selection["languages"][lang]["selected"]
    require(len(rows) == len(selected) == 20 and
            [(r["record_id"], r["document_group_id"]) for r in rows] ==
            [(r["record_id"], r["document_group_id"]) for r in selected] and
            len({r["document_group_id"] for r in rows}) == 20,
            "Preserve all preselected IDs/groups/order without refill")
    require(selection["development_qa_sha256"][qa_path.relative_to(root).as_posix()] == file_hash(qa_path),
            "Development source changed")
