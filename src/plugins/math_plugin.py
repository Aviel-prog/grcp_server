import inspect
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from src.plugins.common.plugin_common import StrictBaseModel, BasePlugin


# ==========================================
# Pydantic Schemas for Inputs
# ==========================================

class AddInput(StrictBaseModel):
    a: int | float = Field(description="First operand")
    b: int | float = Field(description="Second operand")


class SubInput(StrictBaseModel):
    a: int | float = Field(description="First operand")
    b: int | float = Field(description="Second operand")


class MultiplyInput(StrictBaseModel):
    a: int | float = Field(description="First operand")
    b: int | float = Field(description="Second operand")


class PowInput(StrictBaseModel):
    a: int | float = Field(description="Base")
    b: int | float = Field(description="Exponent")


class DivInput(StrictBaseModel):
    a: int | float = Field(description="Numerator")
    b: int | float = Field(description="Denominator")

    @field_validator("b")
    @classmethod
    def prevent_zero_division(cls, value: int | float) -> int | float:
        if value == 0:
            raise ValueError("Division by zero is not allowed.")
        return value


# ==========================================
# Pydantic Schemas for Outputs
# ==========================================
class NumberOutput(StrictBaseModel):
    result: int | float = Field(description="Resulting numeric value")


class ManifestOutput(StrictBaseModel):
    plugin_name: str = Field(description="Name of the plugin")
    functions: dict[str, dict[str, Any]] = Field(description="Map of function names to parameter types")


# ==========================================
# Plugin Manager Implementation
# ==========================================
class PluginManager(BasePlugin):
    """Math operations plugin manager with static methods and Pydantic input/output validation."""

    def get_manifest(self) -> str:
        """Dynamically inspects class methods to generate the manifest json."""
        functions_manifest = {}
        try:
            plugin_name = Path(__file__).stem
        except NameError:
            plugin_name = self.__class__.__module__.split(".")[-1]

        # Use inspect.isfunction to capture staticmethods on class
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

        validated_output = ManifestOutput(
            plugin_name=plugin_name,
            functions=functions_manifest,
        )
        return validated_output.model_dump_json(indent=2)

    @staticmethod
    def add(a: int | float, b: int | float) -> int | float:
        val_in = AddInput(a=a, b=b)
        res = val_in.a + val_in.b
        return NumberOutput(result=res).result

    @staticmethod
    def sub(a: int | float, b: int | float) -> int | float:
        val_in = SubInput(a=a, b=b)
        res = val_in.a - val_in.b
        return NumberOutput(result=res).result

    @staticmethod
    def multiply(a: int | float, b: int | float) -> int | float:
        val_in = MultiplyInput(a=a, b=b)
        res = val_in.a * val_in.b
        return NumberOutput(result=res).result

    @staticmethod
    def pow(a: int | float, b: int | float) -> int | float:
        val_in = PowInput(a=a, b=b)
        res = val_in.a ** val_in.b
        return NumberOutput(result=res).result

    @staticmethod
    def div(a: int | float, b: int | float) -> int | float:
        val_in = DivInput(a=a, b=b)
        res = val_in.a / val_in.b
        return NumberOutput(result=res).result


if __name__ == "__main__":
    pw = PluginManager()
    print("Manifest:", pw.get_manifest())
    print("Add:", PluginManager.add(2, 3))
    print("Div:", PluginManager.div(10, 2))
