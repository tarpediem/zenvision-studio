"""Audio-reactive generative visualisers (MilkDrop-ish) for the 256x64 panel.

Plasma / Tunnel / Scope. They always animate on time and react more strongly to
the live audio features (level / bass / treble / waveform) from the shared
analyser. Plasma & Tunnel need numpy (graceful pulse fallback otherwise).
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

from .. import frame as F
from ..audio import HAVE_NP, AudioLevel
from .base import Applet, AppletMeta, Ctx

if HAVE_NP:
    import numpy as np


class _Viz(Applet):
    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._audio = AudioLevel.get()
        self._gsize = None

    def _grids(self):
        w, h = self.size
        if self._gsize != (w, h):
            xs = np.linspace(0, 1, w, dtype=np.float32)
            ys = np.linspace(0, 1, h, dtype=np.float32)
            self._gx, self._gy = np.meshgrid(xs, ys)
            self._gsize = (w, h)
        return self._gx, self._gy

    def _pulse(self, ctx: Ctx):
        w, h = self.size
        img = F.canvas(w, h)
        a = self._audio
        lvl = a.level if a.ok else (0.5 - 0.5 * math.cos(ctx.t * 2))
        r = int(min(w, h) * 0.1 + min(w, h) * 0.38 * lvl)
        ImageDraw.Draw(img).ellipse([w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r], outline=255)
        return img


class PlasmaApplet(_Viz):
    meta = AppletMeta(key="plasma", name="Plasma", description="Audio-reactive plasma field",
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"}})

    def render(self, ctx: Ctx):
        if not HAVE_NP:
            return self._pulse(ctx)
        gx, gy = self._grids()
        a = self._audio
        t, bass, lvl = ctx.t, a.bass, a.level
        speed = 1.0 + 3.0 * bass
        v = (np.sin(gx * 6.0 + t * speed)
             + np.sin(gy * 6.0 + t * 1.3)
             + np.sin((gx + gy) * 5.0 + t * 0.7)
             + np.sin(np.sqrt((gx - 0.5) ** 2 + (gy - 0.5) ** 2) * 18.0 - t * 2.0 * (1.0 + lvl)))
        lo, hi = float(v.min()), float(v.max())
        v = (v - lo) / (hi - lo + 1e-6)
        g = np.clip(v * (0.50 + 0.50 * lvl) * 255.0, 0, 255).astype(np.uint8)
        return Image.fromarray(g, "L")


class TunnelApplet(_Viz):
    meta = AppletMeta(key="tunnel", name="Tunnel", description="Audio-reactive tunnel",
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"}})

    def render(self, ctx: Ctx):
        if not HAVE_NP:
            return self._pulse(ctx)
        gx, gy = self._grids()
        a = self._audio
        t, bass, lvl, treble = ctx.t, a.bass, a.level, a.treble
        dx, dy = gx - 0.5, gy - 0.5
        r = np.sqrt(dx * dx + dy * dy) + 1e-3
        ang = np.arctan2(dy, dx)
        u = (np.sin(ang * (6 + int(8 * treble)) + t * 1.5)
             + np.sin(1.0 / r * (2.5 + 2.0 * bass) - t * 3.0))
        lo, hi = float(u.min()), float(u.max())
        u = (u - lo) / (hi - lo + 1e-6)
        g = np.clip(u * (0.50 + 0.50 * lvl) * 255.0, 0, 255).astype(np.uint8)
        return Image.fromarray(g, "L")


class ScopeApplet(_Viz):
    meta = AppletMeta(key="scope", name="Scope", description="Audio oscilloscope",
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"}})

    def render(self, ctx: Ctx):
        w, h = self.size
        img = F.canvas(w, h)
        d = ImageDraw.Draw(img)
        a = self._audio
        amp = h * 0.42
        wave = a.wave if (a.ok and any(a.wave)) else None
        if wave:
            n = len(wave)
            cy = h / 2
            pts = []
            for i in range(n):
                x = i * (w - 1) / (n - 1)
                y = cy - max(-1.0, min(1.0, wave[i])) * amp
                d.line([(x, cy), (x, y)], fill=70)        # tonal body (mid gray)
                pts.append((x, y))
            d.line(pts, fill=255, width=1)                # bright trace on top
        else:
            lvl = a.level if a.ok else (0.5 - 0.5 * math.cos(ctx.t * 2))
            d.line([(0, h / 2), (w - 1, h / 2)], fill=70)
            y = h / 2 - lvl * amp
            d.line([(0, y), (w - 1, y)], fill=255)
        return img
