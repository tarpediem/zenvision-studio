"""In-memory frame player — used by the web editor ("Draw") to push frames."""
from __future__ import annotations

from PIL import Image

from .. import frame as F
from .base import Applet, AppletMeta, Ctx


class FramesApplet(Applet):
    meta = AppletMeta(
        key="frames",
        name="Frames",
        description="Play frames sent from the editor",
        config_schema={"fps": {"type": "int", "default": 15, "label": "FPS"}},
    )

    def __init__(self, *a, frames: list[Image.Image] | None = None, **k) -> None:
        super().__init__(*a, **k)
        self._frames = [f.convert("L") for f in (frames or [])]

    def set_frames(self, frames: list[Image.Image]) -> None:
        self._frames = [f.convert("L") for f in frames]

    def render(self, ctx: Ctx) -> Image.Image:
        if not self._frames:
            return F.canvas(*self.size)
        # Advance by our own fps (decoupled from the compositor's tick rate) so
        # the editor's playback speed matches what lands on the panel.
        idx = int(ctx.t * self.fps) % len(self._frames)
        return self._frames[idx]
