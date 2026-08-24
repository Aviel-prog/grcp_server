"""Conversions between native Python values and their protobuf
representations (`Argument` / `FuncCallResponse`).
"""

import json
from typing import Any

from src.generated import engine_pb2

def value_to_argument(value: Any) -> engine_pb2.Argument:
    """Converts a Python value into an `Argument` protobuf message."""
    argument = engine_pb2.Argument()

    if isinstance(value, bool):
        argument.bool_value = value
    elif isinstance(value, int):
        argument.int_value = value
    elif isinstance(value, float):
        argument.double_value = value
    elif isinstance(value, str):
        argument.str_value = value
    elif isinstance(value, (list, tuple)):
        argument.list_value.items.extend(value_to_argument(item) for item in value)
    else:
        argument.json_data = json.dumps(value)

    return argument


def argument_to_value(argument: engine_pb2.Argument) -> Any:
    """Converts an `Argument` protobuf message back into a Python value."""
    field = argument.WhichOneof("value")

    if field is None:
        return None
    if field == "list_value":
        return [argument_to_value(item) for item in argument.list_value.items]
    if field == "json_data":
        return json.loads(argument.json_data)

    return getattr(argument, field)


def build_response(value: Any) -> engine_pb2.FuncCallResponse:
    """Converts a Python value into a `FuncCallResponse` protobuf message."""
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


def read_response(response: engine_pb2.FuncCallResponse) -> Any:
    """Converts a `FuncCallResponse` protobuf message back into a Python
    value.

    Deliberately does not catch `json.JSONDecodeError`: a malformed
    `json_data` payload means the wire contract was violated somewhere,
    which is a bug worth failing loudly on rather than silently returning
    a raw string to the caller.
    """
    field = response.WhichOneof("value")

    if field is None:
        return None
    if field == "json_data":
        return json.loads(response.json_data)

    return getattr(response, field)
