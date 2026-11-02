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


# --- approved keep-source exceptions ----------------------------------------------------

def _kept(state="distribution_eligible", reason="의성어는 일본어 유지 (사용자 결정 2026-10-28)"):
    store = textdb.sync(None, FILE, _mf("ドドド"))
    store["entries"][0].update(keep_source=reason, state=state)
    return store


def test_release_accepts_approved_keep_source_exception():
    out, report = textdb.apply(_mf("ドドド"), _kept(), policy="release")
    assert out.entries[0].text == "ドドド" and report["kept_source"] == 1


def test_keep_source_requires_reason():
    with pytest.raises(textdb.TranslationError, match="원문 유지 사유"):
        textdb.apply(_mf("ドドド"), _kept(reason=""), policy="release")


def test_keep_source_conflicts_with_translation():
    store = _kept()
    store["entries"][0]["ko"] = "두두두"
    with pytest.raises(textdb.TranslationError, match="원문 유지와 번역문"):
        textdb.apply(_mf("ドドド"), store, policy="dev")


# --- import from work files -------------------------------------------------------------

def _store(*texts):
    return textdb.sync(None, FILE, _mf(*texts))


def _row(i, src, ko, state="needs_review", note=""):
    return {"id": f"0x{0x100 + i:08x}", "src": src, "ko": ko, "state": state, "note": note}


def test_import_updates_ko_state_note_only():
    store = _store("決定", "戻る")
    out, report = textdb.import_rows(store, [_row(0, "決定", "결정", note="초안")])
    rec = out["entries"][0]
    assert (rec["ko"], rec["state"], rec["note"]) == ("결정", "needs_review", "초안")
    assert rec["src_sha1"] == store["entries"][0]["src_sha1"]
    assert out["entries"][1] == store["entries"][1] and store["entries"][0]["ko"] == ""
    assert report == {"updated": 1, "skipped": 0}


def test_import_skips_rows_without_translation():
    _, report = textdb.import_rows(_store("決定"), [_row(0, "決定", "", state="untranslated")])
    assert report == {"updated": 0, "skipped": 1}


def test_import_rejects_changed_source():
    with pytest.raises(textdb.TranslationError, match="원문"):
        textdb.import_rows(_store("決定"), [_row(0, "決定する", "결정")])


def test_import_rejects_unknown_id_and_tag_problems():
    with pytest.raises(textdb.TranslationError, match="없는 항목"):
        textdb.import_rows(_store("決定"), [_row(5, "決定", "결정")])
    with pytest.raises(textdb.TranslationError, match="태그 누락"):
        textdb.import_rows(_store("<string />枚"), [_row(0, "<string />枚", "장")])


def test_import_cannot_mark_distribution_eligible_or_touch_keep_source():
    with pytest.raises(textdb.TranslationError, match="distribution_eligible"):
        textdb.import_rows(_store("決定"), [_row(0, "決定", "결정", state="distribution_eligible")])
    store = _store("ドン")
    store["entries"][0].update(state="distribution_eligible", keep_source="의성어")
    with pytest.raises(textdb.TranslationError, match="원문 유지"):
        textdb.import_rows(store, [_row(0, "ドン", "쿵")])


# --- release promotion ------------------------------------------------------------------

def _promo_store(*entries):
    return {"file": FILE, "entries": [dict(id=f"0x{i}", src_sha1="s", note="", **e)
                                      for i, e in enumerate(entries)]}


def test_promote_marks_reviewed_lines_eligible_and_keeps_placeholders_as_source():
    store = _promo_store(dict(ko="가", state="needs_review"), dict(ko="", state="untranslated"),
                   dict(ko="", state="distribution_eligible", keep_source="의성어"))
    out = textdb.promote(store, reviewed_by="GPT 검수", keep_reason="개발용 자리 문구")
    a, b, c = out["entries"]
    assert a["state"] == "distribution_eligible" and a["ko"] == "가"
    assert b["state"] == "distribution_eligible" and b["keep_source"] == "개발용 자리 문구"
    assert c == store["entries"][2]
    assert store["entries"][0]["state"] == "needs_review"  # input untouched
    assert "배포 승인: GPT 검수" in a["note"]


def test_promote_refuses_lines_still_waiting_for_a_person():
    store = _promo_store(dict(ko="가", state="needs_human_review"), dict(ko="", state="in_progress"))
    with pytest.raises(textdb.TranslationError, match="0x0.*\n.*0x1"):
        textdb.promote(store, reviewed_by="x", keep_reason="y")
