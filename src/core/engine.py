import sys
from pathlib import Path

from src.core.proxy import ProxyWrapper, _Proxy
from src.genereted import engine_pb2_grpc, engine_pb2
from src.server import run_plugin_server
from src.utils.plugin_utils import import_plugin_manager, build_registered_functions, find_free_port

# Fix sys.path for Windows child processes
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import multiprocessing
import time
from contextlib import contextmanager
import grpc



class Loader:
    _func_to_plugin = {}
    _loaded = {}
    HOST = "localhost"

    @classmethod
    @contextmanager
    def load_plugin(cls, plugin_filename: str, host: str = None):
        host = host or cls.HOST

        if plugin_filename in cls._loaded:
            info = cls._loaded[plugin_filename]
            yield ProxyWrapper(_Proxy(info["host"], info["port"]))
            return

        # Dynamically import to get function names
        plugin_manager_cls = import_plugin_manager(plugin_filename)
        function_names = list(build_registered_functions(plugin_manager_cls()).keys())

        port = find_free_port()

        process = multiprocessing.Process(
            target=run_plugin_server,
            args=(plugin_filename, host, port),
            daemon=True,
        )
        process.start()

        cls._loaded[plugin_filename] = {
            "process": process,
            "host": host,
            "port": port,
            "functions": function_names
        }

        for func_name in function_names:
            cls._func_to_plugin[func_name] = plugin_filename if hasattr(cls, "_func_to_plugin") else None

        try:
            cls._wait_until_ready(host, port, timeout=5)
        except Exception as err:
            process.terminate()
            cls._loaded.pop(plugin_filename, None)
            raise TimeoutError(f"Plugin '{plugin_filename}' on {host}:{port} failed healthcheck: {err}")

        try:
            yield ProxyWrapper(_Proxy(host, port))
        finally:
            cls.unload_plugin(plugin_filename)

    @classmethod
    def unload_plugin(cls, plugin_filename: str):
        info = cls._loaded.pop(plugin_filename, None)
        if info:
            info["process"].terminate()
            info["process"].join(timeout=2)

    @staticmethod
    def _wait_until_ready(host, port, timeout=5):
        deadline = time.time() + timeout
        channel = grpc.insecure_channel(f'{host}:{port}')
        stub = engine_pb2_grpc.PluginServiceStub(channel)

        while time.time() < deadline:
            try:
                # Polling health-check call
                stub.GetManifest(engine_pb2.GetManifestRequest(), timeout=0.5)
                channel.close()
                return
            except grpc.RpcError:
                time.sleep(0.1)

        channel.close()
        raise TimeoutError(f"Plugin server on {host}:{port} did not become ready within {timeout}s")