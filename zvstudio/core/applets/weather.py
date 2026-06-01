"""Weather applet — current temperature via Open-Meteo (no API key).

Fetches in a background thread so render() never blocks on the network. Degrades
to a placeholder until the first successful fetch.
"""
from __future__ import annotations

import json
import threading
import urllib.request

from PIL import Image

from .. import frame as F
from .base import Applet, AppletMeta, Ctx

# Open-Meteo WMO weather codes -> short label.
_CODES = {
    0: "Clear", 1: "Clear", 2: "Cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog", 51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
    61: "Rain", 63: "Rain", 65: "Rain", 71: "Snow", 73: "Snow", 75: "Snow",
    80: "Showers", 81: "Showers", 82: "Showers", 95: "Storm", 96: "Storm", 99: "Storm",
}


class WeatherApplet(Applet):
    meta = AppletMeta(
        key="weather",
        name="Weather",
        description="Current temperature (Open-Meteo)",
        config_schema={
            "lat": {"type": "str", "default": "48.85", "label": "Latitude"},
            "lon": {"type": "str", "default": "2.35", "label": "Longitude"},
            "label": {"type": "str", "default": "Paris", "label": "Place label"},
            "fps": {"type": "int", "default": 1, "label": "FPS"},
        },
    )

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._data: dict | None = None
        self._stop = threading.Event()
        threading.Thread(target=self._loop, name="weather", daemon=True).start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                lat = float(self.config.get("lat", 48.85))
                lon = float(self.config.get("lon", 2.35))
                url = ("https://api.open-meteo.com/v1/forecast"
                       f"?latitude={lat}&longitude={lon}&current_weather=true")
                with urllib.request.urlopen(url, timeout=8) as r:
                    cw = json.loads(r.read().decode()).get("current_weather", {})
                self._data = {"temp": cw.get("temperature"), "code": cw.get("weathercode")}
            except Exception:
                pass
            self._stop.wait(600)  # refresh every 10 min

    def on_stop(self) -> None:
        self._stop.set()

    def render(self, ctx: Ctx) -> Image.Image:
        w, h = self.size
        img = F.canvas(w, h)
        label = str(self.config.get("label") or "")
        if not self._data or self._data.get("temp") is None:
            F.text(img, (w // 2, h // 2), "weather…", size=16, anchor="mm")
            return img
        temp = round(float(self._data["temp"]))
        cond = _CODES.get(int(self._data.get("code") or 0), "")
        if label:
            F.text(img, (8, 14), label, size=15, anchor="lm")
        F.text(img, (8, 42), "%d°C" % temp, size=30, anchor="lm")
        if cond:
            F.text(img, (w - 8, 42), cond, size=15, anchor="rm")
        return img
