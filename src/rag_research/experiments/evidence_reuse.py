"""Explicit zero-call reuse of complete diagnostics after one metadata-only repair.

The old experiment retains its original identity.  A separate receipt proves the
current candidate has identical inference conditions and an allowed source diff;
it never relabels a report as a newly executed experiment.
"""

import ast
import json
import shutil
import tempfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import yaml

from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.phase11_autonomy import COMPONENTS, validate_chain_identity
from rag_research.experiments.storage import read_json
from rag_research.retrieval.common import file_hash

VERSION = "phase11-semantic-evidence-reuse-v1"
FIELD = "semantic_evidence_reuse"
PREFIX = "src/rag_research/experiments/"
ADDED_SOURCE = PREFIX + "evidence_reuse.py"
CHANGED_FUNCTIONS = {
    PREFIX + "bilingual_runner.py": {"_run"},
    PREFIX + "semantic_diagnostics.py": {"load_config"},
    PREFIX + "bilingual_certification.py": {"adopted_sources", "verify_prerequisite"},
}
CONFIG_METADATA = {"study_version", "diagnostics", "candidate_identity_sha256", FIELD}
PLAN_METADATA = {"created_at_utc", "change", "parent_plan_sha256", "candidate_identity_sha256"}
FIELDS = {"schema_version", "purpose", "version", "status", "created_at_utc", "source_report", "source_manifest",
          "source_config", "source_plan", "source_run_plan", "current_plan", "source_candidate_identity_sha256",
          "candidate_identity_sha256", "conditions_sha256", "current_identity_files", "source_snapshots",
          "source_run_files_sha256", "reused_native_calls", "new_model_calls", "new_model_servers"}


def bound(root, value):
    require(isinstance(value, dict) and set(value) == {"path", "sha256"} and
            isinstance(value["path"], str) and not Path(value["path"]).is_absolute(), "Invalid reuse binding")
    path = (root / value["path"]).resolve()
    require(path.is_relative_to(root) and path.is_file() and file_hash(path) == value["sha256"],
            "Semantic evidence reuse artifact changed")
    return path


def binding(root, path):
    path = Path(path).resolve()
    require(path.is_relative_to(root) and path.is_file(), "Reuse artifact escapes repository")
    return {"path": path.relative_to(root).as_posix(), "sha256": file_hash(path)}


def condition_value(config, plan):
    """Ignore only declared provenance; all Expected, full cases and budgets remain."""
    return {"config": {k: v for k, v in config.items() if k not in CONFIG_METADATA},
            "plan": {k: v for k, v in plan.items() if k not in PLAN_METADATA}}


def identity_digest(files):
    require(isinstance(files, dict) and set(files) == COMPONENTS and
            all(isinstance(rows, list) and rows for rows in files.values()), "Incomplete reuse identity")
    for rows in files.values():
        require(all(set(row) == {"path", "sha256"} for row in rows) and
                len({row["path"] for row in rows}) == len(rows), "Duplicate or malformed identity binding")
    return digest({name: sorted(rows, key=lambda row: row["path"]) for name, rows in files.items()})


def tree_value(node):
    return ast.dump(node, include_attributes=False)


def function(tree, name):
    matches = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    require(len(matches) == 1, "Missing/duplicate source boundary function")
    return matches[0]


def statement_with_message(nodes, message):
    found = [node for node in nodes if any(isinstance(value, ast.Constant) and value.value == message
                                         for value in ast.walk(node))]
    require(len(found) == 1, "Missing/duplicate registered AST insertion boundary")
    return found[0]


