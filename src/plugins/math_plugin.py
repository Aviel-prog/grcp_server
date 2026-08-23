import inspect
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


# ==========================================
# Pydantic Schemas for Inputs
# ==========================================
class PingOutput(BaseModel):
    response: str = Field()

class AddInput(BaseModel):
    a: int | float = Field(description="First operand")
    b: int | float = Field(description="Second operand")


class SubInput(BaseModel):
    a: int | float = Field(description="First operand")
    b: int | float = Field(description="Second operand")


class MultiplyInput(BaseModel):
    a: int | float = Field(description="First operand")
    b: int | float = Field(description="Second operand")


class PowInput(BaseModel):
    a: int | float = Field(description="Base")
    b: int | float = Field(description="Exponent")


class DivInput(BaseModel):
    a: int | float = Field(description="Numerator")
    b: int | float = Field(description="Denominator")

    @field_validator("b")
    @classmethod
    def prevent_zero_division(cls, value: int | float) -> int | float:
        if value == 0:
            raise ValueError("Division by zero is not allowed.")
        return value


# ==========================================
# Plugin Manager Implementation
# ==========================================

class PluginManager:
    """Math operations plugin manager with static methods and Pydantic input models."""

    def get_manifest(self) -> dict: # TODO add value return
        """Dynamically inspects class static methods to generate the manifest."""
        excluded = {"get_manifest"}
        functions_manifest = {}
        try:
            plugin_name = Path(__file__).stem
        except NameError:
            plugin_name = self.__class__.__module__.split(".")[-1]

        # Use inspect.isfunction to capture staticmethods on class
        for name, method in inspect.getmembers(self.__class__, predicate=inspect.isfunction):
            if name.startswith("_") or name in excluded:
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

        return {
            "plugin_name": plugin_name,
            "functions": functions_manifest,
        }

    @staticmethod
    def ping() -> str:
        """Health check function that returns validated 'pong'."""
        return PingOutput(response="pong").response

    @staticmethod
    def add(a: int | float, b: int | float) -> int | float:
        validated = AddInput(a=a, b=b)
        return validated.a + validated.b

    @staticmethod
    def sub(a: int | float, b: int | float) -> int | float:
        validated = SubInput(a=a, b=b)
        return validated.a - validated.b

    @staticmethod
    def multiply(a: int | float, b: int | float) -> int | float:
        validated = MultiplyInput(a=a, b=b)
        return validated.a * validated.b

    @staticmethod
    def pow(a: int | float, b: int | float) -> int | float:
        validated = PowInput(a=a, b=b)
        return validated.a ** validated.b

    @staticmethod
    def div(a: int | float, b: int | float) -> int | float:
        validated = DivInput(a=a, b=b)
        return validated.a / validated.b


if __name__ == '__main__':
    pw = PluginManager()
    print("Manifest:", pw.get_manifest())
    print("Add:", PluginManager.add(2, 3))
    print("Div:", PluginManager.div(10, 2))