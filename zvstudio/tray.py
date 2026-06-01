"""Optional system-tray icon for KDE / Plasma (and any SNI-capable desktop).

This is a thin HTTP client over a running ``zvstudio daemon`` — it talks to the
same REST API the CLI uses and does **not** own the panel itself. Menu state
(power, beat-flash, current applet) is pulled live from ``/api/status`` each time
the menu opens.

KDE Plasma only exposes a StatusNotifierItem tray (no legacy XEmbed), so we force
pystray's AppIndicator backend, which speaks SNI over D-Bus. That backend needs
``python-gobject`` plus ``libayatana-appindicator`` (or ``libappindicator-gtk3``)
installed as system packages. Override with ``PYSTRAY_BACKEND`` if needed.
"""
from __future__ import annotations

import os
import webbrowser
from pathlib import Path

from PIL import Image

from .cli import DEFAULT_URL, _req

WEB = Path(__file__).parent / "web"

# Brightness presets shown in the submenu: (label, 0-255 value).
_BRIGHTNESS = [("25%", 64), ("50%", 128), ("75%", 191), ("100%", 255)]


def _icon_image() -> Image.Image:
    """A square RGBA icon for the tray (the app logo, or a fallback dot)."""
    try:
        img = Image.open(WEB / "logo.png").convert("RGBA")
        if img.width != img.height:
            side = max(img.size)
            sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
            sq.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
            img = sq
        return img
    except Exception:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        from PIL import ImageDraw
        ImageDraw.Draw(img).ellipse([8, 8, 56, 56], fill=(255, 255, 255, 255))
        return img


def run_tray(url: str = DEFAULT_URL) -> int:
    os.environ.setdefault("PYSTRAY_BACKEND", "appindicator")
    try:
        import pystray
        from pystray import Menu
        from pystray import MenuItem as Item
    except ImportError as e:
        print(
            "tray needs the AppIndicator backend. Install:\n"
            "  pip install 'zenvision-studio[tray]'\n"
            "  # plus the system libs (Arch/CachyOS):\n"
            "  sudo pacman -S --needed python-gobject libayatana-appindicator\n"
            "The venv must be able to import 'gi' — create it with "
            "`python -m venv --system-site-packages .venv` or install into a\n"
            "Python that already has python-gobject.\n"
            f"(import error: {e})",
            file=__import__("sys").stderr,
        )
        return 1

    def status() -> dict:
        try:
            return _req(url, "/api/status")
        except Exception:
            return {}

    def post(path: str, body: dict | None = None):
        def handler(icon, item) -> None:
            try:
                _req(url, path, "POST", body or {})
            except Exception:
                pass
        return handler

    def open_ui(icon, item) -> None:
        webbrowser.open(url)

    def toggle_power(icon, item) -> None:
        try:
            _req(url, "/api/power", "POST", {"on": not status().get("enabled", True)})
        except Exception:
            pass

    def toggle_flash(icon, item) -> None:
        try:
            _req(url, "/api/flash", "POST", {"on": not status().get("flash", False)})
        except Exception:
            pass

    def applet_items():
        try:
            applets = _req(url, "/api/applets")
        except Exception:
            applets = []

        def pin(key: str):
            return lambda icon, item: post("/api/pin", {"key": key})(icon, item)

        return [
            Item(
                a.get("name", a["key"]),
                pin(a["key"]),
                checked=lambda item, k=a["key"]: status().get("current") == k,
                radio=True,
            )
            for a in applets
        ]

    def brightness_items():
        return [Item(label, post("/api/brightness", {"value": val})) for label, val in _BRIGHTNESS]

    menu = Menu(
        Item("Open web UI", open_ui, default=True),
        Menu.SEPARATOR,
        Item("Power", toggle_power, checked=lambda item: bool(status().get("enabled", False))),
        Item("Beat-flash", toggle_flash, checked=lambda item: bool(status().get("flash", False))),
        Menu.SEPARATOR,
        Item("Applets", Menu(applet_items)),
        Item("Brightness", Menu(brightness_items)),
        Item("Resume rotation", post("/api/resume")),
        Menu.SEPARATOR,
        Item("Quit tray", lambda icon, item: icon.stop()),
    )

    icon = pystray.Icon("zvstudio", _icon_image(), "zenvision-studio", menu)
    icon.run()
    return 0
