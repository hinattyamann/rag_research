"""Explicit auxiliary-model identity; never changes the baseline model constants."""

from rag_research.experiments.frozen_trace import require
from rag_research.experiments.protocol import ROOT
from rag_research.experiments.storage import read_json
from rag_research.generation.artifacts import model_identity
from rag_research.retrieval.common import file_hash


def auxiliary_identity(config):
    name = config.get("auxiliary_model_manifest")
    if name is None:
        return model_identity()
    path = (ROOT / name).resolve()
    require(path.is_relative_to(ROOT / "data/manifests"), "Unexpected auxiliary manifest path")
    manifest = read_json(path)
    require(manifest["schema_version"] == 1 and manifest["purpose"] == "development-auxiliary-model",
            "Unsupported auxiliary model manifest")
    require(manifest["files"] and len({f["path"] for f in manifest["files"]}) == len(manifest["files"]),
            "Missing/duplicate auxiliary model files")
    require(manifest["entrypoint"] in {f["path"] for f in manifest["files"]}, "Missing entrypoint")
    for artifact in manifest["files"]:
        candidate = (ROOT / artifact["path"]).resolve()
        require(candidate.is_relative_to(ROOT / "data/models") and candidate.suffix == ".gguf",
                "Auxiliary model escapes model directory")
    return {**manifest, "manifest_sha256": file_hash(path)}


def auxiliary_server_kwargs(config):
    if "auxiliary_model_manifest" not in config:
        return {}
    manifest = auxiliary_identity(config)
    for artifact in manifest["files"]:
        path = ROOT / artifact["path"]
        require(path.stat().st_size == artifact["bytes"] and file_hash(path) == artifact["sha256"],
                "Auxiliary model size/hash mismatch")
    options = manifest.get("runtime_options", {})
    require(set(options) <= {"jinja"} and type(options.get("jinja", False)) is bool,
            "Unsupported auxiliary runtime options")
    return {"model_path": ROOT / manifest["entrypoint"], **options}
