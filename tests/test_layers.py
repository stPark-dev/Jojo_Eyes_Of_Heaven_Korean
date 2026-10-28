from eoh import cpk
from eoh.layers import GameFs


def test_later_layer_wins(tmp_path):
    base, p1 = tmp_path / "base.cpk", tmp_path / "p1.cpk"
    cpk.write([("d/a", b"old"), ("d/b", b"base-only")], base)
    cpk.write([("d/a", b"new")], p1)
    fs = GameFs([base, p1])
    assert fs.read("d/a") == b"new"
    assert fs.read("d/b") == b"base-only"
    assert fs.source("d/a") == p1
    assert fs.paths() == ["d/a", "d/b"]


def test_final_sources_of_text_and_font(game_fs):
    assert game_fs.source("data/message/PS3/jpn/messageInfo_common.bin.xfbin").parent.name == "4"
    assert game_fs.source("data/message/PS3/jpn/messageInfo_adv.bin.xfbin").parent.name == "3"
    assert game_fs.source("data/ui/font/jpn/xfgame_cmn.fnt.xfbin").parent.name == "1"
