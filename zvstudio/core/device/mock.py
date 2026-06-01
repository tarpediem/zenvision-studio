"""Hardware-free panel backend.

Keeps the most recent frame in memory (for the web UI live preview) and can
optionally write frames to PNG. Lets the whole stack — daemon, applets, web UI,
tests — run on any machine without the real device.
"""
from __future__ import annotations

import os
import threading

from PIL import Image

from .base import Panel


class MockPanel(Panel):
    name = "mock"
    width = 256
    height = 64

    def __init__(self, save_dir: str | None = None) -> None:
        self._lock = threading.Lock()
        self._last = Image.new("L", self.size, 0)
        self.brightness = 255
        self.frames_pushed = 0
        self.save_dir = save_dir or os.environ.get("ZVSTUDIO_MOCK_DIR")
        if self.save_dir:
            os.makedirs(self.save_dir, exist_ok=True)

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def _put(self, img: Image.Image) -> None:
        img = self.fit(img)
        with self._lock:
            self._last = img.copy()
            self.frames_pushed += 1
            n = self.frames_pushed
        if self.save_dir:
            img.save(os.path.join(self.save_dir, "frame_%06d.png" % n))

    def show_image(self, img: Image.Image, brightness: int = 255) -> None:
        self.brightness = brightness
        self._put(img)

    def begin_stream(self, brightness: int = 255) -> None:
        self.brightness = brightness

    def push_frame(self, img: Image.Image) -> None:
        self._put(img)

    def set_brightness(self, brightness: int) -> None:
        self.brightness = brightness

    def snapshot(self) -> Image.Image:
        """Latest frame (used by the web UI preview)."""
        with self._lock:
            return self._last.copy()
