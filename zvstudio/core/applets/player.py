"""Player applet — display an image, animated GIF, or video on the panel.

This is the "import a custom animation" path: point it at a file and it is
decoded to a sequence of panel-sized grayscale frames and looped.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageSequence

from .. import frame as F
from .base import Applet, AppletMeta, Ctx

STILL = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
ANIM = {".gif", ".apng"}
VIDEO = {".mp4", ".webm", ".mkv", ".mov", ".avi", ".gifv"}


class PlayerApplet(Applet):
    meta = AppletMeta(
        key="player",
        name="Player",
        description="Play an image / GIF / video",
        config_schema={
            "path": {"type": "path", "default": "", "label": "File"},
            "fit": {"type": "str", "default": "contain", "label": "Fit (contain|cover|stretch)"},
            "fps": {"type": "int", "default": 20, "label": "FPS"},
        },
    )

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._frames: list[Image.Image] = []
        self._loaded: str | None = None

    def _fit(self, img: Image.Image) -> Image.Image:
        w, h = self.size
        img = img.convert("L")
        mode = self.config.get("fit", "contain")
        if mode == "stretch":
            return img.resize((w, h), Image.LANCZOS)
        out = F.canvas(w, h)
        src = img.copy()
        if mode == "cover":
            scale = max(w / src.width, h / src.height)
            src = src.resize((max(1, int(src.width * scale)), max(1, int(src.height * scale))), Image.LANCZOS)
            out.paste(src, ((w - src.width) // 2, (h - src.height) // 2))
        else:  # contain
            src.thumbnail((w, h), Image.LANCZOS)
            out.paste(src, ((w - src.width) // 2, (h - src.height) // 2))
        return out

    def _load(self, path: str) -> None:
        self._loaded = path
        self._frames = []
        p = Path(path)
        if not path or not p.exists():
            return
        suffix = p.suffix.lower()
        if suffix in ANIM:
            im = Image.open(p)
            self._frames = [self._fit(fr) for fr in ImageSequence.Iterator(im)]
        elif suffix in STILL:
            self._frames = [self._fit(Image.open(p))]
        elif suffix in VIDEO:
            try:
                import imageio.v3 as iio

                self._frames = [self._fit(Image.fromarray(fr)) for fr in iio.imiter(p)]
            except Exception:
                self._frames = []

    def render(self, ctx: Ctx) -> Image.Image:
        path = self.config.get("path") or ""
        if path != self._loaded:
            self._load(path)
        if not self._frames:
            img = F.canvas(*self.size)
            F.text(img, (self.size[0] // 2, self.size[1] // 2), "no media", size=16, anchor="mm")
            return img
        return self._frames[ctx.frame % len(self._frames)]
