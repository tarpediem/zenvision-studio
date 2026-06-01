"""Clock applet — time and date, adapts its font to the zone size."""
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
        secs = self.config.get("seconds", True) and w >= 150
        tf = now.strftime("%H:%M:%S" if secs else "%H:%M")

        fs = int(h * 0.62)
        while fs > 8 and F.text_width(tf, fs) > w - 6:
            fs -= 1

        show_date = h >= 44 and w >= 90
        if show_date:
            F.text(img, (w // 2, int(h * 0.37)), tf, size=fs, anchor="mm")
            df = now.strftime("%a %d %b").upper()
            dfs = max(7, int(h * 0.22))
            while dfs > 7 and F.text_width(df, dfs) > w - 4:
                dfs -= 1
            F.text(img, (w // 2, int(h * 0.80)), df, size=dfs, anchor="mm")
        else:
            F.text(img, (w // 2, h // 2), tf, size=fs, anchor="mm")
        return img
