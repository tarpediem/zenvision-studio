"""Audio-reactive generative visualisers (MilkDrop-ish) for the 256x64 panel.

Plasma / Tunnel / Scope. They animate on time and react to the live audio
features (level / bass / treble / waveform). A feedback buffer adds MilkDrop-style
trails: each frame keeps a decayed (optionally zoom-warped) echo of the previous
output. numpy-accelerated, with a graceful pulse/line fallback without it.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

from .. import frame as F
from ..audio import HAVE_NP, AudioLevel
from .base import Applet, AppletMeta, Ctx

if HAVE_NP:
    import numpy as np

TRAILS = {"type": "int", "default": 80, "label": "Trails %"}
WARP = {"type": "int", "default": 0, "label": "Warp % (zoom)"}


class _Viz(Applet):
    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._audio = AudioLevel.get()
        self._gsize = None
        self._buf = None

    # --- generative grid -------------------------------------------------
    def _grids(self):
        w, h = self.size
        if self._gsize != (w, h):
            xs = np.linspace(0, 1, w, dtype=np.float32)
            ys = np.linspace(0, 1, h, dtype=np.float32)
            self._gx, self._gy = np.meshgrid(xs, ys)
            self._gsize = (w, h)
        return self._gx, self._gy

    # --- MilkDrop feedback (trails) -------------------------------------
    def _zoom(self, buf, factor):
        h, w = buf.shape
        im = Image.fromarray(buf, "F")
        nw, nh = max(w + 1, int(w * factor)), max(h + 1, int(h * factor))
        big = im.resize((nw, nh), Image.BILINEAR)
        left, top = (nw - w) // 2, (nh - h) // 2
        return np.asarray(big.crop((left, top, left + w, top + h)), dtype=np.float32)

    def _feedback(self, frame):
        if not HAVE_NP:
            return Image.fromarray(np.asarray(frame).astype("uint8"), "L")
        f = frame.astype(np.float32)
        h, w = f.shape
        decay = max(0, min(98, int(self.config.get("trails", 80)))) / 100.0
        warp = max(0, int(self.config.get("warp", 0))) / 100.0
        if decay <= 0:
            return Image.fromarray(np.clip(f, 0, 255).astype(np.uint8), "L")
        if self._buf is None or self._buf.shape != (h, w):
            self._buf = np.zeros((h, w), np.float32)
        buf = self._zoom(self._buf, 1.0 + warp) if warp > 0 else self._buf
        out = np.maximum(buf * decay, f)
        self._buf = out
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "L")

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
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"},
                                     "trails": TRAILS, "warp": WARP})

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
        g = v * (0.50 + 0.50 * lvl) * 255.0
        return self._feedback(g)


class TunnelApplet(_Viz):
    meta = AppletMeta(key="tunnel", name="Tunnel", description="Audio-reactive tunnel",
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"},
                                     "trails": {**TRAILS, "default": 82},
                                     "warp": {**WARP, "default": 4}})

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
        g = u * (0.50 + 0.50 * lvl) * 255.0
        return self._feedback(g)


class ScopeApplet(_Viz):
    meta = AppletMeta(key="scope", name="Scope", description="Audio oscilloscope",
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"},
                                     "trails": {**TRAILS, "default": 70}})

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
                d.line([(x, cy), (x, y)], fill=70)
                pts.append((x, y))
            d.line(pts, fill=255, width=1)
        else:
            lvl = a.level if a.ok else (0.5 - 0.5 * math.cos(ctx.t * 2))
            d.line([(0, h / 2), (w - 1, h / 2)], fill=70)
            y = h / 2 - lvl * amp
            d.line([(0, y), (w - 1, y)], fill=255)
        if HAVE_NP:
            return self._feedback(np.asarray(img, dtype=np.float32))
        return img


class KaleidoApplet(_Viz):
    meta = AppletMeta(key="kaleido", name="Kaleidoscope", description="Mirrored audio mandala",
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"},
                                     "segments": {"type": "int", "default": 6, "label": "Segments"},
                                     "trails": {**TRAILS, "default": 60}})

    def render(self, ctx: Ctx):
        if not HAVE_NP:
            return self._pulse(ctx)
        gx, gy = self._grids()
        a = self._audio
        t, bass, lvl, treble = ctx.t, a.bass, a.level, a.treble
        dx, dy = gx - 0.5, gy - 0.5
        r = np.sqrt(dx * dx + dy * dy)
        ang = np.arctan2(dy, dx)
        seg = max(2, int(self.config.get("segments", 6)))
        step = 2 * math.pi / seg
        af = np.abs(np.mod(ang + t * 0.3, step) - step / 2)   # fold into a mirrored wedge
        v = (np.sin(af * seg + r * (8 + 10 * bass) - t * 1.5)
             + np.sin(r * (18 + 12 * treble) - t * 2.0))
        lo, hi = float(v.min()), float(v.max())
        v = (v - lo) / (hi - lo + 1e-6)
        g = v * (0.50 + 0.50 * lvl) * 255.0
        return self._feedback(g)


class LissajousApplet(_Viz):
    meta = AppletMeta(key="lissajous", name="Lissajous", description="X/Y oscilloscope figure",
                      config_schema={"fps": {"type": "int", "default": 30, "label": "FPS"},
                                     "a": {"type": "int", "default": 3, "label": "X freq"},
                                     "b": {"type": "int", "default": 2, "label": "Y freq"},
                                     "trails": {**TRAILS, "default": 72}})

    def render(self, ctx: Ctx):
        w, h = self.size
        img = F.canvas(w, h)
        d = ImageDraw.Draw(img)
        a = self._audio
        t = ctx.t
        lvl = a.level if a.ok else 0.5 - 0.5 * math.cos(t * 1.5)
        fa = max(1, int(self.config.get("a", 3)))
        fb = max(1, int(self.config.get("b", 2)))
        ax, ay = w * 0.46 * (0.55 + 0.5 * lvl), h * 0.46 * (0.55 + 0.5 * lvl)
        cx, cy = w / 2, h / 2
        ph = t * 0.7
        n = 256
        pts = [(cx + ax * math.sin(fa * (2 * math.pi * i / n) + ph),
                cy + ay * math.sin(fb * (2 * math.pi * i / n))) for i in range(n + 1)]
        d.line(pts, fill=255, width=1)
        if HAVE_NP:
            return self._feedback(np.asarray(img, dtype=np.float32))
        return img
