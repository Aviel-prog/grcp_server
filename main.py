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

    with Engine.load_plugin("math_plugin") as math_plugin:
        print(math_plugin.get_manifest())
        print(math_plugin.add(1, 2))
        print(math_plugin.sub(1, 2))



if __name__ == "__main__":
    main()
