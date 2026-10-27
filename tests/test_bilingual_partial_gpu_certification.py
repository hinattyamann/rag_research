"""Completed-session certificate checks use synthetic files, never QA or Native."""

import json
from copy import deepcopy

import pytest
from test_cuda_execution_v3_partial import (
    LOG,
    PROFILE,
    q6_metadata,  # noqa: F401 -- unchanged small-metadata fixture
)

from rag_research.experiments import bilingual_certification as module
from rag_research.generation.local import GenerationError, partial_gpu_log_profile


@pytest.fixture
def sessions(request, monkeypatch):
    root = request.getfixturevalue("q6_metadata")
    monkeypatch.setattr(module, "ROOT", root)
    # Runtime body validation belongs to execution_identity; this test isolates
    # the new completed certificate branch and its actual log/session joins.
    monkeypatch.setattr(module, "execution_identity", lambda config:
                        {"execution": deepcopy(config["execution"]), "runtime": {"synthetic": True}})
    manifest = {"baseline": {"generation": {"context_tokens": 4096},
                             "execution": {"require_full_offload": True}},
                "config": {"auxiliary_runtime": {"context_tokens": 12288},
                           "auxiliary_model_manifest": PROFILE["model_manifest"],
                           "execution": deepcopy(PROFILE)}}
    run = root / "run"
    for stage, context, log in [("baseline", 4096, "using device CUDA0\noffloaded 33/33 layers to GPU\n"),
                                ("internal", 12288, LOG)]:
        folder = run / stage
        folder.mkdir(parents=True)
        (folder / "server-1.log").write_text(log)
        config = manifest["baseline"] if stage == "baseline" else manifest["config"]
        saved = {"execution": deepcopy(config["execution"]), "runtime": {"synthetic": True},
                 "server_context_tokens": context, "actual_gpu_offload": True,
                 "full_gpu_offload": stage == "baseline", "offloaded_layers": 33 if stage == "baseline" else 16,
                 "total_layers": 33}
        if stage == "internal":
            saved["execution_profile_validation"] = partial_gpu_log_profile(log, context)
        (folder / "session-1.json").write_text(json.dumps(saved))
    return run, manifest


def test_full_baseline_and_exact_partial_internal_are_certified(sessions):
    run, manifest = sessions
    assert module.resource_sessions(run, manifest) == ["run/baseline/session-1.json", "run/internal/session-1.json"]


def test_partial_baseline_is_forbidden_before_internal_evidence(sessions):
    run, manifest = sessions
    manifest["baseline"]["execution"] = deepcopy(PROFILE)
    with pytest.raises(ValueError, match="restricted to the internal"):
        module.resource_sessions(run, manifest)


@pytest.mark.parametrize("key,value", [("gpu_layers", 15), ("expected_total_layers", 32),
    ("require_full_offload", True), ("device", "CUDA1"), ("flash_attention", "auto")])
def test_partial_config_mismatch_is_rejected_even_with_runtime_identity_double(sessions, key, value):
    run, manifest = sessions
    manifest["config"]["execution"][key] = value
    with pytest.raises(ValueError, match="explicit GPU"):
        module.resource_sessions(run, manifest)


@pytest.mark.parametrize("key,value", [("full_gpu_offload", True), ("actual_gpu_offload", False),
    ("offloaded_layers", 15), ("total_layers", 32), ("server_context_tokens", 4096),
    ("execution_profile_validation", {}), ("runtime", {"different": True})])
def test_changed_partial_session_or_missing_actual_proof_is_rejected(sessions, key, value):
    run, manifest = sessions
    path = run / "internal/session-1.json"
    saved = json.loads(path.read_text())
    saved[key] = value
    path.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="Main partial session"):
        module.resource_sessions(run, manifest)


@pytest.mark.parametrize("before,after", [("16/33", "33/33"), ("16/33", "16/32"),
    ("using device CUDA0", "using device CUDA1"), ("str = qwen35", "str = qwen3"),
    ("block_count u32 = 32", "block_count u32 = 31"),
    ("flash_attn = disabled", "flash_attn = auto"), (LOG, "")])
def test_partial_certificate_revalidates_actual_log_instead_of_trusting_saved_flag(sessions, before, after):
    run, manifest = sessions
    path = run / "internal/server-1.log"
    path.write_text(path.read_text().replace(before, after))
    with pytest.raises(GenerationError):
        module.resource_sessions(run, manifest)


def test_existing_full_baseline_still_rejects_nonfull_session(sessions):
    run, manifest = sessions
    path = run / "baseline/session-1.json"
    saved = json.loads(path.read_text())
    saved["full_gpu_offload"] = False
    path.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="actual full CUDA offload"):
        module.resource_sessions(run, manifest)
