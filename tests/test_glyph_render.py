from pathlib import Path

import pytest

from eoh import glyph_render

FONT = Path(__file__).resolve().parents[1] / "fonts/SourceHanSerifKR-Heavy.otf"
SIZE = 24  # size used for in-game Hangul glyphs


@pytest.fixture(scope="module")
def renderer():
    return glyph_render.Renderer(FONT, size=SIZE, advance=SIZE)


def test_hangul_glyph_has_ink_and_fullwidth_metrics(renderer):
    alpha, metrics = renderer.render("한")
    h, w = alpha.shape
    assert alpha.max() == 255 and SIZE - 6 <= w <= SIZE and SIZE - 6 <= h <= SIZE + 2
    bearing_x, bearing_y, advance, vert_x, vert_y, vert_adv = metrics
    assert advance == SIZE * 64 and vert_adv == SIZE * 64
    assert (SIZE - 6) * 64 <= bearing_y <= SIZE * 64
    assert vert_x == -(w // 2) * 64


def test_ink_is_cropped_tightly(renderer):
    alpha, _ = renderer.render("가")
    assert alpha[0].any() and alpha[-1].any() and alpha[:, 0].any() and alpha[:, -1].any()


def test_space_like_char_has_empty_bitmap(renderer):
    alpha, metrics = renderer.render(" ")
    assert alpha.shape == (0, 0) and metrics[2] == SIZE * 64
