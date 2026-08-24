import inspect
from email.policy import strict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# ==========================================
# Pydantic Schemas for Validation
# ==========================================

class PingOutput(BaseModel, strict):
    response: str = Field()


class StringInput(BaseModel):
    text: str = Field(min_length=1)


class SubstringInput(BaseModel):
    text: str = Field(min_length=1)
    sub: str = Field(min_length=1)


class StringOutput(BaseModel):
    result: str


class LengthOutput(BaseModel):
    length: int = Field(ge=0)


class ContainsOutput(BaseModel):
    contains: bool


class ManifestOutput(BaseModel):
    plugin_name: str = Field(description="Name of the plugin")
    functions: dict[str, dict[str, Any]] = Field(description="Map of function names to parameter types")


# ==========================================
# Plugin Implementation
# ==========================================

class PluginManager:
    """String operations plugin manager with static methods and self-manifest generation."""

    def get_manifest(self) -> str:
        """Dynamically inspects the class to generate a validated JSON manifest string."""
        functions_manifest = {}
        try:
            plugin_name = Path(__file__).stem
        except NameError:
            plugin_name = self.__class__.__module__.split(".")[-1]

        # Inspect class methods
        for name, method in inspect.getmembers(self.__class__, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue

            sig = inspect.signature(method)
            params = {}

            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                type_hint = param.annotation
                if type_hint != inspect.Parameter.empty:
                    params[param_name] = (
                        type_hint.__name__ if hasattr(type_hint, "__name__") else str(type_hint)
                    )
                else:
                    params[param_name] = "Any"

            functions_manifest[name] = params

        validated_manifest = ManifestOutput(
            plugin_name=plugin_name,
            functions=functions_manifest,
        )
        return validated_manifest.model_dump_json(indent=1)

    @staticmethod
    def ping() -> str:
        """Health check function that returns validated 'pong'."""
        return PingOutput(response="pong").response

    @staticmethod
    def lowercase(text: str) -> str:
        val = StringInput(text=text)
        return StringOutput(result=val.text.lower()).result

    @staticmethod
    def uppercase(text: str) -> str:
        val = StringInput(text=text)
        return StringOutput(result=val.text.upper()).result

    @staticmethod
    def reverse(text: str) -> str:
        val = StringInput(text=text)
        return StringOutput(result=val.text[::-1]).result

    @staticmethod
    def length(text: str) -> int:
        val = StringInput(text=text)
        return LengthOutput(length=len(val.text)).length

    @staticmethod
    def _contains(text: str, sub: str) -> bool:
        val = SubstringInput(text=text, sub=sub)
        return ContainsOutput(contains=val.sub in val.text).contains


if __name__ == "__main__":
    pw = PluginManager()
    print("Manifest:", pw.get_manifest())
    print("ping:", PluginManager.ping())
    print("length:", PluginManager.length("ALEMU"))
    print("lowercase:", PluginManager.lowercase("ALEMU"))