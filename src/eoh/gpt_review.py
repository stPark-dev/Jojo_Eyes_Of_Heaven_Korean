"""Hand the open review work (unresolved glossary terms, needs_human_review lines) to ChatGPT
and read its verdicts back.

Lines: GPT answers 유지 (keep) or 수정 (fixed ko). The result goes back as needs_review with the
verdict appended to the note; promoting to distribution_eligible stays a separate decision.
Terms: GPT answers 승인/수정/보류 with a spelling; it is stored as the term's gpt_review and the
term stays unresolved until a human approves it.
"""
import copy
import json

LINE_VERDICTS = ("유지", "수정")
TERM_VERDICTS = ("승인", "수정", "보류")
EVIDENCE_PER_TERM = 3


def term_jobs(glossary: dict) -> list[dict]:
    return [{"id": t["id"], "src": t["src"], "category": t["category"], "ko": t["ko"],
             "alt": t.get("alt", []), "note": t.get("note", ""),
             "evidence": [f"{e['edition']}: {e['quote']}"
                          for e in t.get("evidence", [])[:EVIDENCE_PER_TERM]]}
            for t in glossary["terms"] if t.get("state") == "unresolved"]


def approved_table(glossary: dict) -> str:
    return "\n".join(f"{t['src']}\t{t['ko']}" for t in glossary["terms"]
                     if t.get("state") == "approved")


def line_jobs(stores: dict, sources: dict) -> list[dict]:
    """stores: file stem -> translation store; sources: (stem, id) -> source text."""
    return [{"file": stem, "id": e["id"], "src": sources[(stem, e["id"])], "ko": e["ko"],
             "note": e.get("note", "")}
            for stem, store in stores.items() for e in store["entries"]
            if e["state"] == "needs_human_review"]


def chunks(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _verdict_note(note: str, verdict: str, reason: str) -> str:
    tail = f"GPT 검수: {verdict}" + (f"({reason})" if reason else "")
    return f"{note} {tail}".strip()


def line_rows(jobs: list[dict], results: list[dict]):
    """Returns ({file stem: import rows}, problems, ids without a result); no rows at all if
    anything is wrong. Lines GPT did not answer stay as they are (still unreviewed)."""
    by_id = {j["id"]: j for j in jobs}
    seen, problems, fixed = set(), [], {}
    for r in results:
        id_, verdict = r.get("id"), r.get("verdict")
        job = by_id.get(id_)
        if job is None:
            problems.append(f"{id_}: 검수 묶음에 없는 항목")
            continue
        seen.add(id_)
        if verdict not in LINE_VERDICTS:
            problems.append(f"{id_}: 판정은 유지/수정 중 하나여야 함 ({verdict!r})")
            continue
        ko = r.get("ko") if verdict == "수정" else job["ko"]
        if not ko:
            problems.append(f"{id_}: 수정인데 ko가 비어 있음")
            continue
        if ko.count("\n") != job["src"].count("\n"):
            problems.append(f"{id_}: 줄바꿈 수가 원문과 다름 "
                            f"({job['src'].count(chr(10))} → {ko.count(chr(10))})")
            continue
        fixed[id_] = (ko, _verdict_note(job["note"], verdict, r.get("reason", "")))
    missing = [j["id"] for j in jobs if j["id"] not in seen]
    if problems:
        return {}, problems, missing
    rows = {}
    for j in jobs:
        if j["id"] in missing:
            continue
        ko, note = fixed[j["id"]]
        rows.setdefault(j["file"], []).append(
            {"id": j["id"], "src": j["src"], "ko": ko, "state": "needs_review", "note": note})
    return rows, [], missing


def term_review(glossary: dict, results: list[dict]):
    """Returns (glossary copy with gpt_review on each answered term, problems)."""
    out = copy.deepcopy(glossary)
    open_terms = {t["id"]: t for t in out["terms"] if t.get("state") == "unresolved"}
    problems = []
    for r in results:
        id_, verdict = r.get("id"), r.get("verdict")
        term = open_terms.get(id_)
        if term is None:
            problems.append(f"{id_}: 검수 대상(미승인) 용어가 아님")
            continue
        if verdict not in TERM_VERDICTS:
            problems.append(f"{id_}: 판정은 승인/수정/보류 중 하나여야 함 ({verdict!r})")
            continue
        ko = r.get("ko") if verdict == "수정" else r.get("ko") or term["ko"]
        if not ko:
            problems.append(f"{id_}: 수정인데 ko가 비어 있음")
            continue
        term["gpt_review"] = {"verdict": verdict, "ko": ko, "reason": r.get("reason", "")}
    return out, problems


def parse_results(text: str) -> list[dict]:
    """JSON lines as GPT gives them: code fences and blank lines are skipped."""
    rows = []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"{n}번째 줄: JSON 오류 ({e.msg})") from None
    return rows
