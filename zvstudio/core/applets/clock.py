"""Clock applet — time and date."""
from __future__ import annotations

import datetime

from PIL import Image

from .. import frame as F
from .base import Applet, AppletMeta, Ctx


class ClockApplet(Applet):
    meta = AppletMeta(
        key="clock",
        name="Clock",
        description="Time and date",
        config_schema={
            "seconds": {"type": "bool", "default": True, "label": "Show seconds"},
            "fps": {"type": "int", "default": 2, "label": "FPS"},
        },
    )

    def render(self, ctx: Ctx) -> Image.Image:
        w, h = self.size
        img = F.canvas(w, h)
        now = datetime.datetime.now()
        fmt = "%H:%M:%S" if self.config.get("seconds") else "%H:%M"
        F.text(img, (w // 2, 24), now.strftime(fmt), size=34, anchor="mm")
        F.text(img, (w // 2, 52), now.strftime("%a %d %b").upper(), size=14, anchor="mm")
        return img
