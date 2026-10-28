import struct

import numpy as np
import pytest

from eoh import texture


def _ntp3(*textures):
    """NTP3 block holding (width, height, fmt, data) textures."""
    body = b""
    for w, h, fmt, data in textures:
        head = struct.pack(">IIIHHBBBBHH", 0x50 + len(data), 0, len(data), 0x50, 0, 0, 1, 0, fmt, w, h)
        body += head.ljust(0x50, b"\0") + data
    return b"NTP3" + struct.pack(">HH", 0x0100, len(textures)) + b"\0" * 8 + body


def _dxt1_block(c0, c1, indices):
    bits = sum(i << (2 * n) for n, i in enumerate(indices))
    return struct.pack("<HHI", c0, c1, bits)


RED, BLUE = 0xF800, 0x001F


def test_find_textures_reads_headers_and_data():
    a = _dxt1_block(RED, BLUE, [0] * 16)
    b = bytes(16)
    buf = b"head" + _ntp3((4, 4, 0, a)) + b"mid" + _ntp3((4, 4, 2, b))
    texs = texture.find_textures(buf)
    assert [(t.width, t.height, t.fmt) for t in texs] == [(4, 4, 0), (4, 4, 2)]
    assert texs[0].data == a and texs[1].data == b
    assert buf[texs[0].offset:texs[0].offset + 8] == a[:8]


def test_find_textures_handles_several_in_one_block():
    a, b = _dxt1_block(RED, BLUE, [1] * 16), _dxt1_block(BLUE, RED, [1] * 16)
    texs = texture.find_textures(_ntp3((4, 4, 0, a), (4, 4, 0, b)))
    assert [t.data for t in texs] == [a, b]


def test_decode_dxt1_four_colour_block():
    idx = [0, 1, 2, 3] * 4
    rgba = texture.decode(texture.find_textures(_ntp3((4, 4, 0, _dxt1_block(RED, BLUE, idx))))[0])
    assert rgba.shape == (4, 4, 4)
    assert tuple(rgba[0, 0]) == (255, 0, 0, 255) and tuple(rgba[0, 1]) == (0, 0, 255, 255)
    assert tuple(rgba[0, 2])[3] == 255 and rgba[0, 2, 0] > rgba[0, 3, 0]


def test_decode_dxt1_three_colour_block_has_transparent_index():
    rgba = texture.decode(texture.find_textures(_ntp3((4, 4, 0, _dxt1_block(BLUE, RED, [3] * 16))))[0])
    assert (rgba[..., 3] == 0).all()


def test_decode_dxt5_uses_alpha_block():
    alpha = struct.pack("<BB", 128, 0) + bytes(6)  # all indices 0 -> alpha 128
    color = _dxt1_block(RED, BLUE, [0] * 16)
    rgba = texture.decode(texture.find_textures(_ntp3((4, 4, 2, alpha + color)))[0])
    assert tuple(rgba[3, 3]) == (255, 0, 0, 128)


def test_decode_real_game_texture(game_fs):
    texs = texture.find_textures(game_fs.read("data/ui/adv/jpn/adv_cmn_txt.xfbin"))
    assert len(texs) == 4 and (texs[0].width, texs[0].height, texs[0].fmt) == (180, 40, 2)
    rgba = texture.decode(texs[0])
    assert rgba.shape == (40, 180, 4) and rgba[..., 3].max() == 255


def test_unknown_format_is_rejected():
    with pytest.raises(ValueError, match="format"):
        texture.decode(texture.find_textures(_ntp3((4, 4, 14, bytes(64))))[0])
