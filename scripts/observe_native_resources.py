"""Observe a new fixed-checkout Native run; never resume or retry its requests."""

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = {
    'preflight': ('preflight_semantic_model.py', 'model_screening'),
    'format': ('probe_final_json_boundary.py', 'runtime_screening'),
    'semantic': ('run_semantic_diagnostics.py', 'semantic_diagnostics'),
}
MEMORY_FIELDS = ('MemTotal', 'MemAvailable', 'MemFree', 'SwapTotal', 'SwapFree')


def now():
    return datetime.now(UTC).isoformat()


def parse_memory(text):
    values = {key: None for key in MEMORY_FIELDS}
    for line in text.splitlines():
        key, _, value = line.partition(':')
        if key in values:
            parts = value.split()
            if len(parts) == 2 and parts[0].isdigit() and parts[1] == 'kB':
                values[key] = int(parts[0])
    return values


def gpu_memory():
    result = subprocess.run(['nvidia-smi', '--id=0', '--query-gpu=memory.used,memory.total',
                             '--format=csv,noheader,nounits'], capture_output=True, text=True,
                            timeout=5, check=False)
    if result.returncode:
        raise RuntimeError(f'nvidia-smi exit={result.returncode}: {result.stderr.strip()}')
    rows = list(csv.reader(result.stdout.splitlines()))
    if len(rows) != 1 or len(rows[0]) != 2 or not all(v.strip().isdigit() for v in rows[0]):
        raise ValueError('GPU memory is unavailable or not a single numeric device row')
    used, total = map(lambda v: int(v.strip()), rows[0])
    return {'used_mib': used, 'total_mib': total}


def process_tree(pid):
    rows, pending = [], [pid] if pid is not None else []
    seen = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        folder = Path('/proc') / str(current)
        try:
            fields = dict(line.split(':', 1) for line in (folder / 'status').read_text().splitlines())
        except (FileNotFoundError, ProcessLookupError):
            continue
        row = {'pid': current, 'name': fields.get('Name', '').strip()}
        for source, target in (('VmRSS', 'rss_kib'), ('VmHWM', 'high_water_rss_kib'), ('VmSwap', 'swap_kib')):
            parts = fields.get(source, '').split()
            row[target] = int(parts[0]) if len(parts) == 2 and parts[0].isdigit() and parts[1] == 'kB' else None
        rows.append(row)
        try:
            pending.extend(int(value) for value in (folder / 'task' / str(current) / 'children').read_text().split())
        except (FileNotFoundError, ProcessLookupError):
            pass
    return rows


def sample_resources(pid):
    row = {'recorded_at_utc': now(), 'host_memory_kib': None, 'gpu_memory': None,
           'native_process_tree': None, 'errors': []}
    for name, operation in (
        ('host_memory_kib', lambda: parse_memory(Path('/proc/meminfo').read_text())),
        ('gpu_memory', gpu_memory), ('native_process_tree', lambda: process_tree(pid)),
    ):
        try:
            row[name] = operation()
            if name == 'host_memory_kib' and any(v is None for v in row[name].values()):
                row['errors'].append('Host memory fields are incomplete')
        except Exception as error:
            row['errors'].append(f'{name}: {type(error).__name__}: {error}')
    return row


def validate_paths(kind, config, output, observations):
    script, scope = KINDS[kind]
    config, output, observations = (Path(path).resolve() for path in (config, output, observations))
    if not config.is_file() or not config.is_relative_to(ROOT / 'configs'):
        raise ValueError('Bind an existing repository config')
    parent = ROOT / 'data/runs' / scope
    observer_parent = ROOT / 'data/runs/resource_observation'
    if output == parent or not output.is_relative_to(parent) or output.exists():
        raise ValueError('Observe only a new Native output; preserve all previous requests')
    if observations == observer_parent or not observations.is_relative_to(observer_parent) or observations.exists():
        raise ValueError('Preserve existing observation evidence and keep it in resource_observation')
    return [sys.executable, str(ROOT / 'scripts' / script), '--config', str(config), '--output-dir', str(output)]


def observe(command, observations, config, *, interval=5.0, sampler=None):
    if not 1 <= interval <= 60:
        raise ValueError('Observation interval must be between 1 and 60 seconds')
    observations, config = Path(observations), Path(config)
    observations.mkdir(parents=True, exist_ok=False)
    sampler = sample_resources if sampler is None else sampler
    metadata = {'created_at_utc': now(), 'command': command, 'interval_seconds': interval,
                'config_sha256': hashlib.sha256(config.read_bytes()).hexdigest(),
                'observer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'fixed_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'observer_pid': os.getpid(), 'new_model_calls_from_observer': 0,
                'no_request_resume_or_retry': True, 'scope': 'resources only, no QA content',
                'observations_include_system_and_observer_overhead': True}
    with (observations / 'launch.json').open('x') as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    count, failures, observed_gpu, observed_available = 0, 0, [], []
    result, launch_error = None, None
    started = time.perf_counter()
    with (observations / 'samples.jsonl').open('x') as stream:
        def capture(pid):
            nonlocal count, failures
            try:
                sample = sampler(pid)
            except Exception as error:
                sample = {'recorded_at_utc': now(), 'errors': [f'{type(error).__name__}: {error}']}
            stream.write(json.dumps(sample, ensure_ascii=False) + '\n')
            stream.flush()
            count += 1
            failures += bool(sample.get('errors'))
            gpu = sample.get('gpu_memory')
            if gpu is not None and gpu.get('used_mib') is not None:
                observed_gpu.append(gpu['used_mib'])
            memory = sample.get('host_memory_kib')
            if memory is not None and memory.get('MemAvailable') is not None:
                observed_available.append(memory['MemAvailable'])
        capture(None)
        try:
            child = subprocess.Popen(command, cwd=ROOT)
        except OSError as error:
            launch_error = f'{type(error).__name__}: {error}'
        else:
            print(json.dumps({'observer_started': True, 'native_runner_pid': child.pid,
                              'observations': str(observations)}), flush=True)
            while True:
                capture(child.pid)
                result = child.poll()
                if result is not None:
                    break
                time.sleep(interval)
    summary = {'finished_at_utc': now(), 'native_runner_returncode': result, 'samples': count,
               'native_runner_launch_error': launch_error,
               'samples_with_observation_errors': failures, 'observation_complete': failures == 0,
               'observed_max_gpu_used_mib': max(observed_gpu) if observed_gpu else None,
               'observed_min_host_available_kib': min(observed_available) if observed_available else None,
               'elapsed_observer_seconds': time.perf_counter() - started,
               'sampled_extrema_are_not_continuous_peaks': True,
               'native_gate_or_semantic_pass_not_asserted': True, 'new_model_calls_from_observer': 0}
    with (observations / 'summary.json').open('x') as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'resource_observation_finished': summary}), flush=True)
    return result if result is not None else 127


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=KINDS, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--observations', type=Path, required=True)
    parser.add_argument('--interval', type=float, default=5.0)
    args = parser.parse_args()
    if Path.cwd().resolve() != ROOT:
        raise ValueError('Run from the fixed checkout root')
    command = validate_paths(args.kind, args.config, args.output_dir, args.observations)
    return observe(command, args.observations, args.config, interval=args.interval)


if __name__ == '__main__':
    sys.exit(main())
