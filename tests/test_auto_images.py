import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/auto_images.py"
spec = importlib.util.spec_from_file_location("auto_images", SCRIPT)
auto_images = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auto_images)


def test_font_defaults_to_serif():
    assert auto_images.font_for("ui/adv/jpn/adv_demo_title/00_a.png") == auto_images.FONT


def test_font_follows_path_fragment():
    png = "ui/customize/jpn/customize_txt/02_customize_edit_subtitle_player.png"
    assert auto_images.font_for(png) == auto_images.ROUND


def test_align_defaults_to_center_and_follows_path_fragment():
    assert auto_images.align_for("ui/adv/jpn/adv_demo_title/00_a.png") == "center"
    assert auto_images.align_for("ui/customize/jpn/customize_txt/02_a.png") == "left"


def test_repaint_box_can_set_the_outline_width():
    import numpy as np
    base = np.zeros((40, 160, 4), np.uint8)

    def dark(ratio):
        recipe = dict(font=auto_images.ROUND, erase=[],
                      boxes=[((4, 4, 156, 36), (255, 255, 255), "contain", (0, 0, 0),
                              dict(stroke_ratio=ratio))])
        out = auto_images.repaint(base, ["가나다"], recipe)
        return ((out[..., 3] > 128) & (out[..., :3].max(2) < 60)).sum()

    assert dark(0.2) > dark(0.05)
