"""More demoscene-style audio-reactive effects: moire, metaballs, ripple, fire,
matrix rain. Original implementations of classic public-domain techniques,
rendered in grayscale for the 256x64 panel.
"""
from __future__ import annotations

import math
import random

from PIL import ImageDraw

from .. import frame as F
from .base import AppletMeta, Ctx
from .viz import HAVE_NP, TRAILS, _Viz

if HAVE_NP:
    import numpy as np


class MoireApplet(_Viz):
    meta = AppletMeta(key="moire", name="Moire", description="Interfering ring sources",
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"},
                                     "trails": {**TRAILS, "default": 40}})

    def render(self, ctx: Ctx):
        if not HAVE_NP:
            return self._pulse(ctx)
        gx, gy = self._grids()
        a = self._audio
        t, bass, lvl = ctx.t, a.bass, a.level
        asp = self.size[0] / self.size[1]
        x = gx * asp
        f1 = (asp * (0.5 + 0.35 * math.sin(t * 0.7)), 0.5 + 0.35 * math.cos(t * 0.9))
        f2 = (asp * (0.5 + 0.35 * math.sin(t * 1.1 + 2)), 0.5 + 0.35 * math.cos(t * 0.6 + 1))
        d1 = np.sqrt((x - f1[0]) ** 2 + (gy - f1[1]) ** 2)
        d2 = np.sqrt((x - f2[0]) ** 2 + (gy - f2[1]) ** 2)
        k = 28 + 22 * bass
        v = np.cos(d1 * k - t * 2) + np.cos(d2 * k + t * 1.5)
        v = (v + 2) / 4
        g = v * (0.5 + 0.5 * lvl) * 255.0
        return self._feedback(g)


class MetaballsApplet(_Viz):
    meta = AppletMeta(key="metaballs", name="Metaballs", description="Gooey blobs",
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"},
                                     "balls": {"type": "int", "default": 4, "label": "Blobs"},
                                     "trails": {**TRAILS, "default": 35}})

    def render(self, ctx: Ctx):
        if not HAVE_NP:
            return self._pulse(ctx)
        w, h = self.size
        gx, gy = self._grids()
        px, py = gx * w, gy * h
        a = self._audio
        t, lvl = ctx.t, a.level
        nb = max(2, int(self.config.get("balls", 4)))
        field = np.zeros((h, w), np.float32)
        rad = (h * 0.42) * (0.7 + 0.5 * lvl)
        for i in range(nb):
            bx = w * (0.5 + 0.42 * math.sin(t * (0.5 + 0.2 * i) + i))
            by = h * (0.5 + 0.42 * math.cos(t * (0.4 + 0.25 * i) + i * 2))
            field += (rad * rad) / ((px - bx) ** 2 + (py - by) ** 2 + 1.0)
        g = np.clip((field - 0.8) * 200, 0, 255)
        return self._feedback(g.astype(np.float32))


class RippleApplet(_Viz):
    meta = AppletMeta(key="ripple", name="Ripple", description="Water ripples (beat drops)",
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"}})

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._cur = self._prev = None
        self._last_beat = 0.0

    def render(self, ctx: Ctx):
        w, h = self.size
        if not HAVE_NP:
            return self._pulse(ctx)
        if self._cur is None or self._cur.shape != (h, w):
            self._cur = np.zeros((h, w), np.float32)
            self._prev = np.zeros((h, w), np.float32)
        a = self._audio
        cur, prev = self._cur, self._prev
        lap = (np.roll(cur, 1, 0) + np.roll(cur, -1, 0) + np.roll(cur, 1, 1) + np.roll(cur, -1, 1))
        nxt = lap * 0.5 - prev
        nxt *= 0.96
        # drop on beat, plus a gentle idle drop
        beat = a.beat if a.ok else 0
        if beat > 0.4 and beat > self._last_beat:
            nxt[random.randint(2, h - 3), random.randint(2, w - 3)] += 260
        self._last_beat = beat
        if int(ctx.t * 2) != int((ctx.t - 0.05) * 2) and beat <= 0.4:
            nxt[h // 2, random.randint(2, w - 3)] += 120
        self._prev, self._cur = cur, nxt
        g = np.clip(128 + nxt, 0, 255).astype(np.uint8)
        from PIL import Image
        return Image.fromarray(g, "L")


class FireApplet(_Viz):
    meta = AppletMeta(key="fire", name="Fire", description="Classic fire (bass-fed)",
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"}})

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._fire = None

    def render(self, ctx: Ctx):
        w, h = self.size
        if not HAVE_NP:
            return self._pulse(ctx)
        if self._fire is None or self._fire.shape != (h, w):
            self._fire = np.zeros((h, w), np.float32)
        a = self._audio
        bass = a.bass if a.ok else 0.4
        fire = self._fire
        below = np.roll(fire, -1, 0)
        nxt = (below * 2 + np.roll(below, 1, 1) + np.roll(below, -1, 1)) / 4.04 - 3.0
        nxt = np.clip(nxt, 0, 255)
        nxt[-1] = np.random.rand(w) * 255 * (0.55 + 0.6 * bass)
        self._fire = nxt
        from PIL import Image
        return Image.fromarray(nxt.astype(np.uint8), "L")


class MatrixApplet(_Viz):
    meta = AppletMeta(key="matrix", name="Matrix", description="Falling code rain",
                      config_schema={"fps": {"type": "int", "default": 18, "label": "FPS"}})

    GLYPH = "01<>/\\|=+*"

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._heads = None
        self._cw = 8
        self._ch = 11

    def render(self, ctx: Ctx):
        w, h = self.size
        cols = max(1, w // self._cw)
        if self._heads is None or len(self._heads) != cols:
            self._heads = [random.uniform(-h, 0) for _ in range(cols)]
        img = F.canvas(w, h)
        d = ImageDraw.Draw(img)
        a = self._audio
        spd = self._ch * (0.6 + 1.6 * (a.level if a.ok else 0.4))
        f = F.font(self._ch)
        for c in range(cols):
            self._heads[c] += spd / 30.0
            if self._heads[c] - 6 * self._ch > h:
                self._heads[c] = random.uniform(-h * 0.5, 0)
            hy = self._heads[c]
            x = c * self._cw + 1
            for kk in range(6):
                y = hy - kk * self._ch
                if -self._ch < y < h:
                    g = 255 if kk == 0 else max(40, 190 - kk * 32)
                    d.text((x, y), random.choice(self.GLYPH), font=f, fill=g)
        return img