def repaired_prerequisite_branch(original):
    expected = deepcopy(original)
    chain = [node for node in expected.body if isinstance(node, ast.If) and
             isinstance(node.test, ast.Name) and node.test.id == "chain"]
    require(len(chain) == 1, "Unexpected Known chain boundary")
    replacement = ast.parse('''
reused = None
if chain:
    if config.get("semantic_evidence_reuse"):
        from rag_research.experiments.evidence_reuse import validate_reuse
        reused = validate_reuse(config, root=ROOT, report_override=prerequisite)
        require(reused["paths"]["source_report"] == prerequisite and
                reused["source_config"] == prior_manifest["config"] and
                reused["source_plan"] == prior_plan, "Known prerequisite differs from explicit reused evidence")
    else:
        validate_chain_identity(config, plan, prior_manifest, prior_report, prior_plan,
                                prior_manifest["config"], root=ROOT)
''').body
    index = expected.body.index(chain[0])
    expected.body[index:index + 1] = replacement
    matching = statement_with_message(expected.body, "Known regression must use the passing candidate settings")
    index = expected.body.index(matching)
    expected.body[index:index + 1] = ast.parse('''
passing_config = prior_manifest["config"]
if reused:
    passing_config = {**passing_config, "candidate_identity_sha256": config["candidate_identity_sha256"],
                      "semantic_evidence_reuse": config["semantic_evidence_reuse"]}
require({k: v for k, v in config.items() if k not in {"study_version", "diagnostics"}} ==
        {k: v for k, v in passing_config.items() if k not in {"study_version", "diagnostics"}},
        "Known regression must use the passing candidate settings")
''').body
    require(not original.orelse, "Original Known prerequisite unexpectedly has an else branch")
    expected.orelse = ast.parse('''
require(not config.get("semantic_evidence_reuse") or allow_reused_view,
        "Reused semantic candidate is a read-only condition view; execute its fresh Known regression instead")
''').body
    return expected


def repaired_certificate_function(original):
    expected = deepcopy(original)
    if original.name == "verify_prerequisite":
        assignment = ast.parse("config, plan, prompts, plan_path = semantic_diagnostics.load_config(candidate_path)").body[0]
        found = [node for node in expected.body if tree_value(node) == tree_value(assignment)]
        require(len(found) == 1, "Unexpected prerequisite loader boundary")
        index = expected.body.index(found[0])
        expected.body[index:index + 1] = ast.parse('''
declared = yaml.safe_load(Path(candidate_path).read_text("utf-8"))
if isinstance(declared, dict) and declared.get("semantic_evidence_reuse"):
    config, plan, prompts, plan_path = semantic_diagnostics.load_config(candidate_path, allow_reused_view=True)
else:
    config, plan, prompts, plan_path = semantic_diagnostics.load_config(candidate_path)
if config.get("semantic_evidence_reuse"):
    from rag_research.experiments.evidence_reuse import validate_reuse
    validate_reuse(config, plan, root=ROOT, report_override=report_path)
    return
''').body
    else:
        loops = [node for node in expected.body if isinstance(node, ast.For) and
                 tree_value(node.target) == tree_value(ast.Name(id="row", ctx=ast.Store()))]
        require(len(loops) == 1, "Unexpected adopted-source loop boundary")
        statements = loops[0].body
        anchor = statement_with_message(statements, "Adopted candidate must stay in configs")
        index = statements.index(anchor) + 1
        statements[index:index] = ast.parse('''
candidate_config = yaml.safe_load(candidate_path.read_text("utf-8"))
if candidate_config.get("semantic_evidence_reuse"):
    from rag_research.experiments.evidence_reuse import reused_bindings
    for name, sha in reused_bindings(candidate_config, root=ROOT).items():
        bind(name, sha)
''').body
    return expected


