"""Prepare all prior scored GPU traces and mandatory old Development errors, without inference."""

import argparse
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.evaluation.sentence_claims import extract_sentence_units  # noqa: E402
from rag_research.experiments.frozen_trace import digest, require  # noqa: E402
from rag_research.experiments.protocol import ROOT  # noqa: E402
from rag_research.experiments.storage import read_json, write_json  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402

AUDIT = "data/runs/calibration/phase11-gpu-twenty-v2/semantic_audit_v2.json"
GPU = "data/runs/calibration/phase11-gpu-twenty-v2/internal"
EXTRA = {
    "armistice": "data/runs/pilot/phase10-twenty-v1/internal/d48d108ab352727a3d42c368/trace.json",
    "warm-front": "data/runs/pilot/phase10-five-v2/internal/312bfc698c74563d9816e85b/trace.json",
    "tar-heels": "data/runs/pilot/phase10-five-v2/internal/252ca3b319d8a7a35e065a3d/trace.json",
}
NEW_EXPECTED = {
    "armistice": [
        ("contradicted", "調印は5時、発効は11時と明記。11時調印という追加詳細は矛盾。"),
        ("contradicted", "根拠は5時の調印と11時の発効を区別し、11時調印という明示引用は誤り。"),
        ("supported", "質問の命題は1918年11月11日の調印。誤った追加時刻を含まないtrueという結論は支持。"),
    ],
    "warm-front": [
        ("supported", "先行する雲と、接近に伴い降雨が増加することを本文が支持。"),
        ("contradicted", "表は通過中に持続的な中程度の雨、通過後には次第に止む弱い霧雨。通常通過後も持続するという列の転記が矛盾。"),
    ],
    "tar-heels": [
        ("not_supported", "正確な語源は不明で、輸出品由来はfolkloreの説。無限定の確定した起源は支持されない。"),
        ("not_supported", "兵が隊列に固執した伝説と、丘を保てず笑われた逸話は別々に記載。前者の句が後者の逸話から生じたという因果関係は支持されない。"),
        ("supported", "侮蔑語から再利用され、1865年頃から誇りとして使われたと本文に明記。"),
    ],
}


