# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`zenvision-studio` drives the 256×64 monochrome lid OLED ("ZenVision") of an ASUS Zenbook
14X OLED Space Edition from **Linux** — a headless daemon plus a no-build vanilla-JS web UI.
It renders live **applets** (clock, sysmon, now-playing, weather…), audio-reactive
**visualisers**, multi-zone **layouts**, and browser-authored timeline **animations**, then
pushes grayscale frames over USB. The USB protocol was reverse-engineered in the sibling
project [`zenvision-linux`](https://github.com/tarpediem/zenvision-linux).

## Commands

```bash
# Setup (mock backend = full stack with no hardware)
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,video]"

# Run the daemon + web UI (real panel auto-detected, falls back to mock)
zvstudio daemon                          # http://127.0.0.1:8787
ZVSTUDIO_BACKEND=mock zvstudio daemon    # force mock (no device)

# Lint + tests (must pass; CI runs these on py3.10–3.12 with ZVSTUDIO_BACKEND=mock)
ruff check .
pytest -q
pytest tests/test_api.py::test_pin_applet   # single test
```

`ruff` config lives in `pyproject.toml` (line-length 110; rules `E,F,I,UP,B`). There is no
separate formatter step — `ruff` handles lint/format. Tests force the **mock** backend at
import time, so they never touch hardware.

## Architecture

Data flows one way: an **applet** renders a PIL `"L"` (8-bit grayscale) image at the panel's
native size → the **compositor** decides which applet is active each tick → the **panel
backend** encodes and pushes the frame. Everything above the backend deals only in PIL
images; only the backend knows the wire format.

```
cli.py            argparse entry point (zvstudio). Two modes:
                  - direct (no daemon): `play`/`anim` open a panel and exit
                  - client: `daemon` runs the server; status/pin/brightness/power are HTTP calls to it
daemon.py         Daemon: owns the panel + Compositor, builds Scenes from config, exposes control verbs
api.py            FastAPI app (create_app(daemon)): REST + /ws/preview WebSocket mirror + static web/
config.py         JSON config under XDG (~/.config/zvstudio/config.json); playlist + preempt + uploads/
core/compositor.py   Render loop in a daemon thread: playlist rotation, preempt, beat-flash, streaming
core/registry.py     Applet discovery: the BUILTIN list + `zvstudio.applets` entry-point plugins
core/frame.py        Pillow drawing helpers (canvas/text/scroll/sparkline/bar, font caches incl. CJK)
core/audio.py        Singleton AudioLevel analyser: parec monitor → RMS/FFT bands/beat/waveform
core/device/         Panel backends (see below)
core/applets/        All applets (see below)
web/                 index.html + app.js + style.css — vanilla JS, no build step
```

### Compositor (`core/compositor.py`)

The single source of truth for what's on screen. Runs `_loop()` in a background daemon
thread at `fps`. Each tick `_pick()` chooses the active applet by priority:

1. **pinned** — an explicit manual override (CLI `show`, web pin, a `draw`/`layout` from the
   editor). Beats everything; no rotation.
2. **preempt** — any applet whose `wants_focus()` returns True grabs focus during rotation
   (e.g. `nowplaying` when a track starts).
3. **playlist** — rotates through `Scene(applet, duration)` entries.

`_reset_current()` calls `on_start()`/`on_stop()` hooks on transitions. The last rendered
frame is cached in `_preview` so **any** backend (including a real USB panel you can't read
back) can mirror to the browser. `beat_flash` brightens the whole frame on each audio beat.
Mutating state (`set_playlist`, `pin`, `set_preempt`) is lock-guarded.

### Applets (`core/applets/`)

An applet subclasses `Applet` (`base.py`), sets a class-level `AppletMeta` (key, name,
`config_schema`), and implements `render(ctx) -> Image` where `Ctx` carries `t` (seconds
since active), `frame`, and `size`. Keep `render()` cheap — it runs every frame. Config
options must be declared in `meta.config_schema` (`{field: {type, default, label, …}}`) so
the UI/CLI can expose them generically; `self.config` merges declared defaults with overrides.

Built-ins are grouped: `clock`, `sysmon`, `nowplaying` (MPRIS via dbus-next, preempting),
`weather`, `text`, `player` (image/gif/video), `logo`; visualisers in `viz.py`
(plasma/tunnel/scope/kaleido/lissajous) and `fx.py` (moiré/metaballs/ripple/fire/matrix);
geometry in `geo.py` (triangles/cube/starfield); `vumeter`. Two meta-applets compose others:
`CycleApplet` (Auto-VJ, cycles visualisers) and `LayoutVJApplet` (switches multi-zone
compositions in tempo) in `cycle.py`; `LayoutApplet` (`layout.py`) renders several applets
into sub-boxes; `FramesApplet` (`frames.py`) plays an in-memory frame sequence from the
web timeline editor.

**To add a built-in applet:** create the class, then add it to `BUILTIN` in
`core/registry.py`. Third-party applets register via a `[project.entry-points."zvstudio.applets"]`
entry (see `examples/sample_applet.py`) and are auto-discovered — no core edit needed.

### Panel backends (`core/device/`)

`Panel` (`base.py`) is the abstract transport: `open/close`, `show_image` (latched still),
`begin_stream`+`push_frame` (flicker-free animation), optional `set_brightness`. `get_panel()`
(`__init__.py`) resolves a backend from the arg or `ZVSTUDIO_BACKEND` (`zenvision`/`mock`/`auto`);
`auto` tries the real USB panel and silently falls back to `mock`. `mock.py` renders to memory
for dev/CI; `zenvision.py` speaks the real protocol (USB `0b05:8835`, 4bpp packed into an
8704-byte framebuffer, command channel on interrupt EP `0x03`, pixels on bulk EP `0x07`).
**To support another panel:** implement `Panel` and wire it into `get_panel`.

### Audio (`core/audio.py`)

`AudioLevel.get()` is a process-wide singleton that captures the default output **monitor**
via `parec` (PipeWire/PulseAudio) and exposes `level`/`bands`/`peaks`/`bass`/`mid`/`treble`/
`beat`/`wave`. It reads loudness only, never content. Degrades gracefully: no `parec`/monitor
→ `ok` stays False; no numpy → RMS level only (no spectrum/waveform). Visualisers and the
VU-meter pull from this singleton.

## Conventions & gotchas

- **Frames are always PIL `"L"`** at the panel's native size. The compositor converts non-`L`
  output, but applets should produce grayscale directly.
- **Mock-first.** Anything you build must run under `ZVSTUDIO_BACKEND=mock` — that's what CI
  and the tests use. Don't assume a device is attached.
- **Optional deps degrade, never crash.** `audio` (numpy) and `video` (imageio) are extras;
  `parec`/`pactl` are system deps. Guard their use and fall back, matching `core/audio.py`.
- The daemon thread swallows per-frame render exceptions to stay alive — a broken applet shows
  a blank/frozen frame rather than killing the loop. Check logs/preview, not a crash.
- Config persists to `~/.config/zvstudio/config.json`; uploads go to `~/.config/zvstudio/uploads/`.
- Non-root USB access needs `udev/70-zenvision.rules` installed (the `70-` prefix matters —
  it must sort before `73-seat-late.rules` or the `uaccess` ACL is never applied). Run at login via the user
  systemd unit in `systemd/` (runs as your user so MPRIS/now-playing works).
