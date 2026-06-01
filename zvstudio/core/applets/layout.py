"""Layout applet — compose several applets into rectangular zones of the panel.

Each zone owns a child applet rendered at the zone's size, then pasted into its
box. Thin separators are drawn between zones. Built dynamically by the daemon
from a layout spec (not in the registry).
"""
from __future__ import annotations

from PIL import ImageDraw

from .. import frame as F
from .base import Applet, AppletMeta, Ctx


class LayoutApplet(Applet):
    meta = AppletMeta(key="layout", name="Layout", description="Compose applets in zones")

    def __init__(self, *a, zones=None, dividers: bool = True, **k) -> None:
        super().__init__(*a, **k)
        # zones: list of (applet, (x, y, w, h))
        self.zones = zones or []
        self.dividers = dividers

    def on_start(self) -> None:
        for ap, _ in self.zones:
            try:
                ap.on_start()
            except Exception:
                pass

    def on_stop(self) -> None:
        for ap, _ in self.zones:
            try:
                ap.on_stop()
            except Exception:
                pass

    def render(self, ctx: Ctx):
        img = F.canvas(*self.size)
        for ap, (x, y, bw, bh) in self.zones:
            try:
                sub = ap.render(Ctx(t=ctx.t, frame=ctx.frame, size=(bw, bh)))
                if sub.mode != "L":
                    sub = sub.convert("L")
                if sub.size != (bw, bh):
                    sub = sub.resize((bw, bh))
                img.paste(sub, (x, y))
            except Exception:
                pass
        if self.dividers:
            d = ImageDraw.Draw(img)
            W, H = self.size
            for _, (x, y, bw, bh) in self.zones:
                if x > 0:
                    d.line([(x - 1, 2), (x - 1, H - 3)], fill=55)
                if y > 0:
                    d.line([(2, y - 1), (W - 3, y - 1)], fill=55)
        return img
