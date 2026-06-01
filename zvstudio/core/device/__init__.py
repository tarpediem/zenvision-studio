"""Device backends. The compositor talks to a :class:`Panel`; concrete backends
implement the transport (real USB panel, or a hardware-free mock for dev/CI)."""
from __future__ import annotations

import os

from .base import Panel


def get_panel(name: str | None = None, **kwargs) -> Panel:
    """Return a panel backend by name (or from ``ZVSTUDIO_BACKEND``).

    Falls back to the mock backend if the real device can't be opened, unless an
    explicit backend was requested.
    """
    name = name or os.environ.get("ZVSTUDIO_BACKEND") or "auto"
    if name in ("zenvision", "auto"):
        from .zenvision import ZenVisionPanel
        try:
            p = ZenVisionPanel(**kwargs)
            p.open()
            return p
        except Exception:
            if name == "zenvision":
                raise
            # auto: fall through to mock
    from .mock import MockPanel
    p = MockPanel(**kwargs)
    p.open()
    return p
