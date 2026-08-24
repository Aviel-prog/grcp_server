"""Utility functions for network calls, socket handling, and gRPC channel setups."""

import socket


def find_free_port() -> int:
    """Returns an OS-assigned free TCP port on localhost.

    Note: there is an inherent, small TOCTOU race between this socket being
    released and the plugin server actually binding to the returned port.
    Acceptable for local, single-host process orchestration where plugins
    are loaded sequentially; would need a different strategy (e.g. binding
    and handing off the live socket) under high concurrency.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as temp_socket:
        temp_socket.bind(("", 0))
        return temp_socket.getsockname()[1]
