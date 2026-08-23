import grpc

from src.core.engine import Loader
from src.genereted import engine_pb2, engine_pb2_grpc
from src.utils.proto_utils import value_to_argument, read_response


class _Proxy:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def is_exist(self, called_func):
        return True  # TODO

    def execute_grcp_request(self, called_func, *args, **kwargs):
        with grpc.insecure_channel(f'{self.host}:{self.port}') as channel:
            stub = engine_pb2_grpc.PluginServiceStub(channel)
            request = engine_pb2.FuncCallRequest(
                func_name=called_func,
                args=[value_to_argument(a) for a in args]
            )
            try:
                response = stub.FuncCall(request)
                return read_response(response)
            except grpc.RpcError as exc:
                print(f"gRPC call failed: {exc.code()} - {exc.details()}")
                return None

    def get_manifest(self, plugin_filename: str):
        with grpc.insecure_channel(f'{self.host}:{self.port}') as channel:
            stub = engine_pb2_grpc.PluginServiceStub(channel)
            request = engine_pb2.GetManifestRequest(plugin_name=plugin_filename)
            try:
                response = stub.GetManifest(request)
                return response.json_data
            except grpc.RpcError as exc:
                print(f"gRPC call failed: {exc.code()} - {exc.details()}")
                return None

    def validate_args(self, *args, **kwargs):

        return True  # TODO

    def validate_output(self, response):
        return True  # TODO


class ProxyWrapper:
    def __init__(self, wrapped_proxy):
        self._wrapped_proxy = wrapped_proxy

    def __getattribute__(self, item):
        wrapped_proxy = object.__getattribute__(self, "_wrapped_proxy")

        if hasattr(wrapped_proxy, item):
            return getattr(wrapped_proxy, item)

        if wrapped_proxy.is_exist(item):
            def wrapper(*args, **kwargs):
                if wrapped_proxy.validate_args(item, *args, **kwargs):
                    response = wrapped_proxy.execute_grcp_request(item, *args, **kwargs)
                    if wrapped_proxy.validate_output(response):
                        return response
                    raise ValueError("Invalid output")
                raise ValueError("Invalid input")

            return wrapper

        raise AttributeError(f"'{item}' not found")
