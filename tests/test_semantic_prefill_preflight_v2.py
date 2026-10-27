"""Artificial90 inputs only; no model, Runtime, GPU command, tokenizer or QA."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from rag_research.generation.auxiliary_config import AuxiliaryGenerationConfig

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prefill_preflight_v2_test", ROOT / "scripts/preflight_semantic_model_v2.py")
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


def test_unknown_render_suffix_is_preserved_before_tokenization_or_native(tmp_path):
    class Client:
        def render(self, messages):
            return "<|im_start|>user\n"

        def tokenize(self, *args, **kwargs):
            pytest.fail("Malformed suffix must fail before tokenization")

    path = tmp_path / "input.json"
    with pytest.raises(ValueError, match="exact bare or prefilled"):
        preflight.prepare_input(Client(), [{"role": "user", "content": "Invented."}],
            SimpleNamespace(reasoning_prefill_mode="chatml_think_suffix_v1"), path)
    saved = json.loads(path.read_text())
    assert saved["status"] == "failed" and saved["raw_rendered_prompt"] == "<|im_start|>user\n"


@pytest.mark.parametrize("planned,passes", [(90, True), (91, False)])
def test_every_full_input_counts_and_saves_effective_prefill_with_native_zero(tmp_path, monkeypatch, planned, passes):
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "config.yaml"
    config_path.write_text("invented: true\n")
    output = tmp_path / "data/runs/model_screening/invented-only"
    settings = AuxiliaryGenerationConfig(context_tokens=12288, max_output_tokens=512,
        temperature=0.2, reasoning_budget_tokens=4096, reasoning_prefill_mode="chatml_think_suffix_v1")
    monkeypatch.setattr(preflight, "load_config", lambda path: (
        {"verification_mode": "claimwise-v1"}, {"max_completion_attempts": planned},
        {"en": {}, "ja": {}}, config_path))
    monkeypatch.setattr(preflight, "task_config", lambda *a: settings)
    monkeypatch.setattr(preflight, "auxiliary_identity", lambda config: {"fixture_only": True})
    monkeypatch.setattr(preflight, "auxiliary_server_kwargs", lambda config: {})
    case = {"question": "Invented Q?", "answer": "Invented A.", "claims": [{"claim_id": "c1", "text": "Invented A."}],
        "documents": [{"passage_id": "a", "title": "A", "text": "Invented source."}]}
    monkeypatch.setattr(preflight, "specs", lambda plan: [({**case, "language": "ja" if index % 2 else "en"},
        "original" if index % 2 else "reversed", f"invented-{index}") for index in range(90)])
    monkeypatch.setattr(preflight, "build_messages", lambda prompts, task, payload: [
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])

    class Client:
        completion_attempts = 0

        def render(self, messages):
            return json.dumps(messages, ensure_ascii=False) + "<|im_start|>assistant\n"

        def tokenize(self, text, *, special):
            assert special
            return list(map(ord, text))  # Invented character IDs, not a real tokenizer.

        def complete(self, *args, **kwargs):
            pytest.fail("Every preflight input must remain Native0")

    class Server:
        def __init__(self, *args, **kwargs):
            self.client = Client()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def report(self):
            return {"fixture_only": True, "full_gpu_offload": True}

    monkeypatch.setattr(preflight, "LocalServer", Server)
    monkeypatch.setattr(preflight.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="invented GPU observation"))
    monkeypatch.setattr(sys, "argv", ["preflight-test", "--config", str(config_path), "--output-dir", str(output)])
    if passes:
        preflight.main()
    else:
        with pytest.raises(ValueError, match="every planned full input"):
            preflight.main()
    rows = json.loads((output / "prepared-inputs.json").read_text())
    assert len(rows) == 90 and len({row["condition"] for row in rows}) == 90
    for row in rows:
        assert row["rendered_prompt"] == row["raw_rendered_prompt"] + "<think>\n"
        assert row["prompt_tokens"] == row["raw_prompt_tokens"] + list(map(ord, "<think>\n"))
        assert row["reasoning_prefill_audit"]["applied"] is True
        assert row["input_tokens"] == len(row["prompt_tokens"]) and row["fits"] is True
    report = json.loads((output / "report.json").read_text())
    assert report["completion_attempts"] == 0
    assert report["status"] == ("passed" if passes else "failed")
