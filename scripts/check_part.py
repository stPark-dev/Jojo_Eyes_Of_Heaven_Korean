"""Check a translated work part against its input chunk (rules: translation/STYLE.md).

    python3 -I scripts/check_part.py work/translate/chunks/X.jsonl work/translate/parts/X.jsonl
    python3 -I scripts/check_part.py --tsv work/translate/glossary.tsv   # term list for translators

Reports missing/reordered rows, changed src, tag problems, line-break count, state/note
format and approved-glossary violations. Exit status 1 when anything is wrong.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eoh import glossary, textdb  # noqa: E402

GLOSSARY = ROOT / "translation/glossary.json"
STATES = {"needs_review", "needs_human_review"}


def write_tsv(path) -> None:
    g = json.loads(GLOSSARY.read_text("utf-8"))
    lines = ["id\tsrc\tko\tstate\tnote"]
    for t in g["terms"]:
        ex = "; ".join(f"{e['scope']}: {e['ko']}" for e in t.get("exceptions", []))
        lines.append(f"{t['id']}\t{t['src']}\t{t['ko']}\t{t['state']}\t{ex}")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", "utf-8")
    print(f"{len(g['terms'])} terms -> {path}")


def check(inp, out) -> list[str]:
    src_rows = [json.loads(l) for l in Path(inp).read_text("utf-8").splitlines() if l.strip()]
    try:
        out_rows = [json.loads(l) for l in Path(out).read_text("utf-8").splitlines() if l.strip()]
    except json.JSONDecodeError as e:
        return [f"JSON 오류: {e}"]
    terms = glossary.approved(json.loads(GLOSSARY.read_text("utf-8")))
    problems = []
    if len(out_rows) != len(src_rows):
        problems.append(f"건수 불일치: 입력 {len(src_rows)}, 출력 {len(out_rows)}")
    for i, (a, b) in enumerate(zip(src_rows, out_rows)):
        tag = f"{i + 1}행 {a['id']}"
        if b.get("id") != a["id"]:
            problems.append(f"{tag}: id 순서 불일치 (출력 {b.get('id')})")
            continue
        if b.get("src") != a["src"]:
            problems.append(f"{tag}: src가 입력과 다름")
        ko = b.get("ko", "")
        if not ko:
            problems.append(f"{tag}: ko 비어 있음")
            continue
        if b.get("state") not in STATES:
            problems.append(f"{tag}: state {b.get('state')!r}")
        if not str(b.get("note", "")).startswith("초안(Claude)."):
            problems.append(f"{tag}: note가 '초안(Claude).'로 시작하지 않음")
        problems += [f"{tag}: {p}" for p in textdb.check(a["src"], ko)]
        if ko.count("\n") != a["src"].count("\n"):
            problems.append(f"{tag}: 줄바꿈 수 {ko.count(chr(10))} (원문 {a['src'].count(chr(10))})")
        problems += [f"{tag}: {p}" for p in glossary.check(a["src"], ko, terms)]
    human = sum(r.get("state") == "needs_human_review" for r in out_rows)
    problems_summary = f"문제 {len(problems)}건 / 출력 {len(out_rows)}행 (needs_human_review {human})"
    return problems + [problems_summary]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) == 3 and sys.argv[1] == "--tsv":
        write_tsv(sys.argv[2])
        return
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    lines = check(*sys.argv[1:3])
    print("\n".join(lines))
    sys.exit(0 if lines[-1].startswith("문제 0건") else 1)


if __name__ == "__main__":
    main()
