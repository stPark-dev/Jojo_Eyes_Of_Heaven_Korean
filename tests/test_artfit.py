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
