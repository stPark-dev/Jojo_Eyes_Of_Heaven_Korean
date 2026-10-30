import numpy as np
import pytest

from eoh import artfit

MAGENTA = (255, 0, 255)


def _rgba(h, w, colour=(0, 0, 0, 0)):
    img = np.zeros((h, w, 4), np.uint8)
    img[:] = colour
    return img


def test_key_magenta_background_to_transparent():
    rgb = np.zeros((1, 4, 3), np.uint8)
    rgb[0] = [MAGENTA, (0, 0, 0), (255, 255, 255), (128, 0, 128)]
    out = artfit.remove_background(rgb)
    assert list(out[0, :, 3]) == [0, 255, 255, 127]
    assert tuple(out[0, 1, :3]) == (0, 0, 0) and tuple(out[0, 2, :3]) == (255, 255, 255)
    assert tuple(out[0, 3, :3]) == (0, 0, 0)  # half magenta over black edge -> black


def test_transparent_input_is_kept():
    img = _rgba(2, 2, (10, 20, 30, 200))
    assert (artfit.remove_background(img) == img).all()


def test_opaque_rgba_input_is_keyed():
    img = _rgba(1, 1, (*MAGENTA, 255))
    assert artfit.remove_background(img)[0, 0, 3] == 0


def _sheet(rows, gap=30, h=20, w=60):
    """Opaque bars of height h separated by gap transparent rows."""
    img = _rgba(gap + rows * (h + gap), w + 20)
    for i in range(rows):
        y = gap + i * (h + gap)
        img[y:y + h, 10:10 + w] = (255, 255, 255, 255)
    return img


def test_split_rows_finds_each_line_and_crops_tight():
    parts = artfit.split_rows(_sheet(3))
    assert len(parts) == 3 and all(p.shape[:2] == (20, 60) for p in parts)


def test_split_rows_keeps_small_internal_gaps_and_drops_specks():
    img = _sheet(2)
    img[40:43] = 0  # a 3-row gap inside the first line (e.g. between jamo)
    img[2, 0] = (255, 255, 255, 255)  # a speck
    parts = artfit.split_rows(img)
    assert len(parts) == 2 and parts[0].shape[0] == 20


def test_content_box_of_original():
    img = _rgba(48, 192)
    img[10:38, 20:150, 3] = 255
    assert artfit.content_box(img) == (20, 10, 150, 38)


def test_fit_scales_into_box_keeping_aspect_and_centres():
    art = _rgba(50, 100, (255, 255, 255, 255))
    out = artfit.fit(art, 192, 48, box=(20, 10, 172, 38))
    assert out.shape == (48, 192, 4)
    ys, xs = np.nonzero(out[..., 3] > 127)
    assert ys.min() >= 10 and ys.max() < 38          # height limited to 28
    assert abs((xs.min() + xs.max()) / 2 - 95.5) <= 1  # centred horizontally
    assert 54 <= xs.max() - xs.min() + 1 <= 58         # 100 * 28/50 = 56 wide


def test_fit_long_text_is_limited_by_width_margin():
    art = _rgba(10, 400, (255, 255, 255, 255))
    out = artfit.fit(art, 192, 48, box=(20, 10, 172, 38), margin=4)
    xs = np.nonzero(out[..., 3].any(0))[0]
    assert xs.min() >= 4 and xs.max() <= 187


def test_fit_rejects_empty_art():
    with pytest.raises(ValueError):
        artfit.fit(_rgba(10, 10), 192, 48, box=(0, 0, 192, 48))


def test_split_rows_with_count_separates_lines_with_tiny_gap():
    img = _sheet(3, gap=30)
    img[60:80] = 0
    img[50:76, 10:70] = (255, 255, 255, 255)  # line 1 grown down to 4 rows above line 2
    img[52:54] = 0                             # small gap inside line 1
    assert len(artfit.split_rows(img)) == 2
    parts = artfit.split_rows(img, count=3)
    assert [p.shape[0] for p in parts] == [46, 20, 20]


