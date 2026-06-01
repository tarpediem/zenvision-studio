import pytest
from PIL import Image

from zvstudio.core.applets.base import Ctx
from zvstudio.core.registry import all_applets

SIZE = (256, 64)


@pytest.mark.parametrize("key", list(all_applets().keys()))
def test_applet_renders_panel_sized_grayscale(key):
    klass = all_applets()[key]
    applet = klass(size=SIZE)
    img = applet.render(Ctx(t=0.0, frame=0, size=SIZE))
    assert isinstance(img, Image.Image)
    assert img.size == SIZE
    assert img.mode == "L"


def test_player_no_media_placeholder():
    from zvstudio.core.applets.player import PlayerApplet

    p = PlayerApplet(size=SIZE, config={"path": "/does/not/exist.gif"})
    img = p.render(Ctx(t=0.0, frame=0, size=SIZE))
    assert img.size == SIZE


def test_frames_applet_advances_by_its_own_fps():
    from zvstudio.core.applets.frames import FramesApplet

    a = Image.new("L", SIZE, 0)
    b = Image.new("L", SIZE, 255)
    fa = FramesApplet(size=SIZE, frames=[a, b], config={"fps": 10})
    # index = int(t * fps) % n  ->  0.00s -> frame 0, 0.10s -> frame 1, 0.20s -> wraps to 0
    assert fa.render(Ctx(t=0.00, frame=0, size=SIZE)).getpixel((0, 0)) == 0
    assert fa.render(Ctx(t=0.10, frame=0, size=SIZE)).getpixel((0, 0)) == 255
    assert fa.render(Ctx(t=0.20, frame=0, size=SIZE)).getpixel((0, 0)) == 0


def test_frames_applet_empty_is_blank():
    from zvstudio.core.applets.frames import FramesApplet

    fa = FramesApplet(size=SIZE, frames=[])
    img = fa.render(Ctx(t=1.23, frame=5, size=SIZE))
    assert img.size == SIZE and img.mode == "L"
