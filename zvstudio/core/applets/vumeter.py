"""VU-meter applet — graphic-equalizer spectrum bars (uses the shared analyser)."""
from __future__ import annotations

from PIL import ImageDraw

from .. import frame as F
from ..audio import HAVE_NP, AudioLevel
from .base import Applet, AppletMeta, Ctx


class VuMeterApplet(Applet):
    meta = AppletMeta(
        key="vumeter",
        name="VU Meter",
        description="Equalizer-style audio spectrum",
        config_schema={
            "fps": {"type": "int", "default": 30, "label": "FPS"},
            "bands": {"type": "int", "default": 24, "label": "Bands"},
            "peaks": {"type": "bool", "default": True, "label": "Peak caps"},
            "mirror": {"type": "bool", "default": False, "label": "Mirror from center"},
        },
    )

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._audio = AudioLevel.get(int(self.config.get("bands", 24)))

    def render(self, ctx: Ctx):
        w, h = self.size
        img = F.canvas(w, h)
        d = ImageDraw.Draw(img)
        if not self._audio.ok:
            d.line([(0, h - 1), (w - 1, h - 1)], fill=90)
            F.text(img, (w // 2, h // 2 - 6), "no audio", size=14, anchor="mm")
            return img

        if HAVE_NP:
            bands, peaks = self._audio.bands, self._audio.peaks
        else:
            bands, peaks = list(self._audio.level_hist), None

        n = len(bands)
        gap = 1 if w // n > 2 else 0
        bw = w / n
        mirror = self.config.get("mirror", False)
        show_peaks = self.config.get("peaks", True) and peaks is not None
        for i, v in enumerate(bands):
            x0 = int(i * bw)
            x1 = int((i + 1) * bw) - 1 - gap
            if x1 < x0:
                x1 = x0
            bh = int(v * (h - 2))
            if mirror:
                cy = h // 2
                d.rectangle([x0, cy - bh // 2, x1, cy + bh // 2], fill=255)
            else:
                d.rectangle([x0, h - 1 - bh, x1, h - 1], fill=255)
                if show_peaks:
                    py = h - 1 - int(peaks[i] * (h - 2))
                    d.rectangle([x0, py, x1, py], fill=160)
        return img
