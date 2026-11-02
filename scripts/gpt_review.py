"""Hand the open review work to ChatGPT (web) and bring its verdicts back.

    python3 scripts/textdb.py export           # refresh work/translate/*.jsonl first (source text)
    python3 scripts/gpt_review.py pack  용어|문장
    python3 scripts/gpt_review.py apply 용어|문장

pack writes work/gpt/검수/<kind>/NN/프롬프트.txt (self-contained: rules, approved terms, the
batch). Paste it into ChatGPT and save its JSON lines as 결과.jsonl next to the prompt.
apply reads every 결과.jsonl present and checks it as a whole before writing anything:
용어 -> translation/glossary.json gpt_review (terms stay unresolved),
문장 -> translation/*.json (needs_review, verdict in the note).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eoh import gpt_review, textdb  # noqa: E402

STORE_DIR = ROOT / "translation"
GLOSSARY = STORE_DIR / "glossary.json"
STYLE = STORE_DIR / "STYLE.md"
WORK = ROOT / "work/translate"
OUT = ROOT / "work/gpt/검수"
BATCH = {"용어": 60, "문장": 120}
STYLE_SECTIONS = ("2.", "3.", "4.", "6.", "7.", "8.")  # 1·5 are Claude's own work process

LINE_PROMPT = """당신은 『죠죠의 기묘한 모험』 한국어 번역 검수자입니다. 게임: PS3 『죠죠의 기묘한 모험 아이즈 오브 헤븐』(격투 액션).
아래 [입력]의 각 줄은 일본어 원문(src), Claude가 만든 한국어 초안(ko), 초안 메모(note)입니다. file은 출처(스토리·전투 대사·캐릭터 코드)입니다.
note에 적힌 확인 사항을 중심으로, 문장 전체를 검수하세요.

# 검수 기준
- 오역·누락·어색한 한국어, 캐릭터 말투(정발 만화·국내 애니 기준), 유명 대사·말버릇의 정발 표기.
- 태그(<...>)는 개수 그대로, 줄바꿈(\\n) 수는 원문과 같게, 한 줄이 원문 줄보다 눈에 띄게 길지 않게.
- 의성어·효과음(ゴゴゴ, ドドド 등)은 일본어 그대로 둡니다.
- 고유명사는 [승인 용어] 표기를 따릅니다. 승인 용어에 없는 고유명사의 표기는 따로 검수 중이니 바꾸지 말고, 의견이 있으면 reason에 적으세요.
- 정발 표기를 확실히 모르면 지어내지 말고 유지하세요(reason에 "정발 미확인").

# 출력 (반드시 지킬 것)
[입력]의 모든 id에 대해 입력 순서대로 한 줄씩, JSON Lines 코드 블록 하나로만 답하세요. 다른 설명은 쓰지 마세요.
{{"id": "0x…", "verdict": "유지", "reason": "한 문장(없으면 빈 문자열)"}}
{{"id": "0x…", "verdict": "수정", "ko": "고친 번역문 전체", "reason": "무엇을 왜 고쳤는지 한 문장"}}
줄바꿈은 JSON 문자열 안에서 \\n으로 씁니다. 줄이 {count}개여야 합니다. 다 못 쓰면 이어서 쓰라고 할 테니 끊긴 곳부터 이어 쓰세요.

# 번역 지침
{style}

# 승인 용어 (일본어<TAB>한국어)
{approved}

# 입력 ({count}줄)
{rows}
"""

TERM_PROMPT = """『죠죠의 기묘한 모험』 고유명사의 한국어 표기를 검수해 주세요. 게임 한글 패치(PS3 『아이즈 오브 헤븐』)의 용어집입니다.

# 표기 기준 (우선순위)
{policy}

# 할 일
[입력]의 각 용어(src=일본어, ko=현재 후보, alt=다른 표기, evidence=지금까지 모은 근거, note=메모)에 대해:
- 승인: 현재 ko가 정발 표기와 맞음
- 수정: 정발 표기가 다름 → ko에 바른 표기
- 보류: 정발 근거를 확인하지 못함
웹 검색을 할 수 있으면 정발판(애니북스·문학동네 단행본, 국내 애니 자막)을 찾아 확인하고, reason에 근거(판본·권/화·출처 URL)를 적으세요.
근거 없이 추측으로 승인하지 마세요. 확인 못 하면 보류입니다.

# 출력 (반드시 지킬 것)
모든 id에 대해 입력 순서대로 한 줄씩, JSON Lines 코드 블록 하나로만 답하세요.
{{"id": "T0000", "verdict": "승인|수정|보류", "ko": "최종 표기", "reason": "근거"}}
줄이 {count}개여야 합니다.

