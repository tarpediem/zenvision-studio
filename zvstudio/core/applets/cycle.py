"""Auto-VJ — cycles through a set of visualisers, switching on a timer and,
optionally, whenever the playing track changes."""
from __future__ import annotations

from PIL import Image

from .. import frame as F
from .base import Applet, AppletMeta, Ctx

DEFAULT_SET = "plasma,tunnel,kaleido,lissajous,triangles,cube,starfield,scope"


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
