from PIL import Image

from zvstudio.core.device.zenvision import FRAME_BYTES, encode


def test_encode_size():
    img = Image.new("L", (256, 64), 200)
    fb = encode(img)
    assert len(fb) == FRAME_BYTES == 8704


def test_packet_headers():
    fb = encode(Image.new("L", (256, 64), 255))
    headers = [fb[i * 512] for i in range(17)]
    assert headers == list(range(17))


def test_resizes_any_input():
    fb = encode(Image.new("L", (100, 40), 128))
    assert len(fb) == 8704
