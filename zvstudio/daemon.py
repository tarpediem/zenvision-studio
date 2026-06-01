"""Daemon: owns the panel and the compositor, builds scenes from config, and
exposes everything to the API / CLI."""
from __future__ import annotations

import io

from PIL import Image

from . import config as cfg
from .core import registry
from .core.compositor import Compositor, Scene
from .core.device import get_panel


class Daemon:
    def __init__(self, backend: str | None = None) -> None:
        self.panel = get_panel(backend)
        self.cfg = cfg.load()
        self.comp = Compositor(self.panel, fps=self.cfg.get("fps", 20))
        self._applets: dict[str, object] = {}
        self.comp.set_brightness(self.cfg.get("brightness", 255))
        self.apply_config()

    # --- build from config ----------------------------------------------
    def _make(self, key: str, config: dict | None = None):
        klass = registry.get_applet(key)
        if klass is None:
            return None
        return klass(size=self.panel.size, config=config or {})

    def apply_config(self) -> None:
        scenes = []
        for item in self.cfg.get("playlist", []):
            ap = self._make(item.get("applet"), item.get("config"))
            if ap:
                scenes.append(Scene(ap, float(item.get("duration", 10))))
        self.comp.set_playlist(scenes)
        preempt = [self._make(k) for k in self.cfg.get("preempt", [])]
        self.comp.set_preempt([p for p in preempt if p])

    # --- lifecycle -------------------------------------------------------
    def start(self) -> None:
        self.comp.start()

    def stop(self) -> None:
        self.comp.stop()
        try:
            self.panel.clear()
        except Exception:
            pass
        self.panel.close()

    # --- control ---------------------------------------------------------
    def status(self) -> dict:
        return {
            "backend": self.panel.name,
            "size": list(self.panel.size),
            "enabled": self.comp.enabled,
            "brightness": self.comp.brightness,
            "flash": self.comp.beat_flash,
            "current": self.comp.current_key(),
            "playlist": self.cfg.get("playlist", []),
            "preempt": self.cfg.get("preempt", []),
        }

    def list_applets(self) -> list[dict]:
        out = []
        for klass in registry.all_applets().values():
            m = klass.meta
            out.append({"key": m.key, "name": m.name, "description": m.description,
                        "config_schema": m.config_schema})
        return out

    def set_brightness(self, value: int) -> None:
        self.comp.set_brightness(value)
        self.cfg["brightness"] = self.comp.brightness
        cfg.save(self.cfg)

    def set_enabled(self, on: bool) -> None:
        self.comp.set_enabled(on)

    def set_flash(self, on: bool) -> None:
        self.comp.beat_flash = bool(on)

    def pin(self, key: str | None, config: dict | None = None) -> None:
        if key is None:
            self.comp.pin(None)
            self.apply_config()
            return
        ap = self._make(key, config)
        if ap:
            self.comp.pin(ap)

    def set_playlist(self, playlist: list[dict]) -> None:
        self.cfg["playlist"] = playlist
        cfg.save(self.cfg)
        self.apply_config()

    def draw(self, frames, fps=None) -> None:
        """Pin an in-memory frame sequence (from the web editor)."""
        from .core.applets.frames import FramesApplet

        config = {"fps": float(fps)} if fps else None
        ap = FramesApplet(size=self.panel.size, frames=frames, config=config)
        self.comp.pin(ap)

    def set_layout(self, zones_spec: list[dict]) -> None:
        """Pin a multi-zone layout. zones_spec: [{applet, config, box:[x,y,w,h]}]."""
        from .core.applets.layout import LayoutApplet

        zones = []
        for z in zones_spec:
            ap = self._make(z.get("applet"), z.get("config"))
            box = z.get("box") or [0, 0, *self.panel.size]
            if ap and len(box) == 4:
                x, y, bw, bh = (int(v) for v in box)
                ap.size = (bw, bh)
                zones.append((ap, (x, y, bw, bh)))
        if zones:
            self.comp.pin(LayoutApplet(size=self.panel.size, zones=zones))

    def preview_png(self) -> bytes:
        img = self.comp.preview()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def preview_image(self) -> Image.Image:
        return self.comp.preview()
