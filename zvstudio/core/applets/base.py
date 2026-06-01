"""Applet plugin interface.

An applet renders frames for the panel. Implement :meth:`render` (one frame per
tick). Declare metadata + a tiny config schema so the web UI / CLI can expose
options generically. Third-party applets register via the ``zvstudio.applets``
entry-point group.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from PIL import Image

from .. import frame as F


@dataclass
class Ctx:
    """Render context passed to :meth:`Applet.render`."""

    t: float                 # seconds since this applet became active
    frame: int               # frame counter since active
    size: tuple[int, int]    # (width, height)


@dataclass
class AppletMeta:
    key: str
    name: str
    description: str = ""
    # field -> {"type": "bool|int|str|path|color", "default": ..., "label": ..., ...}
    config_schema: dict = field(default_factory=dict)


class Applet:
    meta: AppletMeta = AppletMeta(key="base", name="Applet")

    def __init__(self, size: tuple[int, int] = (256, 64), config: dict | None = None) -> None:
        self.size = size
        self.config = {**self.defaults(), **(config or {})}

    @classmethod
    def defaults(cls) -> dict:
        return {k: v.get("default") for k, v in cls.meta.config_schema.items()}

    # --- override one of these ------------------------------------------
    def render(self, ctx: Ctx) -> Image.Image:
        """Return a single grayscale frame for this tick."""
        return F.canvas(*self.size)

    # --- optional hooks --------------------------------------------------
    @property
    def fps(self) -> float:
        return float(self.config.get("fps", 10) or 10)

    def wants_focus(self) -> bool:
        """Return True to preempt the playlist (e.g. media just started)."""
        return False

    def on_start(self) -> None:
        pass

    def on_stop(self) -> None:
        pass
