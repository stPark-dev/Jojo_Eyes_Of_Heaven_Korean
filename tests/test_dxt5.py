import io
import struct

import numpy as np
import pytest
from PIL import Image

from eoh import dxt5


def _pil_decode(data: bytes, w: int, h: int) -> np.ndarray:
    head = struct.pack("<4sIIIIIII44s", b"DDS ", 124, 0x81007, h, w, len(data), 0, 1, bytes(44))
    pf = struct.pack("<II4s5I", 32, 0x4, b"DXT5", 0, 0, 0, 0, 0)
    img = Image.open(io.BytesIO(head + pf + struct.pack("<5I", 0x1000, 0, 0, 0, 0) + data))
    return np.array(img.getchannel("A"))


def test_constant_blocks_are_exact():
    alpha = np.zeros((8, 8), np.uint8)
    alpha[:4, :4] = 255
    alpha[4:, 4:] = 77
    assert np.array_equal(dxt5.decode_alpha(dxt5.encode(alpha), 8, 8), alpha)


def test_gradient_error_is_bounded():
    alpha = np.tile(np.arange(0, 256, 16, dtype=np.uint8), (16, 1))
    out = dxt5.decode_alpha(dxt5.encode(alpha), 16, 16).astype(int)
    # 8-level interpolation per 4x4 block: worst case half a step of (max-min)/7.
    assert np.abs(out - alpha).max() <= 48 // 14 + 1


def test_encoded_alpha_matches_pil_decoder():
    rng = np.random.default_rng(1)
    alpha = rng.integers(0, 256, (16, 16), dtype=np.uint8)
    data = dxt5.encode(alpha)
    assert np.array_equal(_pil_decode(data, 16, 16), dxt5.decode_alpha(data, 16, 16))


def test_color_is_white_where_alpha_present():
    alpha = np.zeros((4, 8), np.uint8)
    alpha[:, 4:] = 200
    data = dxt5.encode(alpha)
    assert data[8:16] == dxt5.EMPTY_COLOR
    assert data[16 + 8:32] == dxt5.WHITE_COLOR


def test_encode_rejects_unaligned_size():
    with pytest.raises(ValueError):
        dxt5.encode(np.zeros((5, 4), np.uint8))


def test_blit_replaces_only_covered_blocks():
    base = dxt5.encode(np.full((8, 8), 9, np.uint8))
    patch = np.full((4, 4), 200, np.uint8)
    out = dxt5.blit(base, 8, patch, x=4, y=4)
    dec = dxt5.decode_alpha(out, 8, 8)
    assert (dec[4:, 4:] == 200).all() and (dec[:4, :] == 9).all() and (dec[:, :4] == 9).all()


def test_decoder_matches_pil_on_game_atlas(game_fs):
    from eoh import font
    f = font.parse(game_fs.read(font.JPN_FONT))
    w = h = 256  # top-left region is enough and keeps the test fast
    rows = [f.texture[(by * (f.width // 4)) * 16:(by * (f.width // 4) + w // 4) * 16]
            for by in range(h // 4)]
    data = b"".join(rows)
    assert np.array_equal(dxt5.decode_alpha(data, w, h), _pil_decode(data, w, h))
