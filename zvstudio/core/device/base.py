"""Abstract panel interface.

A panel is a small monochrome display you push 8-bit grayscale PIL images to.
Backends own the wire encoding; the rest of zenvision-studio only deals in PIL
images at the panel's native resolution.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image


class Panel(ABC):
    name: str = "panel"
    width: int = 256
    height: int = 64
    grayscale: bool = True

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    # --- lifecycle -------------------------------------------------------
    @abstractmethod
    def open(self) -> None:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    # --- output ----------------------------------------------------------
    @abstractmethod
    def show_image(self, img: Image.Image, brightness: int = 255) -> None:
        """Display a single still image (latched until the next call)."""

    @abstractmethod
    def begin_stream(self, brightness: int = 255) -> None:
        """Enter streaming mode for flicker-free animation."""

    @abstractmethod
    def push_frame(self, img: Image.Image) -> None:
        """Push one animation frame (only valid after :meth:`begin_stream`)."""

    def set_brightness(self, brightness: int) -> None:  # optional
        pass

    # --- helpers ---------------------------------------------------------
    def clear(self) -> None:
        self.show_image(Image.new("L", self.size, 0), 0)

    def fit(self, img: Image.Image) -> Image.Image:
        img = img.convert("L")
        if img.size != self.size:
            img = img.resize(self.size, Image.LANCZOS)
        return img

    def __enter__(self) -> Panel:
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()
