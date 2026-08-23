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
    """אוסף גם methods רגילות וגם staticmethods, ניגש דרך ה-instance
    כדי שקריאה בפועל (func(*args)) תעבוד זהה בשני המקרים."""
    excluded = {"get_manifest"}
    plugin_cls = type(plugin_instance)

    registered = {}
    for name, _ in inspect.getmembers(plugin_cls, predicate=inspect.isfunction):
        if name.startswith("_") or name in excluded:
            continue
        registered[name] = getattr(plugin_instance, name)

    return registered