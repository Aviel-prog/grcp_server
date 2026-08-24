"""Supervises the lifecycle of plugin gRPC server processes.

Each plugin runs in its own OS process, spawned lazily on first use, and is
addressed over a local gRPC channel. `Engine` is the single entry point for
loading, resolving, and unloading plugins.
"""

import logging
import multiprocessing
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import grpc

from src.core.proxy import ProxyWrapper, _Proxy
from src.generated import engine_pb2, engine_pb2_grpc
from src.plugin_server import run_plugin_server
from src.utils.network_utils import find_free_port

logger = logging.getLogger(__name__)


def _ensure_project_root_importable() -> None:
    """`multiprocessing` on Windows/macOS ('spawn' start method) re-imports
    this module from scratch inside the child process, which does not
    inherit the parent's `sys.path`. The project root must be importable
    there too, since the child process needs to import `src.plugin_server`,
    `src.generated`, etc. on its own.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


_ensure_project_root_importable()


class PluginStartupError(Exception):
    """Raised when a plugin process fails to start or become healthy."""


class Engine:
    """Loads plugins as isolated gRPC server processes and hands back a
    proxy for calling their functions.
    """

    HOST = "localhost"
    _READINESS_TIMEOUT_SECONDS = 5.0
    _READINESS_POLL_INTERVAL_SECONDS = 0.1
    _PROCESS_JOIN_TIMEOUT_SECONDS = 2.0

    _loaded: dict[str, dict] = {}
    _lock = threading.Lock()

    @classmethod
    @contextmanager
    def load_plugin(cls, plugin_filename: str) -> Iterator[ProxyWrapper]:
        """Loads `plugin_filename` (starting its process if it isn't
        already running) and yields a proxy for calling its functions.

        The proxy's gRPC channel is always closed when the `with` block
        exits. The underlying plugin *process*, however, is only torn down
        if this call is the one that started it - a plugin already running
        (e.g. loaded by an earlier `with` block) is left running for other
        callers.
        """
        with cls._lock:
            already_running = plugin_filename in cls._loaded
            info = cls._loaded.get(plugin_filename) or cls._start_plugin_process(plugin_filename)

        wrapper = ProxyWrapper(_Proxy(info["host"], info["port"]))
        try:
            yield wrapper
        finally:
            wrapper.close()
            if not already_running:
                cls.unload_plugin(plugin_filename)

    @classmethod
    def unload_plugin(cls, plugin_filename: str) -> None:
        """Terminates a running plugin process, if any. No-op if the
        plugin isn't currently loaded."""
        with cls._lock:
            info = cls._loaded.pop(plugin_filename, None)

        if info is None:
            return

        info["process"].terminate()
        info["process"].join(timeout=cls._PROCESS_JOIN_TIMEOUT_SECONDS)
        logger.info("Unloaded plugin '%s'", plugin_filename)

    @classmethod
    def _start_plugin_process(cls, plugin_filename: str) -> dict:
        """Spawns a new plugin process and blocks until it is healthy.
        Must be called while holding `cls._lock`.
        """
        port = find_free_port()

        process = multiprocessing.Process( # plug_server can be on k9s
            target=run_plugin_server,
            args=(plugin_filename, cls.HOST, port),
            name=f"plugin:{plugin_filename}",
            daemon=True,
        )
        process.start()

        try:
            cls._wait_until_ready(cls.HOST, port)
        except PluginStartupError:
            process.terminate()
            process.join(timeout=cls._PROCESS_JOIN_TIMEOUT_SECONDS)
            raise

        info = {"process": process, "host": cls.HOST, "port": port}
        cls._loaded[plugin_filename] = info
        logger.info("Loaded plugin '%s' on %s:%s (pid=%s)", plugin_filename, cls.HOST, port, process.pid)
        return info

    @classmethod
    def _wait_until_ready(cls, host: str, port: int) -> None:
        """Polls the plugin's `GetManifest` RPC until it responds
        successfully or the readiness timeout elapses.
        """
        deadline = time.monotonic() + cls._READINESS_TIMEOUT_SECONDS

        with grpc.insecure_channel(f"{host}:{port}") as channel:
            stub = engine_pb2_grpc.PluginServiceStub(channel)

            while time.monotonic() < deadline:
                try:
                    stub.GetManifest(engine_pb2.GetManifestRequest(), timeout=0.5)
                    return
                except grpc.RpcError:
                    time.sleep(cls._READINESS_POLL_INTERVAL_SECONDS)

        raise PluginStartupError(
            f"Plugin server on {host}:{port} did not become ready "
            f"within {cls._READINESS_TIMEOUT_SECONDS}s"
        )
