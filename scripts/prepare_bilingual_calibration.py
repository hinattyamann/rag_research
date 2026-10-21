"""Preregister held-out Calibration only after reverified complete main evidence."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_research.experiments.calibration_protocol import create  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("main-inputs", "main-certificate", "reservation", "reservation-policy", "rules", "output-dir"):
        parser.add_argument("--" + field, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(create(args.main_inputs, args.main_certificate, args.reservation,
        args.reservation_policy, args.rules, args.output_dir), ensure_ascii=False))
