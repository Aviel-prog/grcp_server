"""gRPC server that exposes a single dynamically-loaded plugin over the
network. Each plugin instance is intended to run in its own OS process,
spawned and supervised by `src.core.engine.Engine`.
"""

import logging
from concurrent import futures

import grpc

from src.generated import engine_pb2, engine_pb2_grpc
from src.utils.plugin_engine import PluginLoadError, build_registered_functions, import_plugin_manager
from src.utils.proto_utils import argument_to_value, build_response

logger = logging.getLogger(__name__)

DEFAULT_MAX_WORKERS = 10


class PluginServicer(engine_pb2_grpc.PluginServiceServicer):
    """Adapts a loaded plugin instance to the `PluginService` gRPC contract."""

    def __init__(self, plugin_instance, registered_functions: dict):
        self._plugin_instance = plugin_instance
        self._registered_functions = registered_functions

    def GetManifest(self, request, context):
        try:
            manifest_json = self._plugin_instance.get_manifest()
        except Exception:
            logger.exception("Failed to build manifest")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Failed to build plugin manifest")
            return engine_pb2.GetManifestResponse()

        return engine_pb2.GetManifestResponse(json_data=manifest_json)

    def FuncCall(self, request, context):
        func = self._registered_functions.get(request.func_name)
        if func is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Function '{request.func_name}' not found")
            return engine_pb2.FuncCallResponse()

        args = [argument_to_value(arg) for arg in request.args]

        try:
            result = func(*args)
        except (TypeError, ValueError) as exc:
            # Argument-count mismatches (TypeError) and Pydantic/validation
            # failures (ValueError) are caller mistakes, not server bugs -
            # surface them to the caller.
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(exc))
            return engine_pb2.FuncCallResponse()
        except Exception:
            # Anything else is an unexpected server-side failure: log the
            # full traceback for diagnosis, but never leak internals to
            # the caller.
            logger.exception("Unhandled error while executing '%s'", request.func_name)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return engine_pb2.FuncCallResponse()

        return build_response(result)


def run_plugin_server(
    plugin_filename: str,
    host: str,
    port: int,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> None:
    """Entry point executed inside the dedicated plugin process.

    Loads the plugin, exposes it over a gRPC server, and blocks until the
    process is terminated by its supervisor (`Engine`).
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    try:
        plugin_manager_cls = import_plugin_manager(plugin_filename)
    except PluginLoadError:
        logger.exception("Could not load plugin '%s'", plugin_filename)
        raise

    plugin_instance = plugin_manager_cls()
    registered_functions = build_registered_functions(plugin_instance)
    logger.info("Plugin '%s' functions: %s", plugin_filename, list(registered_functions))

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    engine_pb2_grpc.add_PluginServiceServicer_to_server(
        PluginServicer(plugin_instance, registered_functions), server
    )

    # NOTE: plaintext gRPC (add_insecure_port). Acceptable here because
    # plugin servers only ever bind to `localhost` and are only reachable
    # from the same machine via `Engine`. If plugins are ever exposed
    # beyond localhost, switch to `add_secure_port` with TLS credentials.
    server.add_insecure_port(f"{host}:{port}")
    server.start()
    logger.info("Plugin '%s' listening on %s:%s", plugin_filename, host, port)
    server.wait_for_termination()
