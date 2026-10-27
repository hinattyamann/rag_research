"""Only v6 Q6/partial-placement deltas; no actual tokenizer, Model or Native."""

import ast
import copy
import hashlib
import json
import re
import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import ModuleType

import pytest

from rag_research.evaluation.reasoning_budget import BUDGET_MESSAGE
from rag_research.evaluation.schema import cited_verdict_schema, object_schema
from rag_research.experiments.frozen_trace import digest, require
from rag_research.experiments.storage import write_json
from rag_research.generation.auxiliary_config import (
    CHATML_THINK_SUFFIX,
    THINK_PREFILL,
    AuxiliaryGenerationConfig,
    tokenize_reasoning_prompt,
)

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
# Compile the actual pure functions, not the entry imports that load Runtime
# clients. The preserved test-runner failures were attributed separately to
# automatic pytest plugin import; this suite needs no plugin or Runtime import.
probe = ModuleType("format_v6_source_test")
probe.__dict__.update(ROOT=ROOT, json=json, re=re, hashlib=hashlib, Path=Path,
    asdict=asdict, replace=replace, require=require, digest=digest, write_json=write_json,
    CHATML_THINK_SUFFIX=CHATML_THINK_SUFFIX, THINK_PREFILL=THINK_PREFILL,
    BUDGET_MESSAGE=BUDGET_MESSAGE, tokenize_reasoning_prompt=tokenize_reasoning_prompt,
    object_schema=object_schema, cited_verdict_schema=cited_verdict_schema)


def exact_source_nodes(relative_path, names):
    tree = ast.parse((ROOT / relative_path).read_text())
    nodes = [node for node in tree.body if
        (isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names) or
        (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets))]
    assert len(nodes) == len(names), (relative_path, names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(ROOT / relative_path), "exec"), probe.__dict__)


exact_source_nodes("src/rag_research/generation/cuda_runtime.py", {"PARTIAL_GPU_VERSION"})
exact_source_nodes("src/rag_research/generation/local.py", {"GenerationError", "partial_gpu_log_profile"})
exact_source_nodes("src/rag_research/retrieval/common.py", {"file_hash"})
exact_source_nodes("scripts/probe_thinking_json_schema_v6.py", {
    "MODEL_MANIFEST", "MODEL_GGUF", "REASONING_TAG_IDS", "PARTIAL_EXECUTION", "cases",
    "tokenizer_contract", "messages_for", "validate_server_context", "capture_tokenizer_witnesses"})



def config():
    return {'auxiliary_model_manifest': probe.MODEL_MANIFEST['path'],
        'format_tokenizer_contract': {'version': 'phase11-tokenizer-v6', 'model_manifest': probe.MODEL_MANIFEST,
            'open_token_id': 248068, 'close_token_id': 248069, 'single_token_tags': True,
            'fresh_witness_required': 11, 'expected_model_block_count': 32,
            'expected_total_layers': 33, 'expected_offloaded_layers': 16},
        'sampling': {'reasoning_budget_tokens': 4096, 'final_json_grammar_mode': 'closing_tag_root_v3',
                     'reasoning_prefill_mode': 'chatml_think_suffix_v1'},
        'auxiliary_runtime': {'context_tokens': 12288, 'batch_tokens': 128},
        'tasks': {'verify_claims': {'max_output_tokens': 6144}},
        'output_constraints': 'thinking_json_passage_ids_v3', 'phase12_allowed': False,
        'execution': copy.deepcopy(probe.PARTIAL_EXECUTION)}


def base():
    return AuxiliaryGenerationConfig(context_tokens=12288, max_output_tokens=512,
        temperature=0.2, batch_tokens=128, reasoning_budget_tokens=128,
        reasoning_prefill_mode='chatml_think_suffix_v1', final_json_grammar=True,
        final_json_grammar_mode='closing_tag_root_v3')


@pytest.fixture(autouse=True)
def no_native_or_model_read(monkeypatch):
    original = probe.file_hash

    def small_only(path):
        assert not str(path).endswith('.gguf'), 'No Model body Hash in Source tests'
        return original(path)
    monkeypatch.setattr(probe, 'file_hash', small_only)


