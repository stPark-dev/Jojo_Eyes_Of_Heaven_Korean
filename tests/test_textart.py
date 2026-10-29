from pathlib import Path

import numpy as np

from eoh import textart

FONT = Path(__file__).resolve().parents[1] / "fonts/SourceHanSerifKR-Heavy.otf"


def test_render_crops_and_uses_fill_and_stroke():
    art = textart.render("가", FONT, 64, fill=(255, 255, 255), stroke=(0, 0, 0), stroke_ratio=0.1)
    assert art.shape[2] == 4 and art[0].any() and art[-1].any()  # cropped tight
    solid = art[..., 3] == 255
    colours = {tuple(c) for c in art[solid][:, :3]}
    assert (255, 255, 255) in colours and (0, 0, 0) in colours


def test_render_vertical_gradient_fill():
    art = textart.render("ㅡ", FONT, 64, fill=((255, 0, 0), (0, 0, 255)), stroke=None)
    rows = np.nonzero(art[..., 3].max(1) == 255)[0]
    top = art[rows[0], art[rows[0], :, 3] == 255, :3].mean(0)
    bottom = art[rows[-1], art[rows[-1], :, 3] == 255, :3].mean(0)
    assert top[0] > top[2] and bottom[2] > bottom[0]


def test_line_boxes_of_two_line_original():
    img = np.zeros((100, 200, 4), np.uint8)
    img[10:30, 80:120, 3] = 255
    img[50:80, 20:180, 3] = 255
    img[55:57, :, 3] = 0  # small gap inside line 2
    assert textart.line_boxes(img) == [(80, 10, 120, 30), (20, 50, 180, 80)]


def test_compose_places_each_line_in_its_box():
    a = np.full((10, 40, 4), 255, np.uint8)
    b = np.full((10, 80, 4), 255, np.uint8)
    out = textart.compose([a, b], 200, 100, [(80, 10, 120, 30), (20, 50, 180, 80)])
    assert out.shape == (100, 200, 4)
    ys = np.nonzero(out[..., 3].any(1))[0]
    assert ys.min() >= 10 and ys.max() < 80 and not out[35:45, :, 3].any()


def test_compose_requires_matching_line_count():
    import pytest
    with pytest.raises(ValueError, match="줄"):
        textart.compose([np.full((4, 4, 4), 255, np.uint8)], 10, 10, [(0, 0, 5, 5), (0, 5, 5, 10)])


def test_overlay_erases_and_writes_text_on_a_copy():
    base = np.zeros((60, 200, 4), np.uint8)
    base[..., :3], base[..., 3] = 100, 255
    out = textart.overlay(base, erase=[((10, 10, 190, 50), (239, 239, 239))],
                          texts=[dict(text="가나", font=FONT, box=(20, 20, 180, 40), fill=(255, 0, 0),
                                      align="left")])
    assert (base[..., 0] == 100).all()                   # input untouched
    assert tuple(out[5, 5, :3]) == (100, 100, 100)        # outside the erased rect
    assert tuple(out[12, 100, :3]) == (239, 239, 239)     # erased, no text there
    red = (out[..., 0] > 200) & (out[..., 1] < 80)
    ys, xs = np.nonzero(red)
    assert ys.min() >= 20 and ys.max() < 40 and xs.min() <= 22
    assert (out[..., 3] == 255).all()
