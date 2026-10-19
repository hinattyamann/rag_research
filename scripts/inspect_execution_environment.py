"""Record the local host/GPU inventory; this is not evidence of successful GPU inference."""

import argparse
import json
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.frozen_trace import require  # noqa: E402
from rag_research.experiments.storage import checkpoint  # noqa: E402


def command_inventory(command):
    executable = shutil.which(command[0])
    if executable is None:
        return {"status": "not_found", "command": command}
    try:
        result = subprocess.run([executable, *command[1:]], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=20, check=False)
        return {"status": "ok" if result.returncode == 0 else "failed", "command": command,
                "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"status": "failed", "command": command, "error": str(error)}


def inventory(root):
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage(root)
    return {"schema_version": 1, "purpose": "execution-environment-inventory-not-inference-proof",
            "recorded_at_utc": datetime.now(UTC).isoformat(),
            "os": platform.platform(), "machine": platform.machine(), "cpu": platform.processor(),
            "physical_cores": psutil.cpu_count(logical=False), "logical_cpus": psutil.cpu_count(),
            "ram_total_bytes": memory.total, "ram_available_bytes": memory.available,
            "workspace_disk_total_bytes": disk.total, "workspace_disk_free_bytes": disk.free,
            "python": platform.python_version(),
            "nvidia_smi": command_inventory(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                                               "--format=csv,noheader,nounits"]),
            "uv": command_inventory(["uv", "--version"]),
            "nvcc": command_inventory(["nvcc", "--version"]),
            "gpu_inference_verified": False, "gate11_passed": False}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    path = args.output.resolve()
    require(path.is_relative_to(ROOT / "data/runs"), "Inventory output must stay in local runs")
    require(not path.exists(), "Preserve the previous inventory; choose a new file")
    path.parent.mkdir(parents=True, exist_ok=True)
    value = checkpoint(path, inventory(ROOT))
    print(json.dumps({key: value[key] for key in ("os", "ram_total_bytes", "workspace_disk_free_bytes",
                     "nvidia_smi", "gpu_inference_verified", "gate11_passed")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
