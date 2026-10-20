"""Preselect Calibration QA and bind a provisional, explicitly unfrozen protocol."""

import hashlib
import json

import yaml

from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.protocol import ROOT, load_protocol
from rag_research.experiments.storage import checkpoint, read_json, verify_checkpoint
from rag_research.pilot.selection import title_key
from rag_research.retrieval.common import file_hash

QA_PATH = "data/processed/clapnq/c508d78-split-v1/calibration.jsonl"
OPEN_ITEMS = {
    "semantic_validity": "時期・限定・不確実性・正しい結論の誤棄却をCalibrationで確認する",
    "refusal_fallback": "単独拒否と採点不能時の扱いを根拠付きで確定する",
    "fresh_parser_validation": "引用重複修正後の処理を新規Model出力で確認する",
    "external_quality": "外部AI採点のセッション・Model識別子・保存方法を確定する",
    "runtime_and_scale": "本番環境の時間と有効比較数から対象数・反復数を決定する",
    "analysis_and_threshold": "閾値・分母・欠測・統計・条件別分析を事前に固定する",
}


def local_path(name):
    path = (ROOT / name).resolve()
    require(path.is_relative_to(ROOT), "Path escapes repository")
    return path


def load_config(path):
    config = yaml.safe_load(path.read_text("utf-8"))
    require(config["schema_version"] == 1 and config["purpose"] == "phase11-calibration",
            "Not a Phase 11 Calibration config")
    require(config["qa_path"] == QA_PATH, "Calibration only; do not open Evaluation")
    require(type(config["count"]) is int and config["count"] > 0, "Invalid Calibration count")
    require(type(config["selection_seed"]) is int and config["selection_seed"] >= 0,
            "Invalid Calibration seed")
    require(config["automatic_retries"] == 0 and config["replace_failed_questions"] is False
            and config["human_reviewed"] is False, "Retries/replacement/human provenance changed")
    require(config["status"] == "candidate_not_frozen" and config["phase12_allowed"] is False,
            "This entry point cannot freeze or run Evaluation")
    protocol, _, _ = load_protocol(local_path(config["internal_protocol"]), split="calibration")
    require(protocol["baseline_config"] == config["baseline_config"], "Baseline configs differ")
    require(config["baseline_prompts"] == "configs/prompts.yaml", "Baseline prompt must stay fixed")
    require(protocol["decision"]["threshold"] == 0.7,
            "Initial Calibration candidate retains tau=0.7; revision needs a new version")
    rules = config["health_gate"]
    require(type(rules["after_questions"]) is int and 0 < rules["after_questions"] <= config["count"],
            "Invalid health checkpoint")
    require(type(rules["minimum_complete_scorable_questions"]) is int and
            0 < rules["minimum_complete_scorable_questions"] <= rules["after_questions"],
            "Invalid minimum comparable count")
    require(type(rules["maximum_judge_error_fraction"]) in {int, float} and
            0 <= rules["maximum_judge_error_fraction"] <= 1 and
            rules["stop_on_input_overflow"] is True, "Invalid health failure policy")
    return config


def select_calibration(rows, count, seed):
    require(type(count) is int and count > 0 and type(seed) is int and seed >= 0,
            "Invalid Calibration selection")
    require(all(r["research_split"] == "calibration" for r in rows), "Calibration only")
    require(len({r["record_id"] for r in rows}) == len(rows), "Duplicate Calibration ID")
    require(all(type(r["is_answerable"]) is bool for r in rows), "Invalid Answerable flag")
    eligible = sorted((r for r in rows if r["is_answerable"]), key=lambda r:
                      hashlib.sha256(f"{seed}:{r['record_id']}".encode()).hexdigest())
    chosen, seen = [], set()
    for row in eligible:
        key = title_key(row["source_title"])
        if key not in seen:
            chosen.append(row)
            seen.add(key)
        if len(chosen) == count:
            break
    require(len(chosen) == count, "Not enough Calibration titles")
    return chosen


def immutable_checkpoint(path, value):
    if path.exists():
        saved = read_json(path)
        verify_checkpoint(saved)
        require({k: v for k, v in saved.items() if k != "result_sha256"} == value,
                "Prepared conditions changed; preserve this run and choose a new version")
        return saved
    path.parent.mkdir(parents=True, exist_ok=True)
    return checkpoint(path, value)


