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