def test_fixed_Q6_contract_is_not_an_8B_or_fullGPU_contract():
    contract = probe.tokenizer_contract(config())
    assert (contract['open_token_id'], contract['close_token_id']) == probe.REASONING_TAG_IDS == (248068, 248069)
    assert probe.MODEL_MANIFEST['sha256'] == 'acadda5c012105a454b07ee95d406a217fe0aab8f498f3988bf44de36ebade65'
    assert probe.MODEL_GGUF['sha256'] == '91898433cf5ce0a8f45516a4cc3e9343b6e01d052d01f684309098c66a326c59'
    assert len(contract) == 9 and len(probe.PARTIAL_EXECUTION) == 8


@pytest.mark.parametrize('failure', ['8B-tags', '8B-manifest', 'full-layers', '8B-total', 'float-total',
                                     'extra-contract', 'full-execution', 'extra-execution', 'batch'])
def test_wrong_restored_Model_or_placement_contract_stops_before_native(failure):
    c = config()
    contract = c['format_tokenizer_contract']
    if failure == '8B-tags':
        contract.update(open_token_id=151667, close_token_id=151668)
    elif failure == '8B-manifest':
        contract['model_manifest'] = {'path': '8B.json', 'sha256': '0' * 64}
    elif failure == 'full-layers':
        contract['expected_offloaded_layers'] = 33
    elif failure == '8B-total':
        contract['expected_total_layers'] = 37
    elif failure == 'float-total':
        contract['expected_total_layers'] = 33.0
    elif failure == 'extra-contract':
        contract['expected_full_offload_layers'] = 33
    elif failure == 'full-execution':
        c['execution'].update(gpu_layers=99, require_full_offload=True)
    elif failure == 'extra-execution':
        c['execution']['unregistered_flag'] = True
    else:
        c['auxiliary_runtime']['batch_tokens'] = 256
    with pytest.raises(ValueError):
        probe.tokenizer_contract(c)


def startup_log():
    return ('general.architecture str = qwen35\nqwen35.block_count u32 = 32\n'
            'print_info: n_layer_all = 32\nusing device CUDA0\n'
            'offloaded 16/33 layers to GPU\nllama_context: n_ctx = 12288\n'
            'llama_context: flash_attn = disabled\n')


def server_report(log):
    return {'execution': copy.deepcopy(probe.PARTIAL_EXECUTION), 'server_context_tokens': 12288,
        'actual_gpu_offload': True, 'full_gpu_offload': False, 'offloaded_layers': 16, 'total_layers': 33,
        'execution_profile_validation': probe.partial_gpu_log_profile(log, 12288),
        'command': ['invented-server', '--flash-attn', 'off', '--gpu-layers', '16', '--device', 'CUDA0',
            '--ctx-size', '12288', '--batch-size', '128', '--ubatch-size', '128', '--model',
            str(probe.ROOT / probe.MODEL_GGUF['path']), '--jinja'],
        'runtime': {'source_commit': '50569eb87df530daff11afda229ceb9ab8e6cae8',
            'backend': 'Ubuntu-x64-CUDA-12.9-graph-off-source-v1', 'cmake_options': {'GGML_CUDA_GRAPHS': 'OFF'}}}


@pytest.mark.parametrize('failure', [None, 'forged-profile', 'full-report', 'command-layer', 'actual-log-conflict'])
def test_saved_actual_log_profile_and_command_must_join(failure):
    log = startup_log()
    server = server_report(log)
    if failure == 'forged-profile':
        server['execution_profile_validation']['model_block_count'] = 36
    elif failure == 'full-report':
        server['full_gpu_offload'] = True
    elif failure == 'command-layer':
        server['command'][server['command'].index('--gpu-layers') + 1] = '99'
    elif failure == 'actual-log-conflict':
        log += 'offloaded 33/33 layers to GPU\n'
    if failure:
        with pytest.raises((ValueError, RuntimeError)):
            probe.validate_server_context(server, config(), probe.tokenizer_contract(config()), log)
    else:
        probe.validate_server_context(server, config(), probe.tokenizer_contract(config()), log)


