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
