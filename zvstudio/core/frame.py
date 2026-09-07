"""Drawing helpers for 256x64 grayscale frames (Pillow-based)."""
from __future__ import annotations

import functools

from PIL import Image, ImageDraw, ImageFont, ImageOps

WIDTH, HEIGHT = 256, 64

_FONT_CANDIDATES = [
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
]


_CJK_CANDIDATES = [
    ("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc", 0),
    ("/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc", 0),
    ("/usr/share/fonts/adobe-source-han-sans/SourceHanSansCN-Regular.otf", 0),
    ("/usr/share/fonts/noto/NotoSansJP-Regular.ttf", 0),
]


@functools.lru_cache(maxsize=16)
def font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


@functools.lru_cache(maxsize=16)
def cjk_font(size: int) -> ImageFont.FreeTypeFont:
    """A font able to render CJK / katakana (for the Matrix effect)."""
    for path, idx in _CJK_CANDIDATES:
        try:
            return ImageFont.truetype(path, size, index=idx)
        except OSError:
            continue
    return font(size)


# --- Emoji -----------------------------------------------------------------
# The panel is monochrome 4bpp, so we render each emoji with the color emoji
# font (the only one shipped) and flatten it to grayscale. NotoColorEmoji is a
# CBDT bitmap font with a *single* strike (109 px): Pillow only loads it at that
# size, so we rasterize at 109 and scale the glyph down to the text height.
_EMOJI_CANDIDATES = [
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/NotoColorEmoji.ttf",
]
_EMOJI_STRIKE = 109


@functools.lru_cache(maxsize=1)
def _emoji_font() -> ImageFont.FreeTypeFont | None:
    for path in _EMOJI_CANDIDATES:
        try:
            return ImageFont.truetype(path, _EMOJI_STRIKE)
        except OSError:
            continue
    return None


def _is_emoji(cp: int) -> bool:
    return (
        0x1F300 <= cp <= 0x1FAFF   # pictographs, emoticons, transport, symbols A/B
        or 0x1F000 <= cp <= 0x1F0FF  # mahjong / dominoes / playing cards
        or 0x1F1E6 <= cp <= 0x1F1FF  # regional indicators (flags)
        or 0x2600 <= cp <= 0x27BF    # misc symbols + dingbats
        or 0x2B00 <= cp <= 0x2BFF    # stars / arrows block
        or cp in (0x203C, 0x2049, 0x2122, 0x2139, 0x2328, 0x24C2, 0x25AA, 0x25AB,
                  0x25B6, 0x25C0, 0x25FB, 0x25FC, 0x25FD, 0x25FE)
    )


def _is_emoji_mod(cp: int) -> bool:
    # skin-tone modifiers, variation selectors, ZWJ, keycap combiner
    return (
        0x1F3FB <= cp <= 0x1F3FF
        or 0xFE00 <= cp <= 0xFE0F
        or cp == 0x200D
        or cp == 0x20E3
    )


def _segments(s: str):
    """Split ``s`` into ('text', run) and ('emoji', cluster) segments, L→R.

    Emoji clusters absorb trailing modifiers (skin tone, VS16) and ZWJ-joined
    bases so compound emoji stay together; plain digits/#/* become an emoji
    cluster only when followed by the keycap combiner.
    """
    out: list[tuple[str, str]] = []
    buf: list[str] = []
    n = len(s)
    i = 0

    def flush() -> None:
        if buf:
            out.append(("text", "".join(buf)))
            buf.clear()

    while i < n:
        cp = ord(s[i])
        keycap = s[i] in "#*0123456789" and i + 1 < n and ord(s[i + 1]) in (0xFE0F, 0x20E3)
        if _is_emoji(cp) or keycap:
            flush()
            j = i + 1
            while j < n:
                c2 = ord(s[j])
                if _is_emoji_mod(c2):
                    j += 1
                elif ord(s[j - 1]) == 0x200D and _is_emoji(c2):
                    j += 1  # ZWJ-joined base
                else:
                    break
            out.append(("emoji", s[i:j]))
            i = j
        else:
            buf.append(s[i])
            i += 1
    flush()
    return out


@functools.lru_cache(maxsize=256)
def _emoji_glyph(cluster: str, height: int) -> Image.Image | None:
    """Rasterize one emoji cluster to a grayscale strip of the given height."""
    f = _emoji_font()
    if f is None:
        return None
    pad = 12
    cv = Image.new("RGBA", (_EMOJI_STRIKE + 2 * pad, _EMOJI_STRIKE + 2 * pad), (0, 0, 0, 0))
    try:
        ImageDraw.Draw(cv).text((pad, pad), cluster, font=f, embedded_color=True)
    except Exception:
        return None
    bbox = cv.getbbox()
    if not bbox:
        return None
    g = cv.crop(bbox)
    alpha = g.split()[3]
    # luminance where the glyph is opaque; stretch so dark emojis stay visible
    lum = Image.composite(g.convert("L"), Image.new("L", g.size, 0), alpha)
    lum = ImageOps.autocontrast(lum, cutoff=1)
    w, h = lum.size
    nw = max(1, round(w * height / h))
    return lum.resize((nw, height), Image.LANCZOS)


def _emoji_gap(size: int) -> int:
    return max(1, size // 10)


def canvas(w: int = WIDTH, h: int = HEIGHT) -> Image.Image:
    return Image.new("L", (w, h), 0)


def draw(img: Image.Image) -> ImageDraw.ImageDraw:
    return ImageDraw.Draw(img)


def text_width(s: str, size: int) -> int:
    total = 0
    for kind, run in _segments(s):
        if kind == "text":
            total += int(font(size).getlength(run))
        else:
            g = _emoji_glyph(run, size)
            total += (g.width + _emoji_gap(size)) if g is not None else int(font(size).getlength(run))
    return total


def _blit_runs(strip: Image.Image, x0: int, cy: int, s: str, size: int, fill: int) -> int:
    """Draw text + emoji runs onto ``strip`` starting at (x0, cy); return end x."""
    d = ImageDraw.Draw(strip)
    x = x0
    for kind, run in _segments(s):
        if kind == "text":
            d.text((x, cy), run, font=font(size), fill=fill, anchor="lm")
            x += int(font(size).getlength(run))
        else:
            g = _emoji_glyph(run, size)
            if g is None:
                d.text((x, cy), run, font=font(size), fill=fill, anchor="lm")
                x += int(font(size).getlength(run))
                continue
            if fill != 255:
                g = g.point(lambda p: p * fill // 255)
            strip.paste(g, (x, cy - g.height // 2))
            x += g.width + _emoji_gap(size)
    return x


def text(img, xy, s, size=16, fill=255, anchor="lm"):
    # Fast path: no emoji -> exact original behaviour (keeps all anchors intact).
    if all(seg[0] == "text" for seg in _segments(s)):
        ImageDraw.Draw(img).text(xy, s, font=font(size), fill=fill, anchor=anchor)
        return img
    # Emoji present: honour horizontal anchor (l/m/r), vertically center on y.
    x, y = xy
    ha = anchor[0] if anchor else "l"
    w = text_width(s, size)
    if ha == "m":
        x -= w // 2
    elif ha == "r":
        x -= w
    _blit_runs(img, int(x), int(y), s, size, fill)
    return img


def render_text(s: str, size: int, fill: int = 255) -> Image.Image:
    """Render a string to a tightly-sized grayscale strip (for scrolling)."""
    w = max(1, text_width(s, size))
    strip = Image.new("L", (w, HEIGHT), 0)
    _blit_runs(strip, 0, HEIGHT // 2, s, size, fill)
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