def source_boundary(name, old_text, current_text):
    """Fail closed outside the registered metadata and read-only gate functions."""
    old, current = ast.parse(old_text), ast.parse(current_text)
    require(name in CHANGED_FUNCTIONS, "Native or unregistered source changed")
    if name.endswith("bilingual_runner.py"):
        old_run, new_run = function(old, "_run"), function(current, "_run")

        def selection(value):
            rows = [node for node in ast.walk(value) if isinstance(node, ast.Assign) and
                    len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "selection"]
            require(len(rows) == 1, "Unexpected selection registration boundary")
            return rows[0]

        original, changed = selection(old_run), selection(new_run)
        expected = ast.parse('selection = [{k: r[k] for k in (("record_id", "question", "document_group_id") '
                             'if main else ("record_id", "question"))} for r in rows]').body[0]
        require(tree_value(changed) == tree_value(expected), "Only the registered Group metadata repair is reusable")
        changed.value = deepcopy(original.value)
    elif name.endswith("semantic_diagnostics.py"):
        original, changed = function(old, "load_config"), function(current, "load_config")
        expected_args = deepcopy(original.args)
        expected_args.kwonlyargs.append(ast.arg(arg="allow_reused_view"))
        expected_args.kw_defaults.append(ast.Constant(value=False))
        require(tree_value(changed.args) == tree_value(expected_args), "Unexpected diagnostic loader signature change")
        changed.args = deepcopy(original.args)

        def prerequisite_branch(value):
            rows = [node for node in value.body if isinstance(node, ast.If) and
                    isinstance(node.test, ast.Name) and node.test.id == "regression"]
            require(len(rows) >= 1, "Missing Known prerequisite branch")
            return rows[0]

        previous, replacement = prerequisite_branch(original), prerequisite_branch(changed)
        require(tree_value(replacement) == tree_value(repaired_prerequisite_branch(previous)),
                "Known prerequisite diff is not the exact registered read-only reuse branch")
        changed.body[changed.body.index(replacement)] = deepcopy(previous)
    else:
        for allowed in CHANGED_FUNCTIONS[name]:
            previous, replacement = function(old, allowed), function(current, allowed)
            require(tree_value(replacement) == tree_value(repaired_certificate_function(previous)),
                    "Certificate diff is not the exact registered read-only reuse insertion")
            current.body[current.body.index(replacement)] = deepcopy(previous)
    require(tree_value(old) == tree_value(current), "Source diff escapes the non-inference repair boundary")


def run_snapshot(folder):
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            require(path.resolve().is_relative_to(folder.resolve()), "Reuse run artifact escapes its source")
            result[path.relative_to(folder).as_posix()] = file_hash(path)
    return result


