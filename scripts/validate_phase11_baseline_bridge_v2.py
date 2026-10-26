"""Portable, read-only validation of the issued two-input baseline Health bridge."""

import hashlib
import json
import sys
from pathlib import Path

BRIDGE_PATH = "data/manifests/phase11_baseline_current_core_bridge_v2.json"
BRIDGE_SHA256 = "aadb2f7ec4206c57afcddafc0bac6bc5d6ddfb71f2d5a75432dcb7f1fb39ac60"
COUNTS = {"original_native_calls": 2, "standard_task_successes": 0,
          "guard_unvalidated_returned": 2, "independent_health_responses": 2, "new_native_calls": 0}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class ClosedFiles:
    """Only the original audit's twenty byte-identical Raw aliases are portable."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.aliases, self.required, self.verified = {}, {}, {}

    def path(self, name):
        require(isinstance(name, str) and name and not Path(name).is_absolute() and ".." not in Path(name).parts,
                "Bridge input must have a relative contained path")
        path = (self.root / name).resolve()
        require(path.is_relative_to(self.root), "Bridge input escapes checkout")
        return path

    def bound(self, binding):
        require(isinstance(binding, dict) and set(binding) == {"path", "sha256"}, "Exact bridge binding required")
        name, wanted = binding["path"], binding["sha256"]
        self.path(name)
        resolved = self.aliases.get(name, name)
        path = self.path(resolved)
        require(path.is_file(), "Missing closed bridge artifact: " + resolved)
        if resolved not in self.verified:
            self.verified[resolved] = file_sha(path)
        observed = self.verified[resolved]
        require(observed == wanted, "Closed bridge artifact changed: " + resolved)
        require(resolved not in self.required or self.required[resolved] == wanted, "Conflicting bridge reference")
        self.required[resolved] = wanted
        return path

    def read(self, binding):
        return json.loads(self.bound(binding).read_text("utf-8"))


def _source_proof(root, bridge, files):
    # All current core bytes are verified before importing any repository module.
    import yaml

    sys.path.insert(0, str(root / "src"))
    from rag_research.experiments.evidence_reuse import validate_receipt

    config = yaml.safe_load(files.bound(bridge["current_config"]).read_text("utf-8"))
    receipt = files.read(bridge["semantic_non_inference_source_proof"])
    plan = files.read(receipt["current_plan"])
    # validate_receipt also checks both identity chains' authorization/legacy
    # protocol; expose these as portable, directly registrable dependencies.
    old_config = yaml.safe_load(files.bound(receipt["source_config"]).read_text("utf-8"))
    original_plan = files.read(receipt["source_run_plan"])
    require(original_plan["identity_files"] == bridge["old_identity_files"] and
            digest({key: sorted(value, key=lambda item: item["path"])
                    for key, value in original_plan["identity_files"].items()}) == bridge["old_execution_identity_sha256"],
            "Original baseline/semantic execution identities differ")
    for mode in ("preflight", "smoke"):
        name = "data/runs/development_screening/phase11-autonomy-v3-plans/baseline-" + mode + ".json"
        registered = files.read({"path": name, "sha256": bridge["bound_artifact_files_sha256"][name]})
        require(registered["identity_files"] == original_plan["identity_files"] and
                registered["candidate_identity_sha256"] == bridge["old_execution_identity_sha256"] and
                registered["fixed_commit"] == bridge["old_execution_commit"], "Original baseline registration differs")
    for value in (config, old_config):
        protocol = files.read(value["autonomy_protocol"])
        files.bound(protocol["authorization"])
        files.bound(protocol["legacy_result"])
    require(receipt["source_candidate_identity_sha256"] == bridge["old_execution_identity_sha256"] and
            receipt["candidate_identity_sha256"] == config["candidate_identity_sha256"] ==
            bridge["current_adoption_identity_sha256"], "Old execution and current adoption source proof differ")
    require(receipt["current_identity_files"] == bridge["current_identity_files"], "Current identity inventory differs")
    for key in ("source_report", "source_manifest", "source_plan", "source_run_plan"):
        files.bound(receipt[key])
    for item in receipt["source_snapshots"].values():
        files.bound(item)
    for name, wanted in receipt["source_run_files_sha256"].items():
        files.bound({"path": str(Path(receipt["source_report"]["path"]).parent / name), "sha256": wanted})
    validate_receipt(receipt, config, plan, root=root, replay=False)
    return config


def validate_bridge(root, bridge_path=BRIDGE_PATH):
    """Return the complete portable binding list; no QA loading, GPU, HTTP or writes."""
    root = Path(root).resolve()
    files = ClosedFiles(root)
    if Path(bridge_path).is_absolute():
        require(Path(bridge_path).resolve().is_relative_to(root), "Bridge receipt escapes checkout")
        bridge_path = Path(bridge_path).resolve().relative_to(root).as_posix()
    bridge_binding = {"path": str(bridge_path), "sha256": BRIDGE_SHA256}
    bridge = files.read(bridge_binding)
    require(bridge["purpose"] == "phase11-baseline-runtime-health-evidence-bridge-v1" and
            bridge["status"] == "verified_zero_call_bridge_not_new_experiment" and bridge["issuance_envelope_version"] == 2,
            "Use the issued bridge v2")
    require(bridge["counts"] == COUNTS and bridge["scope"] == "two_old_known_connection_inputs_EN_JA_only" and
            bridge["independent_runtime_health_passed"] is True, "Preserve the original two-response Health scope/counts")
    require(bridge["old_execution_identity_sha256"] != bridge["current_adoption_identity_sha256"] and
            bridge["new_native_calls"] == bridge["new_model_servers"] == bridge["new_tokenizer_or_GPU_enumeration_or_HTTP"] == 0,
            "Do not relabel old execution as current Native")
    require(all(bridge[key] is False for key in ("source_is_current_execution_core_claimed", "numeric_output_equivalence_assumed",
            "original_evidence_rewritten", "complete_judge_adoption_claimed", "main_cal_quality_claimed",
            "new_main_forty_baselines_proven", "gate11_passed", "phase12_allowed")), "Bridge adoption scope changed")
    audit = files.read(bridge["old_execution_audit"])
    require(audit["independent_runtime_health_passed"] is True and
            audit["standard_checkpoint_task_successes"] == 0 and audit["guard_unvalidated_returned"] ==
            audit["independently_audited_runtime_health_responses"] == 2 and
            audit["fixed_commit"] == bridge["old_execution_commit"] and
            audit["judge_candidate_identity_at_execution"] == bridge["old_execution_identity_sha256"] and
            audit["reuse_conditions_for_new_core_receipt"]["baseline_native_dependency_sha256"] ==
            bridge["native_dependency_sha256"], "Original limited Health/native audit differs")
    aliases = {}
    for mode in ("preflight", "smoke"):
        stage = audit["stages"][mode]
        require(stage["original_before_sha256"] == stage["canonical_sha256"] == stage["original_after_sha256"],
                "Original and portable baseline Raw proofs differ")
        original, canonical = stage["original"], stage["canonical"]
        require(original == ".tools/worktrees/phase11-baseline-v3-4793a17/" + canonical and
                canonical == "data/runs/runtime_screening/phase11-v3-baseline-" + mode,
                "Only the sealed old baseline checkout Raw can be aliased")
        for name, info in stage["canonical_sha256"].items():
            old_name, portable_name = original + "/" + name, canonical + "/" + name
            require(bridge["bound_artifact_files_sha256"].get(old_name) == info["sha256"] ==
                    bridge["bound_artifact_files_sha256"].get(portable_name), "Portable alias is not in the sealed closure")
            aliases[old_name] = portable_name
    require(len(aliases) == 20, "Preserve all twenty original preflight/smoke Raw files")
    files.aliases = aliases
    require(set(name for name in bridge["bound_artifact_files_sha256"] if name.startswith(".tools/")) == set(aliases),
            "Unregistered old checkout dependency")
    for name, wanted in bridge["bound_artifact_files_sha256"].items():
        files.bound({"path": name, "sha256": wanted})
    require(len(bridge["bound_artifact_files_sha256"]) == 698, "Original bridge closure incomplete")
    current = bridge["current_identity_files"]
    identity = digest({key: sorted(value, key=lambda item: item["path"]) for key, value in current.items()})
    require(identity == bridge["current_adoption_identity_sha256"], "Current full identity digest differs")
    actual_core = {p.relative_to(root).as_posix(): file_sha(p) for p in sorted((root / "src/rag_research").rglob("*.py"))}
    require(len(actual_core) == bridge["current_core_files"] == 94 and
            actual_core == {item["path"]: item["sha256"] for item in current["core"]}, "Current full94 source differs")
    for items in current.values():
        for binding in items:
            files.bound(binding)
    require(len(bridge["native_dependency_sha256"]) == bridge["native_dependency_files"] == 36,
            "Original Native dependency inventory differs")
    for name, wanted in bridge["native_dependency_sha256"].items():
        files.bound({"path": name, "sha256": wanted})
    for key in ("preserved_previous_issuance", "old_generation_identity", "current_config", "baseline_config", "validator",
                "validation_spec", "closed_original_artifacts", "old_terminal_ledger_rows"):
        files.bound(bridge[key])
    require(files.read(bridge["closed_original_artifacts"]) == bridge["bound_artifact_files_sha256"],
            "Original protected artifact inventory changed")
    positive, negative = files.read(bridge["positive_validation"]), files.read(bridge["negative_validation"])
    require(positive["passed"] is True and positive["counts"] == COUNTS and
            positive["protected_original_hashes_unchanged"] is True and positive["source_files"] == 94 and
            positive["native_dependencies"] == 36, "Original positive validation differs")
    require(negative["all_rejected"] is True and negative["cases"] == 42 and
            all(case["rejected"] is True for case in negative["negative_cases"]), "Original counterexample audit differs")
    history = files.read(bridge["validation_attempt_history"])
    require(len(history["attempts"]) == 3 and [attempt["returncode"] for attempt in history["attempts"]] == [1, 1, 0] and
            all(attempt["process_elapsed_seconds"] is None for attempt in history["attempts"][:2]),
            "Preserve both stopped audits and their unmeasured process times")
    for attempt in history["attempts"]:
        for key in ("script", "log"):
            # The sealed history also records bytes/lines and log provenance.
            info = attempt[key]
            path = files.bound({name: info[name] for name in ("path", "sha256")})
            if key == "script":
                require(path.stat().st_size == info["bytes"] and len(path.read_text("utf-8").splitlines()) == info["lines"],
                        "Preserved audit script metadata differs")
        if "outcome" in attempt:
            files.bound(attempt["outcome"])
    candidate = _source_proof(root, bridge, files)
    return {"bridge": bridge, "bridge_binding": bridge_binding, "candidate": candidate,
            "required_bindings": [{"path": name, "sha256": wanted} for name, wanted in sorted(files.required.items())],
            "original_reference_count": 698, "resolved_old_checkout_references": 20,
            "portable_physical_artifact_count": len(files.required), "native_calls": 0, "phase12_allowed": False}
