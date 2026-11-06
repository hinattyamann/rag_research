"""Start the sealed workflow and startup witness under the user service manager."""

import argparse
import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, required=True)
    args = p.parse_args()
    cfg = json.loads(args.config.read_text())
    import sys
    sys.path.insert(0, str(Path(cfg["helper_dir"]) / "legacy"))
    from common import read, sha, write
    if subprocess.run(["systemctl", "--user", "is-active", "--quiet", "cal-extension-v1.service"]).returncode == 0:
        raise ValueError("Extension service is already active")
    for path in cfg["batches"]:
        batch = read(Path(path))
        if any(list((Path(batch["cal_run"]) / lang / "baseline").glob("*/record.json")) for lang in ["en", "ja"]):
            raise ValueError("Use explicit recovery for an already-started workflow")
    artificial = read(Path(cfg["state_dir"]) / "artificial-cli-preflight/result.json")
    if artificial["all_validated"] is not True or artificial["artificial_cli_invocations"] != 2:
        raise ValueError("Artificial CLI preflight has not completed")
    # Allow the startup witness to report before closing the current editor session.
    cfg["vscode_close_not_before_utc"] = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    write(args.config, cfg)
    args.config.with_suffix(".sha256").write_text(sha(args.config) + "\n")
    helper, python = Path(cfg["helper_dir"]), cfg["cpu_python"]
    post = " ".join([python, str(helper / "service.py"), "--config", str(args.config.resolve()), "--post-stop"])
    command = ["systemd-run", "--user", "--unit=cal-extension-v1", "--description=Fixed-v23 balanced Cal extension",
        "--property=Type=exec", "--property=Restart=no", "--property=KillMode=control-group", "--property=TimeoutStopSec=45",
        "--property=WorkingDirectory=" + cfg["checkout"], "--property=ExecStopPost=" + post]
    for key in ["DISPLAY", "XAUTHORITY", "XDG_RUNTIME_DIR", "LD_LIBRARY_PATH"]:
        if os.environ.get(key):
            command.append("--setenv=" + key + "=" + os.environ[key])
    command += ["--setenv=PYTHONUNBUFFERED=1", "--setenv=MPLBACKEND=Agg",
                "--setenv=MPLCONFIGDIR=" + str(Path(cfg["state_dir"]) / "matplotlib-cache"),
                python, str(helper / "service.py"), "--config", str(args.config.resolve())]
    subprocess.run(command, check=True)
    subprocess.run(["systemd-run", "--user", "--unit=cal-extension-startup-witness-v1",
        "--property=Type=exec", "--property=WorkingDirectory=" + cfg["checkout"],
        python, str(helper / "observe_start.py"), "--config", str(args.config.resolve())], check=True)
    write(Path(cfg["state_dir"]) / "launch.json", {"at_utc": datetime.now(UTC).isoformat(),
        "unit": "cal-extension-v1.service", "independent_startup_witness": True,
        "vscode_close_not_before_utc": cfg["vscode_close_not_before_utc"], "configured_qa": 120})
    print(json.dumps(read(Path(cfg["state_dir"]) / "launch.json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
