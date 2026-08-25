"""Proxy interface for forwarding communication between the engine and plugin modules."""
# TODO add doc
import json
import logging
from typing import Any
import builtins

import grpc

from src.generated import engine_pb2, engine_pb2_grpc
from src.utils.proto_utils import read_response, value_to_argument

logger = logging.getLogger(__name__)


class PluginCallError(Exception):
    """Raised when a plugin function call fails: unknown function, argument
    mismatch, or a transport-level gRPC failure."""


class Proxy:
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

    def __getattr__(self, item):
        if not self._is_exist(item):
            raise AttributeError(f"'{item}' is not exposed by this plugin")

        def call_remote(*args: Any, **kwargs: Any) -> Any:
            if kwargs:
                raise PluginCallError(
                    "Keyword arguments are not supported by plugin calls; use positional arguments"
                )
            if self._validate_args(item, *args):
                response = self._call(item, *args)
                return response
            else:
                raise ValueError("Invalid input")

        return call_remote

    def close(self) -> None:
        self._channel.close()

    @property
    def manifest(self) -> dict:
        """Returns the plugin's manifest (function names, parameters,
        return types), fetched once from the server and cached."""
        if self._manifest is None:
            response = self._stub.GetManifest(engine_pb2.GetManifestRequest())
            self._manifest = json.loads(response.json_data)
        return self._manifest

    def _is_exist(self, function_name: str) -> bool:
        """Checks whether `function_name` is exposed by the plugin."""
        try:
            return function_name in self.manifest.get("functions", {})
        except grpc.RpcError:
            logger.error("Could not reach plugin server to resolve '%s'", function_name)
            return False

    def _validate_args(self, function_name: str, *args: Any) -> bool:
        """Validates that the number and types of the given args match the manifest."""
        params = self.manifest.get("functions", {}).get(function_name, {})

        if len(args) != len(params):
            return False

        for arg, type_name in zip(args, params.values()):
            expected_types = tuple(
                getattr(builtins, t.strip(), None) for t in type_name.split("|")
            )
            expected_types = tuple(t for t in expected_types if isinstance(t, type))

            if expected_types and not isinstance(arg, expected_types):
                return False

        return True

    def _call(self, function_name: str, *args: Any) -> Any:
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
