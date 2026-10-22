"""Wrong precision labels must fail before downloads or experimental manifests."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def acquisition(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / "scripts/prepare_auxiliary_model.py"
    loader = importlib.util.spec_from_file_location("auxiliary_acquisition_fixture", source)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    state = {"downloads": 0, "metadata": 0}
    content = b"GGUF-fixture-not-a-real-model"

    def download(folder, name, size, sha, **kwargs):
        state["downloads"] += 1
        path = folder / name
        path.write_bytes(content)
        return path

    def metadata(*args, **kwargs):
        state["metadata"] += 1

    monkeypatch.setattr(module, "download_gguf", download)
    monkeypatch.setattr(module, "hf_hub_download", metadata)
    manifest = tmp_path / "data/manifests/candidate.json"
    manifest.parent.mkdir(parents=True)
    spec = {"model_id": "fixture/pinned-gguf", "revision": "fixed-revision", "directory": "fixture",
            "files": [{"name": "model-Q5_K_M.gguf", "bytes": len(content),
                       "sha256": hashlib.sha256(content).hexdigest()}], "runtime_options": {"jinja": True}}

    def invoke(value):
        path = tmp_path / "spec.json"
        path.write_text(json.dumps(value))
        monkeypatch.setattr(sys, "argv", [str(source), "--spec", str(path), "--manifest", str(manifest)])
        module.main()
        return json.loads(manifest.read_text())

    return invoke, spec, manifest, state, tmp_path


@pytest.mark.parametrize("explicit", [False, True])
def test_precision_identity_survives_real_manifest_serialization(acquisition, explicit):
    invoke, spec, manifest, state, _ = acquisition
    precision = "Q5_K_M" if explicit else "Q4_K_M"
    spec["files"][0]["name"] = "model-" + precision + ".gguf"
    if explicit:
        spec["quantization"] = precision
    result = invoke(spec)
    assert result["quantization"] == precision
    assert result["revision"] == spec["revision"] and result["runtime_options"] == {"jinja": True}
    assert result["files"][0]["sha256"] == spec["files"][0]["sha256"]
    assert manifest.exists() and state == {"downloads": 1, "metadata": 1}


@pytest.mark.parametrize("declaration", ["Q4_K_M", "omitted", None, True])
def test_q5_cannot_be_silently_recorded_as_q4_or_invalid_identity(acquisition, declaration):
    invoke, spec, manifest, state, root = acquisition
    if declaration != "omitted":
        spec["quantization"] = declaration
    with pytest.raises(ValueError, match="quantization"):
        invoke(spec)
    assert state == {"downloads": 0, "metadata": 0}
    assert not manifest.exists() and not (root / "data/models").exists()
