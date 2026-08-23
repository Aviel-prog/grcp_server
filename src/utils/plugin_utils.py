import importlib.util
import inspect
import os
import socket


PLUGINS_DIR = "src/plugins"


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def import_plugin_manager(plugin_filename: str):
    """טוען דינמית קובץ plugins/<plugin_filename>.py ומחזיר את מחלקת PluginManager שבתוכו"""
    module_path = os.path.join(PLUGINS_DIR, f"{plugin_filename}.py")

    if not os.path.isfile(module_path):
        raise FileNotFoundError(f"Plugin file not found: {module_path}")

    spec = importlib.util.spec_from_file_location(plugin_filename, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "PluginManager"):
        raise AttributeError(f"'{plugin_filename}.py' does not define a PluginManager class")

    return module.PluginManager


def build_registered_functions(plugin_instance) -> dict:
    excluded = {"get_manifest"}
    return {
        name: method
        for name, method in inspect.getmembers(plugin_instance, predicate=inspect.ismethod)
        if not name.startswith("_") and name not in excluded
    }