def prepare(prerequisite_report):
    report_path = Path(prerequisite_report).resolve()
    require(report_path.is_relative_to(ROOT), "Prerequisite escapes repository")
    prerequisite = read_json(report_path)
    require(prerequisite["diagnostic_gate_passed"] is True and prerequisite["completion_attempts_recorded"] == 128,
            "Complete passing bilingual source-reading diagnostics first")
    expected_path = ROOT / "configs/phase11_known_trace_expected_v1.json"
    plan_path = ROOT / "configs/phase11_known_trace_regression_v1.json"
    require(not expected_path.exists() and not plan_path.exists(), "Preserve existing preregistration")
    audit = read_json(ROOT / AUDIT)
    annotations = deepcopy(audit["claims"])
    source_sha = {AUDIT: file_hash(ROOT / AUDIT)}
    cases, refusals = [], []
    old_report = read_json(ROOT / GPU / "report.private.json")
    for row in old_report["records"]:
        trace = row["trace"]
        path = ROOT / GPU / digest(trace["record_id"])[:24] / "trace.json"
        require(read_json(path) == trace, "Old trace/report differ")
        source_sha[path.relative_to(ROOT).as_posix()] = file_hash(path)
        claims = extract_sentence_units(trace["answer"])["claims"]
        old = [a for a in annotations if a["record_id"] == trace["record_id"]]
        require({a["claim_id"] for a in old} == {c["claim_id"] for c in claims}, "Old audit units differ")
        if not claims:
            refusals.append({"record_id": trace["record_id"], "trace_path": path.relative_to(ROOT).as_posix(),
                             "fixed_unit_count": 0, "score": None, "scope": "separate_bare_refusal_fallback_validation"})
            continue
        cases.append(make_case("known-gpu-" + digest(trace["record_id"])[:12], trace, claims, old,
                               "known_used_calibration", source_sha[path.relative_to(ROOT).as_posix()]))
    for name, path in EXTRA.items():
        trace = read_json(ROOT / path)
        source_sha[path] = file_hash(ROOT / path)
        claims = extract_sentence_units(trace["answer"])["claims"]
        require(len(claims) == len(NEW_EXPECTED[name]), "Expected source unit count changed")
        rows = [{"record_id": trace["record_id"], "claim_id": c["claim_id"], "expected_label": label,
                 "ambiguous_scope": False, "reason": reason, "evidence": [],
                 "annotation_source": "Codex AI source-only preregistration before candidate output; whole original trace retained"}
                for c, (label, reason) in zip(claims, NEW_EXPECTED[name], strict=True)]
        annotations.extend(rows)
        cases.append(make_case("known-" + name, trace, claims, rows, "known_used_development", file_hash(ROOT / path)))
    require(len(cases) == 15 and len(refusals) == 8 and sum(len(c["claims"]) for c in cases) == 42,
            "Preserve all 12 scored/8 refusal GPU QA plus mandatory 3 old Development traces")
    expected = {"schema_version": 1, "purpose": "phase11-known-trace-regression-expected-before-candidate",
        "created_at_utc": datetime.now(UTC).isoformat(), "actual_assessor": "Codex AI in same development thread",
        "human_reviewed": False, "exact_model_identifier_available": False, "history_isolated": False,
        "preserved_audit_path": AUDIT, "preserved_audit_sha256": file_hash(ROOT / AUDIT), "claims": annotations,
        "limitations": ["AI source-based annotations, not human ground truth", "old output/history known; no claim of blind independent annotation",
                        "new 8 unit labels fixed before candidate outputs for those traces; existing 34 labels unchanged"]}
    write_json(expected_path, expected)
    source_sha[expected_path.relative_to(ROOT).as_posix()] = file_hash(expected_path)
    value = {"schema_version": 1, "purpose": "phase11-known-trace-semantic-regression", "phase12_allowed": False,
        "orders": ["original", "reversed"], "verification_mode": "source-reading-v1", "cases": cases,
        "source_sha256": source_sha, "bare_refusal_cases_retained_separately": refusals,
        "prerequisite": {"report_path": report_path.relative_to(ROOT).as_posix(), "sha256": file_hash(report_path)},
        "expected_annotations": {"human_reviewed": False, "known_trace_expected_source": expected_path.relative_to(ROOT).as_posix(),
                                 "known_trace_expected_sha256": file_hash(expected_path)},
        "gate": {"stop_on_task_error": True, "stop_after_critical_failure": True, "critical_all_exact": True,
                 "known_min_accuracy": .9, "known_min_supported_accuracy": .9, "known_max_false_support": 0},
        "max_completion_attempts": 2 * sum(1 + len(c["claims"]) for c in cases)}
    write_json(plan_path, value)
    return {"qa": len(cases), "fixed_units": 42, "ambiguous_units_preserved": sum(a["ambiguous_scope"] for a in annotations),
            "bare_refusals_retained_separately": len(refusals), "max_calls": value["max_completion_attempts"]}


def make_case(name, trace, claims, annotations, scope, sha):
    return {"id": name, "language": "en", "scope": scope, "original_record_id": trace["record_id"],
            "source_trace_sha256": sha, **{k: trace[k] for k in ("question", "answer", "documents")}, "claims": claims,
            "expected": {a["claim_id"]: None if a["ambiguous_scope"] else a["expected_label"] for a in annotations},
            "expected_reasons": {a["claim_id"]: a["reason"] for a in annotations},
            "critical_claim_ids": [a["claim_id"] for a in annotations if not a["ambiguous_scope"] and
                                    a["expected_label"] in {"contradicted", "not_supported"}]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prerequisite-report", type=Path, required=True)
    print(prepare(parser.parse_args().prerequisite_report))
