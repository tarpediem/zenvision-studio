"""FastAPI app: REST control + a WebSocket that mirrors the panel to the browser."""
from __future__ import annotations

import asyncio
import base64
from pathlib import Path

from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from . import config as cfg
from .daemon import Daemon

WEB = Path(__file__).parent / "web"


def create_app(daemon: Daemon) -> FastAPI:
    app = FastAPI(title="zenvision-studio")

    @app.get("/api/status")
    def status() -> dict:
        return daemon.status()

    @app.get("/api/applets")
    def applets() -> list:
        return daemon.list_applets()

    @app.post("/api/brightness")
    def brightness(payload: dict) -> dict:
        daemon.set_brightness(int(payload.get("value", 255)))
        return {"ok": True, "brightness": daemon.comp.brightness}

    @app.post("/api/power")
    def power(payload: dict) -> dict:
        daemon.set_enabled(bool(payload.get("on", True)))
        return {"ok": True, "enabled": daemon.comp.enabled}

    @app.post("/api/pin")
    def pin(payload: dict) -> dict:
        key = payload.get("key")
        daemon.pin(key, payload.get("config"))
        return {"ok": True, "current": key}

    @app.post("/api/resume")
    def resume() -> dict:
        daemon.pin(None)
        return {"ok": True}

    @app.post("/api/playlist")
    def playlist(payload: dict) -> dict:
        daemon.set_playlist(payload.get("playlist", []))
        return {"ok": True}

    @app.post("/api/draw")
    def draw(payload: dict) -> dict:
        import base64
        import io

        from PIL import Image

        frames = []
        for d in payload.get("frames", []):
            b = d.split(",", 1)[-1]
            try:
                frames.append(Image.open(io.BytesIO(base64.b64decode(b))).convert("L"))
            except Exception:
                continue
        if frames:
            daemon.draw(frames)
        return {"ok": True, "n": len(frames)}

    @app.post("/api/upload")
    async def upload(file: UploadFile, play: bool = True) -> dict:
        dest = cfg.uploads_dir() / Path(file.filename).name
        dest.write_bytes(await file.read())
        if play:
            daemon.pin("player", {"path": str(dest)})
        return {"ok": True, "path": str(dest)}

    @app.get("/preview.png")
    def preview() -> Response:
        return Response(content=daemon.preview_png(), media_type="image/png")

    @app.websocket("/ws/preview")
    async def ws_preview(ws: WebSocket) -> None:
        await ws.accept()
        try:
            while True:
                png = daemon.preview_png()
                await ws.send_text("data:image/png;base64," + base64.b64encode(png).decode())
                await asyncio.sleep(1 / 15)
        except WebSocketDisconnect:
            return
        except Exception:
            return

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return (WEB / "index.html").read_text()

    if WEB.exists():
        app.mount("/static", StaticFiles(directory=str(WEB)), name="static")

    return app
