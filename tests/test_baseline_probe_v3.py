"""Exercise the new entrypoint with fake tokenization and zero native processes."""

import importlib.util
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from rag_research.generation.local import GenerationError

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "baseline_probe_v3", REPO / "scripts/probe_phase11_baseline_v3.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class FakeClient:
    def __init__(self, fail=False):
        self.completion_attempts, self.rendered, self.fail = 0, [], fail
        self.on_call = None

    def render(self, messages):
        text = json.dumps(messages, ensure_ascii=False)
        self.rendered.append(text)
        return text

    def tokenize(self, text, *, special=False):
        return list(map(ord, text))

    def detokenize(self, tokens):
        return "".join(map(chr, tokens))

    def complete(self, tokens, config):
        self.completion_attempts += 1
        if self.on_call:
            self.on_call()
        assert config.max_output_tokens == 512 and config.timeout_seconds == 300
        if self.fail:
            raise GenerationError("fake response lost after submission")
        return {"content": "A supported answer [p1].", "tokens": [1, 2, 3],
                "stop_type": "eos", "truncated": False}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(probe, "ROOT", root)
    monkeypatch.chdir(root)
    monkeypatch.setattr(probe, "subprocess", SimpleNamespace(check_output=lambda *a, **k: "a" * 40))
    script = root / "scripts/probe_phase11_baseline_v3.py"
    script.parent.mkdir()
    script.write_text("fake source fixture; no native implementation")
    monkeypatch.setattr(probe, "__file__", str(script))

    def write(name, value):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False))
        return path

    def binding(path):
        return {"path": str(path.relative_to(root)), "sha256": probe.file_hash(path)}

    original = yaml.safe_load((REPO / "configs/phase11_bilingual_baseline_v1.yaml").read_text())
    origin = write("configs/old-baseline.yaml", original)
    config = deepcopy(original)
    config["execution"]["runtime_spec"] = probe.GRAPH_OFF_SPEC
    config_path = write("configs/new-baseline.yaml", config)
    runtime = {"tag": "b11433", "source_commit": "fixed-fixture", "backend": "fake-graph-off"}
    monkeypatch.setattr(probe, "execution_identity", lambda c: {
        "execution": c["execution"], "runtime": runtime})
    prior = write("data/manifests/old-generation.json", {"model": probe.model_identity()})
    prompts, targets = {}, []
    for language, directory in probe.KNOWN_RUNS.items():
        prompt = {"version": f"unchanged-{language}", "system": "Use supplied passages."}
        prompt_path = write(f"configs/phase11_bilingual_initial_{language}_v1.yaml", prompt)
        prompts[language] = binding(prompt_path)
        identifier = "known-" + language
        manifest = write(directory + "/manifest.json", {"language": language, "config": {
            "execution_scope": "connection_smoke_only", "data": {"record_ids": [identifier]}}})
        documents = [{"passage_id": "p1", "title": "Exact title", "text": "本文 full evidence."}]
        question = "Question <|im_start|> with data, unchanged?"
        record = write(directory + "/baseline/fixture/record.json", {"status": "ok",
            "record_id": identifier, "question": question, "used_context": documents,
            "prompt_spec": prompt, "gold": "SECRET_GOLD", "answer": "SECRET_OLD_RESPONSE"})
        inputs = {"question": question, "documents": documents}
        targets.append({"target_id": f"baseline/{language}/{identifier}", "language": language,
            "record_id": identifier, "source_manifest": binding(manifest),
            "source_record": binding(record), "initial_prompt": prompts[language], **inputs,
            "input_sha256": probe.digest(inputs)})
    identity = {"schema_version": 3, "purpose": "phase11-baseline-graph-off-identity-v3",
        "status": "preregistered_pending_baseline_smoke", "phase12_allowed": False,
        "judge_candidate_identity_sha256": probe.JUDGE_IDENTITY,
        "baseline_config": binding(config_path), "baseline_origin": binding(origin),
        "prior_generation_identity": binding(prior), "model": probe.model_identity(),
        "runtime": runtime, "execution": config["execution"], "generation": config["generation"],
        "initial_prompts": prompts}
    identity_path = write("data/manifests/new-generation.json", identity)
    plan = {"schema_version": 3, "purpose": "phase11-baseline-known-runtime-probe-v3",
        "status": "preregistered", "source_scope": "known_development_connection_only",
        "judge_candidate_identity_sha256": probe.JUDGE_IDENTITY, "maximum_calls": 2,
        "automatic_retries": 0, "phase12_allowed": False,
        "baseline_config": binding(config_path), "generation_identity": binding(identity_path),
        "targets": targets}
    plan_path = write("configs/probes.json", plan)
    output = root / "data/runs/runtime_screening/fresh"
    ledger_path = root / "data/runs/fake-ledger/ledger.json"

    def register(mode="smoke"):
        calls = 0 if mode == "preflight" else 2
        command = [str(script.relative_to(root)), "--mode", mode, "--config",
            str(config_path.relative_to(root)), "--probe-plan", str(plan_path.relative_to(root)),
            "--output-dir", str(output.relative_to(root))]
        value = {"version": "phase11-autonomy-v3", "runs": [{"run_id": "fake-run",
            "state": "running", "plan": {"stage": mode,
                "candidate_identity_sha256": probe.JUDGE_IDENTITY,
                "budget": {"planned_calls": calls, "maximum_calls": calls},
                "automatic_retries": 0, "phase12_allowed": False,
                "targets": [t["target_id"] for t in targets],
                "output_dir": str(output.relative_to(root)), "command": command,
                "bindings": [binding(p) for p in (script, config_path, plan_path, identity_path)]}}]}
        write(str(ledger_path.relative_to(root)), value)

    register()
    monkeypatch.setenv("RAG_PHASE11_AUTONOMY_CONTEXT", json.dumps({
        "ledger_dir": str(ledger_path.parent), "run_id": "fake-run"}))
    client = FakeClient()
    starts = []

    class FakeServer:
        def __init__(self, generation, path, **kwargs):
            starts.append(path)
            self.client = client

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def report(self):
            return {"full_gpu_offload": True, "server_context_tokens": 4096,
                    "fake_server_no_native_process": True}

    monkeypatch.setattr(probe, "LocalServer", FakeServer)
    return SimpleNamespace(root=root, config=config_path, plan_path=plan_path, plan=plan,
        write=write, client=client, starts=starts, register=register, output=output)


