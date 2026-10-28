import copy
from pathlib import Path

import pytest

from eoh import build, font, message, textdb
from eoh.glyph_render import Renderer

FONT = Path(__file__).resolve().parents[1] / "fonts/SourceHanSerifKR-Heavy.otf"
COMMON = "data/message/PS3/jpn/messageInfo_common.bin.xfbin"


@pytest.fixture(scope="module")
def renderer():
    return Renderer(FONT, size=24)


@pytest.fixture(scope="module")
def fresh_stores(game_fs):
    """Stores as `textdb.py sync` makes them: everything untranslated."""
    return {p: textdb.sync(None, p, message.parse(game_fs.read(p)))
            for p in game_fs.paths() if p.startswith(build.MSG_DIR)}


def _with_ko(game_fs, fresh_stores, ko, state="in_progress"):
    stores = copy.deepcopy(fresh_stores)
    mf = message.parse(game_fs.read(COMMON))
    target = next(e for e in mf.entries if e.text and not textdb.tags(e.text))
    rec = next(r for r in stores[COMMON]["entries"] if r["id"] == f"0x{target.hash:08x}")
    rec.update(ko=ko, state=state)
    return stores, target.hash


def test_nothing_to_build_without_korean_text(game_fs, fresh_stores, renderer):
    files, report = build.build(game_fs, fresh_stores, "dev", renderer)
    assert files == [] and report["applied"] == 0 and report["glyphs"] == ""


def test_dev_build_applies_text_and_adds_only_missing_glyphs(game_fs, fresh_stores, renderer):
    stores, hash_ = _with_ko(game_fs, fresh_stores, "あ한글")
    files, report = build.build(game_fs, stores, "dev", renderer)
    out = dict(files)
    assert set(out) == {COMMON, font.JPN_FONT}
    assert next(e for e in message.parse(out[COMMON]).entries if e.hash == hash_).text == "あ한글"
    before = font.parse(game_fs.read(font.JPN_FONT))
    after = font.parse(out[font.JPN_FONT])
    assert len(after.glyphs) == len(before.glyphs) + 2
    for ch in "あ한글":
        assert font.lookup(after, ord(ch)).code == ord(ch)
    assert report["applied"] == 1 and report["glyphs"] == "글한"


def test_release_build_rejects_unfinished_entries(game_fs, fresh_stores, renderer):
    stores, _ = _with_ko(game_fs, fresh_stores, "한글", state="needs_review")
    with pytest.raises(textdb.TranslationError):
        build.build(game_fs, stores, "release", renderer)


def test_unsupported_character_missing_from_font_is_an_error(game_fs, fresh_stores, renderer):
    stores, _ = _with_ko(game_fs, fresh_stores, "한அ")
    with pytest.raises(build.BuildError, match="அ"):
        build.build(game_fs, stores, "dev", renderer)


def test_missing_store_is_an_error(game_fs, fresh_stores, renderer):
    stores = dict(fresh_stores)
    del stores[COMMON]
    with pytest.raises(build.BuildError, match="messageInfo_common"):
        build.build(game_fs, stores, "dev", renderer)


def test_allowed_korean_punctuation_is_added_like_hangul(game_fs, fresh_stores, renderer):
    stores, _ = _with_ko(game_fs, fresh_stores, "한·글~")
    files, report = build.build(game_fs, stores, "dev", renderer)
    after = font.parse(dict(files)[font.JPN_FONT])
    for ch in "·~":
        assert font.lookup(after, ord(ch)).code == ord(ch)
    assert set(report["glyphs"]) == set("한글·~")