# 입력 ({count}개)
{rows}
"""


def load(path: Path):
    return json.loads(path.read_text("utf-8"))


def style_text() -> str:
    parts = re.split(r"(?m)^## ", STYLE.read_text("utf-8"))[1:]
    return "\n".join("## " + p.strip() + "\n" for p in parts if p.startswith(STYLE_SECTIONS))


def stores() -> dict:
    return {p.stem: load(p) for p in sorted(STORE_DIR.glob("*.json"))
            if p.name not in ("glossary.json", "images.json")}


def sources() -> dict:
    out = {}
    for path in WORK.glob("*.jsonl"):
        for line in path.read_text("utf-8").splitlines():
            row = json.loads(line)
            out[(path.stem, row["id"])] = row["src"]
    return out


def jsonl(rows) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)


def write_batches(kind: str, batches: list, prompt) -> None:
    for n, batch in enumerate(batches, 1):
        d = OUT / kind / f"{n:02d}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "프롬프트.txt").write_text(prompt(batch), "utf-8")
        (d / "묶음.jsonl").write_text(jsonl(batch) + "\n", "utf-8")
    print(f"{kind}: {sum(map(len, batches))}개 → {len(batches)}묶음 ({OUT / kind})")


def cmd_pack(kind: str) -> None:
    g = load(GLOSSARY)
    if kind == "용어":
        policy = "\n".join(f"- {v}" if isinstance(v, str) else "\n".join(f"- {x}" for x in v)
                           for k, v in g["policy"].items() if k != "decided")
        batches = gpt_review.chunks(gpt_review.term_jobs(g), BATCH[kind])
        write_batches(kind, batches, lambda b: TERM_PROMPT.format(
            policy=policy, count=len(b), rows=jsonl(b)))
        return
    style, approved = style_text(), gpt_review.approved_table(g)
    jobs = gpt_review.line_jobs(stores(), sources())
    if len({j["id"] for j in jobs}) != len(jobs):  # GPT answers by id alone
        sys.exit("여러 파일에 같은 id가 있어 id만으로 결과를 가를 수 없음")
    batches = gpt_review.chunks(jobs, BATCH[kind])
    write_batches(kind, batches, lambda b: LINE_PROMPT.format(
        style=style, approved=approved, count=len(b), rows=jsonl(b)))


def results(kind: str):
    """(batch jobs, GPT results) for every batch that has a 결과.jsonl."""
    jobs, rows, done = [], [], 0
    for d in sorted((OUT / kind).glob("[0-9][0-9]")):
        res = d / "결과.jsonl"
        if not res.exists():
            continue
        try:
            rows += gpt_review.parse_results(res.read_text("utf-8"))
        except ValueError as e:
            sys.exit(f"{res}: {e}")
        jobs += [json.loads(x) for x in (d / "묶음.jsonl").read_text("utf-8").splitlines()]
        done += 1
    if not done:
        sys.exit(f"{OUT / kind}: 결과.jsonl 없음")
    print(f"{kind}: 결과 {done}묶음, {len(rows)}줄")
    return jobs, rows


def cmd_apply(kind: str) -> None:
    jobs, rows = results(kind)
    if kind == "용어":
        g, problems = gpt_review.term_review(load(GLOSSARY), rows)
        missing = {j["id"] for j in jobs} - {r.get("id") for r in rows}
        problems += [f"{i}: 결과에 없음" for i in sorted(missing)]
        if problems:
            sys.exit("반영 안 함\n" + "\n".join(problems))
        GLOSSARY.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", "utf-8")
        verdicts = [t["gpt_review"]["verdict"] for t in g["terms"] if "gpt_review" in t]
        print({v: verdicts.count(v) for v in gpt_review.TERM_VERDICTS})
        return
    by_file, problems, missing = gpt_review.line_rows(jobs, rows)
    if problems:
        sys.exit("반영 안 함\n" + "\n".join(problems))
    updated = {}
    for stem, file_rows in by_file.items():  # check every file before writing any
        try:
            updated[stem], _ = textdb.import_rows(load(STORE_DIR / f"{stem}.json"), file_rows)
        except textdb.TranslationError as e:
            sys.exit(f"{stem}: 반영 안 함\n{e}")
    for stem, store in updated.items():
        (STORE_DIR / f"{stem}.json").write_text(
            json.dumps(store, ensure_ascii=False, indent=1) + "\n", "utf-8")
    fixes = sum(r.get("verdict") == "수정" for r in rows)
    print(f"반영 {len(rows)}문장 (수정 {fixes}, 유지 {len(rows) - fixes})")
    if missing:
        print(f"결과 없음(검수 안 된 채로 둠) {len(missing)}: {' '.join(missing)}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("pack", "apply") or sys.argv[2] not in BATCH:
        sys.exit(__doc__)
    {"pack": cmd_pack, "apply": cmd_apply}[sys.argv[1]](sys.argv[2])