def validate_receipt(receipt, config, plan, *, root, report_override=None, replay=True):
    root = Path(root).resolve()
    require(isinstance(receipt, dict) and set(receipt) == FIELDS and receipt["schema_version"] == 1 and
            receipt["purpose"] == "phase11-non-inference-semantic-evidence-reuse" and receipt["version"] == VERSION and
            receipt["status"] == "verified_reuse_not_new_experiment" and receipt["new_model_calls"] ==
            receipt["new_model_servers"] == 0 and receipt["reused_native_calls"] == 70,
            "Invalid non-inference semantic reuse receipt")
    require(datetime.fromisoformat(receipt["created_at_utc"]).utcoffset() is not None,
            "Reuse receipt needs an actual timezone-aware timestamp")
    paths = {name: bound(root, receipt[name]) for name in
             ("source_report", "source_manifest", "source_config", "source_plan", "source_run_plan", "current_plan")}
    require(read_json(paths["current_plan"]) == plan, "Current semantic condition plan changed")
    require(paths["source_report"].name == "report.json" and
            paths["source_manifest"] == paths["source_report"].parent / "manifest.json" and
            paths["source_report"].is_relative_to(root / "data/runs/semantic_diagnostics"), "Unexpected original diagnostic run")
    old_config = yaml.safe_load(paths["source_config"].read_text())
    old_plan, old_manifest, old_report, old_run = [read_json(paths[name]) for name in
                                               ("source_plan", "source_manifest", "source_report", "source_run_plan")]
    require(FIELD not in old_config and old_config["diagnostics"] == paths["source_plan"].relative_to(root).as_posix(),
            "Reuse source must be an original unreused candidate")
    validate_chain_identity(old_config, old_plan, old_manifest, old_report, root=root)
    validate_chain_identity(config, plan, root=root)
    require(old_config["candidate_identity_sha256"] == receipt["source_candidate_identity_sha256"] ==
            old_run["candidate_identity_sha256"] == identity_digest(old_run["identity_files"]) and
            config["candidate_identity_sha256"] == receipt["candidate_identity_sha256"] ==
            identity_digest(receipt["current_identity_files"]) and receipt["candidate_identity_sha256"] !=
            receipt["source_candidate_identity_sha256"], "Old/current reuse identities differ from actual full inventories")
    require(old_run["stage"] == "semantic" and old_run["budget"]["planned_calls"] ==
            old_run["budget"]["maximum_calls"] == 70 and old_manifest["config"] == old_config and
            old_manifest["plan_sha256"] == file_hash(paths["source_plan"]) and
            old_report["manifest_sha256"] == digest(old_manifest), "Original semantic registration/manifest changed")
    condition = condition_value(old_config, old_plan)
    require(condition == condition_value(config, plan) and digest(condition) == receipt["conditions_sha256"],
            "Reuse requires all inference settings, full scope, Expected and criteria unchanged")
    require(old_plan["purpose"] == "phase11-known-bilingual-semantic-diagnostics" and
            old_plan["verification_mode"] == "claimwise-v1" and old_plan["max_completion_attempts"] ==
            old_report["completion_attempts_recorded"] == 70 and
            old_report["diagnostic_gate_passed"] is True and not old_report["not_attempted_ids"] and
            old_report["planned_conditions"] == old_report["completed_conditions"] == 2 * len(old_plan["cases"]) and
            old_report["cost_incomplete"] is False, "Reuse requires complete passing fully costed original seventy calls")
    current_identity, previous_identity = receipt["current_identity_files"], old_run["identity_files"]
    for component in COMPONENTS - {"core"}:
        require(sorted(current_identity[component], key=lambda row: row["path"]) ==
                sorted(previous_identity[component], key=lambda row: row["path"]), "Model/Runtime/Prompt/Sampler/Schema changed")
        for item in current_identity[component]:
            bound(root, item)
    current_core = {item["path"]: item["sha256"] for item in current_identity["core"]}
    old_core = {item["path"]: item["sha256"] for item in previous_identity["core"]}
    actual_core = {path.relative_to(root).as_posix(): file_hash(path) for path in sorted((root / "src/rag_research").rglob("*.py"))}
    require(current_core == actual_core and set(current_core) == set(old_core) | {ADDED_SOURCE} and
            ADDED_SOURCE not in old_core, "Current full source inventory must contain only the declared new helper")
    snapshots = receipt["source_snapshots"]
    require(isinstance(snapshots, dict) and set(snapshots) == set(old_core), "Preserve every original source file")
    for name, old_sha in old_core.items():
        snapshot = bound(root, snapshots[name])
        require(snapshot.is_relative_to(root / "data/sourceproof") and snapshots[name]["sha256"] == old_sha,
                "Original source snapshot differs from executed identity")
        if current_core[name] != old_sha:
            source_boundary(name, snapshot.read_text(), (root / name).read_text())
    source = paths["source_report"].parent
    require((source / ".run.lock").is_file() and (source / ".run.lock").stat().st_size > 0 and
            run_snapshot(source) == receipt["source_run_files_sha256"], "Original diagnostic evidence changed")
    if replay:
        from rag_research.experiments.bilingual_certification import verify_prerequisite

        selected_report = Path(report_override).resolve() if report_override is not None else paths["source_report"]
        require(selected_report.is_relative_to(root / "data/runs/semantic_diagnostics") and
                run_snapshot(selected_report.parent) == receipt["source_run_files_sha256"], "Replay copy differs from original evidence")

        def replay_copy():
            with tempfile.TemporaryDirectory(prefix=".reuse-replay-", dir=root / "data/runs/semantic_diagnostics") as temporary:
                target = Path(temporary) / "run"
                shutil.copytree(selected_report.parent, target)
                verify_prerequisite(target / "report.json", paths["source_config"])
                require(run_snapshot(target) == receipt["source_run_files_sha256"], "Read-only semantic replay changed saved raw evidence")

        # Always replay a copy and compare every original byte before/after.
        # Main certification may already hold the canonical run's flock while
        # validate_main recursively reloads its Known prerequisite. This helper
        # neither mutates nor reacquires the original lock in that path.
        replay_copy()
        require(run_snapshot(source) == receipt["source_run_files_sha256"], "Original evidence changed during replay")
    return {"receipt": receipt, "source_config": old_config, "source_plan": old_plan,
            "source_report": old_report, "source_manifest": old_manifest, "paths": paths,
            "new_model_calls": 0, "new_model_servers": 0}


