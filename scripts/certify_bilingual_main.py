"""Save verified full main Development evidence; never start Calibration or a model."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.bilingual_certification import certify_main  # noqa: E402
from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.storage import checkpoint, run_lock  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    parent = ROOT / "data/runs/development_certification"
    require(output.is_relative_to(parent) and output != parent and not output.exists(),
            "Use a new main certification output; preserve prior certificates")
    value = certify_main(args.inputs)
    with run_lock(output):
        require({p.name for p in output.iterdir()} == {".run.lock"}, "Certificate output already used")
        saved = checkpoint(output / "certificate.private.json", value)
    print(json.dumps({"status": value["status"], "certificate_sha256": saved["result_sha256"],
                      "new_model_calls": 0, "calibration_execution_allowed": False, "gate11_passed": False}))
