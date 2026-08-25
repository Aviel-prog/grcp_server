"""Example entry point demonstrating plugin loading and invocation."""

import logging

from src.core.engine import Engine


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> None:
    configure_logging()

    with Engine.load_plugin("string_plugin") as math_plugin:
        print(math_plugin.lowercase("ALEMU"))
        print(math_plugin.ping())
        print(math_plugin.get_manifest())

    with Engine.load_plugin("math_plugin") as math_plugin:
        print(math_plugin.add(1, 2))
        print(math_plugin.sub(1, 2551))
        print(math_plugin.get_manifest())
        print(math_plugin.ping())



if __name__ == "__main__":
    main()
