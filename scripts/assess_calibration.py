"""Grade immutable public Calibration packets while internal inference continues."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.storage import read_json, run_lock, verify_checkpoint  # noqa: E402
from rag_research.pilot.assessment import open_candidate, save_candidate  # noqa: E402
from rag_research.retrieval.common import file_hash  # noqa: E402


def assess(run, packet, action, decision=None):
    require(run.is_relative_to(ROOT / "data/runs/calibration") and type(packet) is int and packet > 0,
            "Unexpected Calibration packet")
    require(action in {"open", "save"}, "Unknown assessment action")
    bundle = run / "quality" / f"ready-{packet:03d}"
    exported = read_json(bundle / "export_manifest.json")
    verify_checkpoint(exported)
    require(exported["annotation_kind"] == "AI" and exported["human_reviewed"] is False and
            exported["mapping_sha256"] == file_hash(bundle / "mapping.private.json") and
            exported["packet_sha256"] == read_json(bundle / "packet.json")["packet_sha256"],
            "Public packet provenance differs")
    assessment = run / "quality/assessments" / f"packet-{packet:03d}"
    # A packet is immutable once published. Its assessment has a separate lock,
    # so the inference process may keep the parent run lock without blocking grading.
    with run_lock(assessment):
        if action == "open":
            return open_candidate(bundle, assessment)
        require(decision is not None, "A saved AI decision is required")
        return save_candidate(bundle, assessment, decision)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["open", "save"])
    parser.add_argument("--packet", type=int, required=True)
    parser.add_argument("--decision", type=Path)
    parser.add_argument("--run", type=Path, default=ROOT / "data/runs/calibration/phase11-cpu-five-v1")
    args = parser.parse_args()
    print(json.dumps(assess(args.run.resolve(), args.packet, args.action, args.decision),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
