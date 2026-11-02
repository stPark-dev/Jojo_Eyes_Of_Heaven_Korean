"""Rewrite small text inside screenshots (tip pictures) without a clean background to copy.

Each item names a rect around one line of original text. The text pixels inside it are found
by an Otsu threshold (light text, dark text, or colour difference from the rect border),
inpainted away, and the Korean line (or a ready-made art piece) is drawn at the same height,
in the text's own colour, against the line's left, right or centre.
"""
from pathlib import Path

import cv2
import numpy as np

from eoh import artfit, textart

STROKE_RATIO = 0.05


def retext(img: np.ndarray, items: list[dict], font: Path) -> np.ndarray:
    """items: dict(rect, text | art, align="left"|"right"|"center", polarity="light"|"dark"|"diff",
    fill=None (sampled), stroke=fill colour (fattens), clip=False (keep height, run past
    the rect and get cut at the picture edge instead of shrinking), within=lum (only erase on the
    bright balloon of pixels above that luminance))."""
    out = img.copy()
    for item in items:
        out = _one(out, item, font)
    return out


def _feature(reg: np.ndarray, polarity: str) -> np.ndarray:
    if polarity == "light":
        return reg.mean(-1)
    if polarity == "dark":
        return 255 - reg.mean(-1)
    border = np.concatenate([reg[0], reg[-1], reg[:, 0], reg[:, -1]])
    return np.linalg.norm(reg - np.median(border, 0), axis=-1).clip(0, 255)


def _text_mask(reg: np.ndarray, polarity: str) -> tuple[np.ndarray, np.ndarray, float]:
    """(text pixels by Otsu, feature, Otsu threshold)"""
    feat = _feature(reg, polarity)
    t, _ = cv2.threshold(np.rint(feat).astype(np.uint8), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return feat > t, feat, t


def _one(out: np.ndarray, item: dict, font: Path) -> np.ndarray:
    x0, y0, x1, y1 = item["rect"]
    polarity = item.get("polarity", "light")
    reg = out[y0:y1, x0:x1, :3].astype(np.float64)
    mask, feat, t = _text_mask(reg, polarity)
    if "within" in item:  # only text on a bright balloon: drop the dark scene around it
        bright = (reg.mean(-1) > item["within"]).astype(np.uint8)
        balloon = cv2.morphologyEx(bright, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8),
                                   borderType=cv2.BORDER_CONSTANT, borderValue=0).astype(bool)
        mask &= balloon
    ys, xs = np.nonzero(mask)
    if not len(ys):
        raise ValueError(f"{item['rect']}: 글자 없음")
    gx0, gx1, gy0, gy1 = x0 + xs.min(), x0 + xs.max() + 1, y0 + ys.min(), y0 + ys.max() + 1
    core = mask & (feat >= np.median(feat[mask]))
    fill = item.get("fill") or tuple(int(v) for v in np.median(reg[core], 0))

    # the text's outline / drop shadow: opposite-tone pixels hugging the text
    near = cv2.dilate(mask.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    bg = np.median(feat[~mask]) if (~mask).any() else 0
    halo = near & (feat < bg - 25)
    fringe = near & (feat > bg + 0.35 * (t - bg))  # anti-aliased edges below the Otsu cut
    if "within" in item:
        halo &= balloon
        fringe &= balloon
    full = np.zeros(out.shape[:2], np.uint8)
    full[y0:y1, x0:x1] = (mask | halo | fringe) * 255
    full = cv2.dilate(full, np.ones((3, 3), np.uint8))
    out = out.copy()
    out[..., :3] = cv2.inpaint(np.ascontiguousarray(out[..., :3]), full, 3, cv2.INPAINT_TELEA)

    if "art" in item:
        art = artfit._crop(item["art"])
    else:
        stroke = item.get("stroke", fill)  # default: fattened in its own colour, like the UI font
        art = textart.render(item["text"], font, 160, fill, stroke, STROKE_RATIO)
    h, w = art.shape[:2]
    scale = (gy1 - gy0) / h
    if not item.get("clip") and w * scale > x1 - x0:
        scale = (x1 - x0) / w
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    align = item.get("align", "left")
    x = gx0 if align == "left" else gx1 - nw if align == "right" else round((gx0 + gx1 - nw) / 2)
    if not item.get("clip"):
        x = min(max(x, x0), x1 - nw)
    y = round((gy0 + gy1 - nh) / 2)
    pad = max(nw, nh) + 1  # lets the art start left of / above the picture and be cut there
    H, W = out.shape[:2]
    layer = artfit._paste(art, W + 2 * pad, H + 2 * pad, scale, x + pad, y + pad)[pad:-pad, pad:-pad]
    textart._over(out, layer)
    return out