def prepare(config_path, config, selection_path, output):
    qa_path = local_path(config["qa_path"])
    rows = [json.loads(line) for line in qa_path.read_text("utf-8").splitlines()]
    preselected = config.get("preselected_manifest")
    if preselected:
        require(selection_path.resolve() == local_path(preselected), "Use the original preselection")
        selection = read_json(selection_path)
        verify_checkpoint(selection)
        require(selection["purpose"] == "phase11-gpu-calibration-preselection-not-executed"
                and selection["count"] == config["count"]
                and selection["selection_seed"] == config["selection_seed"]
                and selection["qa_sha256"] == file_hash(qa_path), "GPU preselection differs")
        eligible = [r for r in rows if r["record_id"] not in selection["excluded_ids"]
                    and title_key(r["source_title"]) not in selection["excluded_title_keys"]]
        chosen = select_calibration(eligible, config["count"], config["selection_seed"])
        require(selection["records"] == [{k: r[k] for k in ("record_id", "question", "source_title")}
                                          for r in chosen], "GPU selected records changed")
    else:
        chosen = select_calibration(rows, config["count"], config["selection_seed"])
    split_path = ROOT / "data/manifests/clapnq_split_manifest.json"
    split = read_json(split_path)
    require(all(split["group_assignments"][title_key(r["source_title"])] == "calibration"
                for r in rows), "Calibration title assignment differs from fixed Split")
    if preselected:
        require(selection["split_manifest_sha256"] == file_hash(split_path), "Split manifest changed")
    else:
        selection = immutable_checkpoint(selection_path, {
            "schema_version": 1, "purpose": "phase11-calibration-preselected-before-inference",
            "study_version": config["study_version"], "split": "calibration",
            "qa_sha256": file_hash(qa_path), "split_manifest_sha256": file_hash(split_path),
            "count": len(chosen), "selection_seed": config["selection_seed"],
            "selection_rule": "sha256(seed:record_id)_ascending_first_unique_NFC_casefold_title",
            "one_question_per_title": True, "replace_failed_questions": False,
            "retrieval_calibration_previously_used_answerable_questions": 225,
            "records": [{k: r[k] for k in ("record_id", "question", "source_title")} for r in chosen]})
    protocol_path = local_path(config["internal_protocol"])
    protocol, _, prompt_path = load_protocol(protocol_path, split="calibration")
    paths = [config_path, protocol_path, prompt_path, local_path(config["baseline_config"]),
             local_path(config["baseline_prompts"]), local_path(config["quality_protocol"]),
             ROOT / "configs/quality_ai_prompt_v1.txt", ROOT / protocol["identity_manifest"],
             ROOT / protocol["auxiliary_model_manifest"], ROOT / "pyproject.toml", ROOT / "uv.lock",
             ROOT / "scripts/run_calibration.py"]
    # Bind every imported research module; the old Phase 10 raw runs are never resumed here.
    paths.extend(sorted((ROOT / "src/rag_research").rglob("*.py")))
    if "execution" in protocol:
        paths.append(local_path(protocol["execution"]["runtime_spec"]))
    candidate = immutable_checkpoint(output / "candidate_manifest.json", {
        "schema_version": 1, "purpose": "phase11-provisional-conditions-not-final-freeze",
        "status": "candidate_not_frozen", "gate11_passed": False, "phase12_allowed": False,
        "selection_sha256": digest(selection), "config": config,
        "candidate_internal_protocol": protocol,
        "runtime_scope": ("Ubuntu CUDA separately versioned candidate" if "execution" in protocol else
                          "Windows CPU preliminary calibration; Ubuntu/CUDA not implemented"),
        "evaluation_outcomes_opened": False,
        "open_items": OPEN_ITEMS,
        "source_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths}})
    return selection, candidate


def baseline_stage(config, selection, output, max_new_questions=None):
    from rag_research.pilot.baseline import run_baseline

    binding_path = output / "internal/manifest.json"
    if binding_path.exists():
        binding = read_json(binding_path)
        require(binding["selection_sha256"] == digest(selection), "Frozen baseline selection differs")
        for name, key in (("answers.jsonl", "baseline_answers_sha256"),
                          ("run_manifest.json", "baseline_provenance_sha256")):
            require(file_hash(output / "baseline" / name) == binding[key], "Frozen baseline changed")
        return {"status": "frozen_baseline_reused", "additional_completion_attempts": 0}
    return run_baseline(config, selection, output / "baseline", split="calibration",
                        max_new_questions=max_new_questions)


def progress_report(output, candidate):
    """Public counters only: no internal score/decision or candidate-stage mapping."""
    baseline_path = output / "baseline/run_manifest.json"
    baseline = read_json(baseline_path) if baseline_path.exists() else {}
    public_path = output / "progress.json"
    public = read_json(public_path) if public_path.exists() else {}
    return {"purpose": "phase11-readiness-not-final-freeze", "gate11_passed": False,
            "phase12_allowed": False, "candidate_sha256": candidate["result_sha256"],
            "baseline_status": baseline.get("status", "not_started"),
            "baseline_completed": baseline.get("completed_questions", 0),
            "baseline_successful": baseline.get("successful_questions", 0),
            "public_progress": public, "unresolved": candidate["open_items"]}
