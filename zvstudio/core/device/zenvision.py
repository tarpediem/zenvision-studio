"""ASUS ZenVision backend (USB 0b05:8835, 256x64 4bpp).

Wraps the reverse-engineered protocol from the sibling project `zenvision-linux`
(MIT). Transport: vendor interface 0, command channel on interrupt EP 0x03, pixels
on bulk EP 0x07. See that project's PROTOCOL.md for the full description.
"""
from __future__ import annotations

from PIL import Image

from .base import Panel

VID, PID = 0x0B05, 0x8835
IFACE = 0
EP_CMD = 0x03   # interrupt OUT — 512-byte commands
EP_BULK = 0x07  # bulk OUT — 8704-byte framebuffer
FRAME_BYTES = 8704


def encode(img: Image.Image, width: int = 256, height: int = 64) -> bytes:
    """PIL image -> 8704-byte ZenVision framebuffer (4bpp + 17x512 packet framing)."""
    img = img.convert("L")
    if img.size != (width, height):
        img = img.resize((width, height), Image.LANCZOS)
    px = img.load()

    n = bytearray(width * height)
    i = 0
    for y in range(height):
        for x in range(width):
            n[i] = px[x, y] >> 4
            i += 1

    data = bytearray(8192)
    for k in range(4096):
        s = 4 * k
        data[2 * k] = n[s + 2] | (n[s + 3] << 4)
        data[2 * k + 1] = n[s] | (n[s + 1] << 4)

    out = bytearray(FRAME_BYTES)
    pos = d = 0
    while pos < FRAME_BYTES and d <= 0x1FFF:
        bp = pos & 0x1FF
        if bp == 0:
            out[pos] = (pos >> 9) & 0xFF
        elif bp == 1:
            if (pos >> 9) == 16:
                out[pos] = 1
        elif bp >= 4:
            out[pos] = data[d]
            d += 1
        pos += 1
    return bytes(out)


def _cmd(*head: int) -> bytes:
    b = bytearray(512)
    b[: len(head)] = bytes(head)
    return bytes(b)


class ZenVisionPanel(Panel):
    name = "zenvision"
    width = 256
    height = 64

    def __init__(self) -> None:
        self.dev = None
        self._bright = 0xFF

    def open(self) -> None:
        import usb.core
        import usb.util

        self.dev = usb.core.find(idVendor=VID, idProduct=PID)
        if self.dev is None:
            raise RuntimeError("ZenVision (0b05:8835) not found")
        try:
            if self.dev.is_kernel_driver_active(IFACE):
                self.dev.detach_kernel_driver(IFACE)
        except Exception:
            pass
        usb.util.claim_interface(self.dev, IFACE)

    def _c(self, data: bytes) -> None:
        self.dev.write(EP_CMD, data, timeout=3000)

    def _b(self, data: bytes) -> None:
        self.dev.write(EP_BULK, data, timeout=3000)

    def show_image(self, img: Image.Image, brightness: int = 255) -> None:
        fb = encode(img, self.width, self.height)
        self._c(_cmd(0x30, 0x06, 0x05, 0, 0, 0, 0, 0x01))     # begin static
        self._b(fb)                                           # pixels
        self._c(_cmd(0x31, 0x02, brightness & 0xFF, 0x03))    # apply + brightness

    def begin_stream(self, brightness: int = 255) -> None:
        self._bright = brightness & 0xFF
        self._c(_cmd(0x30, 0x06, 0x05, 0, 0, 0, 0, 0x02))     # streaming mode
        self._c(_cmd(0x31, 0x02, self._bright, 0x03))         # brightness

    def push_frame(self, img: Image.Image) -> None:
        self._b(encode(img, self.width, self.height))

    def set_brightness(self, brightness: int) -> None:
        self._bright = brightness & 0xFF
        self._c(_cmd(0x31, 0x02, self._bright, 0x03))

    def close(self) -> None:
        if self.dev is not None:
            import usb.util

            try:
                usb.util.release_interface(self.dev, IFACE)
                usb.util.dispose_resources(self.dev)
            except Exception:
                pass
            self.dev = None