@pytest.mark.parametrize("mode,calls", [("preflight", 0), ("smoke", 2)])
def test_exact_payloads_exclude_source_gold_and_preserve_all_body_and_ids(setup, mode, calls):
    setup.register(mode)
    report = probe.run(mode, setup.config, setup.plan_path, setup.output)
    assert report["runtime_health_passed"] and report["completion_attempts_recorded"] == calls
    assert setup.client.completion_attempts == calls and len(setup.starts) == 1
    for index, target in enumerate(setup.plan["targets"], 1):
        saved = json.loads((setup.output / f"prepared-{index}.json").read_text())
        assert saved["used_context"] == target["documents"]
        assert all(not row["truncated"] and not row["omitted"] for row in saved["context_audit"])
        assert "\\u003c" in saved["messages"][1]["content"]
    assert "SECRET_GOLD" not in "".join(setup.client.rendered)
    assert "SECRET_OLD_RESPONSE" not in "".join(setup.client.rendered)


def test_existing_output_never_sends_a_second_copy_of_either_request(setup):
    probe.run("smoke", setup.config, setup.plan_path, setup.output)
    with pytest.raises(ValueError, match="fresh output"):
        probe.run("smoke", setup.config, setup.plan_path, setup.output)
    assert setup.client.completion_attempts == 2 and len(setup.starts) == 1


def test_unknown_stops_before_second_target_and_never_imputes_zero_output_cost(setup):
    setup.client.fail = True

    def check_before_response():
        journal = json.loads((setup.output / "probe-1.json").read_text())
        assert journal["completion_attempted"] and journal["cost_incomplete"]
        assert journal["status"] == "started" and journal["runtime_response"] is None

    setup.client.on_call = check_before_response
    report = probe.run("smoke", setup.config, setup.plan_path, setup.output)
    assert not report["runtime_health_passed"] and report["completion_attempts_recorded"] == 1
    assert report["unknown_responses"] == 1 and report["total_output_tokens"] is None
    saved = json.loads((setup.output / "probe-1.json").read_text())
    assert saved["cost_incomplete"] and saved["runtime_response"] is None
    assert not (setup.output / "probe-2.json").exists()


def test_nonwhitelisted_target_fields_and_draft_plans_fail_before_server_start(setup):
    setup.plan["targets"][0]["gold"] = "forbidden"
    setup.plan_path.write_text(json.dumps(setup.plan))
    with pytest.raises(ValueError, match="Unexpected probe fields"):
        probe.run("preflight", setup.config, setup.plan_path, setup.output)
    del setup.plan["targets"][0]["gold"]
    setup.plan["status"] = "draft_not_registered"
    setup.plan_path.write_text(json.dumps(setup.plan))
    with pytest.raises(ValueError, match="registered two-known-input"):
        probe.run("preflight", setup.config, setup.plan_path, setup.output)
    assert not setup.starts and setup.client.completion_attempts == 0


def test_main_scope_cannot_masquerade_as_a_known_connection(setup):
    target = setup.plan["targets"][0]
    path = setup.root / target["source_manifest"]["path"]
    value = json.loads(path.read_text())
    value["config"]["execution_scope"] = "main_development_v1"
    path.write_text(json.dumps(value))
    target["source_manifest"]["sha256"] = probe.file_hash(path)
    setup.plan_path.write_text(json.dumps(setup.plan))
    with pytest.raises(ValueError, match="Never substitute a Main/Cal"):
        probe.run("preflight", setup.config, setup.plan_path, setup.output)
    assert not setup.starts


def test_custom_probe_plan_must_be_hash_bound_by_the_supervisor(setup):
    setup.plan["rationale"] = "Changed metadata still needs a new registered hash."
    setup.plan_path.write_text(json.dumps(setup.plan))
    with pytest.raises(ValueError, match="Supervisor must bind"):
        probe.run("smoke", setup.config, setup.plan_path, setup.output)
    assert not setup.starts and setup.client.completion_attempts == 0
