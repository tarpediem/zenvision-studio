"""Geometric / demoscene visualisers — nested triangles, a wireframe cube and a
starfield. They animate on time, react to the audio (level / bass / beat) and
reuse the viz feedback buffer for MilkDrop-style trails.
"""
from __future__ import annotations

import math

from PIL import ImageDraw

from .. import frame as F
from .base import AppletMeta, Ctx
from .viz import HAVE_NP, TRAILS, WARP, _Viz

if HAVE_NP:
    import numpy as np


def _poly(cx, cy, r, sides, rot):
    return [(cx + r * math.cos(rot + 2 * math.pi * k / sides),
             cy + r * math.sin(rot + 2 * math.pi * k / sides)) for k in range(sides)]


class TrianglesApplet(_Viz):
    meta = AppletMeta(key="triangles", name="Triangles", description="Nested rotating triangles",
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"},
                                     "layers": {"type": "int", "default": 6, "label": "Layers"},
                                     "trails": {**TRAILS, "default": 55}})

    def render(self, ctx: Ctx):
        w, h = self.size
        img = F.canvas(w, h)
        d = ImageDraw.Draw(img)
        a = self._audio
        t = ctx.t
        lvl = a.level if a.ok else 0.5 - 0.5 * math.cos(t * 1.5)
        bass = a.bass if a.ok else lvl
        layers = max(1, int(self.config.get("layers", 6)))
        base = min(w, h) * (0.46 + 0.18 * lvl)
        cx, cy = w / 2, h / 2
        for i in range(layers):
            f = 1 - i / layers
            r = base * f
            rot = t * (0.5 + 0.6 * bass) * (1 if i % 2 == 0 else -1) + i * 0.5
            g = int(70 + 185 * f)
            d.polygon(_poly(cx, cy, r, 3, rot), outline=g)
        if HAVE_NP:
            return self._feedback(np.asarray(img, dtype=np.float32))
        return img


class CubeApplet(_Viz):
    meta = AppletMeta(key="cube", name="Cube", description="Rotating wireframe cube",
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"},
                                     "trails": {**TRAILS, "default": 50}})

    V = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
         (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
    E = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
         (0, 4), (1, 5), (2, 6), (3, 7)]

    def render(self, ctx: Ctx):
        w, h = self.size
        img = F.canvas(w, h)
        d = ImageDraw.Draw(img)
        a = self._audio
        t = ctx.t
        lvl = a.level if a.ok else 0.5 - 0.5 * math.cos(t * 1.5)
        ax, ay = t * 0.7, t * 0.9
        s = min(w, h) * 0.34 * (0.85 + 0.5 * lvl)
        cx, cy = w / 2, h / 2
        ca, sa = math.cos(ax), math.sin(ax)
        cb, sb = math.cos(ay), math.sin(ay)
        proj = []
        for x, y, z in self.V:
            y, z = y * ca - z * sa, y * sa + z * ca   # rotate X
            x, z = x * cb + z * sb, -x * sb + z * cb  # rotate Y
            proj.append((cx + x * s, cy + y * s, z))
        for i, j in self.E:
            zavg = (proj[i][2] + proj[j][2]) / 2
            g = int(110 + 110 * (zavg + 1.6) / 3.2)   # nearer edges brighter
            d.line([proj[i][:2], proj[j][:2]], fill=max(40, min(255, g)), width=1)
        if HAVE_NP:
            return self._feedback(np.asarray(img, dtype=np.float32))
        return img


class StarfieldApplet(_Viz):
    meta = AppletMeta(key="starfield", name="Starfield", description="Warp stars (beat-reactive)",
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"},
                                     "count": {"type": "int", "default": 90, "label": "Stars"},
                                     "trails": {**TRAILS, "default": 45}, "warp": {**WARP, "default": 0}})

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._stars: list[list[float]] = []
        self._lt = 0.0

    def _seed(self, n):
        import random
        self._stars = [[random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0.05, 1.0)]
                       for _ in range(n)]

    def render(self, ctx: Ctx):
        import random
        w, h = self.size
        img = F.canvas(w, h)
        d = ImageDraw.Draw(img)
        a = self._audio
        n = max(8, int(self.config.get("count", 90)))
        if len(self._stars) != n:
            self._seed(n)
        dt = max(0.0, min(0.1, ctx.t - self._lt))
        self._lt = ctx.t
        lvl = a.level if a.ok else 0.4
        speed = (0.25 + 1.4 * lvl + 1.8 * (a.beat if a.ok else 0)) * dt
        cx, cy = w / 2, h / 2
        scale = min(w, h) * 0.9
        for st in self._stars:
            st[2] -= speed
            if st[2] <= 0.02:
                st[0], st[1], st[2] = random.uniform(-1, 1), random.uniform(-1, 1), 1.0
            sx = cx + st[0] / st[2] * scale
            sy = cy + st[1] / st[2] * scale
            if 0 <= sx < w and 0 <= sy < h:
                g = int(60 + 195 * (1 - st[2]))
                rad = 0 if st[2] > 0.4 else 1
                d.ellipse([sx - rad, sy - rad, sx + rad, sy + rad], fill=g)
        if HAVE_NP:
            return self._feedback(np.asarray(img, dtype=np.float32))
        return img
