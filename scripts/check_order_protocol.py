"""Check Phase 7 assets and real token budgets without any completion calls."""

import argparse
import hashlib
import json
import random
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import yaml  # noqa: E402

from rag_research.generation.artifacts import model_identity  # noqa: E402
from rag_research.generation.config import GenerationConfig  # noqa: E402
from rag_research.generation.context import literal_json  # noqa: E402
from rag_research.generation.local import LocalServer  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402

FIELDS = {
    "extract_claims": ["answer"],
    "verify_claims": ["question", "answer", "claims", "documents"],
    "rewrite_answer": ["question", "answer", "documents"],
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_protocol(config_path):
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    require(config["schema_version"] == 1, "Unsupported protocol schema")
    require(config["purpose"] == "phase7-development-protocol", "Not a Phase 7 protocol")
    require(config["data"]["split"] == "development", "Preflight only reads Development")
    require(config["data"]["answerable_only"] is True, "Preflight requires Answerable QA")
    require(
        config["data"]["qa_path"]
        == "data/processed/clapnq/c508d78-split-v1/development.jsonl",
        "Unexpected Development source path",
    )
    trials = config["trials"]
    for key in (
        "repeated_prompt_result_cache",
        "regenerate_claims_per_trial",
        "regenerate_answer_per_trial",
        "repack_or_truncate_per_trial",
    ):
        require(trials[key] is False, f"Comparison would change inputs or skip trials: {key}")
    require(trials["same_order_total_trials"] == 5, "Initial protocol expects five repeats")
    require(trials["share_original_first_trial"] is True, "Initial trial must be shared")
    require(config["errors"]["automatic_retries"] == 0, "Initial protocol has no retries")
    require(config["decision"]["no_claims_score"] is None, "No-claim score must be null")
    require(config["rewrite"]["include_judge_feedback"] is False, "Feedback changes repair")
    require(config["rewrite"]["retrieve_again"] is False, "Preflight repair uses fixed evidence")
    require(config["rewrite"]["reuse_one_candidate_across_trials"] is True, "Repair must be fixed")
    require(config["quality"]["llm_labels_are_final"] is False, "Quality needs manual confirmation")
    prompt_path = ROOT / config["prompts"]
    require(prompt_path.resolve().is_relative_to(ROOT), "Prompt path escapes repository")
    prompts = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
    require(prompts["schema_version"] == 1, "Unsupported prompt schema")
    require(set(prompts["tasks"]) == set(FIELDS), "Prompt task set differs")
    for task, fields in FIELDS.items():
        spec = prompts["tasks"][task]
        require(spec["input_fields"] == fields, f"Unexpected model fields: {task}")
        require(isinstance(spec["system"], str) and spec["system"].strip(), "Empty prompt")
        GenerationConfig(
            **config["auxiliary_runtime"],
            max_output_tokens=config["tasks"][task]["max_output_tokens"],
        )
    return config, prompts, prompt_path


def build_messages(prompts, task, payload):
    require(task in FIELDS, "Unknown task")
    require(set(payload) == set(FIELDS[task]), "Missing or forbidden model input field")
    require(isinstance(payload["answer"], str), "Answer must be text")
    if "question" in payload:
        require(isinstance(payload["question"], str), "Question must be text")
    if "claims" in payload:
        require(isinstance(payload["claims"], list), "Claims must be a list")
        for index, claim in enumerate(payload["claims"], start=1):
            require(set(claim) == {"claim_id", "text"}, "Unexpected claim fields")
            require(claim["claim_id"] == f"c{index}", "Claim IDs must be consecutive")
            require(isinstance(claim["text"], str), "Claim text must be text")
    if "documents" in payload:
        require(isinstance(payload["documents"], list), "Documents must be a list")
        for document in payload["documents"]:
            require(set(document) == {"passage_id", "title", "text"}, "Unexpected evidence fields")
            require(all(isinstance(value, str) for value in document.values()), "Invalid document")
    return [
        {"role": "system", "content": prompts["tasks"][task]["system"]},
        {"role": "user", "content": "Input JSON:\n" + literal_json(payload)},
    ]


def check_budgets(config_path, output):
    config, prompts, prompt_path = load_protocol(config_path)
    require(output.resolve().is_relative_to(ROOT), "Output must stay in the repository")
    qa_path = ROOT / config["data"]["qa_path"]
    qa = {}
    for line in qa_path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        require(record["research_split"] == "development", "Non-Development QA found")
        qa[record["record_id"]] = record
    for identifier in config["data"]["protocol_example_ids"]:
        require(qa[identifier]["is_answerable"] is True, "Rubric example is not Answerable")
    baseline_path = ROOT / config["data"]["preflight_baseline_answers"]
    require(
        baseline_path.resolve()
        == (ROOT / "data/runs/phase6/development-five-v1/answers.jsonl").resolve(),
        "Preflight must use the existing Development smoke run",
    )
    smoke = json.loads((ROOT / "data/manifests/phase6_smoke_report.json").read_text("utf-8"))
    require(file_hash(baseline_path) == smoke["artifacts"]["answers_sha256"], "Baseline changed")
    records = [json.loads(line) for line in baseline_path.read_text("utf-8").splitlines()]
    records = [record for record in records if qa[record["record_id"]]["is_answerable"]]
    require(len(records) == 3 and all(r["status"] == "ok" for r in records), "Probe source differs")
    identity = json.loads((ROOT / config["identity_manifest"]).read_text("utf-8"))
    require(identity["model"] == model_identity(), "Model identity differs")
    output.mkdir(parents=True, exist_ok=False)
    settings = GenerationConfig(**config["auxiliary_runtime"], max_output_tokens=512)
    rows = []
    with LocalServer(settings, output / "server.log") as server:
        for record in records:
            original = record["used_context"]
            orders = [original, list(reversed(original))]
            rng = random.Random(config["trials"]["shuffle_seed"])
            for _ in range(3):
                shuffled = list(original)
                rng.shuffle(shuffled)
                orders.append(shuffled)
            for task, fields in FIELDS.items():
                for index, documents in enumerate(orders if task == "verify_claims" else [original]):
                    require(
                        sorted(literal_json(d) for d in documents)
                        == sorted(literal_json(d) for d in original),
                        "Order probe changed evidence",
                    )
                    values = {
                        "question": record["question"],
                        "answer": record["answer"],
                        "claims": [{"claim_id": "c1", "text": record["answer"]}],
                        "documents": documents,
                    }
                    messages = build_messages(prompts, task, {key: values[key] for key in fields})
                    rendered = server.client.render(messages)
                    count = len(server.client.tokenize(rendered, special=True))
                    reserve = config["tasks"][task]["max_output_tokens"]
                    rows.append(
                        {
                            "record_id": record["record_id"],
                            "task": task,
                            "order_index": index,
                            "input_tokens": count,
                            "reserved_output_tokens": reserve,
                            "required_total_tokens": count + reserve,
                            "fits_4096": count + reserve <= 4096,
                            "fits_8192": count + reserve <= 8192,
                            "rendered_prompt_sha256": hashlib.sha256(
                                rendered.encode("utf-8")
                            ).hexdigest(),
                        }
                    )
        require(server.client.completion_attempts == 0, "Preflight must not generate outputs")
        actual_context = server.report()["server_context_tokens"]
        require(actual_context == settings.context_tokens, "Runtime context differs from config")
    report = {
        "schema_version": 1,
        "purpose": "phase7-token-budget-only-not-judge-validation",
        "study_version": config["study_version"],
        "model": identity["model"],
        "runtime_tag": identity["runtime"]["tag"],
        "settings": asdict(settings),
        "config_sha256": file_hash(config_path),
        "prompts_sha256": file_hash(prompt_path),
        "checker_sha256": file_hash(Path(__file__)),
        "baseline_answers_sha256": file_hash(baseline_path),
        "development_qa_sha256": file_hash(qa_path),
        "claim_probe_kind": "whole_answer_as_one_placeholder_claim_not_extracted_claims",
        "limit": "Real claim lengths and judge quality are untested; check actual Phase 8 inputs.",
        "records": len(records),
        "input_probes": len(rows),
        "completion_attempts": 0,
        "all_fit_8192": all(row["fits_8192"] for row in rows),
        "overflow_4096": sum(not row["fits_4096"] for row in rows),
        "maximum_required_tokens": max(row["required_total_tokens"] for row in rows),
        "server_context_tokens": actual_context,
        "rows": rows,
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    require(report["all_fit_8192"], "Pilot input exceeded 8192; inspect saved report")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/order_pilot.yaml")
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "data/runs/phase7/protocol-preflight-v1"
    )
    args = parser.parse_args()
    report = check_budgets(args.config, args.output_dir)
    keys = (
        "records", "input_probes", "completion_attempts", "all_fit_8192",
        "overflow_4096", "maximum_required_tokens", "server_context_tokens",
    )
    print(json.dumps({key: report[key] for key in keys}))


if __name__ == "__main__":
    main()
