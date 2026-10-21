"""Prepare known/synthetic Development contrasts before any new model result."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.evaluation.sentence_claims import extract_sentence_units  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402

SCENARIOS = [
    ("actor", "委員会は2020年に閉会した。委員会は新しい支援制度を承認しなかった。2022年、市長がその制度を承認した。", [
        ("市長は2022年に新しい支援制度を承認した。", "supported"),
        ("委員会は新しい支援制度を承認した。", "contradicted"),
        ("市長は東京の会議室で制度を承認した。", "not_supported")]),
    ("count", "朝日クラブの監督は就任後の最初の2年間で大会に2回優勝した。3年目にさらに優勝し、通算優勝回数は3回となった。", [
        ("監督は大会に通算3回優勝した。", "supported"),
        ("監督は大会に通算2回優勝した。", "contradicted"),
        ("監督は選手時代にも大会に優勝した。", "not_supported")]),
    ("compound", "青葉図書館は1990年7月7日の午前8時に開館した。同日の開館式は午前10時に始まった。", [
        ("青葉図書館は1990年7月7日の午前8時に開館した。", "supported"),
        ("青葉図書館は1990年7月7日の午前10時に開館した。", "contradicted"),
        ("青葉図書館は1990年7月7日に開館し、最初の館長は山田太郎だった。", "not_supported")]),
    ("qualification", "青山村の名前の由来は不明である。一つの説では、近くの山が青く見えることに由来するとされる。", [
        ("一つの説では、青山村の名前は近くの山が青く見えることに由来するとされる。", "supported"),
        ("青山村の名前の由来は確定している。", "contradicted"),
        ("青山村の名前は近くの山が青く見えることに由来する。", "not_supported")]),
    ("table", "図書館の開館状態の表。列の順序は、改修前、改修中、改修後。対応する値は、開館、休館、開館。", [
        ("図書館は改修後に開館している。", "supported"),
        ("図書館は改修後に休館している。", "contradicted"),
        ("図書館の改修費用は500万円だった。", "not_supported")]),
]


def prepare():
    old = ROOT / "data/runs/calibration/phase11-gpu-twenty-v2"
    audit_path = old / "semantic_audit_v2.json"
    audit = json.loads(audit_path.read_text())
    cases, bindings = [], {}
    for name, folder in (("known-council", "323bf35882bc45a96feb3e1d"),
                         ("known-zidane", "31e646aa96013a84580e692c")):
        path = old / "internal" / folder / "trace.json"
        trace = json.loads(path.read_text())
        annotations = [r for r in audit["claims"] if r["record_id"] == trace["record_id"]]
        cases.append({"id": name, "language": "en", "scope": "known_used_calibration",
                      **{k: trace[k] for k in ("question", "answer", "documents")},
                      "claims": extract_sentence_units(trace["answer"])["claims"],
                      "expected": {r["claim_id"]: None if r["ambiguous_scope"] else r["expected_label"] for r in annotations},
                      "expected_reasons": {r["claim_id"]: r["reason"] for r in annotations},
                      "critical_claim_ids": ["c4"] if name == "known-council" else ["c1"],
                      "original_record_id": trace["record_id"], "source_trace_sha256": file_hash(path)})
        bindings[path.relative_to(ROOT).as_posix()] = file_hash(path)
    path = ROOT / "configs/measurement_diagnostics.json"
    for item in json.loads(path.read_text())["judge"]:
        cases.append({"id": "en-" + item["id"], "language": "en", "scope": "synthetic_development",
                      "question": item["question"], "answer": item["claim"], "documents": item["documents"],
                      "claims": [{"claim_id": "c1", "text": item["claim"]}], "expected": {"c1": item["expected"]},
                      "critical_claim_ids": [], "expected_reasons": {"c1": "Pre-existing explicit synthetic contrast; label preserved."}})
    bindings[path.relative_to(ROOT).as_posix()] = file_hash(path)
    for family, text, claims in SCENARIOS:
        for index, (claim, expected) in enumerate(claims, 1):
            cases.append({"id": f"ja-{family}-{index}", "language": "ja", "scope": "synthetic_development",
                          "question": "この資料が示す事実は何か。", "answer": claim,
                          "documents": [{"passage_id": "d1", "title": "人工診断資料", "text": text}],
                          "claims": [{"claim_id": "c1", "text": claim}], "expected": {"c1": expected},
                          "critical_claim_ids": [], "expected_reasons": {"c1": "本文の主体/関係・時期・範囲・数量・限定と全詳細を比較。明示の不一致は矛盾、欠ける詳細は支持不足。"}})
    value = {"schema_version": 1, "purpose": "phase11-known-bilingual-semantic-diagnostics",
             "status": "development_only_not_final_evaluation", "created_at_utc": datetime.now(UTC).isoformat(),
             "orders": ["original", "reversed"], "cases": cases, "source_sha256": bindings,
             "expected_annotations": {"actual_author": "Codex AI", "human_reviewed": False,
                 "known_trace_expected_source": audit_path.relative_to(ROOT).as_posix(),
                 "known_trace_expected_sha256": file_hash(audit_path)},
             "gate": {"stop_on_task_error": True, "stop_after_critical_failure": True, "critical_all_exact": True,
                      "synthetic_min_accuracy_per_language": .9, "synthetic_max_false_support": 0},
             "max_completion_attempts": len(cases) * 2, "phase12_allowed": False}
    output = ROOT / "configs/phase11_semantic_diagnostics_v1.json"
    config_path = ROOT / "configs/phase11_semantic_candidate_v1.yaml"
    if output.exists() or config_path.exists():
        raise ValueError("Preserve existing diagnostic inputs and use a new version")
    source = yaml.safe_load((ROOT / "configs/phase11_bilingual_connection_en_v2.yaml").read_text())
    keys = ("auxiliary_runtime", "tasks", "trials", "decision", "errors", "output_constraints",
            "auxiliary_model_manifest", "sampling", "execution")
    config = {k: source[k] for k in keys}
    config.update(schema_version=1, purpose="phase11-bilingual-semantic-candidate", status="candidate_not_frozen",
                  study_version="semantic-known-v1", diagnostics=output.relative_to(ROOT).as_posix(),
                  prompts={lang: f"configs/phase11_bilingual_order_prompts_{lang}_v1.yaml" for lang in ("en", "ja")},
                  phase12_allowed=False)
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
    return {"critical_cases": 2, "synthetic_cases": len(cases) - 2, "max_calls": value["max_completion_attempts"]}


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(prepare()))
