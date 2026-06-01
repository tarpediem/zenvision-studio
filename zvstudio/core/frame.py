"""Drawing helpers for 256x64 grayscale frames (Pillow-based)."""
from __future__ import annotations

import functools

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 256, 64

_FONT_CANDIDATES = [
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
]


@functools.lru_cache(maxsize=16)
def font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def canvas(w: int = WIDTH, h: int = HEIGHT) -> Image.Image:
    return Image.new("L", (w, h), 0)


def draw(img: Image.Image) -> ImageDraw.ImageDraw:
    return ImageDraw.Draw(img)


def text_width(s: str, size: int) -> int:
    return int(font(size).getlength(s))


def text(img, xy, s, size=16, fill=255, anchor="lm"):
    ImageDraw.Draw(img).text(xy, s, font=font(size), fill=fill, anchor=anchor)
    return img


def render_text(s: str, size: int, fill: int = 255) -> Image.Image:
    """Render a string to a tightly-sized grayscale strip (for scrolling)."""
    f = font(size)
    w = max(1, int(f.getlength(s)))
    strip = Image.new("L", (w, HEIGHT), 0)
    ImageDraw.Draw(strip).text((0, HEIGHT // 2), s, font=f, fill=fill, anchor="lm")
    return strip


def scroll(strip: Image.Image, offset: int, dest: Image.Image, x: int = 0, gap: int = 24) -> None:
    """Blit a horizontally-scrolling strip into ``dest`` at column ``x``.

    Wraps with a gap so long text marquees seamlessly. ``offset`` advances left.
    """
    w = strip.width + gap
    off = offset % w if w else 0
    visible = dest.width - x
    tile = Image.new("L", (w, strip.height), 0)
    tile.paste(strip, (0, 0))
    cur = -off
    while cur < visible:
        dest.paste(tile, (x + cur, 0))
        cur += w


def sparkline(values, w: int, h: int, fill: int = 255) -> Image.Image:
    img = Image.new("L", (w, h), 0)
    if not values:
        return img
    lo, hi = min(values), max(values)
    rng = (hi - lo) or 1.0
    d = ImageDraw.Draw(img)
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = int(i * (w - 1) / max(1, n - 1))
        y = int((h - 1) * (1 - (v - lo) / rng))
        pts.append((x, y))
    if len(pts) >= 2:
        d.line(pts, fill=fill, width=1)
    else:
        d.point(pts, fill=fill)
    return img


def bar(value: float, w: int, h: int, fill: int = 255, frame: int = 90) -> Image.Image:
    """Horizontal progress bar; ``value`` in 0..1."""
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=frame)
    fw = int((w - 2) * max(0.0, min(1.0, value)))
    if fw > 0:
        d.rectangle([1, 1, fw, h - 2], fill=fill)
    return img
