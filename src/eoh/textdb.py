"""Translation store for message tables.

One JSON store per message file, committed to the repo. It never contains source text
(copyrighted game script): each entry carries the SHA-1 of its source string instead, so a
changed source is detected and the translation is sent back for review.

Entry fields: id ("0x%08x" message hash), src_sha1, ko (Korean text, "" if none),
state (see STATES), note, and source_changed when the source moved under a translation.
"""
import copy
import hashlib
import re
from collections import Counter
from dataclasses import replace

from eoh.message import MessageFile

STATES = ("untranslated", "in_progress", "needs_review", "needs_human_review",
          "distribution_eligible")
_TAG = re.compile(r"</?[A-Za-z][^>]*>")


class TranslationError(Exception):
    pass


def tags(text: str) -> list[str]:
    return _TAG.findall(text)


def _is_ruby(tag: str) -> bool:
    return tag.startswith("<ruby") or tag == "</ruby>"


def check(src: str, ko: str) -> list[str]:
    """Mechanical checks: every non-ruby tag kept (any order), ruby balanced if used."""
    want = Counter(t for t in tags(src) if not _is_ruby(t))
    have = Counter(t for t in tags(ko) if not _is_ruby(t))
    problems = [f"태그 누락: {t}" for t in (want - have).elements()]
    problems += [f"원문에 없는 태그: {t}" for t in (have - want).elements()]
    ko_tags = tags(ko)
    if sum(t.startswith("<ruby") for t in ko_tags) != ko_tags.count("</ruby>"):
        problems.append("ruby 태그 짝이 맞지 않음")
    return problems


def _id(hash_: int) -> str:
    return f"0x{hash_:08x}"


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def sync(store, file: str, mf: MessageFile) -> dict:
    """Create or update a store against the current source; returns a new store."""
    old = {e["id"]: e for e in (store or {}).get("entries", [])}
    current = {_id(e.hash): e.text for e in mf.entries if e.text is not None}
    missing = sorted(set(old) - set(current))
    if missing:
        raise ValueError(f"{file}: 원문에서 사라진 항목 {missing[:5]}")
    entries = []
    for id_, text in current.items():
        sha = _sha1(text)
        if id_ not in old:
            entries.append({"id": id_, "src_sha1": sha, "ko": "", "state": "untranslated",
                            "note": ""})
            continue
        e = copy.deepcopy(old[id_])
        if e["src_sha1"] != sha:
            e.update(src_sha1=sha, source_changed=True)
            if e["ko"]:
                e["state"] = "needs_review"
        entries.append(e)
    return {"file": file, "entries": entries}


def apply(mf: MessageFile, store: dict, policy: str):
    """Return (MessageFile with Korean applied, report). policy: "dev" or "release"."""
    if policy not in ("dev", "release"):
        raise ValueError(policy)
    by_id = {e["id"]: e for e in store["entries"]}
    out, problems, applied, kept = [], [], 0, 0
    for entry in mf.entries:
        if entry.text is None:
            out.append(entry)
            continue
        id_ = _id(entry.hash)
        rec = by_id.get(id_)
        if rec is None:
            raise TranslationError(f"{id_}: 번역 파일에 없는 항목")
        if rec["state"] not in STATES:
            raise TranslationError(f"{id_}: 알 수 없는 상태 {rec['state']!r}")
        if rec["src_sha1"] != _sha1(entry.text):
            raise TranslationError(f"{id_}: 원문 지문 불일치 (원문이 바뀜, sync 필요)")
        if policy == "release" and (rec["state"] != "distribution_eligible" or not rec["ko"]):
            raise TranslationError(f"{id_}: 배포 가능 상태가 아닌 항목 ({rec['state']})")
        if not rec["ko"]:
            out.append(entry)
            kept += 1
            continue
        issues = check(entry.text, rec["ko"])
        problems += [f"{id_}: {p}" for p in issues]
        out.append(replace(entry, text=rec["ko"]))
        applied += 1
    if problems:
        raise TranslationError("\n".join(problems))
    return replace(mf, entries=out), {"applied": applied, "kept_source": kept, "problems": []}
