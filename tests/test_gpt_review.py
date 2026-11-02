import pytest

from eoh import gpt_review

GLOSSARY = {"terms": [
    {"id": "T0001", "src": "承太郎", "category": "character", "ko": "죠타로", "alt": [],
     "state": "approved", "evidence": [], "note": ""},
    {"id": "T0002", "src": "ツェペリ", "category": "character", "ko": "체펠리", "alt": ["체펠리씨"],
     "state": "unresolved", "note": "[부분검증] 성만 확인",
     "evidence": [{"edition": "애니북스", "url": "u", "quote": f"q{i}"} for i in range(5)]},
]}


def test_term_jobs_lists_only_unresolved_terms_with_short_evidence():
    jobs = gpt_review.term_jobs(GLOSSARY)
    assert [j["id"] for j in jobs] == ["T0002"]
    assert jobs[0]["evidence"] == ["애니북스: q0", "애니북스: q1", "애니북스: q2"]
    assert jobs[0]["ko"] == "체펠리" and jobs[0]["note"] == "[부분검증] 성만 확인"


def test_approved_table_is_one_line_per_approved_term():
    assert gpt_review.approved_table(GLOSSARY) == "承太郎\t죠타로"


def test_line_jobs_take_needs_human_review_with_source_and_note():
    stores = {"EoH_battleChara_3jtr": {"entries": [
        {"id": "0x1", "ko": "가", "state": "needs_review", "note": ""},
        {"id": "0x2", "ko": "나", "state": "needs_human_review", "note": "초안(Claude). 말버릇"},
    ]}}
    sources = {("EoH_battleChara_3jtr", "0x2"): "やれやれだぜ"}
    assert gpt_review.line_jobs(stores, sources) == [
        {"file": "EoH_battleChara_3jtr", "id": "0x2", "src": "やれやれだぜ", "ko": "나",
         "note": "초안(Claude). 말버릇"}]


def test_chunks_split_evenly_in_order():
    assert gpt_review.chunks(list(range(5)), 2) == [[0, 1], [2, 3], [4]]


JOBS = [{"file": "F", "id": "0x1", "src": "やれやれ\nだぜ", "ko": "이거 참\n골치 아프군", "note": "초안(Claude)."},
        {"file": "F", "id": "0x2", "src": "<string />だ", "ko": "<string />다", "note": "초안(Claude)."}]


def test_line_rows_apply_fixes_and_record_the_review_in_the_note():
    results = [{"id": "0x1", "verdict": "수정", "ko": "야레야레\n다구", "reason": "정발 표기"},
               {"id": "0x2", "verdict": "유지", "reason": ""}]
    rows, problems, missing = gpt_review.line_rows(JOBS, results)
    assert problems == [] and missing == []
    assert rows["F"] == [
        {"id": "0x1", "src": "やれやれ\nだぜ", "ko": "야레야레\n다구", "state": "needs_review",
         "note": "초안(Claude). GPT 검수: 수정(정발 표기)"},
        {"id": "0x2", "src": "<string />だ", "ko": "<string />다", "state": "needs_review",
         "note": "초안(Claude). GPT 검수: 유지"}]


def test_line_rows_report_missing_unknown_bad_verdict_and_line_breaks():
    results = [{"id": "0x1", "verdict": "수정", "ko": "한 줄", "reason": ""},
               {"id": "0x9", "verdict": "유지"},
               {"id": "0x2", "verdict": "몰라"}]
    rows, problems, _ = gpt_review.line_rows(JOBS, results)
    assert rows == {}
    assert problems == ["0x1: 줄바꿈 수가 원문과 다름 (1 → 0)",
                        "0x9: 검수 묶음에 없는 항목",
                        "0x2: 판정은 유지/수정 중 하나여야 함 ('몰라')"]


def test_line_rows_leave_rows_without_a_result_unreviewed():
    rows, problems, missing = gpt_review.line_rows(JOBS, [{"id": "0x1", "verdict": "유지"}])
    assert problems == [] and missing == ["0x2"]
    assert [r["id"] for r in rows["F"]] == ["0x1"]


def test_term_review_records_proposal_but_keeps_terms_unresolved():
    results = [{"id": "T0002", "verdict": "수정", "ko": "체펠리", "reason": "정발 표기"}]
    out, problems = gpt_review.term_review(GLOSSARY, results)
    assert problems == []
    term = out["terms"][1]
    assert term["state"] == "unresolved"
    assert term["gpt_review"] == {"verdict": "수정", "ko": "체펠리", "reason": "정발 표기"}
    assert "gpt_review" not in GLOSSARY["terms"][1]  # input untouched


def test_term_review_rejects_approved_or_unknown_terms_and_bad_verdicts():
    results = [{"id": "T0001", "verdict": "승인"}, {"id": "T9999", "verdict": "승인"},
               {"id": "T0002", "verdict": "좋음"}]
    _, problems = gpt_review.term_review(GLOSSARY, results)
    assert problems == ["T0001: 검수 대상(미승인) 용어가 아님", "T9999: 검수 대상(미승인) 용어가 아님",
                        "T0002: 판정은 승인/수정/보류 중 하나여야 함 ('좋음')"]


def test_term_review_needs_a_spelling_for_fixes():
    _, problems = gpt_review.term_review(GLOSSARY, [{"id": "T0002", "verdict": "수정", "ko": ""}])
    assert problems == ["T0002: 수정인데 ko가 비어 있음"]


def test_parse_results_reads_jsonl_inside_a_code_fence():
    text = 'ok\n```json\n{"id": "0x1", "verdict": "유지"}\n\n{"id": "0x2", "verdict": "유지"}\n```\n'
    assert [r["id"] for r in gpt_review.parse_results(text)] == ["0x1", "0x2"]


def test_parse_results_reports_bad_json_line():
    with pytest.raises(ValueError, match="2번째 줄"):
        gpt_review.parse_results('{"id": "0x1"}\n{oops}\n')
