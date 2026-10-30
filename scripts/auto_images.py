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
    "btl_cmn_txt/11_": "sample",
}
_SUBTITLE = dict(fill=WHITE, stroke=(150, 30, 180), stroke_ratio=0.1, shadow=(10, 10, BLACK))
_MENU = ("customize_txt/", "gallery_txt/", "freebtl_txt/", "shop_txt/")  # purple subtitles
STYLES.update({key: _SUBTITLE for key in _MENU})
# PNG path fragment -> font (gothic originals) / line alignment; else FONT / center
FONTS = {key: ROUND for key in _MENU + ("supportitem_menu_txt/", "btl_cmn_txt/11_")}
ALIGNS = {key: "left" for key in _MENU}
_RIM = dict(stroke=(70, 48, 22), stroke_ratio=0.09, outer=(255, 255, 255), outer_ratio=0.05)
_SILVER = dict(_RIM, fill=((255, 255, 255), (140, 140, 150)))
_BLUE = dict(_RIM, fill=((255, 255, 240), (80, 200, 230)))
_GOLD = dict(_RIM, fill=((255, 250, 200), (225, 150, 40)))
# Lists whose lines each have their own colours (read off the original), one style per line.
LINE_STYLES = {
    "ui/adv/jpn/adv_poker_txt/18_tex18.png": [_SILVER] + [_BLUE] * 5 + [_GOLD] * 5,
    "ui/supportitem_menu/jpn/supportitem_menu_txt/01_supportitem_menu_target_txt.png": [
        dict(fill=((235, 250, 255), (150, 220, 255)), stroke=(1, 32, 132), stroke_ratio=0.1),
        dict(fill=((255, 235, 235), (255, 170, 175)), stroke=(140, 4, 8), stroke_ratio=0.1)],
}
INK, PAPER = (8, 8, 8), (255, 255, 255)
CESA_BG, CESA_RED, CESA_GREY = (239, 239, 239), (209, 79, 50), (123, 123, 123)
LABEL = (30, 30, 30)  # dark outline of the white UI labels
CLEAR = (0, 0, 0, 0)
OVERLAYS = {  # png -> font, erase [(rect, colour)], per `ko` line (box, fill, align[, stroke[, render options]]) or
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
_CMDLIST = "ui/commandlist/jpn/commandlist_text/{:02d}_commandlist_txt_icon{:02d}.png"
_TAGS = {0: (64, (247, 255, 123)), 1: (44, (208, 121, 255)), 2: (44, (123, 255, 156)),  # n: (width,
         3: (44, (255, 190, 132)), 4: (60, (123, 223, 255)), 5: (60, (255, 130, 132)),  # colour)
         6: (60, (148, 130, 255)), 7: (128, (255, 134, 222)), 8: (64, (239, 255, 123)),
         9: (64, (214, 127, 255)), 10: (64, (231, 251, 115)), 11: (112, (255, 190, 123)),
         12: (60, (123, 223, 255)), 13: (80, (255, 130, 132))}
for n, (w, rgb) in _TAGS.items():  # move-list tags: keep the glowing frame, rewrite the label
    OVERLAYS[_CMDLIST.format(n, n)] = dict(font=ROUND, erase=[((7, 8, w - 7, 23), rgb + (22,))],
                                           boxes=[((8, 9, w - 8, 22), rgb, "contain")])
_RED, _CYAN, _DARK = (255, 0, 57), (0, 170, 220), (8, 8, 8)
_HEAVY = dict(stroke_ratio=0.04, outer=BLACK, outer_ratio=0.09)  # fill-coloured stroke fattens the font
OVERLAYS.update({
    "ui/cmn/jpn/cmn_txt/06_tex06.png": dict(font=ROUND, erase=[
        ((46, 0, 170, 43), CLEAR), ((46, 46, 140, 82), CLEAR)],
        boxes=[((50, 4, 200, 38), _RED, "left", _DARK), ((50, 49, 170, 80), _CYAN, "left", _DARK)]),
    "ui/online/jpn/online_txt/00_tex00.png": dict(font=ROUND, erase=[
        ((43, 8, 135, 44), CLEAR), ((44, 50, 170, 96), CLEAR)],
        boxes=[((45, 12, 160, 40), _CYAN, "left", _DARK), ((46, 55, 220, 91), (255, 0, 0), "left", _DARK)]),
    "ui/gauge/jpn/gauge_text/02_gauge_support_retire.png": dict(font=ROUND, erase=[
        ((48, 12, 146, 37), (0, 0, 0, 44))], boxes=[((51, 14, 143, 35), WHITE, "contain", _DARK)]),
    "ui/supportitem_menu/jpn/supportitem_menu_txt/00_supportitem_menu_status_txt.png": dict(
        font=ROUND, erase=[((30, 0, 180, 80), ("tile", 0, 30))],
        boxes=[((20, 6, 160, 35), WHITE, "contain", (8, 113, 198)),
               ((20, 46, 160, 75), WHITE, "contain", (178, 24, 24))]),
    # 「特殊」 is red in the original line 2, so that line is two pieces
    "ui/btlsel/vscmn/jpn/vscmn_txt/03_vscmn_txt_dha_title.png": dict(font=ROUND, erase=[
        ((0, 0, 648, 144), CLEAR)],
        boxes=[((150, 6, 498, 42), WHITE, "contain", WHITE, _HEAVY),
               ((148, 54, 222, 91), (255, 0, 0), "right", (255, 0, 0), _HEAVY),
               ((228, 54, 500, 91), WHITE, "left", WHITE, _HEAVY),
               ((150, 102, 498, 138), WHITE, "contain", WHITE, _HEAVY)]),
})
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


def styled_lines(orig: np.ndarray, lines: list[str], styles: list[dict], font: Path) -> np.ndarray:
    boxes = artfit.row_boxes(orig, count=len(lines))
    arts = [textart.render(t, font, 160, **st) for t, st in zip(lines, styles)]
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
                  stroke=b[3] if len(b) > 3 else None, **(b[4] if len(b) > 4 else {}))
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
            img = styled_lines(orig, e["ko"].split("\n"), LINE_STYLES[e["png"]], font_for(e["png"]))
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
