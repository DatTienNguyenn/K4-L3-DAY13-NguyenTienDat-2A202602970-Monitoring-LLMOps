from __future__ import annotations

import os
import socket
from contextlib import contextmanager
from typing import Any

_orig_getaddrinfo = socket.getaddrinfo


def _fast_getaddrinfo(host: Any, port: Any, *args: Any, **kwargs: Any):
    results = _orig_getaddrinfo(host, port, *args, **kwargs)
    if host == "cloud.langfuse.com":
        fast = [r for r in results if r[4][0] != "54.154.141.85"]
        if fast:
            return fast
    return results


socket.getaddrinfo = _fast_getaddrinfo

try:
    from langfuse import get_client, observe, propagate_attributes

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False

    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    class _DummyClient:
        def update_current_span(self, **kwargs: Any) -> None:
            return None

        def update_current_generation(self, **kwargs: Any) -> None:
            return None

    def get_client():
        return _DummyClient()

    @contextmanager
    def propagate_attributes(**kwargs: Any):
        yield


def get_langfuse_client():
    return get_client()


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )
