"""Example third-party applet: a bouncing dot ("DVD logo" energy).

Ship this in your own package and register it so zenvision-studio picks it up:

    # pyproject.toml
    [project.entry-points."zvstudio.applets"]
    bounce = "your_package.sample_applet:BounceApplet"

Then it appears in the web UI / `zvstudio show bounce` automatically.
"""
from __future__ import annotations

from PIL import ImageDraw

from zvstudio.core import frame as F
from zvstudio.core.applets.base import Applet, AppletMeta, Ctx


class BounceApplet(Applet):
    meta = AppletMeta(
        key="bounce",
        name="Bounce",
        description="A dot bouncing around the panel",
        config_schema={
            "fps": {"type": "int", "default": 30, "label": "FPS"},
            "speed": {"type": "int", "default": 90, "label": "px/s"},
            "radius": {"type": "int", "default": 4, "label": "Dot radius"},
        },
    )

    def render(self, ctx: Ctx):
        w, h = self.size
        r = int(self.config.get("radius", 4))
        spd = float(self.config.get("speed", 90))
        span_x, span_y = w - 2 * r, h - 2 * r

        def tri(p):  # triangle wave 0..1..0
            p %= 2.0
            return p if p < 1.0 else 2.0 - p

        x = r + span_x * tri(ctx.t * spd / max(1, span_x))
        y = r + span_y * tri(ctx.t * spd / max(1, span_y) * 0.73)

        img = F.canvas(w, h)
        ImageDraw.Draw(img).ellipse([x - r, y - r, x + r, y + r], fill=255)
        return img
