"""Resource evidence must preserve unknowns, failures and prior output without Native calls."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    'native_observation', Path(__file__).resolve().parents[1] / 'scripts/observe_native_resources.py')
observation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(observation)


def test_missing_memory_stays_unknown_and_real_zero_is_kept():
    result = observation.parse_memory('MemTotal: 1024 kB\nSwapFree: 0 kB\nMemAvailable: N/A\n')
    assert result['MemTotal'] == 1024 and result['SwapFree'] == 0
    assert result['MemAvailable'] is result['MemFree'] is result['SwapTotal'] is None


def test_gpu_failure_is_recorded_without_replacing_it_with_zero(monkeypatch):
    def failed_gpu():
        raise RuntimeError('unavailable GPU')
    monkeypatch.setattr(observation, 'gpu_memory', failed_gpu)
    sample = observation.sample_resources(None)
    assert sample['gpu_memory'] is None
    assert any('unavailable GPU' in error for error in sample['errors'])
    assert sample['native_process_tree'] == []


def test_existing_observations_reject_before_child_launch(tmp_path, monkeypatch):
    output = tmp_path / 'existing'
    output.mkdir()
    preserved = output / 'keep.txt'
    preserved.write_text('prior evidence')
    monkeypatch.setattr(observation.subprocess, 'Popen', lambda *a, **k: pytest.fail('must not launch'))
    with pytest.raises(FileExistsError):
        observation.observe(['unused'], output, tmp_path / 'missing-config')
    assert preserved.read_text() == 'prior evidence'


@pytest.mark.parametrize('interval', [0, 61, float('nan')])
def test_invalid_interval_rejects_before_output_or_process(tmp_path, interval):
    output = tmp_path / 'new'
    with pytest.raises(ValueError, match='interval'):
        observation.observe(['unused'], output, tmp_path / 'missing', interval=interval)
    assert not output.exists()


def test_new_child_failure_and_sampled_extrema_are_preserved(tmp_path):
    config = tmp_path / 'config.yaml'
    config.write_text('test fixture only')
    output = tmp_path / 'observations'

    def sample(pid):
        return {'gpu_memory': {'used_mib': 100 if pid is None else 120},
                'host_memory_kib': {'MemAvailable': 300 if pid is None else 280}, 'errors': []}

    result = observation.observe([sys.executable, '-c', 'raise SystemExit(2)'], output,
                                 config, interval=1, sampler=sample)
    summary = json.loads((output / 'summary.json').read_text())
    assert result == summary['native_runner_returncode'] == 2
    assert summary['observed_max_gpu_used_mib'] == 120
    assert summary['observed_min_host_available_kib'] == 280
    assert summary['sampled_extrema_are_not_continuous_peaks'] is True
    assert summary['native_gate_or_semantic_pass_not_asserted'] is True
    assert len((output / 'samples.jsonl').read_text().splitlines()) >= 2


def test_sampling_failure_never_claims_complete_observation_or_zero_peak(tmp_path):
    config = tmp_path / 'config.yaml'
    config.write_text('test fixture only')
    output = tmp_path / 'observations'

    def failed_sample(pid):
        raise OSError('fixture read failed')

    assert observation.observe([sys.executable, '-c', 'pass'], output, config,
                               interval=1, sampler=failed_sample) == 0
    summary = json.loads((output / 'summary.json').read_text())
    assert summary['observation_complete'] is False
    assert summary['samples_with_observation_errors'] == summary['samples']
    assert summary['observed_max_gpu_used_mib'] is summary['observed_min_host_available_kib'] is None


def test_child_launch_failure_is_saved_without_native_outcome(tmp_path, monkeypatch):
    config = tmp_path / 'config.yaml'
    config.write_text('test fixture only')
    output = tmp_path / 'observations'
    monkeypatch.setattr(observation.subprocess, 'check_output', lambda *a, **k: 'fixture-commit\n')

    def failed_launch(*a, **k):
        raise OSError('fixture launch failed')

    monkeypatch.setattr(observation.subprocess, 'Popen', failed_launch)
    assert observation.observe(['unused'], output, config, sampler=lambda p: {'errors': []}) == 127
    summary = json.loads((output / 'summary.json').read_text())
    assert summary['native_runner_returncode'] is None
    assert 'fixture launch failed' in summary['native_runner_launch_error']
    assert summary['observed_max_gpu_used_mib'] is None


def test_native_output_and_observation_scope_guards(tmp_path, monkeypatch):
    monkeypatch.setattr(observation, 'ROOT', tmp_path)
    config = tmp_path / 'configs/candidate.yaml'
    config.parent.mkdir()
    config.write_text('fixture')
    native = tmp_path / 'data/runs/semantic_diagnostics/prior'
    native.mkdir(parents=True)
    obs = tmp_path / 'data/runs/resource_observation/new'
    with pytest.raises(ValueError, match='new Native output'):
        observation.validate_paths('semantic', config, native, obs)
    new_native = native.with_name('new')
    with pytest.raises(ValueError, match='resource_observation'):
        observation.validate_paths('semantic', config, new_native, tmp_path / 'outside')
    command = observation.validate_paths('semantic', config, new_native, obs)
    assert command[0] == sys.executable and command[-1] == str(new_native)
    assert not new_native.exists() and not obs.exists()