class FakeClient:
    """Invented reversible encoding with contract IDs, never a real Model tokenizer."""

    def __init__(self, *, bare=False, closing=248069):
        self.completion_attempts = 0
        self.bare = bare
        self.closing = closing

    def tokenize(self, text, *, special=False):
        assert special
        tokens = []
        while text:
            if text.startswith('<think>'):
                tokens.append(248068)
                text = text[len('<think>'):]
            elif text.startswith('</think>'):
                tokens.append(self.closing)
                text = text[len('</think>'):]
            else:
                tokens.append(ord(text[0]) + 1000)
                text = text[1:]
        return tokens

    def detokenize(self, tokens):
        return ''.join('<think>' if x == 248068 else '</think>' if x == self.closing else chr(x - 1000) for x in tokens)

    def render(self, messages):
        return json.dumps(messages, ensure_ascii=False) + ('<|im_start|>assistant\n' if self.bare else probe.CHATML_THINK_SUFFIX)

    def complete(self, *args, **kwargs):
        pytest.fail('Fresh11 capture must never use completion')


@pytest.mark.parametrize('bare', [False, True])
def test_new_partial_context_has_fresh11_before_each_mode_completion(tmp_path, bare):
    client = FakeClient(bare=bare)
    planned = probe.cases(constraints='thinking_json_passage_ids_v3')
    context = {'fixture_only': True, 'execution': probe.PARTIAL_EXECUTION, 'settings': asdict(base())}
    captured, manifest = probe.capture_tokenizer_witnesses(client, base(), planned,
        probe.tokenizer_contract(config()), context, tmp_path)
    assert manifest['schema_version'] == 6 and manifest['file_count'] == 11 and len(captured) == 10
    assert manifest['completion_attempts_before'] == manifest['completion_attempts_after'] == client.completion_attempts == 0
    assert manifest['saved_old_tokenizer_observations_substituted_for_fresh_witnesses'] is False
    assert manifest['tag_contract_constants_source'] == 'same-Model saved Q6 metadata, independently recaptured11 in this run'
    assert 'old_model_token_ids_or_witnesses_reused' not in manifest
    assert manifest['old_full_GPU_placement_evidence_reused'] is False
    for reference in manifest['files']:
        p = tmp_path / reference['path']
        assert probe.file_hash(p) == reference['sha256']
        row = json.loads(p.read_text())
        assert row['status'] == 'validated' and row['context_sha256'] == probe.digest(context)
    for row in captured:
        assert row['reasoning_tag_tokens'] == {'open': [248068], 'close': [248069]}
        assert row['settings']['reasoning_budget_tokens'] == 128 and row['settings']['max_output_tokens'] == 512
        assert row['reasoning_prefill_audit']['applied'] is bare


def test_foreign_observed_tag_saves_failure_without_any_completion(tmp_path):
    client = FakeClient(closing=151668)
    with pytest.raises(ValueError, match='reasoning-tag tokens differ'):
        probe.capture_tokenizer_witnesses(client, base(), probe.cases(constraints='thinking_json_passage_ids_v3'),
            probe.tokenizer_contract(config()), {'fixture_only': True}, tmp_path)
    assert client.completion_attempts == 0 and not (tmp_path / 'tokenizer_witness_manifest.json').exists()
    assert json.loads((tmp_path / 'tokenizer_witnesses/plan.json').read_text())['status'] == 'failed'


def test_unchanged_science_and_ownership_AST_reuses_v5_validation():
    trees = [ast.parse((ROOT / 'scripts' / name).read_text()) for name in
             ('probe_thinking_json_schema_v5.py', 'probe_thinking_json_schema_v6.py')]
    for name in ('cases', 'conforms', 'messages_for', 'complete_case', 'fixed_worktree_metadata', 'verify_live_supervisor'):
        functions = [next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name) for tree in trees]
        assert ast.dump(functions[0], include_attributes=False) == ast.dump(functions[1], include_attributes=False)
