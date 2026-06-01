# zenvision-studio

> 🟢 **The first open-source Linux support for the ASUS ZenVision lid OLED.**
> The protocol was reverse-engineered from scratch (Ghidra on MyASUS) and lives in
> the companion driver **[zenvision-linux](https://github.com/tarpediem/zenvision-linux)**.

Drive the **ASUS ZenVision** lid OLED (the 256×64 monochrome screen in the lid of
the Zenbook 14X OLED Space Edition, UX5401ZAS) with **live applets**, play and
**import custom animations**, all from Linux — and from any desktop or your phone.

It's a small **headless daemon** that owns the panel and runs a compositor, plus a
local **web UI** to control it and a **plugin system** so you can add your own
widgets in a few lines.

> Protocol & low-level driver: see the sibling project
> [zenvision-linux](https://github.com/tarpediem/zenvision-linux).

![The ZenVision lid OLED running zenvision-studio](docs/lid.gif)

*Audio-reactive visualisers on the actual lid OLED of an ASUS Zenbook (UX5401ZAS).
Rendered effects up close: [docs/demo.gif](docs/demo.gif).*

## Features

- **Applets**: clock, system monitor (CPU/RAM/temp + sparkline), now-playing
  (MPRIS marquee + progress), **text** marquee, **weather** (Open-Meteo), and a
  media player (image / GIF / video).
- **Audio-reactive visualisers**: a VU-meter spectrum plus demoscene effects —
  plasma, tunnel, kaleidoscope, Lissajous, moiré, metaballs, ripple, fire,
  katakana **Matrix** rain, starfield, wireframe cube, triangles — with MilkDrop-style
  trails, a global **beat-flash**, an **Auto-VJ** that cycles them, and a **Layout-VJ**
  that switches multi-effect compositions in tempo.
- **Web UI**: a polished dashboard with a live panel mirror, an **in-browser
  animation editor** (stylus-friendly, draw frames → send to the panel), a
  **drag-and-drop zone layout editor** (split the panel into regions), per-applet
  settings, brightness/power and drag-and-drop upload. Works from your phone over
  the LAN / Tailscale.
- **Compositor**: rotates a playlist of scenes; an applet can *preempt* (e.g.
  now-playing pops in when the track changes). Flicker-free streaming.
- **Cross-desktop**: nothing depends on KDE/GNOME — the core is a daemon, the UI is
  a browser page. Optional tray launcher.
- **Hardware-free dev**: a `mock` backend renders to a preview/PNG so the whole
  thing (and CI) runs with no device attached.
- **Pluggable**: third-party applets register via the `zvstudio.applets`
  entry point. See [`examples/`](examples/).

## Install

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e .            # add ".[video]" for video, ".[tray]" for the tray
```

Non-root USB access:

```bash
sudo cp udev/99-zenvision.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

## Run

```bash
# Start the daemon + web UI (real panel auto-detected, else mock)
zvstudio daemon                 # then open http://127.0.0.1:8787

# No hardware? Force the mock backend and watch the live preview in the browser:
ZVSTUDIO_BACKEND=mock zvstudio daemon

# Control from the CLI
zvstudio status
zvstudio brightness 0x80
zvstudio show clock
zvstudio power off

# Or skip the daemon entirely for a one-shot:
zvstudio play picture.png
zvstudio anim frames/ --fps 20
```

Reach it from your phone: `zvstudio daemon --host 0.0.0.0` (or via Tailscale).

### Run at login (systemd user service)

```bash
cp systemd/zvstudio.service ~/.config/systemd/user/
systemctl --user enable --now zvstudio
```

## Writing an applet

An applet returns one 256×64 grayscale frame per tick:

```python
from zvstudio.core.applets.base import Applet, AppletMeta, Ctx
from zvstudio.core import frame as F

class HelloApplet(Applet):
    meta = AppletMeta(key="hello", name="Hello", description="says hi")

    def render(self, ctx: Ctx):
        img = F.canvas(*self.size)
        F.text(img, (self.size[0] // 2, 32), "hello :)", size=22, anchor="mm")
        return img
```

Register it via an entry point (`[project.entry-points."zvstudio.applets"]`) and it
shows up in the UI automatically. Full example in [`examples/`](examples/).

## Roadmap (v2)

- In-browser frame/timeline **animation editor** (draw on a 256×64 canvas).
- Richer **trigger system** (notifications, lid events, idle/screensaver).
- More applets (weather, RSS/ticker, calendar, VU-meter), other panels behind the
  `Panel` abstraction.

## License

[MIT](LICENSE). Unofficial; not affiliated with or endorsed by ASUS.
