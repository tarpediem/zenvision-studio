"""Command-line interface.

Two modes:
  * direct (no daemon): ``play`` / ``anim`` push to the panel and exit;
  * client: ``daemon`` runs the server, the rest talk to it over HTTP.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request

DEFAULT_URL = "http://127.0.0.1:8787"


# --- HTTP client helpers -------------------------------------------------
def _req(url: str, path: str, method: str = "GET", body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url + path, data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode() or "{}")


# --- direct (no daemon) --------------------------------------------------
def cmd_play(args) -> int:
    from PIL import Image

    from .core.device import get_panel

    panel = get_panel(args.backend)
    try:
        img = Image.new("L", panel.size, 255) if args.white else Image.open(args.path)
        panel.show_image(img, args.bright)
        if args.hold:
            time.sleep(args.hold)
    finally:
        panel.close()
    return 0


def cmd_anim(args) -> int:
    import glob

    from PIL import Image

    from .core.device import get_panel

    files = sorted(glob.glob(args.dir.rstrip("/") + "/*.png") +
                   glob.glob(args.dir.rstrip("/") + "/*.jpg"))
    if not files:
        print("no frames in", args.dir, file=sys.stderr)
        return 1
    frames = [Image.open(f).convert("L") for f in files]
    panel = get_panel(args.backend)
    try:
        panel.begin_stream(args.bright)
        delay = 1.0 / args.fps
        print("streaming %d frames @ %.0f fps (Ctrl-C to stop)" % (len(frames), args.fps))
        while True:
            for fr in frames:
                panel.push_frame(fr)
                time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        panel.close()
    return 0


def cmd_daemon(args) -> int:
    import uvicorn

    from .api import create_app
    from .daemon import Daemon

    d = Daemon(backend=args.backend)
    d.start()
    app = create_app(d)

    @app.on_event("shutdown")
    def _shutdown() -> None:
        d.stop()

    print("zenvision-studio daemon on http://%s:%d (backend=%s)" % (args.host, args.port, d.panel.name))
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


# --- client commands -----------------------------------------------------
def cmd_status(args) -> int:
    print(json.dumps(_req(args.url, "/api/status"), indent=2))
    return 0


def cmd_brightness(args) -> int:
    print(_req(args.url, "/api/brightness", "POST", {"value": args.value}))
    return 0


def cmd_power(args) -> int:
    print(_req(args.url, "/api/power", "POST", {"on": args.state == "on"}))
    return 0


def cmd_show(args) -> int:
    print(_req(args.url, "/api/pin", "POST", {"key": args.applet}))
    return 0


def cmd_tray(args) -> int:
    from .tray import run_tray

    return run_tray(args.url)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="zvstudio", description="Drive the ZenVision lid OLED.")
    p.add_argument("--url", default=DEFAULT_URL, help="daemon URL for client commands")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("play", help="show a single image (no daemon)")
    sp.add_argument("path", nargs="?")
    sp.add_argument("--white", action="store_true")
    sp.add_argument("--bright", type=lambda x: int(x, 0), default=0xFF)
    sp.add_argument("--hold", type=float, default=0.0)
    sp.add_argument("--backend", default=None)
    sp.set_defaults(func=cmd_play)

    sa = sub.add_parser("anim", help="stream a folder of frames (no daemon)")
    sa.add_argument("dir")
    sa.add_argument("--fps", type=float, default=20.0)
    sa.add_argument("--bright", type=lambda x: int(x, 0), default=0xFF)
    sa.add_argument("--backend", default=None)
    sa.set_defaults(func=cmd_anim)

    sd = sub.add_parser("daemon", help="run the daemon + web UI")
    sd.add_argument("--host", default="127.0.0.1")
    sd.add_argument("--port", type=int, default=8787)
    sd.add_argument("--backend", default=None)
    sd.set_defaults(func=cmd_daemon)

    sub.add_parser("status", help="daemon status").set_defaults(func=cmd_status)

    sb = sub.add_parser("brightness", help="set brightness 0-255")
    sb.add_argument("value", type=lambda x: int(x, 0))
    sb.set_defaults(func=cmd_brightness)

    spw = sub.add_parser("power", help="turn the panel on/off")
    spw.add_argument("state", choices=["on", "off"])
    spw.set_defaults(func=cmd_power)

    ss = sub.add_parser("show", help="pin a single applet")
    ss.add_argument("applet")
    ss.set_defaults(func=cmd_show)

    sub.add_parser("tray", help="system-tray icon (KDE/SNI; needs the 'tray' extra)").set_defaults(func=cmd_tray)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
