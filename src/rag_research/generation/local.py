"""Owned loopback CPU server and native HTTP API; no external LLM service."""

import json
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import psutil

from rag_research.generation.artifacts import verify_model, verify_runtime


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
        request = urllib.request.Request(
            self.url + route,
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with self.opener.open(request, timeout=timeout or self.timeout) as response:
                value = json.load(response)
        except (OSError, ValueError, urllib.error.URLError) as error:
            raise GenerationError(f"Local runtime request failed ({route}): {error}") from error
        if not isinstance(value, dict) or "error" in value:
            raise GenerationError(f"Invalid runtime response ({route}): {value}")
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
        return self.request("/completion", payload)


class LocalServer:
    """Start one verified server, measure both processes, and always stop owned process."""

    def __init__(self, config, log_path: Path, *, model_path=None):
        self.config = config
        self.model_path = Path(model_path).resolve() if model_path is not None else None
        self.log_path = log_path
        self.process = None
        self._stop = threading.Event()
        self._thread = None

    def __enter__(self):
        started = time.perf_counter()
        model = self.model_path or verify_model().resolve()
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
            "0",
            "--batch-size",
            str(self.config.batch_tokens),
            "--ubatch-size",
            str(self.config.batch_tokens),
            "--cache-ram",
            "0",
            "--no-context-shift",
            "--offline",
        ]
        if not self.config.repack:
            self.command.append("--no-repack")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_path.open("x", encoding="utf-8")
        self.peak_server = 0
        self.peak_python = 0
        self.peak_combined = 0
        self.minimum_available = psutil.virtual_memory().available
        try:
            self.process = subprocess.Popen(
                self.command,
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
        }

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
