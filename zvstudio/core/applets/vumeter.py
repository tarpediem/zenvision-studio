"""VU-meter applet — graphic-equalizer spectrum bars.

Captures the default output monitor with `parec` (PipeWire/PulseAudio) in a
background thread and computes a log-spaced frequency spectrum (numpy FFT) with
fast-attack / slow-decay smoothing and falling peak caps — the classic EQ look.
Only loudness/spectrum levels are read, never audio content. Degrades to a flat
baseline if `parec`/a monitor source isn't available, and to a simple level
meter if numpy isn't installed.
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

try:
    import numpy as np
    HAVE_NP = True
except Exception:
    HAVE_NP = False

RATE = 22050
N = 1024  # FFT window size (samples)


class AudioLevel:
    """Shared background audio analyser (spectrum bands + fallback level)."""

    _instance: AudioLevel | None = None

    def __init__(self, nbands: int = 24) -> None:
        self.nbands = nbands
        self.bands = [0.0] * nbands
        self.peaks = [0.0] * nbands
        self.level_hist: collections.deque = collections.deque([0.0] * 64, maxlen=64)
        self.ok = False
        self._agc = 1e-3
        self._stop = threading.Event()
        if HAVE_NP:
            self._win = np.hanning(N).astype(np.float32)
            raw = np.logspace(math.log10(2), math.log10(N // 2), nbands + 1)
            edges = np.round(raw).astype(int)
            for i in range(1, len(edges)):
                if edges[i] <= edges[i - 1]:
                    edges[i] = edges[i - 1] + 1
            self._edges = np.clip(edges, 1, N // 2)
        threading.Thread(target=self._run, name="audiolevel", daemon=True).start()

    @classmethod
    def get(cls, nbands: int = 24) -> AudioLevel:
        if cls._instance is None:
            cls._instance = AudioLevel(nbands)
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
        try:
            proc = subprocess.Popen(
                ["parec", "--format=s16le", f"--rate={RATE}", "--channels=1",
                 "--device", self._monitor(), "--latency-msec=40"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
        except Exception:
            return
        need = N * 2
        while not self._stop.is_set():
            buf = b""
            while len(buf) < need:
                chunk = proc.stdout.read(need - len(buf))
                if not chunk:
                    return
                buf += chunk
            self.ok = True
            if HAVE_NP:
                self._spectrum(buf)
            else:
                self._level(buf)

    def _level(self, buf: bytes) -> None:
        samples = array.array("h")
        samples.frombytes(buf)
        rms = math.sqrt(sum(s * s for s in samples) / len(samples)) / 32768.0
        self.level_hist.append(min(1.0, rms * 4.0))

    def _spectrum(self, buf: bytes) -> None:
        x = np.frombuffer(buf, dtype=np.int16).astype(np.float32) / 32768.0
        x = x[:N] * self._win
        mag = np.abs(np.fft.rfft(x)) * (2.0 / N)
        e = self._edges
        vals = np.array([mag[e[i]:e[i + 1]].max() if e[i + 1] > e[i] else mag[e[i]]
                         for i in range(self.nbands)], dtype=np.float32)
        # auto gain (slow decay) so quiet and loud both fill nicely; gamma for punch
        self._agc = max(self._agc * 0.999, float(vals.max()), 1e-4)
        lvl = np.clip(vals / self._agc, 0.0, 1.0) ** 0.6
        for i in range(self.nbands):
            self.bands[i] = max(float(lvl[i]), self.bands[i] * 0.80)   # fast attack, slow decay
            self.peaks[i] = max(self.bands[i], self.peaks[i] - 0.03)   # falling cap


class VuMeterApplet(Applet):
    meta = AppletMeta(
        key="vumeter",
        name="VU Meter",
        description="Equalizer-style audio spectrum",
        config_schema={
            "fps": {"type": "int", "default": 30, "label": "FPS"},
            "bands": {"type": "int", "default": 24, "label": "Bands"},
            "peaks": {"type": "bool", "default": True, "label": "Peak caps"},
            "mirror": {"type": "bool", "default": False, "label": "Mirror from center"},
        },
    )

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        self._audio = AudioLevel.get(int(self.config.get("bands", 24)))

    def render(self, ctx: Ctx):
        w, h = self.size
        img = F.canvas(w, h)
        d = ImageDraw.Draw(img)
        if not self._audio.ok:
            d.line([(0, h - 1), (w - 1, h - 1)], fill=90)
            F.text(img, (w // 2, h // 2 - 6), "no audio", size=14, anchor="mm")
            return img

        if HAVE_NP:
            bands, peaks = self._audio.bands, self._audio.peaks
        else:  # fallback: scrolling level bars
            bands, peaks = list(self._audio.level_hist), None

        n = len(bands)
        gap = 1 if w // n > 2 else 0
        bw = w / n
        mirror = self.config.get("mirror", False)
        show_peaks = self.config.get("peaks", True) and peaks is not None
        for i, v in enumerate(bands):
            x0 = int(i * bw)
            x1 = int((i + 1) * bw) - 1 - gap
            if x1 < x0:
                x1 = x0
            bh = int(v * (h - 2))
            if mirror:
                cy = h // 2
                d.rectangle([x0, cy - bh // 2, x1, cy + bh // 2], fill=255)
            else:
                d.rectangle([x0, h - 1 - bh, x1, h - 1], fill=255)
                if show_peaks:
                    py = h - 1 - int(peaks[i] * (h - 2))
                    d.rectangle([x0, py, x1, py], fill=160)
        return img
