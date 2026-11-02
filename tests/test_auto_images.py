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


def test_tip_items_carry_the_korean_lines_for_known_tip_pictures():
    png = "ui/tips_cmn/jpn/tips_network_00/00_tips_network_00_00.png"
    items = auto_images.tip_items(png)
    assert [i["text"] for i in items] == ["온라인 배틀", "플레이어 매치", "랭크 매치"]
    assert all(len(i["rect"]) == 4 for i in items)
    assert auto_images.tip_items("ui/tips_cmn/jpn/tips_stg1_00/00_tips_stg1_00_00.png") is None


def test_every_tip_stem_names_a_real_tip_picture():
    import json
    pngs = {Path(e["png"]).stem for e in json.loads(auto_images.MANIFEST.read_text("utf-8"))["images"]
            if e["category"] == "팁 화면"}
    assert set(auto_images.TIPS) <= pngs


def test_art_piece_cuts_one_line_of_a_finished_korean_picture():
    import numpy as np
    whole = auto_images.art_piece("ui/adv/jpn/adv_poker_txt/13_tex13.png", None)
    call = auto_images.art_piece("ui/adv/jpn/adv_poker_txt/13_tex13.png", 1)  # 레이즈/콜/드롭
    assert call.shape[2] == 4 and call[..., 3].max() == 255
    assert call.shape[0] < whole.shape[0] / 2


def test_tip_items_resolve_art_references_to_pixels():
    import numpy as np
    items = [i for lines in auto_images.TIPS for i in auto_images.tip_items(lines + ".png") if "art" in i]
    assert items and all(isinstance(i["art"], np.ndarray) for i in items)


def test_logo_swaps_name_save_pictures_in_the_manifest():
    import json
    pngs = {e["png"] for e in json.loads(auto_images.MANIFEST.read_text("utf-8"))["images"]}
    assert set(auto_images.LOGO_SWAPS) == {"save/PS3/JP/ICON0/00_ICON0.png",
                                           "save/PS3/JP/PIC1/00_PIC1.png"}
    assert set(auto_images.LOGO_SWAPS) <= pngs