def validate_reuse(config, plan=None, *, root, report_override=None):
    receipt_path = bound(Path(root).resolve(), config[FIELD])
    receipt = read_json(receipt_path)
    plan = read_json(bound(Path(root).resolve(), receipt["current_plan"])) if plan is None else plan
    return validate_receipt(receipt, config, plan, root=root, report_override=report_override)


def reused_bindings(config, *, root):
    """Complete file closure for the existing Main -> Cal -> Freeze seals."""
    root = Path(root).resolve()
    receipt_path = bound(root, config[FIELD])
    receipt = read_json(receipt_path)
    plan_path = bound(root, receipt["current_plan"])
    checked = validate_receipt(receipt, config, read_json(plan_path), root=root, replay=False)
    result = {receipt_path.relative_to(root).as_posix(): file_hash(receipt_path),
              plan_path.relative_to(root).as_posix(): file_hash(plan_path)}
    for path in checked["paths"].values():
        result[path.relative_to(root).as_posix()] = file_hash(path)
    for item in receipt["source_snapshots"].values():
        result[item["path"]] = item["sha256"]
    for rows in receipt["current_identity_files"].values():
        for item in rows:
            result[item["path"]] = item["sha256"]
    return result


def create_receipt(*, root, source_report, source_config, source_run_plan, source_checkout,
                   current_config, current_plan, current_identity_files, output, snapshot_directory):
    """Issue a receipt only after complete cached replay; current config is not self-hashed.

    Pass unmodified current config/plan values with their new actual identity.
    Write the returned binding into the current config only after this succeeds.
    The source checkout is read only. No inference client or server is started.
    """
    root, output, snapshot_directory = Path(root).resolve(), Path(output).resolve(), Path(snapshot_directory).resolve()
    require(output.is_relative_to(root / "data/manifests") and not output.exists() and
            snapshot_directory.is_relative_to(root / "data/sourceproof") and not snapshot_directory.exists(),
            "Preserve original receipts and source snapshots")
    source_config_path, source_report_path = Path(source_config).resolve(), Path(source_report).resolve()
    old_config = yaml.safe_load(source_config_path.read_text())
    old_plan_path = root / old_config["diagnostics"]
    current_plan_path = root / current_config["diagnostics"]
    require(current_plan_path.is_file() and read_json(current_plan_path) == current_plan,
            "Write the new non-executed semantic condition plan before issuing its receipt")
    old_run = read_json(source_run_plan)
    snapshots = {}
    for item in old_run["identity_files"]["core"]:
        original = (Path(source_checkout).resolve() / item["path"]).resolve()
        require(original.is_relative_to(Path(source_checkout).resolve()) and original.is_file() and
                file_hash(original) == item["sha256"], "Fixed source checkout differs from original run identity")
        target = snapshot_directory / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(original.read_bytes())
        snapshots[item["path"]] = binding(root, target)
    receipt = {"schema_version": 1, "purpose": "phase11-non-inference-semantic-evidence-reuse", "version": VERSION,
               "status": "verified_reuse_not_new_experiment", "created_at_utc": datetime.now(UTC).isoformat(),
               "source_report": binding(root, source_report_path),
               "source_manifest": binding(root, source_report_path.parent / "manifest.json"),
               "source_config": binding(root, source_config_path), "source_plan": binding(root, old_plan_path),
               "current_plan": binding(root, current_plan_path),
               "source_run_plan": binding(root, Path(source_run_plan)),
               "source_candidate_identity_sha256": old_config["candidate_identity_sha256"],
               "candidate_identity_sha256": current_config["candidate_identity_sha256"],
               "conditions_sha256": digest(condition_value(old_config, read_json(old_plan_path))),
               "current_identity_files": deepcopy(current_identity_files), "source_snapshots": snapshots,
               "source_run_files_sha256": run_snapshot(source_report_path.parent),
               "reused_native_calls": 70, "new_model_calls": 0, "new_model_servers": 0}
    validate_receipt(receipt, current_config, current_plan, root=root)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Do not create a new semantic report or rewrite the source Manifest.
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return binding(root, output)
