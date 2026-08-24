from abc import ABC

from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(strict=True)


class PingOutput(StrictBaseModel):
    response: str


class BasePlugin(ABC):
    def get_manifest(self):
        raise NotImplementedError()

    @staticmethod
    def ping():
        """Health check function that returns validated 'pong'."""
        return PingOutput(response="pong").response
