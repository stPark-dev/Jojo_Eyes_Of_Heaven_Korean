import numpy as np
import pytest

from eoh import dxt5, font
from eoh.font import Glyph


@pytest.fixture(scope="module")
def jpn_font(game_fs):
    return game_fs.read(font.JPN_FONT)


def test_roundtrip_is_byte_identical(jpn_font):
    assert font.serialize(font.parse(jpn_font)) == jpn_font


def test_parse_reads_known_glyph(jpn_font):
    f = font.parse(jpn_font)
    a = next(g for g in f.glyphs if g.code == ord("あ"))
    assert (a.x, a.y, a.w, a.h) == (1111, 61, 23, 24)
    assert a.metrics == (128, 1408, 1664, -704, 0, 1664)
    assert len(f.glyphs) == 3679 and (f.width, f.height) == (2048, 2048)


def test_free_top_is_below_last_glyph(jpn_font):
    assert font.parse(jpn_font).free_top() == 1380


def _square(n=10):
    return np.full((n, n), 255, np.uint8)


def test_add_glyphs_inserts_sorted_and_findable(jpn_font):
    f = font.parse(jpn_font)
    out = font.add_glyphs(f, [(ord("한"), _square(), (0, 640, 1664, -320, 0, 1664)),
                              (ord("가"), _square(), (0, 640, 1664, -320, 0, 1664))])
    back = font.parse(font.serialize(out))
    codes = [g.code for g in back.glyphs]
    assert codes == sorted(codes) and len(codes) == 3681
    for ch in "가한あ":
        assert font.lookup(back, ord(ch)).code == ord(ch)


def test_added_glyph_pixels_land_in_atlas(jpn_font):
    f = font.add_glyphs(font.parse(jpn_font), [(ord("가"), _square(), (0, 0, 1664, 0, 0, 1664))])
    g = font.lookup(f, ord("가"))
    x0, y0 = g.x // 4 * 4, g.y // 4 * 4
    region = dxt5.decode_alpha(font.texture_region(f, x0, y0, 16, 16), 16, 16)
    assert (region[g.y - y0:g.y - y0 + 10, g.x - x0:g.x - x0 + 10] == 255).all()


def test_existing_glyph_texels_untouched(jpn_font):
    f = font.parse(jpn_font)
    out = font.add_glyphs(f, [(ord("가"), _square(), (0, 0, 1664, 0, 0, 1664))])
    used = f.free_top() * f.width  # bytes before the free area (1 byte/texel in DXT5)
    assert out.texture[:used] == f.texture[:used]


def test_add_rejects_existing_code(jpn_font):
    with pytest.raises(ValueError):
        font.add_glyphs(font.parse(jpn_font), [(ord("あ"), _square(), (0,) * 6)])


def test_add_fails_when_atlas_full(jpn_font):
    f = font.parse(jpn_font)
    many = [(0xAC00 + i, _square(26), (0,) * 6) for i in range(5000)]
    with pytest.raises(font.AtlasFull):
        font.add_glyphs(f, many)


def test_lookup_table_matches_game_formula(jpn_font):
    f = font.parse(jpn_font)
    assert font.build_table(f.glyphs) == f.table


def test_glyph_record_roundtrip():
    g = Glyph(code=0xAC00, x=5, y=1384, w=20, h=21, metrics=(1, 2, 3, -4, 5, 6))
    assert font.Glyph.unpack(g.pack(pos=3, remaining=7)) == g
