import pytest

from eoh import textdb
from eoh.message import Entry, MessageFile

FILE = "data/message/PS3/jpn/sample.bin.xfbin"


def _mf(*texts):
    return MessageFile(b"P", b"M" * 8, 4,
                       [Entry(0x100 + i, t, bytes(8)) for i, t in enumerate(texts)], b"S")


# --- tag checks -------------------------------------------------------------------------

def test_tags_ignore_fullwidth_brackets():
    assert textdb.tags("<１>と<icon btn_l1><string 1 />") == ["<icon btn_l1>", "<string 1 />"]


def test_check_accepts_reordered_placeholders():
    assert textdb.check("<string 1 />の<string 2 />", "<string 2 />의 <string 1 />") == []


def test_check_reports_missing_placeholder():
    assert textdb.check("<string />枚", "장") == ["태그 누락: <string />"]


def test_check_reports_extra_tag():
    assert textdb.check("決定", "<icon btn_ok>결정") == ["원문에 없는 태그: <icon btn_ok>"]


def test_check_allows_ruby_to_be_dropped():
    assert textdb.check("<ruby ザ・ワールド>世界</ruby>だ", "더 월드다") == []


def test_check_requires_balanced_ruby_and_color():
    assert textdb.check("<color 0xff>赤</color>", "<color 0xff>빨강") == ["태그 누락: </color>"]
    assert textdb.check("a", "<ruby 읽기>글자") == ["ruby 태그 짝이 맞지 않음"]


# --- store sync -------------------------------------------------------------------------

def test_sync_creates_untranslated_entries_without_source_text():
    store = textdb.sync(None, FILE, _mf("はい", None, "いいえ"))
    assert [e["id"] for e in store["entries"]] == ["0x00000100", "0x00000102"]
    assert all(e["state"] == "untranslated" and e["ko"] == "" for e in store["entries"])
    assert "はい" not in repr(store)


def test_sync_keeps_translation_when_source_unchanged():
    store = textdb.sync(None, FILE, _mf("はい"))
    store["entries"][0].update(ko="예", state="needs_review")
    again = textdb.sync(store, FILE, _mf("はい"))
    assert again["entries"][0]["ko"] == "예" and again["entries"][0]["state"] == "needs_review"


def test_sync_flags_changed_source_for_review():
    store = textdb.sync(None, FILE, _mf("はい"))
    store["entries"][0].update(ko="예", state="distribution_eligible")
    again = textdb.sync(store, FILE, _mf("はいはい"))
    e = again["entries"][0]
    assert e["ko"] == "예" and e["state"] == "needs_review" and e["source_changed"] is True


def test_sync_refuses_entries_missing_from_source():
    store = textdb.sync(None, FILE, _mf("はい", "いいえ"))
    with pytest.raises(ValueError):
        textdb.sync(store, FILE, _mf("はい"))


def test_sync_does_not_mutate_input():
    store = textdb.sync(None, FILE, _mf("はい"))
    before = repr(store)
    textdb.sync(store, FILE, _mf("はいはい"))
    assert repr(store) == before


# --- apply ------------------------------------------------------------------------------

def _translated(state="needs_review"):
    store = textdb.sync(None, FILE, _mf("はい", None, "<string />枚"))
    store["entries"][0].update(ko="예", state=state)
    store["entries"][1].update(ko="<string />장", state=state)
    return store


def test_apply_dev_uses_translations_and_reports():
    out, report = textdb.apply(_mf("はい", None, "<string />枚"), _translated(), policy="dev")
    assert [e.text for e in out.entries] == ["예", None, "<string />장"]
    assert report == {"applied": 2, "kept_source": 0, "problems": []}


def test_apply_dev_keeps_source_for_untranslated():
    store = textdb.sync(None, FILE, _mf("はい"))
    out, report = textdb.apply(_mf("はい"), store, policy="dev")
    assert out.entries[0].text == "はい" and report["kept_source"] == 1


def test_apply_fails_on_tag_problem():
    store = _translated()
    store["entries"][1]["ko"] = "장"
    with pytest.raises(textdb.TranslationError, match="태그 누락"):
        textdb.apply(_mf("はい", None, "<string />枚"), store, policy="dev")


def test_apply_fails_on_stale_source():
    store = _translated()
    with pytest.raises(textdb.TranslationError, match="원문 지문"):
        textdb.apply(_mf("はいはい", None, "<string />枚"), store, policy="dev")


def test_apply_release_requires_every_entry_eligible():
    with pytest.raises(textdb.TranslationError, match="배포 가능"):
        textdb.apply(_mf("はい", None, "<string />枚"), _translated(), policy="release")
    out, _ = textdb.apply(_mf("はい", None, "<string />枚"),
                          _translated("distribution_eligible"), policy="release")
    assert out.entries[0].text == "예"


def test_apply_rejects_unknown_state():
    store = _translated(state="done")
    with pytest.raises(textdb.TranslationError, match="알 수 없는 상태"):
        textdb.apply(_mf("はい", None, "<string />枚"), store, policy="dev")
