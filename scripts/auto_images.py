"""Draw the font-lettered Korean images (images.json maker "auto") with Source Han Serif.

    python3 scripts/auto_images.py          # -> translation/images_ko/, work/gpt/auto_미리보기.png

Each entry's `ko` (lines separated by "\\n") is drawn in the style matched from its PNG path
and fitted line by line into the original's text lines. Entries become needs_review.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from eoh import artfit, textart  # noqa: E402

MANIFEST = ROOT / "translation/images.json"
ORIGINALS = ROOT / "work/images"
KO_DIR = ROOT / "translation/images_ko"
OVERLAY_DIR = ROOT / "work/images_ko"  # derived from game art: never committed
PREVIEW = ROOT / "work/gpt/auto_미리보기.png"
FONT = ROOT / "fonts/SourceHanSerifKR-Heavy.otf"
ROUND = ROOT / "fonts/NanumSquareRoundB.ttf"  # SIL OFL, see fonts/NanumSquareRound-LICENSE.txt
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
STYLES = {  # PNG path fragment -> render options (sizes are font px before fitting)
    "adv_demo_title": dict(fill=WHITE, stroke=BLACK, stroke_ratio=0.06),
    "adv_chapter_end/00_": dict(fill=WHITE, stroke=BLACK, stroke_ratio=0.05),
    "cmn/jpn/cmn_txt/04_": dict(fill=((255, 255, 255), (255, 240, 40)), stroke=(230, 40, 220),
                                stroke_ratio=0.09, shadow=(18, 27, (20, 10, 20))),
    "adv_poker_txt/03_": "sample",
    "customize_txt/02_": dict(fill=WHITE, stroke=(150, 30, 180), stroke_ratio=0.1,
                              shadow=(10, 10, BLACK)),
}
FONTS = {"customize_txt/": ROUND}  # PNG path fragment -> font (gothic originals); else FONT
ALIGNS = {"customize_txt/": "left"}  # PNG path fragment -> line alignment; else center
_RIM = dict(stroke=(70, 48, 22), stroke_ratio=0.09, outer=(255, 255, 255), outer_ratio=0.05)
_SILVER = dict(_RIM, fill=((255, 255, 255), (140, 140, 150)))
_BLUE = dict(_RIM, fill=((255, 255, 240), (80, 200, 230)))
_GOLD = dict(_RIM, fill=((255, 250, 200), (225, 150, 40)))
# Lists whose lines each have their own colours (read off the original), one style per line.
LINE_STYLES = {"ui/adv/jpn/adv_poker_txt/18_tex18.png": [_SILVER] + [_BLUE] * 5 + [_GOLD] * 5}
INK, PAPER = (8, 8, 8), (255, 255, 255)
CESA_BG, CESA_RED, CESA_GREY = (239, 239, 239), (209, 79, 50), (123, 123, 123)
LABEL = (30, 30, 30)  # dark outline of the white UI labels
CLEAR = (0, 0, 0, 0)
OVERLAYS = {  # png -> font, erase [(rect, colour)], per `ko` line (box, fill, align[, stroke]) or
    # None for a line kept as in the original (English)
    "ui/boot/boot_logo/02_cautions.png": dict(font=FONT, erase=[
        ((176, 131, 309, 163), PAPER), ((455, 82, 1012, 118), PAPER), ((529, 115, 988, 151), PAPER),
        ((145, 490, 605, 527), PAPER), ((211, 521, 713, 559), PAPER), ((946, 464, 1144, 496), PAPER)],
        boxes=[((110, 138, 390, 156), INK, "center"), ((463, 89, 1100, 112), INK, "left"),
               ((537, 121, 1100, 144), INK, "left"), ((153, 497, 730, 520), INK, "left"),
               ((219, 528, 730, 552), INK, "left"), ((895, 471, 1185, 489), INK, "center")]),
    "ui/boot/boot_logo/04_cesa.png": dict(font=ROUND, erase=[((270, 105, 1015, 580), CESA_BG)],
        boxes=[((568, 115, 712, 164), CESA_RED, "center")]
              + [((288, y, 1000, y + 38), CESA_GREY, "left") for y in (199, 253, 306, 359, 480, 535)]),
    "ui/adv/jpn/adv_poker_txt/00_tex00.png": dict(font=FONT, erase=[
        ((27, 11, 64, 31), "above"), ((26, 51, 64, 71), "above"),
        ((129, 90, 166, 110), "above"), ((129, 130, 166, 150), "above")],
        boxes=[((28, 11, 110, 30), WHITE, "left", LABEL), ((27, 51, 110, 70), WHITE, "left", LABEL),
               ((80, 90, 165, 109), WHITE, "right", LABEL), ((80, 130, 165, 149), WHITE, "right", LABEL)]),
    "ui/adv/jpn/adv_poker_txt/23_tex23.png": dict(font=FONT, erase=[
        ((0, 39, 100, 68), CLEAR), ((0, 76, 100, 104), CLEAR), ((0, 112, 124, 139), CLEAR),
        ((123, 183, 224, 211), CLEAR), ((123, 219, 224, 248), CLEAR)],
        boxes=[None, ((1, 41, 160, 66), WHITE, "left", LABEL), ((2, 78, 160, 102), WHITE, "left", LABEL),
               ((2, 114, 200, 137), WHITE, "left", LABEL), None,
               ((50, 185, 222, 209), WHITE, "right", LABEL), ((50, 221, 222, 246), WHITE, "right", LABEL)]),
    "ui/adv/jpn/adv_poker_txt/24_tex24.png": dict(font=FONT, erase=[((6, 97, 300, 146), CLEAR)],
        boxes=[None, ((10, 100, 340, 142), WHITE, "left", LABEL), None]),
}
# Layers drawn as the black silhouette of another layer's text, at that layer's placement.
SILHOUETTES = {"ui/cmn/jpn/cmn_txt/05_tex05.png": "ui/cmn/jpn/cmn_txt/04_tex04.png"}


def style(png: str, orig: np.ndarray | None = None) -> dict:
    for key, opts in STYLES.items():
        if key in png:
            return textart.sample_style(orig) if opts == "sample" else opts
    raise SystemExit(f"{png}: 스타일 없음 (STYLES에 추가)")


def font_for(png: str) -> Path:
    return next((f for key, f in FONTS.items() if key in png), FONT)


def align_for(png: str) -> str:
    return next((a for key, a in ALIGNS.items() if key in png), "center")


def styled_lines(orig: np.ndarray, lines: list[str], styles: list[dict]) -> np.ndarray:
    boxes = artfit.row_boxes(orig, count=len(lines))
    arts = [textart.render(t, FONT, 160, **st) for t, st in zip(lines, styles)]
    return textart.compose(arts, orig.shape[1], orig.shape[0], boxes)


def silhouette(entry: dict, ref_png: str) -> np.ndarray:
    """Black text of entry['ko'] placed exactly like the (single-line) text of ref_png."""
    opts = style(ref_png)
    ref = textart.render(entry["ko"], FONT, 160, **opts)
    plain = textart.render(entry["ko"], FONT, 160, **dict(opts, fill=BLACK, stroke=BLACK, shadow=None))
    box = artfit.content_box(np.asarray(Image.open(ORIGINALS / ref_png).convert("RGBA")))
    return artfit.fit_like(plain, ref, entry["width"], entry["height"], box)


def repaint(orig: np.ndarray, lines: list[str], recipe: dict) -> np.ndarray:
    if len(lines) != len(recipe["boxes"]):
        raise SystemExit(f"줄 수 불일치: 한글 {len(lines)}줄, 상자 {len(recipe['boxes'])}개")
    texts = [dict(text=t, font=recipe["font"], box=b[0], fill=b[1], align=b[2],
                  stroke=b[3] if len(b) > 3 else None)
             for t, b in zip(lines, recipe["boxes"]) if b is not None]
    return textart.overlay(orig, recipe["erase"], texts)


def main() -> None:
    data = json.loads(MANIFEST.read_text("utf-8"))
    pairs = []
    for e in data["images"]:
        if e.get("maker") != "auto" or not e.get("ko"):
            continue
        orig = np.asarray(Image.open(ORIGINALS / e["png"]).convert("RGBA"))
        dst = KO_DIR / e["png"]
        if e["png"] in OVERLAYS:
            img, dst = repaint(orig, e["ko"].split("\n"), OVERLAYS[e["png"]]), OVERLAY_DIR / e["png"]
        elif e["png"] in SILHOUETTES:
            img = silhouette(e, SILHOUETTES[e["png"]])
        elif e["png"] in LINE_STYLES:
            img = styled_lines(orig, e["ko"].split("\n"), LINE_STYLES[e["png"]])
        else:
            lines = [textart.render(t, font_for(e["png"]), 160, **style(e["png"], orig))
                     for t in e["ko"].split("\n")]
            img = textart.compose(lines, e["width"], e["height"], textart.line_boxes(orig),
                                  align=align_for(e["png"]))
        dst.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(img, "RGBA").save(dst)
        e["state"] = "needs_review"
        pairs.append((orig, img))
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", "utf-8", newline="\n")
    w = max(o.shape[1] for o, _ in pairs)
    sheet = Image.new("RGBA", (w * 2 + 8, sum(o.shape[0] for o, _ in pairs)), (120, 40, 40, 255))
    y = 0
    for orig, ko in pairs:
        sheet.alpha_composite(Image.fromarray(orig, "RGBA"), (0, y))
        sheet.alpha_composite(Image.fromarray(ko, "RGBA"), (w + 8, y))
        y += orig.shape[0]
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(PREVIEW)
    print(f"생성 {len(pairs)}장, 미리보기: {PREVIEW}")


if __name__ == "__main__":
    main()
