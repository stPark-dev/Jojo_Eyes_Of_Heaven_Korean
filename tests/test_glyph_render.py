from pathlib import Path

import pytest

from eoh import glyph_render

NOTO = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc")


@pytest.fixture(scope="module")
def renderer():
    if not NOTO.exists():
        pytest.skip("Noto Sans CJK not installed")
    return glyph_render.Renderer(NOTO, size=26, index=1, advance=26)


def test_hangul_glyph_has_ink_and_fullwidth_metrics(renderer):
    alpha, metrics = renderer.render("한")
    h, w = alpha.shape
    assert alpha.max() == 255 and 20 <= w <= 26 and 20 <= h <= 27
    bearing_x, bearing_y, advance, vert_x, vert_y, vert_adv = metrics
    assert advance == 26 * 64 and vert_adv == 26 * 64
    assert 18 * 64 <= bearing_y <= 24 * 64
    assert vert_x == -(w // 2) * 64


def test_ink_is_cropped_tightly(renderer):
    alpha, _ = renderer.render("가")
    assert alpha[0].any() and alpha[-1].any() and alpha[:, 0].any() and alpha[:, -1].any()


def test_space_like_char_has_empty_bitmap(renderer):
    alpha, metrics = renderer.render(" ")
    assert alpha.shape == (0, 0) and metrics[2] == 26 * 64
