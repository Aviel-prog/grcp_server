import json

from src.genereted import engine_pb2

def value_to_argument(value) -> engine_pb2.Argument:
    arg = engine_pb2.Argument()
    if isinstance(value, bool):
        arg.bool_value = value
    elif isinstance(value, int):
        arg.int_value = value
    elif isinstance(value, float):
        arg.double_value = value
    elif isinstance(value, str):
        arg.str_value = value
    elif isinstance(value, (list, tuple)):
        arg.list_value.items.extend(value_to_argument(v) for v in value)
    else:
        arg.json_data = json.dumps(value)
    return arg


def argument_to_value(arg: engine_pb2.Argument):
    field = arg.WhichOneof("value")
    if field == "list_value":
        return [argument_to_value(item) for item in arg.list_value.items]
    if field == "json_data":
        return json.loads(arg.json_data)
    return getattr(arg, field) if field else None


def build_response(value) -> engine_pb2.FuncCallResponse:
    response = engine_pb2.FuncCallResponse()
    if isinstance(value, bool):
        response.bool_value = value
    elif isinstance(value, int):
        response.int_value = value
    elif isinstance(value, float):
        response.double_value = value
    elif isinstance(value, str):
        response.str_value = value
    else:
        response.json_data = json.dumps(value)
    return response


def read_response(response: engine_pb2.FuncCallResponse):
    field = response.WhichOneof("value")
    if field == "json_data":
        try:
            return json.loads(response.json_data)
        except json.JSONDecodeError:
            return response.json_data
    return getattr(response, field) if field else None