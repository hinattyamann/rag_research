"""Two bounded artificial CLI checks; never read reserved research QA."""

import argparse
import json
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True)
    args = p.parse_args()
    global_config = json.loads(args.config.read_text())
    sys.path[:0] = [str(Path(global_config["helper_dir"]) / "legacy"), str(Path(global_config["checkout"]) / "src")]
    from common import load_config, read, sha, write
    from review import META, run_job

    from rag_research.experiments.bilingual_semantics import (
        blank_unit_annotations,
        make_unit_packet,
        validate_unit_annotations,
    )
    from rag_research.experiments.quality import blank_annotations, validate_annotations

    state = Path(global_config["state_dir"]) / "artificial-cli-preflight"
    if (state / "result.json").exists():
        raise ValueError("Do not rerun a completed artificial CLI preflight")
    original = Path(global_config["source_repo"]) / ".tools/fixed-v23-automation-v1/audits/citation-controller-revision7/synthetic-packets.json"
    packets = read(original)
    cfg = load_config(Path(global_config["batches"][0]))
    cfg.update(state_dir=str(state), maximum_cli_invocations=2, maximum_cli_job_seconds=600)
    records = []
    for language, kind in [("en", "units"), ("ja", "quality")]:
        packet = make_unit_packet(packets[language], language) if kind == "units" else packets[language]
        blank = blank_unit_annotations(packet) if kind == "units" else blank_annotations(packet)
        annotations = [{k: v for k, v in a.items() if k not in META} for a in blank["annotations"]]
        payload = {"cohort": "artificial-extension-preflight", "language": language, "kind": kind,
            "full_packet_sha256": packet["packet_sha256"], "cases": packet["cases"],
            "rubric_or_instructions": packet.get("rubric", packet.get("instructions")), "annotations": annotations}
        job = state / "jobs" / f"synthetic-{language}-{kind}-citations-v3" / "attempt-0"
        result, provenance = run_job(cfg, job, payload, annotations[0], kind)
        rows = []
        for row in result["annotations"]:
            row.update(elapsed_seconds=provenance["elapsed_seconds"] / len(annotations),
                confirmed_at_utc=provenance["finished_at_utc"], annotator="Codex AI artificial transport preflight")
            if kind == "units":
                row.update(human_reviewed=False, exact_model_identifier=None, history_isolated=False)
            rows.append(row)
        (validate_unit_annotations if kind == "units" else validate_annotations)(packet, {**blank, "annotations": rows})
        events = []
        for line in (job / "invocation.log").read_text().splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
        if any(e.get("item", {}).get("type") in {"command_execution", "mcp_tool_call", "web_search"} for e in events):
            raise ValueError("Anonymous annotation preflight invoked a tool")
        records.append({"language": language, "kind": kind, "annotations_validated": len(rows),
            "elapsed_seconds": provenance["elapsed_seconds"], "provenance_sha256": sha(job / "provenance.json"),
            "tool_calls": 0})
        write(state / "result.json", {"research_native_calls": 0, "artificial_cli_invocations": len(records),
                                      "all_validated": len(records) == 2, "jobs": records})
        print(json.dumps(records[-1]), flush=True)


if __name__ == "__main__":
    main()
