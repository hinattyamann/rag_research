"""Independent startup witness; metadata only, no model calls or control edits."""

import argparse
import json
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True)
    args = p.parse_args()
    cfg = json.loads(args.config.read_text())
    import sys
    sys.path.insert(0, str(Path(cfg["helper_dir"]) / "legacy"))
    from common import read, sha, write
    batch = read(Path(cfg["batches"][0]))
    run = Path(batch["cal_run"])
    start = time.monotonic()
    result = {"checked_at_utc": datetime.now(UTC).isoformat(), "verified": False}
    while time.monotonic() - start < 600:
        active = subprocess.run(["systemctl", "--user", "is-active", "--quiet", "cal-extension-v1.service"]).returncode == 0
        good = []
        for lang in ["en", "ja"]:
            for path in (run / lang / "baseline").glob("*/record.json"):
                try:
                    value = read(path)
                except (ValueError, OSError):
                    continue
                if value.get("status") == "ok":
                    settings = (value.get("runtime_response") or {}).get("generation_settings", {})
                    good.append({"language": lang, "path": str(path.relative_to(run)), "sha256": sha(path),
                        "input_tokens": value.get("input_tokens"), "output_tokens": value.get("output_tokens"),
                        "generation_settings": {k: settings.get(k) for k in ["temperature", "seed", "n_predict"]}})
        if good and active:
            logs = []
            for path in run.glob("*/baseline/server-*.log"):
                text = path.read_text(errors="replace")
                layers = [list(map(int, pair)) for pair in re.findall(r"offloaded (\d+)/(\d+) layers to GPU", text)]
                contexts = [int(n) for n in re.findall(r"llama_context:\s+n_ctx\s*=\s*(\d+)", text)]
                if layers and all(a == b and a > 0 for a, b in layers) and contexts and all(n == 4096 for n in contexts):
                    logs.append({"path": str(path.relative_to(run)), "sha256_at_startup_check": sha(path),
                                 "offload": layers, "context_tokens": contexts})
            if logs:
                protected = read(Path(cfg["state_dir"]) / "protected_original_files.json")
                unchanged = all(sha(path) == expected for path, expected in protected.items())
                result.update(verified=unchanged, checked_at_utc=datetime.now(UTC).isoformat(),
                    detached_service_active=True, successful_native=good, cuda_logs=logs,
                    original_scientific_files_rechecked=len(protected), original_files_unchanged=unchanged,
                    new_model_calls_by_witness=0, original_run_modified=False)
                break
        if not active:
            result["error"] = "Service stopped before startup witness completed"
            break
        time.sleep(5)
    write(Path(cfg["state_dir"]) / "startup_verification.json", result)
    write(Path(cfg["repo"]) / "reports/cal_extension_v1/startup_verification.json", result)
    write(Path(cfg["state_dir"]) / "publication.request", {"event": "startup_witness_finished", "at_utc": datetime.now(UTC).isoformat()})
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
