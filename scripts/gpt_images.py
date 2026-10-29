"""Hand image art jobs to ChatGPT (web) and bring the results back into the patch.

    python3 scripts/gpt_images.py pack  캐릭터_이름   # work/gpt/<category>/: prompts + reference
    python3 scripts/gpt_images.py apply 캐릭터_이름   # out/sheet_NN.png -> translation/images_ko/
    python3 scripts/gpt_images.py place <result.png> <images.json png> [--glow 16]
        # one whole image; --glow adds the soft outer halo the title logo has (radius px)

pack groups the distinct Korean texts (images.json `ko`, maker "gpt") of a category into
sheets of SHEET_SIZE lines. For each sheet ChatGPT draws the lines stacked vertically on a
transparent (or #FF00FF) background; save its PNG as work/gpt/<category>/out/sheet_NN.png.
apply cuts every sheet into lines, checks the line count, fits each line into the text box
of every original texture using that text, writes the Korean PNGs, and marks the entries
needs_review. A preview (original | Korean) is written for checking.

Entries may name a `gpt_group`: lines of one style share sheets in work/gpt/<category>/<group>/
(STYLES[group]). Group "단독" gets one job per image (work/gpt/<category>/단독/NN_name/:
the original enlarged and a prompt; save ChatGPT's picture there as 결과.png).
An entry's `ko` lines are its pieces top to bottom; an image with several pieces (an atlas
the game crops) gets each piece fitted inside the matching piece box of the original.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
from PIL import Image, ImageFilter  # noqa: E402

from eoh import artfit, textart  # noqa: E402

MANIFEST = ROOT / "translation/images.json"
ORIGINALS = ROOT / "work/images"
KO_DIR = ROOT / "translation/images_ko"
GPT_DIR = ROOT / "work/gpt"
SHEET_SIZE = 6
STYLES = {
    "캐릭터 이름": "흰색의 굵은 마커/붓 손글씨. 획 끝이 거칠고 약간 기울어진 역동적인 필체. "
                 "글자 전체를 두꺼운 검은 테두리(획 굵기의 절반 정도)가 감싼다. "
                 "그림자, 그라데이션, 장식, 배경 무늬는 넣지 않는다.",
    "메뉴 제목": "굵은 붓/마커 손글씨. 글자 안쪽은 왼쪽 위 밝은 연두색에서 오른쪽 아래 파란색으로 "
              "변하는 그라데이션, 획 가장자리에 얇은 흰 하이라이트, 바깥은 두꺼운 검은 테두리와 "
              "그 바깥의 얇은 흰 테두리. 약간 기울어진 역동적인 필체.",
    "관중 함성": "작고 통통한 손글씨 외침 글자. 줄마다 색이 다름(1줄 파랑, 2줄 초록, 3줄 주황, "
              "4줄 분홍, 5줄 자홍). 흰 테두리와 얇은 검은 바깥 테두리, 약간 기울어짐.",
}
SINGLE = "단독"
SINGLE_PROMPT = """첨부한 이미지(원본_2배.png)는 게임 「죠죠의 기묘한 모험 아이즈 오브 헤븐」의 화면 글자입니다.
이 이미지의 일본어만 아래 한글로 바꿔 주세요. 영어, 그림, 색, 테두리, 효과, 각 조각의 위치와 크기는 원본 그대로.
조각 {count}개 (위에서 아래 순서, 원본과 같은 순서·같은 간격):
{lines}
배경: 완전 투명 PNG. 투명이 안 되면 다른 것 없이 단색 자홍색(#FF00FF).
캔버스: 원본과 같은 비율({w}×{h}). 글자 철자를 바꾸지 말 것.
"""
PROMPT = """첨부한 이미지는 일본 게임 「죠죠의 기묘한 모험 아이즈 오브 헤븐」의 {category} 글자 스타일입니다.
같은 스타일로 아래 한글 {count}줄을 그려 주세요.

스타일: {style}
배치: 세로로 긴 캔버스(1024×1536). 한 줄에 하나씩, 위에서 아래로 {count}줄. 줄 사이를 넉넉히 띄워 서로 겹치지 않게.
각 줄은 가운데 정렬, 줄바꿈 없이 한 줄로. 모든 줄의 글자 크기는 같게.
배경: 완전 투명 PNG. 투명이 안 되면 다른 것 없이 단색 자홍색(#FF00FF).
글자는 아래와 정확히 같게 (철자·띄어쓰기·괄호·숫자·영문을 바꾸지 말 것):
{lines}
"""


def load() -> dict:
    return json.loads(MANIFEST.read_text("utf-8"))


def save(data: dict) -> None:
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", "utf-8", newline="\n")


def jobs(data: dict, category: str) -> list[dict]:
    return [e for e in data["images"] if e["category"] == category and e.get("maker") == "gpt"]


def group_of(entry: dict) -> str:
    return entry.get("gpt_group", entry["category"])


def group_dir(out: Path, category: str, group: str) -> Path:
    return out if group == category else out / group


def single_dir(out: Path, index: int, entry: dict) -> Path:
    first = entry["ko"].split("\n")[0].split(" (")[0]
    safe = "".join(c for c in first if c not in '/\\:*?"<>|').strip()
    return out / SINGLE / f"{index:02d}_{safe}"


def cmd_pack(category: str, out: Path) -> None:
    entries = jobs(load(), category)
    if not entries:
        raise SystemExit(f"{category}: maker=gpt 항목 없음")
    groups: dict[str, list[dict]] = {}
    for e in entries:
        groups.setdefault(group_of(e), []).append(e)
    for group, members in groups.items():
        if group == SINGLE:
            for i, e in enumerate(members):
                _pack_single(single_dir(out, i, e), e)
            print(f"{SINGLE} {len(members)}장: {out / SINGLE}")
            continue
        _pack_sheets(group_dir(out, category, group), group, members)
    print("각 시트·폴더의 txt 내용과 참고 이미지를 ChatGPT에 넣고 결과를 저장")


def _pack_sheets(out: Path, group: str, entries: list[dict]) -> None:
    texts = list(dict.fromkeys(t for e in entries for t in e["ko"].split("\n")))
    sheets = [texts[i:i + SHEET_SIZE] for i in range(0, len(texts), SHEET_SIZE)]
    (out / "out").mkdir(parents=True, exist_ok=True)
    _reference(entries[:3]).save(out / "참고_원본스타일.png")
    for n, lines in enumerate(sheets):
        (out / f"sheet_{n:02d}.txt").write_text(PROMPT.format(
            category=group, count=len(lines), style=STYLES.get(group, ""),
            lines="\n".join(f"{i}. {t}" for i, t in enumerate(lines, 1))), "utf-8")
    (out / "sheets.json").write_text(json.dumps(sheets, ensure_ascii=False, indent=1), "utf-8")
    print(f"{group}: {len(texts)}개 표기 → 시트 {len(sheets)}장: {out}")


def _pack_single(out: Path, entry: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    im = Image.open(ORIGINALS / entry["png"]).convert("RGBA")
    im.resize((im.width * 2, im.height * 2), Image.LANCZOS).save(out / "원본_2배.png")
    lines = entry["ko"].split("\n")
    (out / "프롬프트.txt").write_text(SINGLE_PROMPT.format(
        count=len(lines), lines="\n".join(f"{i}. {t}" for i, t in enumerate(lines, 1)),
        w=im.width * 2, h=im.height * 2), "utf-8")


def _reference(entries) -> Image.Image:
    ims = [Image.open(ORIGINALS / e["png"]).convert("RGBA") for e in entries]
    w, h = max(i.width for i in ims), sum(i.height for i in ims)
    sheet = Image.new("RGBA", (w, h), (70, 70, 70, 255))
    y = 0
    for im in ims:
        sheet.alpha_composite(im, ((w - im.width) // 2, y))
        y += im.height
    return sheet


def _sheet_cuts(out: Path, problems: list) -> dict:
    cuts = {}
    if not (out / "sheets.json").exists():
        return cuts
    for n, lines in enumerate(json.loads((out / "sheets.json").read_text("utf-8"))):
        path = out / "out" / f"sheet_{n:02d}.png"
        if not path.exists():
            continue
        parts = _cut(path, len(lines))
        if len(parts) != len(lines):
            problems.append(f"{path}: 줄 {len(parts)}개, 필요 {len(lines)}개")
            continue
        cuts.update(zip(lines, parts))
    return cuts


def _cut(path: Path, count: int) -> list[np.ndarray]:
    sheet = artfit.remove_background(np.asarray(Image.open(path).convert("RGBA")))
    return artfit.split_rows(sheet, count=count)


def _render(entry: dict, pieces: list[np.ndarray], orig: np.ndarray) -> np.ndarray:
    if len(pieces) == 1:
        return artfit.fit(pieces[0], entry["width"], entry["height"], artfit.content_box(orig))
    boxes = artfit.row_boxes(orig, count=len(pieces))
    return textart.compose(pieces, entry["width"], entry["height"], boxes, align="contain")


def cmd_apply(category: str, out: Path) -> None:
    data = load()
    entries = jobs(data, category)
    problems, cuts, singles = [], {}, 0
    for group in {group_of(e) for e in entries} - {SINGLE}:
        cuts.update(_sheet_cuts(group_dir(out, category, group), problems))
    done = []
    for i, e in enumerate([e for e in entries if group_of(e) == SINGLE]):
        result = single_dir(out, i, e) / "결과.png"
        lines = e["ko"].split("\n")
        if result.exists():
            parts = _cut(result, len(lines))
            if len(parts) != len(lines):
                problems.append(f"{result}: 조각 {len(parts)}개, 필요 {len(lines)}개")
                continue
            e["_pieces"] = parts
            singles += 1
    for e in entries:
        lines = e["ko"].split("\n")
        pieces = e.pop("_pieces", None) or ([cuts[t] for t in lines] if all(t in cuts for t in lines) else None)
        if pieces is None:
            continue
        orig = np.asarray(Image.open(ORIGINALS / e["png"]).convert("RGBA"))
        img = _render(e, pieces, orig)
        dst = KO_DIR / e["png"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(img, "RGBA").save(dst)
        e["state"] = "needs_review"
        done.append((orig, img))
    save(data)
    if done:
        _preview(done).save(out / "미리보기.png")
    print(f"반영 {len(done)}장 (시트 표기 {len(cuts)}개, 단독 {singles}장), 미리보기: {out / '미리보기.png'}")
    for p in problems:
        print("  확인 필요:", p)


def _preview(pairs) -> Image.Image:
    w = max(o.shape[1] for o, _ in pairs)
    h = sum(o.shape[0] for o, _ in pairs)
    sheet = Image.new("RGBA", (w * 2 + 8, h), (70, 70, 70, 255))
    y = 0
    for orig, ko in pairs:
        sheet.alpha_composite(Image.fromarray(orig, "RGBA"), (0, y))
        sheet.alpha_composite(Image.fromarray(ko, "RGBA"), (w + 8, y))
        y += orig.shape[0]
    return sheet


GLOW_RGB, GLOW_GAIN, GLOW_MAX = (254, 254, 218), 1.8, 200  # measured on the original logo halo


def add_glow(img: np.ndarray, radius: int) -> np.ndarray:
    solid = Image.fromarray(((img[..., 3] > 128) * 255).astype(np.uint8))
    glow = np.clip(np.asarray(solid.filter(ImageFilter.GaussianBlur(radius))) * GLOW_GAIN, 0, GLOW_MAX) / 255
    a = img[..., 3:] / 255
    out_a = a[..., 0] + glow * (1 - a[..., 0])
    rgb = (img[..., :3] * a + np.array(GLOW_RGB) * (glow * (1 - a[..., 0]))[..., None]) \
        / np.maximum(out_a[..., None], 1e-9)
    out = np.zeros_like(img)
    out[..., :3] = np.clip(np.rint(rgb), 0, 255)
    out[..., 3] = np.rint(out_a * 255)
    return out


def cmd_place(result: Path, png: str, glow: int = 0) -> None:
    """A whole generated image (same aspect as the texture) scaled to the texture size."""
    data = load()
    entry = next((e for e in data["images"] if e["png"] == png), None)
    if entry is None:
        raise SystemExit(f"{png}: images.json에 없음")
    art = artfit.remove_background(np.asarray(Image.open(result).convert("RGBA")))
    w, h = entry["width"], entry["height"]
    if abs(art.shape[1] / art.shape[0] - w / h) > 0.01 * w / h:
        raise SystemExit(f"비율이 다름: {art.shape[1]}x{art.shape[0]}, 필요 {w}x{h}")
    img = artfit._paste(art, w, h, w / art.shape[1], 0, 0)
    if glow:
        img = add_glow(img, glow)
    dst = KO_DIR / png
    dst.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img, "RGBA").save(dst)
    entry.update(state="needs_review", maker="gpt")
    save(data)
    print(f"저장: {dst}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["pack", "apply", "place"])
    ap.add_argument("category", help="images.json 분류 (공백은 _ 로), place는 결과 PNG")
    ap.add_argument("png", nargs="?", help="place: images.json의 png 경로")
    ap.add_argument("--glow", type=int, default=0, help="place: 바깥 빛 번짐 반경(px)")
    args = ap.parse_args()
    if args.command == "place":
        cmd_place(Path(args.category), args.png, args.glow)
        return
    category = args.category.replace("_", " ")
    out = GPT_DIR / args.category
    {"pack": cmd_pack, "apply": cmd_apply}[args.command](category, out)


if __name__ == "__main__":
    main()
