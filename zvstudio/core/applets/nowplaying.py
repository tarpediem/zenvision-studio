"""Now-playing applet — MPRIS title/artist marquee + progress bar.

Reads the session bus in a background asyncio thread (dbus-next). Degrades
gracefully to "inactive" if dbus-next is unavailable or no player is running.
"""
from __future__ import annotations

import asyncio
import threading

from PIL import Image

from .. import frame as F
from .base import Applet, AppletMeta, Ctx


class MprisWatcher:
    """Polls MPRIS players on the session bus; caches the active track."""

    def __init__(self, interval: float = 1.0) -> None:
        self.interval = interval
        self.state: dict = {"playing": False, "title": "", "artist": "", "pos": 0.0, "length": 0.0}
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread:
            return
        self._thread = threading.Thread(target=self._run, name="mpris", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self.state)

    def _run(self) -> None:
        try:
            asyncio.run(self._loop())
        except Exception:
            pass

    async def _loop(self) -> None:
        try:
            from dbus_next import BusType
            from dbus_next.aio import MessageBus
        except Exception:
            return
        try:
            bus = await MessageBus(bus_type=BusType.SESSION).connect()
        except Exception:
            return

        intro = await bus.introspect("org.freedesktop.DBus", "/org/freedesktop/DBus")
        dbus_obj = bus.get_proxy_object("org.freedesktop.DBus", "/org/freedesktop/DBus", intro)
        dbus_iface = dbus_obj.get_interface("org.freedesktop.DBus")

        while not self._stop.is_set():
            try:
                await self._poll_once(bus, dbus_iface)
            except Exception:
                with self._lock:
                    self.state["playing"] = False
            await asyncio.sleep(self.interval)

    async def _poll_once(self, bus, dbus_iface) -> None:
        names = await dbus_iface.call_list_names()
        players = [n for n in names if n.startswith("org.mpris.MediaPlayer2.")]
        best = None
        for name in players:
            try:
                intro = await bus.introspect(name, "/org/mpris/MediaPlayer2")
                obj = bus.get_proxy_object(name, "/org/mpris/MediaPlayer2", intro)
                props = obj.get_interface("org.freedesktop.DBus.Properties")
                status = (await props.call_get("org.mpris.MediaPlayer2.Player", "PlaybackStatus")).value
                meta = (await props.call_get("org.mpris.MediaPlayer2.Player", "Metadata")).value
                try:
                    pos = (await props.call_get("org.mpris.MediaPlayer2.Player", "Position")).value
                except Exception:
                    pos = 0
                entry = (status, meta, pos)
                if status == "Playing":
                    best = entry
                    break
                if best is None:
                    best = entry
            except Exception:
                continue

        if best is None:
            with self._lock:
                self.state["playing"] = False
            return

        status, meta, pos = best
        title = meta.get("xesam:title")
        title = title.value if hasattr(title, "value") else (title or "")
        artist = meta.get("xesam:artist")
        artist = artist.value if hasattr(artist, "value") else artist
        if isinstance(artist, list):
            artist = ", ".join(artist)
        length = meta.get("mpris:length")
        length = (length.value if hasattr(length, "value") else length) or 0
        with self._lock:
            self.state = {
                "playing": status == "Playing",
                "title": title or "",
                "artist": artist or "",
                "pos": (pos or 0) / 1e6,
                "length": (length or 0) / 1e6,
            }


class NowPlayingApplet(Applet):
    meta = AppletMeta(
        key="nowplaying",
        name="Now Playing",
        description="MPRIS media: scrolling title/artist + progress",
        config_schema={
            "fps": {"type": "int", "default": 20, "label": "FPS"},
            "preempt": {"type": "bool", "default": True, "label": "Take over when playing"},
            "speed": {"type": "int", "default": 60, "label": "Scroll px/s"},
        },
    )

    _watcher: MprisWatcher | None = None

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        if NowPlayingApplet._watcher is None:
            NowPlayingApplet._watcher = MprisWatcher()
            NowPlayingApplet._watcher.start()

    def wants_focus(self) -> bool:
        if not self.config.get("preempt"):
            return False
        return bool(self._watcher and self._watcher.snapshot().get("playing"))

    def render(self, ctx: Ctx) -> Image.Image:
        w, h = self.size
        img = F.canvas(w, h)
        st = self._watcher.snapshot() if self._watcher else {}
        if not st.get("title"):
            F.text(img, (w // 2, h // 2), "no media", size=16, anchor="mm")
            return img

        speed = float(self.config.get("speed", 60))
        title = F.render_text(st["title"], 22)
        if title.width > w:
            F.scroll(title, int(ctx.t * speed), img, x=0)
        else:
            img.paste(title, (4, 0))

        if st.get("artist"):
            F.text(img, (4, 40), st["artist"][:42], size=13, anchor="lm")

        if st.get("length"):
            prog = st["pos"] / st["length"] if st["length"] else 0.0
            img.paste(F.bar(prog, w - 8, 6, fill=255), (4, h - 8))
        return img
