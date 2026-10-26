"""Atomic checkpoints, content verification and an OS-released exclusive run lock."""

import json
import os
import re
from contextlib import contextmanager

from rag_research.experiments.frozen_trace import digest, require


def read_json(path):
    return json.loads(path.read_text("utf-8"))


def write_json(path, value):
    # Replacement is permitted only for this run's journal/derived report.
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def checkpoint(path, value):
    value = dict(value)
    value["result_sha256"] = digest(value)
    write_json(path, value)
    return value


def verify_checkpoint(value):
    body = {k: v for k, v in value.items() if k != "result_sha256"}
    require(value.get("result_sha256") == digest(body), "Checkpoint hash mismatch")


def next_session(directory):
    """An interrupted server may leave a log without a session report; preserve both."""
    numbers = []
    for path in directory.iterdir():
        match = re.fullmatch(r"(?:server-(\d+)\.log|session-(\d+)\.json)", path.name)
        if match:
            numbers.append(int(match.group(1) or match.group(2)))
    return max(numbers, default=0) + 1


@contextmanager
def run_lock(output):
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".run.lock").open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise ValueError("Another process owns this run") from error
        else:
            import fcntl

            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)
