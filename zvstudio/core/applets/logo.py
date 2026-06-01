"""Logo applet — an animated "spark" mark (pulses and slowly rotates)."""
from __future__ import annotations

import math

from PIL import ImageDraw

from .. import frame as F
from .base import Applet, AppletMeta, Ctx

RAY_LEN = [1.00, 0.82, 0.94, 0.78, 1.00, 0.86, 0.96, 0.80, 0.98, 0.84, 0.92]
RAYS = 11


class LogoApplet(Applet):
    meta = AppletMeta(
        key="logo",
        name="Logo",
        description="Animated spark mark",
        config_schema={
            "fps": {"type": "int", "default": 24, "label": "FPS"},
            "spin": {"type": "bool", "default": True, "label": "Rotate"},
        },
    )

    def render(self, ctx: Ctx):
        w, h = self.size
        img = F.canvas(w, h)
        d = ImageDraw.Draw(img)
        cx, cy = w / 2, h / 2
        base = min(w, h) * 0.46
        inner = max(1.0, base * 0.06)
        pulse = 0.5 - 0.5 * math.cos(ctx.t * 2.0)
        rot = ctx.t * 0.6 if self.config.get("spin", True) else 0.0
        for i in range(RAYS):
            a = rot + 2 * math.pi * i / RAYS
            outer = base * RAY_LEN[i % len(RAY_LEN)] * (0.86 + 0.14 * pulse)
            half = (math.pi / RAYS) * (0.30 + 0.06 * pulse)
            sr = base * 0.16
            tip = (cx + outer * math.cos(a), cy + outer * math.sin(a))
            sh1 = (cx + sr * math.cos(a - half), cy + sr * math.sin(a - half))
            sh2 = (cx + sr * math.cos(a + half), cy + sr * math.sin(a + half))
            cen = (cx + inner * math.cos(a), cy + inner * math.sin(a))
            d.polygon([cen, sh1, tip, sh2], fill=255)
        d.ellipse([cx - inner * 1.6, cy - inner * 1.6, cx + inner * 1.6, cy + inner * 1.6], fill=255)
        return img
