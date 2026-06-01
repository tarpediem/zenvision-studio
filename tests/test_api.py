import os

os.environ["ZVSTUDIO_BACKEND"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from zvstudio.api import create_app  # noqa: E402
from zvstudio.daemon import Daemon  # noqa: E402


def make_client():
    d = Daemon(backend="mock")
    return TestClient(create_app(d)), d


def test_status_and_applets():
    client, d = make_client()
    try:
        s = client.get("/api/status").json()
        assert s["backend"] == "mock"
        assert s["size"] == [256, 64]
        keys = {a["key"] for a in client.get("/api/applets").json()}
        assert {"clock", "sysmon", "player", "nowplaying"} <= keys
    finally:
        d.stop()


def test_brightness_and_power_and_preview():
    client, d = make_client()
    try:
        assert client.post("/api/brightness", json={"value": 128}).json()["brightness"] == 128
        assert client.post("/api/power", json={"on": False}).json()["enabled"] is False
        r = client.get("/preview.png")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"
    finally:
        d.stop()


def test_pin_applet():
    client, d = make_client()
    try:
        assert client.post("/api/pin", json={"key": "clock"}).json()["ok"] is True
    finally:
        d.stop()


def test_draw_accepts_frames_and_fps():
    # 1x1 black PNG as a data URL (the editor sends 256x64, but any decodable PNG works)
    px = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    client, d = make_client()
    try:
        r = client.post("/api/draw", json={"frames": [px, px], "fps": 24}).json()
        assert r["ok"] is True and r["n"] == 2
    finally:
        d.stop()
