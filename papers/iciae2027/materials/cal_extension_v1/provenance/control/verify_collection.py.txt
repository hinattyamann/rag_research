"""Verify the final extension package with standard library only."""

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(value, message):
    if not value:
        raise ValueError(message)


def verify(root):
    manifest = read(root / "artifact_manifest.json")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and
              "__pycache__" not in p.parts and p != root / "artifact_manifest.json"}
    require(actual == set(manifest["files"]), "Root artifact inventory differs")
    for relative, entry in manifest["files"].items():
        path = root / relative
        require(not Path(relative).is_absolute() and ".." not in Path(relative).parts and
                path.resolve().is_relative_to(root.resolve()) and not path.is_symlink(), "Escaping artifact path")
        data = path.read_bytes()
        require(len(data) == entry["bytes"] and hashlib.sha256(data).hexdigest() == entry["sha256"], "Root artifact hash differs")
    complete = read(root / "completion.json")
    plan = read(root / "plan.json")
    require(plan["planned_qa"] == complete["planned_qa"] == 120 and plan["planned_per_language"] == 60,
            "Plan size changed")
    require(plan["native_request_retries"] == 0 and plan["outcome_dependent_stopping"] is False and
            plan["api_billing_allowed"] is False, "Research constraints changed")
    for language in ["en", "ja"]:
        selection = plan["source_selection"][language]["selected"]
        require(len(selection) == len({q["record_id"] for q in selection}) ==
                len({q["document_group_id"] for q in selection}) == 60, "Incomplete source reservation")
    qa = []
    child_results = {}
    for batch in complete["completed_batches"]:
        require(batch in ["batch_01", "batch_02", "batch_03"], "Unknown batch")
        result = subprocess.run([sys.executable, "-I", str(root / batch / "verify_materials.py"), "--audit-open"],
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}, capture_output=True, text=True, timeout=120)
        require(result.returncode == 0, "Child package verification failed: " + result.stderr[-500:])
        child_results[batch] = json.loads(result.stdout)
        qa.extend(read(p) for p in sorted((root / batch / "inputs").glob("*.json")))
    require(len(qa) == complete["included_selected_qa"] and len({q["record_id"] for q in qa}) == len(qa),
            "Missing or duplicate extension QA")
    require(complete["uncollected_or_unsealed_qa"] == 120 - len(qa), "Uncollected state imputed")
    require(not set(plan["old_main_cal_selected_ids"]).intersection(q["record_id"] for q in qa), "Old QA mixed into extension")
    pooled = read(root / "pooled_new_extension.json")
    require(pooled["included_selected_qa"] == len(qa) and pooled["completed_batches"] == complete["completed_batches"],
            "Pooled/batch coverage mismatch")
    counts = {}
    for language in ["en", "ja"]:
        selected = [q for q in qa if q["language"] == language]
        groups = {q["document_group_id"] for q in selected}
        require(len(groups) == len(selected), "Repeated group across batches")
        allowed = {x["record_id"] for x in plan["source_selection"][language]["selected"]}
        require({q["record_id"] for q in selected} <= allowed, "Unselected extension QA")
        good = [q for q in selected if q["statistical_comparison"]["comparable"]]
        counts[language] = {"selected": len(selected), "comparable": len(good)}
        if selected:
            stat = pooled["statistics"]["languages"][language]
            require(stat["selected_qa_count"] == len(selected) and stat["comparable_qa_count"] == len(good), "Pooled denominator mismatch")
            mean = sum(q["statistical_comparison"]["increment"] for q in good) / len(good) if good else None
            require(mean is stat["mean_increment"] if mean is None else math.isclose(mean, stat["mean_increment"], abs_tol=1e-12), "Pooled increment mismatch")
    return {"status": "passed", "planned_qa": 120, "included_selected_qa": len(qa),
            "uncollected_or_unsealed_qa": 120 - len(qa), "languages": counts, "batches": child_results,
            "source_run_required": False, "network_or_auth_required": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-open", action="store_true")
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent
    if args.audit_open:
        def audit(event, values):
            if event == "open" and isinstance(values[0], (str, bytes)):
                path = Path(values[0].decode() if isinstance(values[0], bytes) else values[0]).resolve()
                require(path.is_relative_to(directory), "Root verifier accessed outside package")
            require(not event.startswith("socket."), "Root verifier attempted network access")
        sys.addaudithook(audit)
    print(json.dumps(verify(directory), ensure_ascii=False, indent=2))
