"""Dynamic plugin discovery and loading."""

import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType

# Resolved relative to this file's location rather than a hardcoded
# "src/plugins" string, so it no longer depends on the process's current
# working directory (the previous version broke whenever the script was
# launched from any directory other than the project root).
PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


class PluginLoadError(Exception):
    """Raised when a plugin module cannot be located, imported, or is
    malformed (e.g. missing the required `PluginManager` class)."""


def import_plugin_manager(plugin_filename: str) -> type:
    """Dynamically imports `<PLUGINS_DIR>/<plugin_filename>.py` and returns
    the `PluginManager` class it defines.

    Raises:
        PluginLoadError: if the file is missing, fails to import, or does
            not define a `PluginManager` class.
    """
    module_path = PLUGINS_DIR / f"{plugin_filename}.py"
    if not module_path.is_file():
        raise PluginLoadError(f"Plugin file not found: {module_path}")

    module = _load_module_from_path(plugin_filename, module_path)

    if not hasattr(module, "PluginManager"):
        raise PluginLoadError(f"'{plugin_filename}.py' does not define a PluginManager class")

    return module.PluginManager


def build_registered_functions(plugin_instance) -> dict:
    """Collects every public callable exposed by the plugin's class -
    regular methods and static methods alike - bound through `plugin_instance`
    so both kinds are invoked identically as `func(*args)` by the caller.
    """
    plugin_cls = type(plugin_instance)

    return {
        name: getattr(plugin_instance, name)
        for name, _ in inspect.getmembers(plugin_cls, predicate=inspect.isfunction)
        if not name.startswith("_")
    }


def _load_module_from_path(module_name: str, module_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise PluginLoadError(f"Could not create import spec for: {module_path}")

    module = importlib.util.module_from_spec(spec)

    # Must happen *before* exec_module: inspect.getfile/getsourcefile (used
    # by BasePluginManager.plugin_name) looks the module up via
    # sys.modules[cls.__module__]. Skip this and the module works fine at
    # runtime, but any later introspection of it raises a misleading
    # "is a built-in class" TypeError.
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        raise PluginLoadError(f"Failed to import plugin '{module_name}': {exc}") from exc

    return module
