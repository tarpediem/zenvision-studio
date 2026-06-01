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
