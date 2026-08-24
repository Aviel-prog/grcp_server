"""Client-side facade for calling a loaded plugin's functions as if they
were local, transparently forwarding attribute access to gRPC calls.
"""

import json
import logging
from typing import Any

import grpc

from src.generated import engine_pb2, engine_pb2_grpc
from src.utils.proto_utils import read_response, value_to_argument

logger = logging.getLogger(__name__)


class PluginCallError(Exception):
    """Raised when a plugin function call fails: unknown function, argument
    mismatch, or a transport-level gRPC failure."""


class _Proxy:
    """Owns the gRPC channel to a single running plugin server and exposes
    the low-level operations `ProxyWrapper` needs: manifest retrieval,
    argument validation, and remote function invocation.

    The channel is opened once (not per-call) and must be closed via
    `close()` when the proxy is no longer needed.
    """

    def __init__(self, host: str, port: int):
        self._channel = grpc.insecure_channel(f"{host}:{port}")
        self._stub = engine_pb2_grpc.PluginServiceStub(self._channel)
        self._manifest: dict | None = None

    def close(self) -> None:
        self._channel.close()

    def manifest(self) -> dict:
        """Returns the plugin's manifest (function names, parameters,
        return types), fetched once from the server and cached."""
        if self._manifest is None:
            response = self._stub.GetManifest(engine_pb2.GetManifestRequest())
            self._manifest = json.loads(response.json_data)
        return self._manifest

    def is_exist(self, function_name: str) -> bool:
        """Checks whether `function_name` is exposed by the plugin."""
        try:
            return function_name in self.manifest().get("functions", {})
        except grpc.RpcError:
            logger.error("Could not reach plugin server to resolve '%s'", function_name)
            return False

    def validate_args(self, function_name: str, *args: Any) -> None:
        return True  # TODO

    def validate_output(self, response) -> None:
        return True  # TODO

    def call(self, function_name: str, *args: Any) -> Any:
        """Invokes `function_name` on the remote plugin and returns its
        result."""
        request = engine_pb2.FuncCallRequest(
            func_name=function_name,
            args=[value_to_argument(arg) for arg in args],
        )

        try:
            response = self._stub.FuncCall(request)
        except grpc.RpcError as exc:
            raise PluginCallError(f"{exc.code()}: {exc.details()}") from exc

        return read_response(response)


class ProxyWrapper:
    """Presents a `_Proxy` as if its remote functions were local attributes:
    `wrapper.add(1, 2)` transparently performs a `FuncCall` RPC.
    """

    def __init__(self, proxy: _Proxy):
        # Bypasses __setattr__/__getattr__ entirely for this one internal
        # attribute so it never gets mistaken for a remote function name.
        object.__setattr__(self, "_proxy", proxy)

    def __getattr__(self, function_name: str):
        # __getattr__ (unlike __getattribute__) only fires for attributes
        # that don't already exist on the instance/class, so dunder lookups
        # (__class__, __repr__, pickling hooks, ...) never trigger a
        # manifest RPC - only genuinely-missing names reach here.
        proxy: _Proxy = object.__getattribute__(self, "_proxy")

        if not proxy.is_exist(function_name):
            raise AttributeError(f"'{function_name}' is not exposed by this plugin")

        def call_remote(*args: Any, **kwargs: Any) -> Any:
            if kwargs:
                raise PluginCallError(
                    "Keyword arguments are not supported by plugin calls; use positional arguments"
                )
            if proxy.validate_args(function_name, *args):
                response = proxy.call(function_name, *args)
                if proxy.validate_output(response):
                    return response
                raise ValueError("Invalid output of the plugin")

            else:
                raise ValueError("Invalid input")

        return call_remote

    def close(self) -> None:
        object.__getattribute__(self, "_proxy").close()
