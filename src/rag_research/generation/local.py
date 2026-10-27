"""Owned, verified CPU/CUDA loopback server and native HTTP API."""

import json
import os
import re
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import psutil

from rag_research.generation.artifacts import verify_model, verify_runtime
from rag_research.generation.auxiliary_config import (
    CHATML_THINK_SUFFIX,
    FINAL_JSON_TRIGGER_PATTERN,
    THINK_PREFILL,
)
from rag_research.generation.cuda_runtime import (
    PARTIAL_GPU_VERSION,
    execution_kwargs,
    partial_gpu_model_path,
    verify_cuda_runtime,
)
from rag_research.generation.json_grammar import closing_tag_grammar


class GenerationError(RuntimeError):
    """Transport, runtime or generation failure, never treated as a valid refusal."""


class LlamaClient:
    def __init__(self, port: int, *, timeout: int = 300):
        self.url = f"http://127.0.0.1:{port}"
        self.timeout = timeout
        self.completion_attempts = 0
        # Loopback must not be routed through a user's HTTP proxy.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, route, payload=None, *, timeout=None):
        ticket = None
        if route == "/completion" and os.environ.get("RAG_PHASE11_AUTONOMY_CONTEXT") is not None:
            from rag_research.experiments.phase11_autonomy import (
                begin_native_call,
                finish_native_call,
            )

            ticket = begin_native_call(route, payload, timeout or self.timeout)
        request = urllib.request.Request(
            self.url + route,
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with self.opener.open(request, timeout=timeout or self.timeout) as response:
                value = json.load(response)
        except (OSError, ValueError, urllib.error.URLError) as error:
            if ticket is not None:
                finish_native_call(ticket, error=f"{type(error).__name__}: {error}")
            raise GenerationError(f"Local runtime request failed ({route}): {error}") from error
        if not isinstance(value, dict) or "error" in value:
            if ticket is not None:
                finish_native_call(ticket, error="Invalid native response")
            raise GenerationError(f"Invalid runtime response ({route}): {value}")
        if ticket is not None:
            finish_native_call(ticket, response=value)
        return value

    def tokenize(self, text, *, special=False):
        return self.request(
            "/tokenize", {"content": text, "add_special": False, "parse_special": special}
        )["tokens"]

    def detokenize(self, tokens):
        return self.request("/detokenize", {"tokens": tokens})["content"]

    def render(self, messages):
        return self.request("/apply-template", {"messages": messages})["prompt"]

    def complete(self, prompt_tokens, config, *, json_schema=None):
        # Passing exact counted IDs avoids hidden BOS insertion or retokenization.
        prefill = None
        if getattr(config, "reasoning_prefill_mode", "none") == "chatml_think_suffix_v1":
            rendered = self.detokenize(prompt_tokens)
            suffix_tokens = self.tokenize(THINK_PREFILL, special=True)
            if (not isinstance(rendered, str) or not rendered.endswith(CHATML_THINK_SUFFIX)
                    or not suffix_tokens or list(prompt_tokens[-len(suffix_tokens):]) != suffix_tokens):
                raise GenerationError("Reasoning prefill differs from the actual ChatML prompt suffix")
            # Native /completion needs the already present assistant suffix to
            # initialize its budget sampler. It does not append prompt tokens.
            prefill = THINK_PREFILL
        self.completion_attempts += 1
        payload = {
                "prompt": prompt_tokens,
                "n_predict": config.max_output_tokens,
                "temperature": config.temperature,
                "seed": config.seed,
                "samplers": ["temperature"],
                "repeat_penalty": 1.0,
                "cache_prompt": False,
                "stream": False,
                "return_tokens": True,
        }
        if json_schema is not None:
            payload["json_schema"] = json_schema
        if prefill is not None:
            payload["generation_prompt"] = prefill
        if hasattr(config, "top_k"):
            payload.update({k: getattr(config, k) for k in
                            ("top_k", "top_p", "min_p", "presence_penalty", "repeat_last_n")})
            payload["samplers"] = ["penalties", "top_k", "top_p", "min_p", "temperature"]
            payload["preserved_tokens"] = ["<think>", "</think>"]
            if json_schema is not None and config.final_json_grammar:
                # b11433 PATTERN=2; its first nonempty capture is replayed.
                # Replay the JSON opening brace, not the reasoning end token.
                mode = getattr(config, "final_json_grammar_mode", "brace_trigger_v1")
                if mode in {"closing_tag_root_v2", "closing_tag_root_v3"}:
                    payload.pop("json_schema")
                    payload.update(grammar=closing_tag_grammar(json_schema, bounded_whitespace=mode == "closing_tag_root_v3"), grammar_lazy=True,
                                   grammar_triggers=[{"type": 1, "value": "</think>"}])
                else:
                    payload.update(grammar_lazy=True,
                                   grammar_triggers=[{"type": 2, "value": FINAL_JSON_TRIGGER_PATTERN}])
            if config.reasoning_budget_tokens >= 0:
                payload.update(reasoning_budget_tokens=config.reasoning_budget_tokens,
                               reasoning_budget_start_tag="<think>",
                               reasoning_budget_end_tags=["</think>"],
                               reasoning_budget_message="\nReturn only the requested final JSON now.\n")
        return self.request("/completion", payload)


def partial_gpu_log_profile(log, context_tokens):
    """Pure actual-log validation shared by startup and completed certificates."""
    offloads = re.findall(r"offloaded (\d+)/(\d+) layers to GPU", log)
    devices = re.findall(r"using device (\S+)", log)
    architectures = re.findall(r"general\.architecture\s+str\s*=\s*(\S+)", log)
    blocks = re.findall(r"qwen35\.block_count\s+u32\s*=\s*(\d+)", log)
    layers = re.findall(r"print_info:\s+n_layer_all\s*=\s*(\d+)", log)
    if (not offloads or any(pair != ("16", "33") for pair in offloads)
            or not devices or any(device != "CUDA0" for device in devices)
            or not architectures or any(value != "qwen35" for value in architectures)
            or not blocks or any(value != "32" for value in blocks)
            or not layers or any(value != "32" for value in layers)):
        raise GenerationError("Partial GPU execution did not prove fixed Q6 16/33 CUDA0 offload")
    states = re.findall(r"llama_context:\s+flash_attn\s*=\s*(\S+)", log)
    contexts = re.findall(r"llama_context:\s+n_ctx\s*=\s*(\d+)", log)
    if (not states or any(state != "disabled" for state in states)
            or re.search(r"Flash Attention enabled|\benabling flash_attn\b", log)):
        raise GenerationError("Partial GPU execution did not prove Flash Attention off")
    if not contexts or any(int(value) != context_tokens for value in contexts):
        raise GenerationError("Partial GPU execution actual context log differs from fixed config")
    return {"version": PARTIAL_GPU_VERSION, "requested_gpu_layers": 16,
            "expected_total_layers": 33, "actual_offload_records": [[int(a), int(b)] for a, b in offloads],
            "actual_devices": devices, "model_architecture": "qwen35", "model_block_count": 32,
            "actual_gpu_offload": True, "offloaded_layers": 16, "total_layers": 33,
            "full_gpu_offload": False, "flash_attention": "off",
            "actual_context_flash_attn": states, "actual_context_tokens": [int(value) for value in contexts],
            "enabled_or_auto_context_observed": False,
            "proof": "Pinned Q6 metadata plus every actual CUDA0 16/33 offload, qwen35/32-block, explicit FA-off and context log record"}


class LocalServer:
    """Start one verified server, measure both processes, and always stop owned process."""

    def __init__(self, config, log_path: Path, *, model_path=None, jinja=False, execution=None):
        self.config = config
        self.execution = execution
        execution_kwargs({"execution": execution} if execution is not None else {})
        if type(jinja) is not bool:
            raise ValueError("Jinja setting must be boolean")
        self.jinja = jinja
        self.model_path = Path(model_path).resolve() if model_path is not None else None
        if self.execution and self.execution.get("version") == PARTIAL_GPU_VERSION:
            if self.model_path != partial_gpu_model_path() or not self.jinja:
                raise ValueError("Partial GPU execution requires the fixed Q6 Model path and Jinja")
        self.log_path = log_path
        self.process = None
        self._stop = threading.Event()
        self._thread = None

    def __enter__(self):
        started = time.perf_counter()
        model = self.model_path or verify_model().resolve()
        if self.execution:
            runtime_spec = self.execution["runtime_spec"]
            executable, self.runtime = (verify_cuda_runtime()
                if runtime_spec == "configs/lab_cuda_runtime.json"
                else verify_cuda_runtime(runtime_spec))
        else:
            executable, self.runtime = verify_runtime()
        self.runtime_version = subprocess.run(
            [str(executable.resolve()), "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        with socket.socket() as port_socket:
            port_socket.bind(("127.0.0.1", 0))
            port = port_socket.getsockname()[1]
        self.client = LlamaClient(port, timeout=self.config.timeout_seconds)
        self.command = [
            str(executable.resolve()),
            "--model",
            str(model),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--ctx-size",
            str(self.config.context_tokens),
            "--parallel",
            "1",
            "--threads",
            str(self.config.threads),
            "--threads-batch",
            str(self.config.threads),
            "--gpu-layers",
            str(self.execution["gpu_layers"]) if self.execution else "0",
            "--batch-size",
            str(self.config.batch_tokens),
            "--ubatch-size",
            str(self.config.batch_tokens),
            "--cache-ram",
            "0",
            "--no-context-shift",
            "--offline",
        ]
        if self.execution:
            self.command.extend(["--device", self.execution["device"], "--log-verbosity", "4"])
            if self.execution.get("version") in {"cuda-execution-v2", PARTIAL_GPU_VERSION}:
                self.command.extend(["--flash-attn", "off"])
        if not self.config.repack:
            self.command.append("--no-repack")
        if self.jinja:
            self.command.append("--jinja")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_path.open("x", encoding="utf-8")
        self.peak_server = 0
        self.peak_python = 0
        self.peak_combined = 0
        self.minimum_available = psutil.virtual_memory().available
        try:
            self.process = subprocess.Popen(
                self.command,
                env=({**os.environ, "LD_LIBRARY_PATH": str(executable.resolve().parent)}
                     if self.execution else None),
                stdout=self.log_file,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self._thread = threading.Thread(target=self._sample, daemon=True)
            self._thread.start()
            deadline = time.perf_counter() + self.config.startup_timeout_seconds
            while time.perf_counter() < deadline:
                if self.process.poll() is not None:
                    raise GenerationError(f"Local server exited; see {self.log_path}")
                try:
                    if self.client.request("/health", timeout=1).get("status") == "ok":
                        break
                except GenerationError:
                    pass
                time.sleep(0.2)
            else:
                raise GenerationError(f"Local server startup timed out; see {self.log_path}")
            self.props = self.client.request("/props")
            if self.props["default_generation_settings"]["n_ctx"] != self.config.context_tokens:
                raise GenerationError("Actual server context differs from fixed config")
            if self.execution:
                proof = self.offload_report()
                if self.execution.get("version") == PARTIAL_GPU_VERSION:
                    self.partial_gpu_profile_report()
                elif not proof["full_gpu_offload"]:
                    raise GenerationError("CUDA execution did not offload all layers; preserve server log")
                self.execution_profile_report()
            self.startup_seconds = time.perf_counter() - started
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def _sample(self):
        python = psutil.Process()
        server = psutil.Process(self.process.pid)
        while not self._stop.is_set():
            try:
                local = python.memory_info().rss
                remote = server.memory_info().rss
                self.peak_python = max(self.peak_python, local)
                self.peak_server = max(self.peak_server, remote)
                self.peak_combined = max(self.peak_combined, local + remote)
                self.minimum_available = min(
                    self.minimum_available, psutil.virtual_memory().available
                )
            except psutil.NoSuchProcess:
                break
            self._stop.wait(0.1)

    def offload_report(self):
        self.log_file.flush()
        log = self.log_path.read_text(encoding="utf-8", errors="replace")
        matches = re.findall(r"offloaded (\d+)/(\d+) layers to GPU", log)
        layers, total = tuple(map(int, matches[-1])) if matches else (0, 0)
        cuda = bool(re.search(r"using device CUDA\d+|CUDA\d+.*model buffer", log))
        return {"actual_gpu_offload": cuda and layers > 0, "offloaded_layers": layers,
                "total_layers": total, "full_gpu_offload": cuda and layers == total and total > 0}

    def report(self):
        return {
            "startup_seconds": self.startup_seconds,
            "sampled_peak_python_rss_bytes": self.peak_python,
            "sampled_peak_server_rss_bytes": self.peak_server,
            "sampled_peak_combined_rss_bytes": self.peak_combined,
            "minimum_available_ram_bytes": self.minimum_available,
            "sampling_interval_seconds": 0.1,
            "command": self.command,
            "runtime_version": (self.runtime_version.stdout + self.runtime_version.stderr).strip(),
            "server_context_tokens": self.props["default_generation_settings"]["n_ctx"],
            **({"execution": self.execution, "runtime": self.runtime,
                **self.offload_report()} if self.execution else {}),
            **({"execution_profile_validation": self.execution_profile_report()}
               if self.execution and self.execution.get("version") == "cuda-execution-v2" else {}),
            **({"execution_profile_validation": self.partial_gpu_profile_report()}
               if self.execution and self.execution.get("version") == PARTIAL_GPU_VERSION else {}),
        }

    def partial_gpu_profile_report(self):
        """Require every actual offload/Model record to match this 16-of-33 profile."""
        self.log_file.flush()
        log = self.log_path.read_text(encoding="utf-8", errors="replace")
        return partial_gpu_log_profile(log, self.config.context_tokens)

    def execution_profile_report(self):
        """Prove explicit FA off before output; old execution has no new condition.

        In pinned Source50569eb, explicit disabled sets flash_attn=False and
        auto_fa=False. The auto resolver therefore emits no "disabled" message.
        Require the actual context setting and reject contradictory enablement.
        """
        if not self.execution or self.execution.get("version") != "cuda-execution-v2":
            return {}
        self.log_file.flush()
        log = self.log_path.read_text(encoding="utf-8", errors="replace")
        states = re.findall(r"llama_context:\s+flash_attn\s*=\s*(\S+)", log)
        contexts = re.findall(r"llama_context:\s+n_ctx\s*=\s*(\d+)", log)
        if (not states or any(state != "disabled" for state in states)
                or re.search(r"Flash Attention enabled|\benabling flash_attn\b", log)):
            raise GenerationError("CUDA execution v2 did not prove Flash Attention off; preserve server log")
        if not contexts or any(int(value) != self.config.context_tokens for value in contexts):
            raise GenerationError("CUDA execution v2 actual context log differs from fixed config")
        return {"version": "cuda-execution-v2", "flash_attention": "off",
                "actual_context_flash_attn": states,
                "actual_context_tokens": [int(value) for value in contexts],
                "enabled_or_auto_context_observed": False,
                "proof": "Explicit disabled implies flash_attn=False/auto_fa=False in pinned Source50569eb; no auto-resolution message required"}

    def __exit__(self, *_):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        self.log_file.close()
