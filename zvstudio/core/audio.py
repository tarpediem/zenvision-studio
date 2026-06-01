"""Shared audio analyser — captures the default output monitor with `parec`
(PipeWire/PulseAudio) and exposes loudness/spectrum features for the VU-meter
and the audio-reactive visualisers. Reads levels only, never audio content.

Degrades gracefully: no parec/monitor -> ``ok`` stays False; no numpy -> only the
RMS level / level history are available (no spectrum bands / waveform).
"""
from __future__ import annotations

import array
import collections
import math
import subprocess
import threading

try:
    import numpy as np
    HAVE_NP = True
except Exception:
    HAVE_NP = False

RATE = 22050
N = 1024  # FFT / capture window (samples)
WAVE_POINTS = 128


class AudioLevel:
    """Background analyser (singleton)."""

    _instance: AudioLevel | None = None

    def __init__(self, nbands: int = 24) -> None:
        self.nbands = nbands
        self.bands = [0.0] * nbands
        self.peaks = [0.0] * nbands
        self.level = 0.0
        self.bass = 0.0
        self.mid = 0.0
        self.treble = 0.0
        self.beat = 0.0
        self.wave = [0.0] * WAVE_POINTS
        self.level_hist: collections.deque = collections.deque([0.0] * 64, maxlen=64)
        self.ok = False
        self._agc = 1e-3
        self._energy = 1e-3
        self._stop = threading.Event()
        if HAVE_NP:
            self._win = np.hanning(N).astype(np.float32)
            raw = np.logspace(math.log10(2), math.log10(N // 2), nbands + 1)
            edges = np.round(raw).astype(int)
            for i in range(1, len(edges)):
                if edges[i] <= edges[i - 1]:
                    edges[i] = edges[i - 1] + 1
            self._edges = np.clip(edges, 1, N // 2)
        threading.Thread(target=self._run, name="audio", daemon=True).start()

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
                self._analyse(buf)
            else:
                self._rms(buf)

    def _rms(self, buf: bytes) -> None:
        s = array.array("h")
        s.frombytes(buf)
        rms = math.sqrt(sum(v * v for v in s) / len(s)) / 32768.0
        self.level = min(1.0, rms * 4.0)
        self.bass = self.mid = self.treble = self.level
        self.level_hist.append(self.level)

    def _analyse(self, buf: bytes) -> None:
        raw = np.frombuffer(buf, dtype=np.int16).astype(np.float32) / 32768.0
        x = raw[:N] * self._win
        mag = np.abs(np.fft.rfft(x)) * (2.0 / N)
        e = self._edges
        vals = np.array([mag[e[i]:e[i + 1]].max() if e[i + 1] > e[i] else mag[e[i]]
                         for i in range(self.nbands)], dtype=np.float32)
        self._agc = max(self._agc * 0.999, float(vals.max()), 1e-4)
        lvl = np.clip(vals / self._agc, 0.0, 1.0) ** 0.6
        for i in range(self.nbands):
            self.bands[i] = max(float(lvl[i]), self.bands[i] * 0.80)
            self.peaks[i] = max(self.bands[i], self.peaks[i] - 0.03)

        n = self.nbands
        b = np.asarray(self.bands)
        self.bass = float(b[:max(1, n // 4)].mean())
        self.mid = float(b[n // 4:3 * n // 4].mean())
        self.treble = float(b[3 * n // 4:].mean())
        self.level = float(b.mean())
        self.level_hist.append(self.level)

        # simple beat detector on bass energy
        self._energy = 0.9 * self._energy + 0.1 * self.bass
        self.beat = 1.0 if self.bass > self._energy * 1.5 else max(0.0, self.beat - 0.12)

        # downsampled waveform for the scope
        step = max(1, raw.size // WAVE_POINTS)
        self.wave = raw[::step][:WAVE_POINTS].tolist()
