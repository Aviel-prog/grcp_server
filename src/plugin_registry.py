import inspect

from plugins.math_plugin import PluginManager


def build_registered_functions(plugin_instance) -> dict:
    """רושם אוטומטית כל method ציבורי (חוץ מ-get_manifest) כפונקציה קריאה"""
    excluded = {"get_manifest"}
    return {
        name: method
        for name, method in inspect.getmembers(plugin_instance, predicate=inspect.ismethod)
        if not name.startswith("_") and name not in excluded
    }


plugin_manager = PluginManager()
REGISTERED_FUNCTIONS = build_registered_functions(plugin_manager)
