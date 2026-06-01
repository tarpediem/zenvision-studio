"""Auto-VJ — cycles through a set of visualisers, switching on a timer and,
optionally, whenever the playing track changes."""
from __future__ import annotations

from PIL import Image

from .. import frame as F
from .base import Applet, AppletMeta, Ctx

DEFAULT_SET = ("plasma,tunnel,kaleido,lissajous,moire,metaballs,ripple,fire,"
               "matrix,triangles,cube,starfield,scope")


class CycleApplet(Applet):
    meta = AppletMeta(
        key="cycle",
        name="Auto VJ",
        description="Cycle through visualisers (timer + on track change)",
        config_schema={
            "period": {"type": "int", "default": 20, "label": "Switch seconds"},
            "on_track": {"type": "bool", "default": True, "label": "Switch on track change"},
            "set": {"type": "str", "default": DEFAULT_SET, "label": "Viz keys (csv)"},
        },
    )

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._children: list = []
        self._csize = None
        self._i = 0
        self._last_switch = 0.0
        self._title = None

    def _build(self) -> None:
        from ..registry import get_applet

        keys = [s.strip() for s in str(self.config.get("set", "")).split(",") if s.strip()]
        out = []
        for key in keys:
            if key == "cycle":
                continue
            klass = get_applet(key)
            if klass:
                out.append(klass(size=self.size))
        if not out:
            klass = get_applet("plasma")
            if klass:
                out = [klass(size=self.size)]
        self._children = out
        self._csize = self.size
        self._i = 0

    def _track(self) -> str | None:
        try:
            from .nowplaying import MprisWatcher, NowPlayingApplet
            if NowPlayingApplet._watcher is None:
                NowPlayingApplet._watcher = MprisWatcher()
                NowPlayingApplet._watcher.start()
            st = NowPlayingApplet._watcher.snapshot()
            return st.get("title") if st.get("playing") else None
        except Exception:
            return None

    def render(self, ctx: Ctx) -> Image.Image:
        if not self._children or self._csize != self.size:
            self._build()
            self._last_switch = ctx.t
        if not self._children:
            return F.canvas(*self.size)

        switch = ctx.t - self._last_switch >= max(3, int(self.config.get("period", 20)))
        if self.config.get("on_track", True):
            ti = self._track()
            if ti and ti != self._title:
                if self._title is not None:
                    switch = True
                self._title = ti
        if switch:
            self._i = (self._i + 1) % len(self._children)
            self._last_switch = ctx.t
        return self._children[self._i].render(ctx)


VJ_LAYOUTS = [
    [{"applet": "plasma", "box": [0, 0, 160, 64]}, {"applet": "scope", "box": [160, 0, 96, 64]}],
    [{"applet": "tunnel", "box": [0, 0, 256, 64]}],
    [{"applet": "kaleido", "box": [0, 0, 128, 64]},
     {"applet": "vumeter", "config": {"bands": 16}, "box": [128, 0, 128, 64]}],
    [{"applet": "metaballs", "box": [0, 0, 160, 64]},
     {"applet": "clock", "config": {"seconds": False}, "box": [160, 0, 96, 64]}],
    [{"applet": "moire", "box": [0, 0, 256, 64]}],
    [{"applet": "triangles", "box": [0, 0, 128, 64]}, {"applet": "cube", "box": [128, 0, 128, 64]}],
    [{"applet": "fire", "box": [0, 0, 96, 64]}, {"applet": "matrix", "box": [96, 0, 160, 64]}],
    [{"applet": "lissajous", "box": [0, 0, 160, 64]}, {"applet": "starfield", "box": [160, 0, 96, 64]}],
]


class LayoutVJApplet(Applet):
    meta = AppletMeta(
        key="layoutvj",
        name="Layout VJ",
        description="Cycle multi-effect layouts in tempo (on beats)",
        config_schema={
            "beats": {"type": "int", "default": 16, "label": "Switch every N beats"},
            "period": {"type": "int", "default": 25, "label": "Max seconds / scene"},
            "on_beat": {"type": "bool", "default": True, "label": "Sync to beats"},
        },
    )

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._layouts: list = []
        self._csize = None
        self._i = 0
        self._t0 = 0.0
        self._beats = 0
        self._prev = 0.0

    def _build(self) -> None:
        from ..registry import get_applet
        from .layout import LayoutApplet

        self._layouts = []
        for spec in VJ_LAYOUTS:
            zones = []
            for z in spec:
                klass = get_applet(z["applet"])
                if not klass:
                    continue
                x, y, bw, bh = z["box"]
                zones.append((klass(size=(bw, bh), config=z.get("config") or {}), (x, y, bw, bh)))
            if zones:
                self._layouts.append(LayoutApplet(size=self.size, zones=zones))
        self._csize = self.size
        self._i = 0

    def _beat(self) -> float:
        try:
            from ..audio import AudioLevel
            return AudioLevel.get().beat
        except Exception:
            return 0.0

    def render(self, ctx: Ctx):
        if not self._layouts or self._csize != self.size:
            self._build()
            self._t0 = ctx.t
            self._beats = 0
        if not self._layouts:
            return F.canvas(*self.size)
        switch = False
        if self.config.get("on_beat", True):
            b = self._beat()
            if b > 0.4 and self._prev <= 0.4:
                self._beats += 1
                if self._beats % max(1, int(self.config.get("beats", 16))) == 0:
                    switch = True
            self._prev = b
        if ctx.t - self._t0 >= max(5, int(self.config.get("period", 25))):
            switch = True
        if switch:
            self._i = (self._i + 1) % len(self._layouts)
            self._t0 = ctx.t
        return self._layouts[self._i].render(ctx)
