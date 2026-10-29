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
}
INK, PAPER = (8, 8, 8), (255, 255, 255)
CESA_BG, CESA_RED, CESA_GREY = (239, 239, 239), (209, 79, 50), (123, 123, 123)
OVERLAYS = {  # png -> font, erase [(rect, rgb)], one box per `ko` line (box, fill, align)
    "ui/boot/boot_logo/02_cautions.png": dict(font=FONT, erase=[
        ((176, 131, 309, 163), PAPER), ((455, 82, 1012, 118), PAPER), ((529, 115, 988, 151), PAPER),
        ((145, 490, 605, 527), PAPER), ((211, 521, 713, 559), PAPER), ((946, 464, 1144, 496), PAPER)],
        boxes=[((110, 138, 390, 156), INK, "center"), ((463, 89, 1100, 112), INK, "left"),
               ((537, 121, 1100, 144), INK, "left"), ((153, 497, 730, 520), INK, "left"),
               ((219, 528, 730, 552), INK, "left"), ((895, 471, 1185, 489), INK, "center")]),
    "ui/boot/boot_logo/04_cesa.png": dict(font=ROUND, erase=[((270, 105, 1015, 580), CESA_BG)],
        boxes=[((568, 115, 712, 164), CESA_RED, "center")]
              + [((288, y, 1000, y + 38), CESA_GREY, "left") for y in (199, 253, 306, 359, 480, 535)]),
}
# Layers drawn as the black silhouette of another layer's text, at that layer's placement.
SILHOUETTES = {"ui/cmn/jpn/cmn_txt/05_tex05.png": "ui/cmn/jpn/cmn_txt/04_tex04.png"}


def style(png: str) -> dict:
    for key, opts in STYLES.items():
        if key in png:
            return opts
    raise SystemExit(f"{png}: 스타일 없음 (STYLES에 추가)")


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
    texts = [dict(text=t, font=recipe["font"], box=box, fill=fill, align=align)
             for t, (box, fill, align) in zip(lines, recipe["boxes"])]
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
        else:
            lines = [textart.render(t, FONT, 160, **style(e["png"])) for t in e["ko"].split("\n")]
            img = textart.compose(lines, e["width"], e["height"], textart.line_boxes(orig))
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
