"""VU-meter applet — an audio-reactive bar meter driven by the system output level.

Captures the default sink monitor with `parec` (PipeWire/PulseAudio) in a
background thread and computes a smoothed RMS level. No external Python deps; it
only reads loudness levels (numbers), not audio content. Degrades to a flat
baseline if `parec` or a monitor source isn't available.
"""
from __future__ import annotations

import array
import collections
import math
import subprocess
import threading

from PIL import ImageDraw

from .. import frame as F
from .base import Applet, AppletMeta, Ctx

BARS = 64


class AudioLevel:
    """Shared background reader of the default output's loudness level."""

    _instance: AudioLevel | None = None

    def __init__(self) -> None:
        self.hist: collections.deque = collections.deque([0.0] * BARS, maxlen=BARS)
        self.ok = False
        self._stop = threading.Event()
        threading.Thread(target=self._run, name="audiolevel", daemon=True).start()

    @classmethod
    def get(cls) -> AudioLevel:
        if cls._instance is None:
            cls._instance = AudioLevel()
        return cls._instance

    def _monitor(self) -> str:
        try:
            sink = subprocess.check_output(["pactl", "get-default-sink"], text=True, timeout=3).strip()
            if sink:
                return sink + ".monitor"
        except Exception:
            pass
        return "@DEFAULT_MONITOR@"

    def _run(self) -> None:
        rate = 22050
        chunk = int(rate * 0.03)  # 30 ms windows
        try:
            proc = subprocess.Popen(
                ["parec", "--format=s16le", f"--rate={rate}", "--channels=1",
                 "--device", self._monitor(), "--latency-msec=40"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
        except Exception:
            return
        while not self._stop.is_set():
            raw = proc.stdout.read(chunk * 2)
            if not raw:
                break
            samples = array.array("h")
            samples.frombytes(raw[: len(raw) // 2 * 2])
            if not samples:
                continue
            rms = math.sqrt(sum(s * s for s in samples) / len(samples)) / 32768.0
            self.ok = True
            self.hist.append(min(1.0, rms * 4.0))


class VuMeterApplet(Applet):
    meta = AppletMeta(
        key="vumeter",
        name="VU Meter",
        description="Audio-reactive bar meter (system output)",
        config_schema={
            "fps": {"type": "int", "default": 30, "label": "FPS"},
            "mirror": {"type": "bool", "default": True, "label": "Mirror from center"},
        },
    )

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._audio = AudioLevel.get()

    def render(self, ctx: Ctx):
        w, h = self.size
        img = F.canvas(w, h)
        d = ImageDraw.Draw(img)
        vals = list(self._audio.hist)
        if not self._audio.ok:
            d.line([(0, h - 1), (w - 1, h - 1)], fill=90)
            F.text(img, (w // 2, h // 2 - 6), "no audio", size=14, anchor="mm")
            return img
        bw = w / len(vals)
        mirror = self.config.get("mirror", True)
        for i, v in enumerate(vals):
            x0 = int(i * bw)
            x1 = int((i + 1) * bw) - 1
            if x1 <= x0:
                x1 = x0
            bh = int(v * (h - 2))
            if mirror:
                cy = h // 2
                d.rectangle([x0, cy - bh // 2, x1, cy + bh // 2], fill=255)
            else:
                d.rectangle([x0, h - 1 - bh, x1, h - 1], fill=255)
        return img
