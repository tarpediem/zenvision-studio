"""System monitor applet — CPU / RAM / temperature with a CPU sparkline."""
from __future__ import annotations

import collections

from PIL import Image

from .. import frame as F
from .base import Applet, AppletMeta, Ctx


class SysmonApplet(Applet):
    meta = AppletMeta(
        key="sysmon",
        name="System",
        description="CPU / RAM / temperature + sparkline",
        config_schema={"fps": {"type": "int", "default": 4, "label": "FPS"}},
    )

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._hist: collections.deque = collections.deque(maxlen=64)
        try:
            import psutil

            psutil.cpu_percent(None)  # prime the first reading
        except Exception:
            pass

    @staticmethod
    def _temp() -> float | None:
        try:
            import psutil

            temps = psutil.sensors_temperatures()
            for entries in temps.values():
                if entries:
                    return entries[0].current
        except Exception:
            pass
        return None

    def render(self, ctx: Ctx) -> Image.Image:
        import psutil

        w, h = self.size
        img = F.canvas(w, h)
        cpu = psutil.cpu_percent(None)
        self._hist.append(cpu)
        ram = psutil.virtual_memory().percent
        temp = self._temp()

        F.text(img, (2, 12), "CPU %3d%%" % int(cpu), size=14, anchor="lm")
        F.text(img, (2, 32), "RAM %3d%%" % int(ram), size=14, anchor="lm")
        if temp is not None:
            F.text(img, (2, 52), "%2d°C" % int(temp), size=14, anchor="lm")

        spark = F.sparkline(list(self._hist), 150, 58)
        img.paste(spark, (w - 152, 3))
        return img
