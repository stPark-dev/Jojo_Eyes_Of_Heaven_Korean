"""Glossary consistency checks against translation/glossary.json.

Only approved terms are enforced. A term found in the source (longest match first, so
"ジョセフ・ジョースター" is not also counted as "ジョセフ") must appear in the Korean text with
its approved spelling, unless an exception for the entry's scope allows another spelling.
Superseded spellings (alt) in the Korean text are reported when the term is in the source.
"""
from pathlib import Path

_MASK = "\0"


def approved(g: dict) -> list[dict]:
    terms = [t for t in g["terms"] if t.get("state") == "approved" and t.get("ko")]
    return sorted(terms, key=lambda t: len(t["src"]), reverse=True)


def _allowed(term: dict, scope: str | None) -> list[str]:
    spellings = [term["ko"]]
    for ex in term.get("exceptions", []):
        if scope is not None and ex.get("scope") in (scope, scope.split(":")[0]):
            spellings.append(ex["ko"])
    return spellings


def check(src: str, ko: str, terms: list[dict], scope: str | None = None) -> list[str]:
    if not ko:
        return []
    problems = []
    for term in terms:
        if term["src"] not in src:
            continue
        src = src.replace(term["src"], _MASK)
        allowed = _allowed(term, scope)
        if not any(s in ko for s in allowed):
            problems.append(f"용어 불일치: {term['src']} → '{term['ko']}' 없음")
        for alias in term.get("alt", []):
            if alias in ko and not any(alias in s for s in allowed):
                problems.append(f"별칭 표기 사용: '{alias}' → '{term['ko']}'")
    return problems


def check_store(store: dict, sources: dict[str, str], terms: list[dict]):
    """sources: entry id -> source text. Returns [(scope, problem)]."""
    stem = Path(store["file"]).name.removesuffix(".bin.xfbin")
    out = []
    for e in store["entries"]:
        scope = f"{stem}:{e['id']}"
        for p in check(sources.get(e["id"], ""), e.get("ko", ""), terms, scope=scope):
            out.append((scope, p))
    return out
