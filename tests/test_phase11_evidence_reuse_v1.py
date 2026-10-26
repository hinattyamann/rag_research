"""Reuse guards use invented evidence and explicit protocol/replay doubles.

No native model is invoked; these are software checks, not research adoption.
"""

import ast
from copy import deepcopy

import pytest
import yaml

from rag_research.experiments import bilingual_certification, semantic_diagnostics
from rag_research.experiments import evidence_reuse as module
from rag_research.experiments.frozen_trace import digest
from rag_research.experiments.storage import read_json, run_lock, write_json
from rag_research.retrieval.common import file_hash

_REAL_VERIFY_PREREQUISITE = bilingual_certification.verify_prerequisite


def put(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.fixture
def reuse(tmp_path, monkeypatch):
    root = tmp_path
    (root / "configs").mkdir()
    events = []

    def chains(*values, root):
        assert root == tmp_path
        assert len({value["candidate_identity_sha256"] for value in values}) == 1
        events.append(("chain", values[0]["candidate_identity_sha256"]))

    monkeypatch.setattr(module, "validate_chain_identity", chains)
    old_sources = {
        module.PREFIX + "bilingual_runner.py":
            'def _run(rows, main):\n    selection = [{"record_id": r["record_id"], "question": r["question"]} for r in rows]\n    return selection\n',
        module.PREFIX + "semantic_diagnostics.py":
            'def load_config(path):\n    regression = True\n    if regression:\n        if chain:\n            validate_chain_identity(config, plan, prior_manifest, prior_report, prior_plan, prior_manifest["config"], root=ROOT)\n        require(config == prior_manifest["config"], "Known regression must use the passing candidate settings")\n    return path\n',
        module.PREFIX + "bilingual_certification.py":
            'def adopted_sources(paths):\n    for row in paths:\n        require(candidate_path.is_relative_to(ROOT / "configs"), "Adopted candidate must stay in configs")\n    return paths\ndef verify_prerequisite(report_path, candidate_path):\n    config, plan, prompts, plan_path = semantic_diagnostics.load_config(candidate_path)\n    return config\n',
        "src/rag_research/evaluation/schema.py": "SCHEMA = 1\n",
        "src/rag_research/evaluation/tasks.py": "def execute_task(client):\n    return client\n",
        "src/rag_research/generation/local.py": "def unchanged_generation():\n    return 1\n",
    }
    old_checkout = root / "old-checkout"
    old_core = []
    for name, text in old_sources.items():
        put(old_checkout, name, text)
        put(root, name, text)
        old_core.append({"path": name, "sha256": file_hash(root / name)})
    put(root, module.PREFIX + "bilingual_runner.py",
        'def _run(rows, main):\n    selection = [{k: r[k] for k in (("record_id", "question", "document_group_id") if main else ("record_id", "question"))} for r in rows]\n    return selection\n')
    # Build a legal source scaffold; the receipt tests below exercise independent
    # metadata, identity, evidence and replay faults rather than this scaffold.
    diagnostic_tree = ast.parse(old_sources[module.PREFIX + "semantic_diagnostics.py"])
    loader = diagnostic_tree.body[0]
    loader.args.kwonlyargs.append(ast.arg(arg="allow_reused_view"))
    loader.args.kw_defaults.append(ast.Constant(value=False))
    loader.body[1] = module.repaired_prerequisite_branch(loader.body[1])
    put(root, module.PREFIX + "semantic_diagnostics.py", ast.unparse(ast.fix_missing_locations(diagnostic_tree)))
    certificate_tree = ast.parse(old_sources[module.PREFIX + "bilingual_certification.py"])
    certificate_tree.body = [module.repaired_certificate_function(node) for node in certificate_tree.body]
    put(root, module.PREFIX + "bilingual_certification.py", ast.unparse(ast.fix_missing_locations(certificate_tree)))
    put(root, module.ADDED_SOURCE, '"""Synthetic helper inventory only."""\n')
    components = {}
    for component in module.COMPONENTS - {"core"}:
        path = put(root, "assets/" + component, component)
        components[component] = [{"path": path.relative_to(root).as_posix(), "sha256": file_hash(path)}]
    old_identity = {**deepcopy(components), "core": old_core}
    current_identity = {**deepcopy(components), "core": [
        {"path": path.relative_to(root).as_posix(), "sha256": file_hash(path)}
        for path in sorted((root / "src/rag_research").rglob("*.py"))]}
    old_id, current_id = module.identity_digest(old_identity), module.identity_digest(current_identity)
    old_config = {"schema_version": 1, "purpose": "phase11-bilingual-semantic-candidate", "study_version": "old",
                  "diagnostics": "configs/old-plan.json", "candidate_identity_sha256": old_id,
                  "sampling": {"seed": 42}, "tasks": {"verify_claims": {"max_tokens": 6144}},
                  "prompts": {"en": "unchanged", "ja": "unchanged"}}
    old_plan = {"purpose": "phase11-known-bilingual-semantic-diagnostics", "verification_mode": "claimwise-v1",
                "max_completion_attempts": 70, "cases": [{"id": "invented-test-only", "expected": {"c1": "supported"}}],
                "gate": {"test": "unchanged"}, "candidate_identity_sha256": old_id}
    current_config = {**deepcopy(old_config), "study_version": "new-not-executed",
                      "diagnostics": "configs/current-plan.json", "candidate_identity_sha256": current_id}
    current_plan = {**deepcopy(old_plan), "candidate_identity_sha256": current_id,
                    "change": "Group metadata only; no fresh semantic execution"}
    write_json(root / "configs/old-plan.json", old_plan)
    write_json(root / "configs/current-plan.json", current_plan)
    put(root, "configs/old.yaml", yaml.safe_dump(old_config))
    run = root / "data/runs/semantic_diagnostics/original"
    run.mkdir(parents=True)
    (run / ".run.lock").write_text("0")
    manifest = {"config": old_config, "plan_sha256": file_hash(root / "configs/old-plan.json"),
                "candidate_identity_sha256": old_id}
    write_json(run / "manifest.json", manifest)
    report = {"candidate_identity_sha256": old_id, "manifest_sha256": digest(manifest),
              "completion_attempts_recorded": 70, "diagnostic_gate_passed": True, "not_attempted_ids": [],
              "planned_conditions": 2, "completed_conditions": 2, "cost_incomplete": False}
    write_json(run / "report.json", report)
    write_json(root / "configs/old-run-plan.json", {"identity_files": old_identity,
        "candidate_identity_sha256": old_id, "stage": "semantic", "budget": {"planned_calls": 70, "maximum_calls": 70}})

    def replay(report_path, candidate_path):
        assert ".reuse-replay-" in str(report_path)
        assert candidate_path == root / "configs/old.yaml"
        assert read_json(report_path) == report
        events.append(("cached_replay", str(report_path)))

    monkeypatch.setattr(bilingual_certification, "verify_prerequisite", replay)
    args = {"root": root, "source_report": run / "report.json", "source_config": root / "configs/old.yaml",
            "source_run_plan": root / "configs/old-run-plan.json", "source_checkout": old_checkout,
            "current_config": current_config, "current_plan": current_plan,
            "current_identity_files": current_identity, "output": root / "data/manifests/reuse.json",
            "snapshot_directory": root / "data/sourceproof/reuse"}
    binding = module.create_receipt(**args)
    current_config[module.FIELD] = binding
    return root, current_config, current_plan, binding, args, events


def test_receipt_keeps_two_identities_and_replays_only_copy_without_new_calls(reuse):
    root, config, plan, receipt_binding, _, events = reuse
    before = module.run_snapshot(root / "data/runs/semantic_diagnostics/original")
    result = module.validate_reuse(config, plan, root=root)
    receipt = read_json(root / receipt_binding["path"])
    assert receipt["candidate_identity_sha256"] != receipt["source_candidate_identity_sha256"]
    assert result["new_model_calls"] == result["new_model_servers"] == 0
    assert before == module.run_snapshot(root / "data/runs/semantic_diagnostics/original")
    assert sum(event[0] == "cached_replay" for event in events) == 2
    closure = module.reused_bindings(config, root=root)
    assert closure[receipt_binding["path"]] == receipt_binding["sha256"]
    assert "configs/current-plan.json" in closure and "configs/old.yaml" in closure
    assert all(item["path"] in closure for item in receipt["source_snapshots"].values())


@pytest.mark.parametrize("change", ["sampling", "prompt", "output_budget", "expected", "full_scope", "gate"])
def test_reject_changed_inference_settings_expected_scope_or_criteria(reuse, change):
    root, config, plan, receipt_binding, _, _ = reuse
    receipt = read_json(root / receipt_binding["path"])
    if change == "sampling":
        config["sampling"]["seed"] = 43
    elif change == "prompt":
        config["prompts"]["ja"] = "different prompt"
    elif change == "output_budget":
        config["tasks"]["verify_claims"]["max_tokens"] = 1
    elif change == "expected":
        plan["cases"][0]["expected"]["c1"] = "not_supported"
    elif change == "full_scope":
        plan["cases"] = []
    else:
        plan["gate"]["test"] = "changed"
    if change in {"expected", "full_scope", "gate"}:
        write_json(root / "configs/current-plan.json", plan)
        receipt["current_plan"] = module.binding(root, root / "configs/current-plan.json")
    with pytest.raises(ValueError, match="unchanged"):
        module.validate_receipt(receipt, config, plan, root=root)


@pytest.mark.parametrize("fault", ["failed", "unknown", "partial", "missing", "rewritten_raw"])
def test_reject_nonpassing_incomplete_unknown_or_changed_original_evidence(reuse, fault):
    root, config, plan, receipt_binding, _, _ = reuse
    receipt = read_json(root / receipt_binding["path"])
    path = root / receipt["source_report"]["path"]
    report = read_json(path)
    if fault == "missing":
        path.unlink()
    else:
        if fault == "failed":
            report["diagnostic_gate_passed"] = False
        elif fault == "unknown":
            report["cost_incomplete"] = True
        elif fault == "partial":
            report["completion_attempts_recorded"] = 69
        else:
            (path.parent / "unregistered-task.json").write_text('{"changed":true}')
        write_json(path, report)
        receipt["source_report"] = module.binding(root, path)
    with pytest.raises(ValueError):
        module.validate_receipt(receipt, config, plan, root=root)


@pytest.mark.parametrize("component", ["model", "runtime", "prompt", "sampler", "schema"])
def test_reject_changed_noncore_component_even_with_updated_current_id(reuse, component):
    root, config, plan, receipt_binding, _, _ = reuse
    receipt = read_json(root / receipt_binding["path"])
    receipt["current_identity_files"][component][0]["sha256"] = "0" * 64
    new_id = module.identity_digest(receipt["current_identity_files"])
    config["candidate_identity_sha256"] = plan["candidate_identity_sha256"] = receipt["candidate_identity_sha256"] = new_id
    write_json(root / "configs/current-plan.json", plan)
    receipt["current_plan"] = module.binding(root, root / "configs/current-plan.json")
    with pytest.raises(ValueError, match="Model/Runtime/Prompt/Sampler/Schema"):
        module.validate_receipt(receipt, config, plan, root=root)


def test_reject_native_core_change_even_when_new_inventory_and_id_are_truthful(reuse):
    root, config, plan, receipt_binding, _, _ = reuse
    receipt = read_json(root / receipt_binding["path"])
    path = root / "src/rag_research/generation/local.py"
    path.write_text("def changed_generation():\n    return 2\n")
    for item in receipt["current_identity_files"]["core"]:
        if item["path"] == path.relative_to(root).as_posix():
            item["sha256"] = file_hash(path)
    new_id = module.identity_digest(receipt["current_identity_files"])
    config["candidate_identity_sha256"] = plan["candidate_identity_sha256"] = receipt["candidate_identity_sha256"] = new_id
    write_json(root / "configs/current-plan.json", plan)
    receipt["current_plan"] = module.binding(root, root / "configs/current-plan.json")
    with pytest.raises(ValueError, match="Native or unregistered"):
        module.validate_receipt(receipt, config, plan, root=root)


def test_group_metadata_proof_rejects_any_other_runner_change(reuse):
    root, _, _, _, args, _ = reuse
    name = module.PREFIX + "bilingual_runner.py"
    old = (args["source_checkout"] / name).read_text()
    current = (root / name).read_text()
    module.source_boundary(name, old, current)
    with pytest.raises(ValueError, match="boundary"):
        module.source_boundary(name, old, current.replace("return selection", "return []"))


def test_replay_must_not_modify_even_the_copied_saved_evidence(reuse, monkeypatch):
    root, config, plan, _, _, _ = reuse

    def modifies(report_path, candidate_path):
        report_path.write_text("changed")

    monkeypatch.setattr(bilingual_certification, "verify_prerequisite", modifies)
    with pytest.raises(ValueError, match="changed saved raw"):
        module.validate_reuse(config, plan, root=root)


def test_mismatched_replay_copy_rejected_without_replay(reuse):
    root, config, plan, _, _, events = reuse
    wrong = root / "data/runs/semantic_diagnostics/wrong"
    wrong.mkdir()
    write_json(wrong / "report.json", {"different": True})
    before = list(events)
    with pytest.raises(ValueError, match="copy differs"):
        module.validate_reuse(config, plan, root=root, report_override=wrong / "report.json")
    assert not any(event[0] == "cached_replay" for event in events[len(before):])


@pytest.mark.parametrize("filename,function_name", [
    ("semantic_diagnostics.py", "load_config"),
    ("bilingual_certification.py", "verify_prerequisite"),
    ("bilingual_certification.py", "adopted_sources"),
])
def test_readonly_source_insertions_reject_extra_native_statement(reuse, filename, function_name):
    root, _, _, _, args, _ = reuse
    name = module.PREFIX + filename
    old_text, current_text = (args["source_checkout"] / name).read_text(), (root / name).read_text()
    tree = ast.parse(current_text)
    target = module.function(tree, function_name)
    if filename == "semantic_diagnostics.py":
        target = [node for node in target.body if isinstance(node, ast.If)][0]
    target.body.append(ast.parse("LocalServer().complete()").body[0])
    with pytest.raises(ValueError, match="exact registered"):
        module.source_boundary(name, old_text, ast.unparse(ast.fix_missing_locations(tree)))


def test_current_candidate_receipt_routes_certification_to_explicit_zero_call_replay(reuse, monkeypatch):
    root, config, plan, _, _, events = reuse
    # Invoke the real dispatch function; only the cached old verifier remains a
    # double so this software test cannot be mistaken for real 70-call evidence.
    real = _REAL_VERIFY_PREREQUISITE
    path = put(root, "configs/current.yaml", yaml.safe_dump(config))
    monkeypatch.setattr(bilingual_certification, "ROOT", root)
    loads = []

    def load(path, **kwargs):
        loads.append(kwargs)
        return config, plan, {}, root / "configs/current-plan.json"

    monkeypatch.setattr(semantic_diagnostics, "load_config", load)
    before = len(events)
    real(root / "data/runs/semantic_diagnostics/original/report.json", path)
    assert loads == [{"allow_reused_view": True}]
    assert sum(event[0] == "cached_replay" for event in events[before:]) == 1


def test_reused_semantic_view_cannot_start_fresh_native_run(tmp_path, monkeypatch):
    monkeypatch.setattr(semantic_diagnostics, "ROOT", tmp_path)
    monkeypatch.setattr(semantic_diagnostics, "validate_chain_identity", lambda *args, **kwargs: None)
    monkeypatch.chdir(tmp_path)
    path = put(tmp_path, "config.yaml", yaml.safe_dump({"schema_version": 1,
        "purpose": "phase11-bilingual-semantic-candidate", "status": "candidate_not_frozen", "phase12_allowed": False,
        "diagnostics": "plan.json", "semantic_evidence_reuse": {"path": "not-read.json", "sha256": "0" * 64}}))
    write_json(tmp_path / "plan.json", {"schema_version": 1, "purpose": "phase11-known-bilingual-semantic-diagnostics",
        "phase12_allowed": False, "orders": ["original", "reversed"], "gate": {"stop_on_task_error": True,
        "stop_after_critical_failure": True, "critical_all_exact": True,
        "synthetic_min_accuracy_per_language": .9, "synthetic_max_false_support": 0}})

    def forbidden(*args, **kwargs):
        raise AssertionError("No Native server may start for a reused semantic view")

    monkeypatch.setattr(semantic_diagnostics, "LocalServer", forbidden)
    with pytest.raises(ValueError, match="read-only condition view"):
        semantic_diagnostics.run(path, tmp_path / "data/runs/semantic_diagnostics/forbidden")


def test_main_certificate_external_closure_contains_reuse_and_old_source_proof(reuse, monkeypatch):
    root, config, _, receipt_binding, _, _ = reuse
    monkeypatch.setattr(bilingual_certification, "ROOT", root)
    monkeypatch.setattr(bilingual_certification, "validate_chain_identity", lambda *args, **kwargs: None)
    current_path = put(root, "configs/current.yaml", yaml.safe_dump(config))
    source_report = root / "data/runs/semantic_diagnostics/original/report.json"
    known_plan = root / "configs/known.json"
    write_json(known_plan, {"source_sha256": {}, "prerequisite": {
        "report_path": source_report.relative_to(root).as_posix(), "sha256": file_hash(source_report)}})
    known_config = put(root, "configs/known.yaml", yaml.safe_dump({"diagnostics": "configs/known.json"}))
    known = root / "data/runs/semantic_diagnostics/known"
    known.mkdir()
    write_json(known / "report.json", {"synthetic": "known evidence only"})
    write_json(known / "manifest.json", {"plan_sha256": file_hash(known_plan)})
    policy = root / "configs/policy.json"
    write_json(policy, {"candidate_config": module.binding(root, current_path)})
    qa = put(root, "qa.synthetic", "Synthetic test fixture, not research QA")
    run = root / "data/runs/bilingual_development/en"
    run.mkdir(parents=True)
    write_json(run / "manifest.json", {"source_sha256": {}, "qa_path": "qa.synthetic", "qa_sha256": file_hash(qa),
        "config": {"adopted_known_regression": {**module.binding(root, known / "report.json"),
        "config": module.binding(root, known_config)}, "main_execution_policy": module.binding(root, policy)}})
    bound_files, roots, prerequisites = bilingual_certification.adopted_sources([{"run": run}])
    assert receipt_binding["path"] in bound_files
    assert "configs/old.yaml" in bound_files and "configs/current-plan.json" in bound_files
    receipt = read_json(root / receipt_binding["path"])
    assert all(item["path"] in bound_files for item in receipt["source_snapshots"].values())
    assert source_report.parent in roots and prerequisites[source_report] == current_path


def test_known_reuse_replay_respects_existing_main_certificate_source_lock(reuse):
    root, config, plan, _, _, _ = reuse
    source = root / "data/runs/semantic_diagnostics/original"
    with run_lock(source):
        result = module.validate_reuse(config, plan, root=root)
    assert result["new_model_calls"] == result["new_model_servers"] == 0
