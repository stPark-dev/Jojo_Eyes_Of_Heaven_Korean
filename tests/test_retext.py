from pathlib import Path

import numpy as np

from eoh import retext

FONT = Path(__file__).resolve().parents[1] / "fonts/NanumSquareRoundB.ttf"
RECT = (10, 10, 60, 22)


def lum(img):
    return img[..., :3].astype(int).mean(-1)


def screen(text_rgb=(255, 255, 255), bg=70):
    """Opaque noisy grey picture with 'text' (vertical strokes, 10 px tall) inside RECT."""
    rng = np.random.default_rng(0)
    img = np.full((40, 80, 4), 255, np.uint8)
    img[..., :3] = rng.integers(bg - 8, bg + 8, (40, 80, 1))
    for x in range(12, 58, 4):
        img[11:21, x:x + 2, :3] = text_rgb
    return img


def test_light_text_is_erased_and_redrawn_at_its_height():
    img = screen()
    out = retext.retext(img, [dict(rect=RECT, text="가")], FONT)
    assert lum(out[11:21, 40:58]).max() < 120  # old strokes beyond the new word are gone
    new = lum(out[RECT[1]:RECT[3], RECT[0]:RECT[2]]) > 200
    rows = np.nonzero(new.any(1))[0]
    assert rows.max() - rows.min() >= 7  # drawn about as tall as the original
    assert (out[:9] == img[:9]).all() and (out[:, 62:] == img[:, 62:]).all()  # outside untouched


def test_fill_colour_is_sampled_from_the_original_text():
    out = retext.retext(screen(text_rgb=(250, 230, 20)), [dict(rect=RECT, text="가")], FONT)
    px = out[RECT[1]:RECT[3], RECT[0]:RECT[2], :3].reshape(-1, 3).astype(int)
    bright = px[px.mean(1) > 140]
    assert len(bright) and bright[:, 0].mean() > 180 and bright[:, 2].mean() < 90


def test_dark_text_on_light_background():
    img = screen(text_rgb=(10, 10, 10), bg=220)
    out = retext.retext(img, [dict(rect=RECT, text="가", polarity="dark")], FONT)
    assert lum(out[11:21, 40:58]).min() > 150
    assert lum(out[RECT[1]:RECT[3], RECT[0]:RECT[0] + 15]).min() < 80


def test_right_align_keeps_the_right_edge():
    out = retext.retext(screen(), [dict(rect=RECT, text="가", align="right")], FONT)
    new = lum(out[RECT[1]:RECT[3], RECT[0]:RECT[2]]) > 200
    cols = np.nonzero(new.any(0))[0]
    assert cols.max() >= 45 and cols.min() > 25


def test_long_text_is_shrunk_to_the_rect_unless_clipped():
    long = "가나다라마바사아자차카타파하"
    fit = retext.retext(screen(), [dict(rect=RECT, text=long)], FONT)
    clip = retext.retext(screen(), [dict(rect=RECT, text=long, clip=True)], FONT)
    assert lum(fit[:, 62:]).max() < 120  # stays inside
    tall = lambda o: np.ptp(np.nonzero((lum(o[RECT[1]:RECT[3], 10:60]) > 200).any(1))[0])
    assert tall(clip) >= 7  # clipped keeps the height and runs off the picture edge
    assert lum(clip[11:21, 62:]).max() > 200


def test_art_is_pasted_instead_of_text():
    art = np.zeros((20, 20, 4), np.uint8)
    art[..., 0] = 255
    art[..., 3] = 255
    out = retext.retext(screen(), [dict(rect=RECT, art=art)], FONT)
    red = (out[..., 0] > 200) & (out[..., 1] < 60)
    ys, xs = np.nonzero(red)
    assert len(ys) and ys.min() >= RECT[1] and ys.max() < RECT[3] and xs.min() >= RECT[0]


def test_dark_shadow_of_light_text_is_erased_too():
    img = screen()
    for x in range(12, 56, 5):  # 2 px drop shadow right of each stroke
        img[11:21, x:x + 2, :3] = 255
        img[11:21, x + 2:x + 4, :3] = 5
    out = retext.retext(img, [dict(rect=RECT, text="가")], FONT)
    assert lum(out[11:21, 40:58]).min() > 40


def test_faint_antialiased_edges_are_erased_too():
    img = screen(bg=30)
    for x in range(12, 58, 4):  # mid-grey fringe beside each white stroke
        img[11:21, x + 2:x + 3, :3] = 95
    out = retext.retext(img, [dict(rect=RECT, text="가")], FONT)
    assert lum(out[11:21, 40:58]).max() < 60


def test_small_text_is_fattened_in_its_own_colour_not_outlined_in_black():
    out = retext.retext(screen(), [dict(rect=RECT, text="가")], FONT)
    assert lum(out[RECT[1]:RECT[3], RECT[0]:RECT[2]]).min() > 45  # bg is 62..78, no black rim


def test_fill_takes_the_brightest_part_of_the_original_strokes():
    img = screen()
    img[11:21, 12:58:4, :3] = 150  # half of every stroke is a dimmer edge
    out = retext.retext(img, [dict(rect=RECT, text="가")], FONT)
    assert lum(out[RECT[1]:RECT[3], RECT[0]:RECT[2]]).max() > 235


def test_within_keeps_the_erase_inside_the_bright_balloon():
    img = np.full((60, 80, 4), 255, np.uint8)
    img[..., :3] = 30  # dark scene
    img[10:50, 10:70, :3] = 250  # white speech balloon
    img[20:40, 20:60:4, :3] = (200, 40, 20)  # red text strokes
    out = retext.retext(img, [dict(rect=(5, 5, 75, 55), text="가", polarity="dark", within=200)], FONT)
    assert (out[5:10, 5:75] == img[5:10, 5:75]).all()  # dark scene around the balloon untouched
    assert lum(out[20:40, 50:60]).min() > 200  # text beyond the new word erased to white
