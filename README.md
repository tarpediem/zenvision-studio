# zenvision-studio

Drive the **ASUS ZenVision** lid OLED (the 256×64 monochrome screen in the lid of
the Zenbook 14X OLED Space Edition, UX5401ZAS) with **live applets**, play and
**import custom animations**, all from Linux — and from any desktop or your phone.

It's a small **headless daemon** that owns the panel and runs a compositor, plus a
local **web UI** to control it and a **plugin system** so you can add your own
widgets in a few lines.

> Protocol & low-level driver: see the sibling project
> [zenvision-linux](https://github.com/tarpediem/zenvision-linux).

![demo](docs/demo.gif)

## Features

- **Applets**: clock, system monitor (CPU/RAM/temp + sparkline), now-playing
  (MPRIS marquee + progress), and a media player (image / GIF / video → panel).
- **Compositor**: rotates a playlist of scenes; an applet can *preempt* (e.g.
  now-playing takes over when music starts). Flicker-free streaming.
- **Web UI**: live mirror of the panel, brightness, on/off, applet switching,
  drag-and-drop file upload. Reachable from your phone over the LAN / Tailscale.
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
