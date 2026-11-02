import numpy as np

from eoh import logoswap


def logo(rgb, box):
    """20x20 transparent logo with an opaque square at box (x0, y0, x1, y1)."""
    a = np.zeros((20, 20, 4), np.uint8)
    x0, y0, x1, y1 = box
    a[y0:y1, x0:x1] = rgb + (255,)
    return a


OLD = logo((255, 0, 0), (2, 2, 18, 18))    # big red square
NEW = logo((0, 0, 255), (6, 6, 14, 14))    # smaller blue square


def scene():
    img = np.zeros((40, 60, 4), np.uint8)
    img[..., :3] = (0, 200, 0)  # green picture
    img[..., 3] = 255
    return img


def test_new_logo_drawn_where_the_old_one_sits():
    img = scene()
    img[10 + 2:10 + 18, 20 + 2:20 + 18, :3] = (255, 0, 0)  # old logo pasted at (20, 10), scale 1
    out = logoswap.swap(img, OLD, NEW, 1.0, 1.0, 20, 10)
    assert (out[10 + 6:10 + 14, 20 + 6:20 + 14, :3] == (0, 0, 255)).all()


def test_old_logo_parts_the_new_one_does_not_cover_are_filled_from_the_picture():
    img = scene()
    img[12:28, 22:38, :3] = (255, 0, 0)
    out = logoswap.swap(img, OLD, NEW, 1.0, 1.0, 20, 10)
    rest = out[12:28, 22:38].reshape(-1, 4)
    assert (rest[:, 0] < 60).all()  # no red left anywhere
    assert (out[:, :15] == img[:, :15]).all()  # picture away from the logo untouched


def test_scale_places_the_logo_at_that_size():
    img = scene()
    out = logoswap.swap(img, OLD, NEW, 0.5, 0.5, 0, 0)  # new square lands on 3..7
    assert (out[3:7, 3:7, :3] == (0, 0, 255)).all()
    assert (out[12:, 12:] == img[12:, 12:]).all()


def test_transparent_picture_gets_only_the_new_logo():
    img = np.zeros((20, 20, 4), np.uint8)
    img[2:18, 2:18] = (255, 0, 0, 255)  # the picture is just the old logo
    out = logoswap.swap(img, OLD, NEW, 1.0, 1.0, 0, 0)
    assert (out[6:14, 6:14] == (0, 0, 255, 255)).all()
    assert out[2:6, 2:18, 3].max() == 0  # old logo gone, background stays clear
