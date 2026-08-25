"""Common abstract base classes and interfaces shared across all plugins."""
from abc import ABC
import socket
from pydantic import TypeAdapter
from pydantic.networks import IPvAnyAddress
from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(strict=True)


class PingOutput(StrictBaseModel):
    response: str


_ip_adapter = TypeAdapter(IPvAnyAddress)

class BasePlugin(ABC):
    def get_manifest(self):
        raise NotImplementedError()

    @staticmethod
    def ping() -> str:
        """Returns the local machine's IP address, validated as a proper IP."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        validated_ip = _ip_adapter.validate_python(ip)
        return str(validated_ip)