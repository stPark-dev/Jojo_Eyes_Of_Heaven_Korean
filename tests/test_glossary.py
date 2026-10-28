from eoh import glossary


def _g(*terms):
    base = {"alt": [], "exceptions": [], "state": "approved"}
    return {"terms": [dict(base, id=f"T{i:04d}", **t) for i, t in enumerate(terms, 1)]}


JOSEPH = {"src": "ジョセフ", "ko": "죠셉"}
JOSEPH_FULL = {"src": "ジョセフ・ジョースター", "ko": "죠셉 죠스타"}
PILLAR = {"src": "柱の男", "ko": "기둥 속 사내", "alt": ["기둥의 남자"]}


def test_approved_terms_only():
    g = _g(JOSEPH, dict(PILLAR, state="unresolved"))
    assert [t["src"] for t in glossary.approved(g)] == ["ジョセフ"]


def test_missing_term_is_reported():
    problems = glossary.check("ジョセフが来た", "조셉이 왔다", glossary.approved(_g(JOSEPH)))
    assert problems == ["용어 불일치: ジョセフ → '죠셉' 없음"]


def test_present_term_passes():
    assert glossary.check("ジョセフが来た", "죠셉이 왔다", glossary.approved(_g(JOSEPH))) == []


def test_longest_match_wins_over_contained_term():
    terms = glossary.approved(_g(JOSEPH, JOSEPH_FULL))
    assert glossary.check("ジョセフ・ジョースターだ", "죠셉 죠스타다", terms) == []
    assert glossary.check("ジョセフ・ジョースターだ", "죠셉이다", terms) == \
        ["용어 불일치: ジョセフ・ジョースター → '죠셉 죠스타' 없음"]


def test_alias_spelling_is_flagged():
    problems = glossary.check("柱の男たち", "기둥 속 사내들, 기둥의 남자", glossary.approved(_g(PILLAR)))
    assert problems == ["별칭 표기 사용: '기둥의 남자' → '기둥 속 사내'"]


def test_scoped_exception_allows_other_spelling():
    dio = {"src": "ＤＩＯ", "ko": "DIO",
           "exceptions": [{"scope": "messageInfo_adv:0x00000001", "ko": "디오", "reason": "1부 회상"}]}
    terms = glossary.approved(_g(dio))
    assert glossary.check("ＤＩＯ様", "디오 님", terms, scope="messageInfo_adv:0x00000001") == []
    assert glossary.check("ＤＩＯ様", "디오 님", terms, scope="messageInfo_adv:0x00000002") == \
        ["용어 불일치: ＤＩＯ → 'DIO' 없음"]


def test_untranslated_entry_is_not_checked():
    assert glossary.check("ジョセフ", "", glossary.approved(_g(JOSEPH))) == []


def test_check_store_reports_entry_ids():
    store = {"file": "data/message/PS3/jpn/messageInfo_common.bin.xfbin",
             "entries": [{"id": "0x00000001", "ko": "조셉"}, {"id": "0x00000002", "ko": "죠셉"}]}
    sources = {"0x00000001": "ジョセフ", "0x00000002": "ジョセフ"}
    out = glossary.check_store(store, sources, glossary.approved(_g(JOSEPH)))
    assert out == [("messageInfo_common:0x00000001", "용어 불일치: ジョセフ → '죠셉' 없음")]


def test_src_exclude_skips_longer_words_containing_the_term():
    mista = {"src": "ミスタ", "ko": "미스타", "src_exclude": ["ミスター"]}
    terms = glossary.approved(_g(mista))
    assert glossary.check("ミスター・プレジデント", "미스터 프레지던트", terms) == []
    assert glossary.check("ミスタとミスター", "미스터와", terms) == ["용어 불일치: ミスタ → '미스타' 없음"]
