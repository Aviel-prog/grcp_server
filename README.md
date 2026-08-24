# grpc-plugin-engine

Loads Python "plugins" as isolated gRPC server processes and calls their
functions as if they were local.

## How it works

1. `Engine.load_plugin("math_plugin")` spawns `src/plugins/math_plugin.py`
   in its own OS process, running a `PluginService` gRPC server on a
   free local port (`src/plugin_server.py`).
2. It waits for the process to answer `GetManifest` (health check), then
   hands back a `ProxyWrapper` (`src/core/proxy.py`).
3. Any attri[README.md](README.md)bute access on the wrapper, e.g. `math_plugin.add(1, 2)`, is
   resolved against the plugin's manifest and turned into a `FuncCall` RPC.
4. When the `with Engine.load_plugin(...) as plugin:` block exits, the
   proxy's channel is closed, and the process is terminated (unless it was
   already running before this call started it).

```
main.py -> Engine.load_plugin("math_plugin")
              |
              spawns a new process running plugin_server.run_plugin_server
              |
              v
        [ math_plugin process ]
        gRPC server on localhost:<port>
        wraps plugins/math_plugin.PluginManager
```

## Writing a new plugin

Create `src/plugins/<name>.py` with a `PluginManager` class extending
`BasePluginManager`:

```python
from src.core.plugin_manifest import BasePluginManager


class PluginManager(BasePluginManager):
    @staticmethod
    def greet(name: str) -> str:
        return f"Hello, {name}!"
```

`ping()`, `get_manifest()`, and `plugin_name()` come from the base class
for free. Every other public `@staticmethod` (or regular method) becomes
callable remotely and shows up in the manifest with its parameter/return
type hints.

Validate inputs with a Pydantic model inside the method body (see
`math_plugin.py` / `string_plugin.py` for examples) - a `ValueError` raised
during validation is translated into a gRPC `INVALID_ARGUMENT` response.

## Development

```bash
pip install -r requirements.txt
python main.py

# after editing engine.proto:
./scripts/generate_proto.sh

# tests:
python -m unittest discover tests
```

## Known limitations

- `Engine` holds a single global lock while starting a plugin process, so
  concurrently loading two *different* plugins from multiple threads is
  serialized rather than parallel. Fine for typical usage; would need
  per-plugin locks to fix.
- Plugin servers are plaintext (`add_insecure_port`), since they only ever
  bind to `localhost`. Switch to `add_secure_port` with TLS credentials if
  they're ever exposed beyond the local machine.
- `GetManifestRequest.plugin_name` is an unused/reserved proto field (see
  `engine.proto`) left over from a previous design with a central plugin
  registry; removing it requires regenerating the proto.
