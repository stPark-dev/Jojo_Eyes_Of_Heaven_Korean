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


def _styled(top, bottom, edge, h=40, w=80, border=3):
    img = np.zeros((h + 20, w + 20, 4), np.uint8)
    img[10:10 + h, 10:10 + w] = (*edge, 255)
    k = np.linspace(0, 1, h - 2 * border)[:, None, None]
    img[10 + border:10 + h - border, 10 + border:10 + w - border, :3] = \
        np.rint(np.array(top) * (1 - k) + np.array(bottom) * k)
    return img


def test_sample_style_reads_gradient_and_outline():
    style = textart.sample_style(_styled((250, 250, 40), (240, 60, 20), (40, 0, 60)))
    (t, b), edge = style["fill"], style["stroke"]
    assert np.abs(np.array(t) - (250, 230, 40)).max() <= 40
    assert np.abs(np.array(b) - (240, 80, 20)).max() <= 40
    assert np.abs(np.array(edge) - (40, 0, 60)).max() <= 10
    assert 0.04 <= style["stroke_ratio"] <= 0.15


def test_overlay_erase_can_clear_to_transparent():
    base = np.full((10, 10, 4), 255, np.uint8)
    out = textart.overlay(base, erase=[((0, 0, 5, 10), (0, 0, 0, 0))])
    assert (out[:, :5, 3] == 0).all() and (out[:, 5:, 3] == 255).all()


def test_compose_contain_keeps_each_piece_in_its_box():
    a = np.full((10, 200, 4), 255, np.uint8)
    out = textart.compose([a, a], 200, 100, [(20, 10, 100, 30), (20, 50, 180, 80)], align="contain")
    top = out[:40]
    xs = np.nonzero(top[..., 3].any(0))[0]
    assert xs.min() >= 20 and xs.max() < 100


def test_overlay_erase_above_copies_the_row_above():
    base = np.zeros((10, 4, 4), np.uint8)
    base[..., 3] = 255
    base[:, :, 0] = np.arange(4) * 50   # horizontal gradient
    base[5:8, 1:3, :3] = 255           # "text"
    out = textart.overlay(base, erase=[((1, 5, 3, 8), "above")])
    assert (out[5:8, 1:3, 0] == base[4, 1:3, 0]).all() and (out[5:8, 1:3, 1] == 0).all()


def test_sample_style_detects_white_rim_around_dark_outline():
    img = _styled((250, 250, 250), (240, 200, 40), (90, 50, 10), h=48, w=96, border=6)
    img[10:58, 10:106][:2] = (255, 255, 255, 255)
    img[10:58, 10:106][-2:] = (255, 255, 255, 255)
    img[10:58, 10:106][:, :2] = (255, 255, 255, 255)
    img[10:58, 10:106][:, -2:] = (255, 255, 255, 255)
    style = textart.sample_style(img)
    assert np.abs(np.array(style["stroke"]) - (90, 50, 10)).max() <= 10
    assert style["outer"] == (255, 255, 255)
    assert np.abs(np.array(style["fill"][1]) - (240, 200, 40)).max() <= 40


def test_render_outer_rim_surrounds_stroke():
    art = textart.render("ㅡ", FONT, 64, fill=(255, 0, 0), stroke=(0, 0, 255), stroke_ratio=0.1,
                         outer=(0, 255, 0), outer_ratio=0.05)
    mid = art.shape[0] // 2
    row = art[:, art.shape[1] // 2]
    solid = np.nonzero(row[:, 3] == 255)[0]
    assert tuple(row[solid[0], :3]) == (0, 255, 0)  # outermost pixel is the rim colour
    colours = {tuple(c) for c in art[art[..., 3] == 255][:, :3]}
    assert (0, 0, 255) in colours and (255, 0, 0) in colours


def test_overlay_erase_tile_repeats_a_clean_strip_in_phase():
    base = np.zeros((4, 40, 4), np.uint8)
    base[..., 3] = 255
    base[..., 0] = (np.arange(40) % 5) * 40   # pattern with period 5
    base[1:3, 12:30, :3] = 255               # "text" over the pattern
    out = textart.overlay(base, erase=[((10, 0, 35, 4), ("tile", 0, 10))])
    assert (out[..., 0] == (np.arange(40) % 5) * 40).all() and (out[..., 1] == 0).all()


def test_overlay_text_can_have_an_outer_rim():
    base = np.zeros((40, 160, 4), np.uint8)
    text = dict(text="가나", font=FONT, box=(4, 4, 156, 36), fill=(255, 255, 255),
                stroke=(255, 255, 255), stroke_ratio=0.05, align="contain")
    plain = textart.overlay(base, texts=[text])
    rimmed = textart.overlay(base, texts=[dict(text, outer=(0, 0, 0), outer_ratio=0.1)])
    dark = lambda img: ((img[..., 3] > 128) & (img[..., :3].max(2) < 60)).sum()
    assert dark(plain) == 0 and dark(rimmed) > 0