def test_split_rows_with_count_ignores_specks():
    img = _sheet(2)
    img[2, 0] = (255, 255, 255, 255)
    assert len(artfit.split_rows(img, count=2)) == 2


def test_fit_like_uses_reference_scale_and_top_left():
    ref = _rgba(50, 100, (255, 255, 255, 255))   # e.g. text + shadow
    art = _rgba(40, 90, (0, 0, 0, 255))          # the same text without the shadow
    box = (20, 10, 172, 38)
    a = artfit.fit(ref, 192, 48, box)
    b = artfit.fit_like(art, ref, 192, 48, box)
    ya, xa = np.nonzero(a[..., 3] > 127)
    yb, xb = np.nonzero(b[..., 3] > 127)
    assert (ya.min(), xa.min()) == (yb.min(), xb.min())
    assert abs((xb.max() - xb.min() + 1) - 90 * 28 / 50) <= 1


def test_fit_align_left_starts_at_box_left():
    art = _rgba(10, 20, (255, 255, 255, 255))
    out = artfit.fit(art, 200, 50, box=(30, 10, 190, 30), align="left")
    xs = np.nonzero(out[..., 3].any(0))[0]
    assert xs.min() == 30 and xs.max() == 69  # 20 * 20/10 = 40 wide


def test_fit_contain_stays_inside_box():
    art = _rgba(10, 100, (255, 255, 255, 255))
    out = artfit.fit(art, 200, 60, box=(50, 10, 150, 50), align="contain")
    ys, xs = np.nonzero(out[..., 3] > 127)
    assert xs.min() >= 50 and xs.max() < 150 and ys.min() >= 10 and ys.max() < 50
    assert xs.max() - xs.min() + 1 >= 98  # width-limited: fills the box width


def test_row_boxes_match_split_rows():
    img = _sheet(3)
    img[40:42] = 0
    boxes = artfit.row_boxes(img, count=3)
    assert boxes == [(10, 30, 70, 50), (10, 80, 70, 100), (10, 130, 70, 150)]


def test_fit_align_right_ends_at_box_right():
    art = _rgba(10, 20, (255, 255, 255, 255))
    out = artfit.fit(art, 200, 50, box=(30, 10, 190, 30), align="right")
    xs = np.nonzero(out[..., 3].any(0))[0]
    assert xs.max() == 189 and xs.min() == 150


def test_split_components_separates_lines_whose_strokes_overlap_vertically():
    img = np.zeros((60, 90, 4), np.uint8)
    img[0:10, 0:50] = (255, 0, 0, 255)      # line 1
    img[20:40, 0:30] = (0, 255, 0, 255)     # line 2 ...
    img[35:55, 40:80] = (0, 0, 255, 255)    # ... and line 3 reach into the same rows
    img[41:43, 30:40, 3] = 20               # faint glow touching both
    assert len(artfit.split_rows(img, count=3)) != 3
    parts = artfit.split_components(img, 3)
    assert [p.shape[:2] for p in parts] == [(10, 50), (20, 30), (20, 40)]
    assert [tuple(p[p.shape[0] // 2, p.shape[1] // 2, :3]) for p in parts] == \
        [(255, 0, 0), (0, 255, 0), (0, 0, 255)]


def test_split_components_ignores_specks_when_grouping():
    img = np.zeros((80, 90, 4), np.uint8)
    img[0:10, 0:50] = 255
    img[20:40, 0:30] = 255
    img[35:55, 40:80] = 255
    img[78, 88] = 255                       # speck far below
    assert [p.shape[:2] for p in artfit.split_components(img, 3)][:2] == [(10, 50), (20, 30)]


def test_split_components_handles_a_speck_labelled_before_the_strokes():
    img = np.zeros((60, 90, 4), np.uint8)
    img[0, 60] = 255                        # speck near line 1, labelled before lines 2 and 3
    img[0:10, 0:50] = 255
    img[20:40, 0:30] = 255
    img[35:55, 40:80] = 255
    assert [p.shape[:2] for p in artfit.split_components(img, 3)][1:] == [(20, 30), (20, 40)]
