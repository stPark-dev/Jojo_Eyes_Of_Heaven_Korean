"""Build the Korean patch files from the translation stores.

Applies every store to its message table (`textdb.apply`, dev or release policy), then adds
to the Japanese font atlas exactly the characters the applied Korean uses but the font
lacks. Only changed files are returned, ready for `merge.install` into patch/5.
"""
from eoh import font, message, textdb

MSG_DIR = "data/message/PS3/jpn/"
# Punctuation common in Korean text but missing from the Japanese font; drawn like Hangul.
EXTRA_CHARS = "~·"


class BuildError(Exception):
    pass


def build(fs, stores: dict, policy: str, renderer):
    """Return ([(path, bytes)], report). stores maps message path -> store."""
    files, used = [], set()
    report = {"files": 0, "applied": 0, "kept_source": 0, "glyphs": ""}
    for path in fs.paths():
        if not path.startswith(MSG_DIR):
            continue
        if path not in stores:
            raise BuildError(f"{path}: 번역 파일 없음 (textdb.py sync 필요)")
        mf = message.parse(fs.read(path))
        out, rep = textdb.apply(mf, stores[path], policy)
        report["applied"] += rep["applied"]
        report["kept_source"] += rep["kept_source"]
        if rep["applied"]:
            files.append((path, message.serialize(out)))
            by_hash = {e.hash: e.text for e in mf.entries}
            used.update(c for e in out.entries if e.text and e.text != by_hash[e.hash]
                        for c in e.text)
    if files:
        fnt = font.parse(fs.read(font.JPN_FONT))
        have = {chr(g.code) for g in fnt.glyphs}
        needed = sorted(c for c in used - have if not c.isspace())
        unsupported = [c for c in needed if not ("가" <= c <= "힣" or c in EXTRA_CHARS)]
        if unsupported:
            raise BuildError(f"폰트에 없고 한글도 아닌 글자: {unsupported}")
        if needed:
            fnt = font.add_glyphs(fnt, [(ord(c), *renderer.render(c)) for c in needed])
            files.append((font.JPN_FONT, font.serialize(fnt)))
        report["glyphs"] = "".join(needed)
    report["files"] = len(files)
    return files, report
