"""Extract the Japanese-only images (UI text art) to PNG and keep the image work list.

    python3 scripts/extract_images.py              # PNGs -> work/images/ (git-ignored)
    python3 scripts/extract_images.py --out DIR

Writes translation/images.json: one entry per texture (file, index, size, format, SHA-1 of
the official pixel data, category, PNG path, state, note, and optionally ko = the Korean text
and maker = gpt/auto). Re-running keeps state/note/ko/maker and
flags entries whose source texture changed. Game images themselves are never committed.
Contact sheets per category go to <out>/_overview/ for a quick look.
"""
import argparse
import hashlib
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image, ImageDraw  # noqa: E402

from eoh import font, texture  # noqa: E402
from eoh.layers import GameFs  # noqa: E402
from eoh.paths import DISC_SIM, PATCH_ROOT  # noqa: E402

MANIFEST = ROOT / "translation/images.json"
SKIP = ("/message/", "/sound/", "/param/")
CATEGORIES = {  # path group -> label (rough plan in HANDOVER 4-3)
    "ui/name": "캐릭터 이름", "ui/tips_cmn": "팁 화면", "ui/title": "타이틀 로고",
    "ui/adv": "스토리 UI", "ui/adv_demo": "스토리 연출", "ui/btl": "전투 연출",
    "save/PS3": "세이브 아이콘", "ui/boot": "부팅 화면",
}
EXTRA_FILES = ("data/ui/boot/boot_logo.xfbin",)  # Japanese text outside the /jpn/ folders
STATES = ("todo", "in_progress", "needs_review", "done", "keep_original")
KEPT = ("ko", "maker")  # hand-set fields kept across re-extraction (Korean text, who makes it)


def official_fs() -> GameFs:
    layers = [DISC_SIM / f"{n}.cpk" for n in ("data0", "data1", "dataRegion0", "dataRegion1")]
    for n in range(1, 6):
        p = PATCH_ROOT / str(n) / "data.cpk"
        backup = p.with_name(p.name + ".kr-backup")
        layers.append(backup if backup.exists() else p)
    return GameFs(layers)


def image_files(fs) -> list[str]:
    return [p for p in fs.paths()
            if p in EXTRA_FILES or
            ("/jpn/" in p or "/JP/" in p) and not any(s in p for s in SKIP) and p != font.JPN_FONT]


def category(path: str) -> str:
    group = "/".join(path.split("/")[1:3])
    return CATEGORIES.get(group, "UI 메뉴")


def texture_names(buf: bytes, count: int) -> list[str]:
    names = list(dict.fromkeys(m.decode() for m in re.findall(rb"[\w/.-]+\.nut", buf)))
    if len(names) == count:
        return [Path(n).stem for n in names]
    return [f"tex{i:02d}" for i in range(count)]


def contact_sheets(entries, out: Path) -> None:
    by_cat = defaultdict(list)
    for e in entries:
        by_cat[e["category"]].append(e)
    sheet_dir = out / "_overview"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    tw, th, cols = 256, 160, 6
    for i, (cat, items) in enumerate(sorted(by_cat.items())):
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * th), (40, 40, 40))
        draw = ImageDraw.Draw(sheet)
        for n, e in enumerate(items):
            im = Image.open(out / e["png"]).convert("RGBA")
            im.thumbnail((tw - 8, th - 24))
            x, y = (n % cols) * tw, (n // cols) * th
            bg = Image.new("RGBA", im.size, (90, 90, 90, 255))
            sheet.paste(Image.alpha_composite(bg, im).convert("RGB"), (x + 4, y + 4))
            draw.text((x + 4, y + th - 18), f"{n}: {Path(e['file']).stem}#{e['index']}", fill=(230, 230, 230))
        sheet.save(sheet_dir / f"{i:02d}.png")
        (sheet_dir / f"{i:02d}.txt").write_text(f"{cat}\n" + "\n".join(
            f"{n}: {e['png']}" for n, e in enumerate(items)) + "\n", "utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "work/images")
    args = ap.parse_args()
    fs = official_fs()
    old = {}
    if MANIFEST.exists():
        old = {(e["file"], e["index"]): e for e in json.loads(MANIFEST.read_text("utf-8"))["images"]}
    entries, changed = [], 0
    for path in image_files(fs):
        buf = fs.read(path)
        rel = Path(path.removeprefix("data/"))
        if path.upper().endswith(".PNG"):
            items = [(0, rel.stem, Image.open(io.BytesIO(buf)).convert("RGBA"), "PNG", buf)]
        else:
            texs = texture.find_textures(buf)
            names = texture_names(buf, len(texs))
            items = [(i, names[i], Image.fromarray(texture.decode(t), "RGBA"),
                      texture.FORMAT_NAMES[t.fmt], t.data) for i, t in enumerate(texs)]
        for index, name, im, fmt, raw in items:
            png = (rel.with_suffix("") / f"{index:02d}_{name}.png").as_posix()
            (args.out / png).parent.mkdir(parents=True, exist_ok=True)
            im.save(args.out / png)
            sha = hashlib.sha1(raw).hexdigest()
            prev = old.get((path, index), {})
            state, note = prev.get("state", "todo"), prev.get("note", "")
            if prev and prev.get("src_sha1") != sha:
                state, note, changed = "needs_review", (note + " 원본 텍스처 변경됨.").strip(), changed + 1
            entry = {"file": path, "index": index, "name": name, "width": im.width,
                     "height": im.height, "format": fmt, "src_sha1": sha,
                     "category": category(path), "png": png, "state": state, "note": note}
            entry.update({k: prev[k] for k in KEPT if k in prev})
            entries.append(entry)
    MANIFEST.write_text(json.dumps({
        "note": "이미지 한글화 대상 목록. PNG는 scripts/extract_images.py로 work/images/에 생성 (게임 리소스라 git 제외).",
        "states": list(STATES), "images": entries}, ensure_ascii=False, indent=1) + "\n", "utf-8", newline="\n")
    contact_sheets(entries, args.out)
    counts = defaultdict(int)
    for e in entries:
        counts[e["category"]] += 1
    print(f"{len(entries)} images from {len({e['file'] for e in entries})} files -> {args.out}")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {cat:10} {n}")
    if changed:
        print(f"원본이 바뀐 항목 {changed}개 → needs_review")


if __name__ == "__main__":
    main()
