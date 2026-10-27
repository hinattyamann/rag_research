"""Explicit zero-output, registered-only amendment of two evidence binding paths.

This does not register, execute, retry, alter scientific conditions or touch Core.
The caller pins a separately reviewed extension protocol by its exact file SHA.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import psutil

VERSION = "phase11-zero-output-metadata-repair-v1"
SOURCE_JSON = (
    "data/manifests/phase11_v26_checkout_reproduction_v1.json",
    "data/manifests/phase11_v26_preflight_result_v1.json",
)
TARGET_PREFIX = "data/runs/lab/phase11-v26-zero-output-evidence-v1/"
REGISTERED_KEYS = {
    "run_id",
    "state",
    "registered_at_utc",
    "plan_sha256",
    "plan_content_sha256",
    "plan",
    "condition_sha256",
}
PROJECT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())


def require(value, message):
    if not value:
        raise ValueError(message)


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text("utf-8"))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def digest(value):
    return sha_bytes(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode()
    )


def contained(root, name):
    name = Path(name)
    require(not name.is_absolute() and ".." not in name.parts, "Contained relative path required")
    result = root / name
    require(result.resolve().is_relative_to(root) and result.resolve() != root, "Path escapes root")
    require(result.resolve() == result, "Do not traverse any symlink in metadata paths")
    return result


def absent(path):
    return not path.exists() and not path.is_symlink()


def ordinary(path):
    require(
        path.is_file() and not path.is_symlink() and path.resolve() == path,
        "Use an ordinary contained file: " + str(path),
    )
    return path


def common_root(root):
    marker = root / ".git"
    require(
        marker.is_file(), "Use the existing dedicated fixed worktree, never the canonical checkout"
    )
    text = marker.read_text("utf-8").strip()
    require(text.startswith("gitdir: "), "Missing worktree Git administrative path")
    admin = (root / text.removeprefix("gitdir: ")).resolve()
    require((admin / "commondir").is_file(), "Dedicated worktree common Git directory required")
    return (admin / (admin / "commondir").read_text("utf-8").strip()).resolve().parent


def git(root, *arguments, allowed_returncodes=(0,)):
    result = subprocess.run(["git", *arguments], cwd=root, capture_output=True, check=False)
    require(
        result.returncode in allowed_returncodes,
        "Read-only Git check failed: " + result.stderr.decode(errors="replace"),
    )
    return result.stdout


def ignored(root, path):
    relative = path.resolve().relative_to(root).as_posix()
    git(root, "check-ignore", "--quiet", "--no-index", "--", relative)


def api(protocol):
    source = PROJECT / "src/rag_research/experiments/phase11_autonomy.py"
    require(sha(source) == protocol["unchanged_guard_sha256"], "Existing v3 Guard source differs")
    sys.path.insert(0, str(PROJECT / "src"))
    from rag_research.experiments import phase11_autonomy as guard

    require(
        Path(guard.__file__).resolve() == source
        and sha(source) == protocol["unchanged_guard_sha256"],
        "Do not substitute or monkeypatch the v3 Guard",
    )
    return guard


def load_protocol(path, expected_sha256):
    ordinary(path)
    require(sha(path) == expected_sha256, "Pin the reviewed extension protocol bytes")
    protocol = read(path)
    require(
        protocol["version"] == VERSION
        and protocol["purpose"] == "registered-zero-output-metadata-path-amendment"
        and protocol["new_native_calls"] == 0
        and protocol["phase12_allowed"] is False,
        "Use only the separate zero-output extension protocol",
    )
    require(
        sha(Path(__file__).resolve()) == protocol["extension_source_sha256"],
        "Extension source differs from reviewed protocol",
    )
    require(
        type(protocol.get("maximum_wall_seconds")) is int
        and 0 < protocol["maximum_wall_seconds"] <= 1800,
        "Finite metadata-operation budget no greater than 1800 seconds required",
    )
    relocation = protocol["relocations"]
    require(
        len(relocation) == 2 and tuple(row["source"] for row in relocation) == SOURCE_JSON,
        "Only these exact two completed-evidence JSON paths may move",
    )
    for row in relocation:
        require(
            set(row) == {"source", "destination", "sha256", "sidecar_sha256"}
            and row["destination"] == TARGET_PREFIX + Path(row["source"]).name,
            "Use the fixed ignored evidence destination and unchanged SHA256",
        )
    require(
        protocol["new_plan_path"].startswith(
            "data/runs/development_screening/phase11-autonomy-v3-plans/"
        )
        and protocol["journal_path"].startswith(
            "data/runs/lab/phase11-zero-output-metadata-repair-v1/"
        )
        and protocol["failure_evidence"],
        "Use fresh canonical ignored plan/journal and actual failure evidence",
    )
    return protocol


def proposed_plan(old, protocol):
    """No sorting, additions, removals, metadata annotations or other field edits."""
    new = deepcopy(old)
    counts = {row["source"]: 0 for row in protocol["relocations"]}
    mapping = {row["source"]: row for row in protocol["relocations"]}
    for binding in new["bindings"]:
        if binding["path"] in mapping:
            item = mapping[binding["path"]]
            require(
                binding == {"path": item["source"], "sha256": item["sha256"]},
                "Evidence SHA or binding schema differs",
            )
            binding["path"] = item["destination"]
            counts[item["source"]] += 1
    require(
        set(counts.values()) == {1}, "Each of the two old evidence paths must occur exactly once"
    )
    reversed_plan = deepcopy(new)
    reverse = {row["destination"]: row["source"] for row in protocol["relocations"]}
    for binding in reversed_plan["bindings"]:
        if binding["path"] in reverse:
            binding["path"] = reverse[binding["path"]]
    require(
        reversed_plan == old and digest(new["identity_files"]) == digest(old["identity_files"]),
        "Only the two binding.path strings may differ",
    )
    return new


def preconditions(root, canonical, protocol, guard):
    require(
        root.resolve() == root and canonical == common_root(root) and root != canonical,
        "Use exact dedicated worktree/common root",
    )
    require(
        git(root, "rev-parse", "HEAD").decode().strip() == protocol["fixed_commit"],
        "Fixed HEAD changed",
    )
    ledger_dir = canonical / "data/runs/development_screening/phase11-autonomy-v3"
    ledger_path = ordinary(ledger_dir / "ledger.json")
    ledger_bytes = ledger_path.read_bytes()
    ledger = json.loads(ledger_bytes)
    require(
        ledger["version"] == guard.VERSION and ledger["phase12_allowed"] is False,
        "Use the existing Phase11 cumulative v3 ledger",
    )
    require(
        sha_bytes(ledger_bytes) == protocol["ledger_before_sha256"],
        "Cumulative ledger changed since the zero-output audit",
    )
    matches = [r for r in ledger["runs"] if r["run_id"] == protocol["run_id"]]
    require(
        len(matches) == 1 and not any(r["state"] == "running" for r in ledger["runs"]),
        "No unique inactive registration",
    )
    row = matches[0]
    require(
        set(row) == REGISTERED_KEYS
        and row["state"] == "registered"
        and digest(row) == protocol["registered_row_sha256"],
        "Only a never-started exact registered row without PID/snapshot/timestamps may be amended",
    )
    old_plan = ordinary(contained(canonical, protocol["old_plan"]["path"]))
    require(
        sha(old_plan) == protocol["old_plan"]["sha256"] == row["plan_sha256"]
        and read(old_plan) == row["plan"]
        and digest(row["plan"]) == row["plan_content_sha256"],
        "Preserve actual original plan bytes and row",
    )
    plan = row["plan"]
    require(
        plan["fixed_commit"] == protocol["fixed_commit"]
        and plan["candidate_identity_sha256"] == protocol["candidate_identity_sha256"]
        and plan["run_id"] == protocol["run_id"]
        and guard.condition_fingerprint(plan)
        == row["condition_sha256"]
        == protocol["condition_sha256"],
        "Candidate, fixed HEAD, run or condition identity differs",
    )
    require(
        absent(ledger_dir / row["run_id"]) and absent(contained(root, plan["output_dir"])),
        "Never amend any existing monitor, Native guard, output, journal or started Run",
    )
    require(
        absent(root / "data/runs/development_screening/phase11-autonomy-v3"),
        "No WT-local operational ledger",
    )
    require(
        guard.native_snapshot(ledger_dir, row["run_id"])["attempts"] == 0,
        "Native reservations must be zero",
    )
    output_snapshot = guard.journal_snapshot(contained(root, plan["output_dir"]))
    require(
        output_snapshot["attempts"] == 0 and not output_snapshot["invalid_journals"],
        "Native/task journal must be absent",
    )
    observed = (
        git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").decode().split("\0")
    )
    expected_dirty = {
        path
        for item in protocol["relocations"]
        for path in (item["source"], item["source"].removesuffix(".json") + ".sha256")
    }
    require(
        set(filter(None, observed)) == {"?? " + p for p in expected_dirty},
        "Only the four exact untracked metadata files may differ; tracked changes forbidden",
    )
    for item in protocol["relocations"]:
        for name, wanted in (
            (item["source"], item["sha256"]),
            (item["source"].removesuffix(".json") + ".sha256", item["sidecar_sha256"]),
        ):
            source, original = ordinary(contained(root, name)), ordinary(contained(canonical, name))
            require(
                sha(source) == sha(original) == wanted
                and source.read_bytes() == original.read_bytes(),
                "WT/canonical exact metadata bytes differ",
            )
        for name in (item["destination"], item["destination"].removesuffix(".json") + ".sha256"):
            target = contained(root, name)
            require(
                absent(target),
                "Preserve an existing relocation target",
            )
            ignored(root, target)
    for binding in protocol["failure_evidence"]:
        require(set(binding) == {"path", "sha256"}, "Failure evidence binding must be exact")
        require(
            sha(ordinary(contained(canonical, binding["path"]))) == binding["sha256"],
            "Original failure evidence changed",
        )
    new_plan_path, journal = (
        contained(canonical, protocol["new_plan_path"]),
        contained(canonical, protocol["journal_path"]),
    )
    require(
        absent(new_plan_path) and absent(journal),
        "Do not repeat an amendment or overwrite a partial journal",
    )
    ignored(canonical, new_plan_path)
    ignored(canonical, journal)
    parent_protocol = ordinary(contained(root, protocol["parent_protocol"]["path"]))
    require(
        sha(parent_protocol) == protocol["parent_protocol"]["sha256"] == ledger["protocol_sha256"],
        "Parent v3 protocol changed",
    )
    guard.validate_plan(root, plan, parent_protocol)
    new = proposed_plan(plan, protocol)
    require(
        guard.condition_fingerprint(new) == row["condition_sha256"],
        "No changed fingerprint or fresh registration",
    )
    return ledger_bytes, ledger, row, new, old_plan, new_plan_path, journal, parent_protocol


def write_once(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def repair(root, protocol_path, protocol_sha256, *, commit=False):
    started = time.monotonic()
    require(
        not os.environ.get("RAG_PHASE11_AUTONOMY_CONTEXT"),
        "Never repair from an owned Native execution context",
    )
    protocol = load_protocol(protocol_path, protocol_sha256)
    canonical = common_root(root)
    guard = api(protocol)
    ledger_dir = canonical / "data/runs/development_screening/phase11-autonomy-v3"
    require(
        absent(ledger_dir / "ledger.json.tmp"),
        "Preserve any incomplete prior atomic ledger write",
    )
    # Use the identical nonblocking OS lock as register/execute; no private substitute.
    with guard.run_lock(ledger_dir):
        data = preconditions(root, canonical, protocol, guard)
        before_bytes, before, row, new_plan, old_plan_path, new_path, journal, parent_protocol = (
            data
        )
        after = deepcopy(before)
        index = next(i for i, r in enumerate(after["runs"]) if r["run_id"] == row["run_id"])
        amendment = {
            "version": VERSION,
            "extension_protocol_sha256": protocol_sha256,
            "extension_source_sha256": sha(Path(__file__).resolve()),
            "immutable_journal": protocol["journal_path"],
            "old_plan_sha256": row["plan_sha256"],
            "new_plan_path": protocol["new_plan_path"],
            "new_plan_sha256": sha_bytes(encoded(new_plan)),
            "condition_sha256": row["condition_sha256"],
            "native_calls_before": 0,
            "new_native_calls": 0,
            "registered_only": True,
            "phase12_allowed": False,
        }
        after["runs"][index] = {
            **deepcopy(row),
            "plan": new_plan,
            "plan_sha256": amendment["new_plan_sha256"],
            "plan_content_sha256": digest(new_plan),
            "zero_output_metadata_amendments": [amendment],
        }
        require(
            {k: v for k, v in before.items() if k != "runs"}
            == {k: v for k, v in after.items() if k != "runs"}
            and all(
                a == b
                for i, (a, b) in enumerate(zip(before["runs"], after["runs"], strict=True))
                if i != index
            ),
            "Keep every other row, legacy count, totals and ledger field unchanged",
        )
        result = {
            "version": VERSION,
            "run_id": row["run_id"],
            "condition_sha256": row["condition_sha256"],
            "proposed_plan_sha256": amendment["new_plan_sha256"],
            "proposed_plan_content_sha256": digest(new_plan),
            "only_two_evidence_binding_paths_changed": True,
            "new_native_calls": 0,
            "registered_new_Run": False,
            "ledger_changed": False,
            "worktree_changed": False,
            "committed": False,
            "phase12_allowed": False,
        }
        require(
            time.monotonic() - started < protocol["maximum_wall_seconds"],
            "Metadata operation exceeded its finite wall budget",
        )
        if not commit:
            return result
        # Durable immutable intent and all prior bytes precede every WT/ledger mutation.
        journal.mkdir(parents=True, exist_ok=False)
        intent = {
            "version": VERSION,
            "state": "immutable_intent_not_commit_receipt",
            "at_utc": datetime.now(UTC).isoformat(),
            "repair_pid": os.getpid(),
            "repair_create_time": psutil.Process().create_time(),
            "extension_protocol_sha256": protocol_sha256,
            "extension_source_sha256": sha(Path(__file__).resolve()),
            "ledger_before_sha256": sha_bytes(before_bytes),
            "ledger_after_sha256_expected": sha_bytes(encoded(after)),
            "old_row_sha256": digest(row),
            "new_row_sha256_expected": digest(after["runs"][index]),
            "new_plan_sha256_expected": amendment["new_plan_sha256"],
            "condition_sha256": row["condition_sha256"],
            "same_run_id_and_fingerprint": True,
            "no_resume_after_partial_without_new_review": True,
            "phase12_allowed": False,
        }
        write_once(journal / "intent.json", encoded(intent))
        write_once(journal / "ledger-before.json", before_bytes)
        write_once(journal / "registered-row-before.json", encoded(row))
        write_once(journal / "original-plan.json", old_plan_path.read_bytes())
        write_once(journal / "extension-protocol.json", protocol_path.read_bytes())
        write_once(journal / "extension-source.py", Path(__file__).resolve().read_bytes())
        for number, binding in enumerate(protocol["failure_evidence"]):
            write_once(
                journal / "failure-evidence" / f"{number:02d}-{Path(binding['path']).name}",
                contained(canonical, binding["path"]).read_bytes(),
            )
        for item in protocol["relocations"]:
            for suffix in (".json", ".sha256"):
                source = contained(root, item["source"].removesuffix(".json") + suffix)
                write_once(journal / "original-metadata" / source.name, source.read_bytes())
        write_once(journal / "amended-plan.json", encoded(new_plan))
        write_once(journal / "ledger-after-expected.json", encoded(after))
        for item in protocol["relocations"]:
            for suffix in (".json", ".sha256"):
                source = contained(root, item["source"].removesuffix(".json") + suffix)
                target = contained(root, item["destination"].removesuffix(".json") + suffix)
                target.parent.mkdir(parents=True, exist_ok=True)
                require(absent(target), "Target appeared while locked; preserve partial intent")
                os.link(source, target)
                source.unlink()
        write_once(new_path, encoded(new_plan))
        require(
            sha(new_path) == amendment["new_plan_sha256"] and read(new_path) == new_plan,
            "Fresh amended plan differs",
        )
        guard.validate_plan(root, new_plan, parent_protocol)
        guard._fixed_checkout(root, new_plan["fixed_commit"])
        require(
            (ledger_dir / "ledger.json").read_bytes() == before_bytes
            and absent(ledger_dir / row["run_id"])
            and absent(contained(root, new_plan["output_dir"])),
            "Concurrent state/output appeared; preserve partial intent without applying ledger",
        )
        require(
            time.monotonic() - started < protocol["maximum_wall_seconds"],
            "Finite metadata deadline exceeded before ledger commit; preserve partial intent",
        )
        guard.write_json(ledger_dir / "ledger.json", after)
        require(
            (ledger_dir / "ledger.json").read_bytes() == encoded(after),
            "Atomic ledger result differs",
        )
        result.update(
            ledger_changed=True,
            worktree_changed=True,
            committed=True,
            actual_v3_validate_plan_passed=True,
            actual_v3_fixed_checkout_clean_passed=True,
            immutable_journal=protocol["journal_path"],
            ledger_after_sha256=sha_bytes(encoded(after)),
        )
        write_once(journal / "committed.json", encoded(result))
        return result


class OfflineBoundary:
    """Native/QA/socket prevention; permit only enumerated read-only Git calls."""

    def __init__(self, root):
        self.counts = {
            "allowed_read_only_git": 0,
            "forbidden_process_starts": 0,
            "socket_operations": 0,
            "reserved_QA_opens": 0,
        }
        canonical = common_root(root)
        self.roots = {root, canonical}
        qa_roots = {PROJECT, *self.roots}
        git_common = canonical / ".git"
        for marker in (git_common / "worktrees").glob("*/gitdir"):
            qa_roots.add((marker.parent / marker.read_text("utf-8").strip()).resolve().parent)
        assets = read(PROJECT / "configs/phase11_bilingual_assets_v2.json")
        names = {
            row["path"] for dataset in assets["datasets"].values() for row in dataset["qa"].values()
        }
        self.reserved = {(base / name).resolve() for base in qa_roots for name in names}
        self.inodes = set()
        for path in self.reserved:
            if path.exists():
                stat = path.stat()
                self.inodes.add((stat.st_dev, stat.st_ino))

    def audit(self, event, args):
        if event == "subprocess.Popen":
            _, argv, cwd, _ = args
            allowed = argv in (
                ["git", "rev-parse", "HEAD"],
                ["git", "status", "--porcelain"],
                ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            )
            allowed = allowed or (
                isinstance(argv, (list, tuple))
                and len(argv) == 6
                and list(argv[:5]) == ["git", "check-ignore", "--quiet", "--no-index", "--"]
            )
            if allowed and Path(cwd).resolve() in self.roots:
                self.counts["allowed_read_only_git"] += 1
                return
            self.counts["forbidden_process_starts"] += 1
            raise RuntimeError(
                "No Native, tokenizer, model-server or non-read-only Git process may start"
            )
        if event in {"os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec"}:
            self.counts["forbidden_process_starts"] += 1
            raise RuntimeError("No other process start during zero-output amendment")
        if event in {"socket.connect", "socket.bind", "socket.getaddrinfo"}:
            self.counts["socket_operations"] += 1
            raise RuntimeError("No socket operations during zero-output amendment")
        if event == "open":
            value = args[0]
            path = (
                Path(os.fsdecode(value)).resolve()
                if isinstance(value, (str, bytes, os.PathLike))
                else None
            )
            try:
                stat = os.fstat(value) if type(value) is int else path.stat() if path else None
                inode = (stat.st_dev, stat.st_ino) if stat else None
            except OSError:
                inode = None
            if path in self.reserved or inode in self.inodes:
                self.counts["reserved_QA_opens"] += 1
                raise RuntimeError("Main/Cal/Evaluation QA bodies must stay unread")

    def install(self):
        sys.addaudithook(self.audit)
        return self


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "commit"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--extension-protocol", type=Path, required=True)
    parser.add_argument("--extension-protocol-sha256", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    boundary = OfflineBoundary(root).install()
    result = repair(
        root,
        args.extension_protocol.resolve(),
        args.extension_protocol_sha256,
        commit=args.action == "commit",
    )
    require(
        not any(v for k, v in boundary.counts.items() if k != "allowed_read_only_git"),
        "Forbidden zero-output repair operation",
    )
    print(json.dumps({**result, "boundary": boundary.counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
