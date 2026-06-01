"""The compositor owns the panel and runs the render loop in a background thread.

It rotates through a playlist of scenes, lets a "focus-wanting" applet preempt
the rotation (e.g. now-playing when media starts), and pushes frames using the
panel's flicker-free streaming mode.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from PIL import Image

from .applets.base import Applet, Ctx
from .device.base import Panel


@dataclass
class Scene:
    applet: Applet
    duration: float = 10.0  # seconds before rotating to the next scene


class Compositor:
    def __init__(self, panel: Panel, fps: float = 20.0) -> None:
        self.panel = panel
        self.fps = fps
        self.brightness = 255
        self.enabled = True

        self._scenes: list[Scene] = []
        self._preempt: list[Applet] = []
        self._pinned: Applet | None = None  # manual override (no rotation)

        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._cur: Applet | None = None
        self._cur_start = 0.0
        self._cur_frame = 0
        self._preview = Image.new("L", panel.size, 0)

    def preview(self) -> Image.Image:
        """Last frame rendered (mirrors the panel; works on any backend)."""
        with self._lock:
            return self._preview.copy()

    def current_key(self) -> str | None:
        ap = self._cur
        return ap.meta.key if ap is not None else None

    # --- configuration ---------------------------------------------------
    def set_playlist(self, scenes: list[Scene]) -> None:
        with self._lock:
            self._scenes = list(scenes)
            self._pinned = None
            self._reset_current(None)

    def set_preempt(self, applets: list[Applet]) -> None:
        with self._lock:
            self._preempt = list(applets)

    def pin(self, applet: Applet | None) -> None:
        with self._lock:
            self._pinned = applet
            self._reset_current(None)

    def set_brightness(self, value: int) -> None:
        self.brightness = max(0, min(255, int(value)))
        try:
            self.panel.set_brightness(self.brightness)
        except Exception:
            pass

    def set_enabled(self, on: bool) -> None:
        self.enabled = bool(on)

    # --- lifecycle -------------------------------------------------------
    def start(self) -> None:
        if self._thread:
            return
        self.panel.begin_stream(self.brightness)
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="compositor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._cur:
            try:
                self._cur.on_stop()
            except Exception:
                pass

    # --- internals -------------------------------------------------------
    def _reset_current(self, applet: Applet | None) -> None:
        if self._cur is applet:
            return
        if self._cur:
            try:
                self._cur.on_stop()
            except Exception:
                pass
        self._cur = applet
        self._cur_start = time.monotonic()
        self._cur_frame = 0
        if applet:
            try:
                applet.on_start()
            except Exception:
                pass

    def _pick(self, now: float, scene_idx: list[int]) -> Applet | None:
        # 1) an explicit manual pin wins — a user choice overrides auto-preempt
        if self._pinned is not None:
            return self._pinned
        # 2) a preempting applet grabs focus during normal rotation (e.g. now-playing)
        for ap in self._preempt:
            try:
                if ap.wants_focus():
                    return ap
            except Exception:
                continue
        # 3) playlist rotation
        if not self._scenes:
            return None
        i = scene_idx[0] % len(self._scenes)
        scene = self._scenes[i]
        if self._cur is scene.applet and (now - self._cur_start) >= scene.duration:
            scene_idx[0] = (i + 1) % len(self._scenes)
            return self._scenes[scene_idx[0]].applet
        if self._cur not in [s.applet for s in self._scenes] and self._pinned is None:
            return scene.applet
        return scene.applet

    def _loop(self) -> None:
        scene_idx = [0]
        period = 1.0 / max(1.0, self.fps)
        black = Image.new("L", self.panel.size, 0)
        while not self._stop.is_set():
            t0 = time.monotonic()
            if not self.enabled:
                try:
                    self.panel.push_frame(black)
                except Exception:
                    pass
                time.sleep(0.1)
                continue
            with self._lock:
                nxt = self._pick(t0, scene_idx)
                self._reset_current(nxt)
                cur = self._cur
            if cur is not None:
                ctx = Ctx(t=t0 - self._cur_start, frame=self._cur_frame, size=self.panel.size)
                try:
                    img = cur.render(ctx)
                    self.panel.push_frame(img)
                    with self._lock:
                        self._preview = img if img.mode == "L" else img.convert("L")
                except Exception:
                    pass
                self._cur_frame += 1
            dt = time.monotonic() - t0
            if dt < period:
                time.sleep(period - dt)
