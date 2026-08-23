import json
from concurrent import futures
import grpc

from src.genereted import engine_pb2_grpc, engine_pb2
from src.utils.plugin_utils import import_plugin_manager, build_registered_functions
from src.utils.proto_utils import argument_to_value, build_response


class PluginServicer(engine_pb2_grpc.PluginServiceServicer):
    def __init__(self, plugin_instance, registered_functions):
        self._plugin_instance = plugin_instance
        self._registered_functions = registered_functions

    def GetManifest(self, request, context):
        manifest_payload = self._plugin_instance.get_manifest()
        return engine_pb2.GetManifestResponse(json_data=json.dumps(manifest_payload))

    def FuncCall(self, request, context):
        func = self._registered_functions.get(request.func_name)
        if func is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Function '{request.func_name}' not found")
            return engine_pb2.FuncCallResponse()

        args = [argument_to_value(a) for a in request.args]
        try:
            result = func(*args)
        except Exception as exc:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(exc))
            return engine_pb2.FuncCallResponse()

        return build_response(result)


def run_plugin_server(plugin_filename: str, host: str, port: int):
    plugin_manager_cls = import_plugin_manager(plugin_filename)
    plugin_instance = plugin_manager_cls()
    registered_functions = build_registered_functions(plugin_instance)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    engine_pb2_grpc.add_PluginServiceServicer_to_server(
        PluginServicer(plugin_instance, registered_functions), server
    )
    server.add_insecure_port(f'{host}:{port}')
    server.start()
    server.wait_for_termination()