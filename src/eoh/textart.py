"""Draw Korean text art with a font (for images that use plain lettering, not hand drawing).

render draws one line (solid or top-to-bottom gradient fill, optional outline) cropped to
its pixels; line_boxes finds the text lines of an original texture; compose fits each
rendered line into the matching line box of the original; overlay repaints parts of a
picture (erase rectangles, then text fitted into boxes) for art that keeps its background.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from eoh import artfit


def render(text: str, font: Path, size: int, fill, stroke=None, stroke_ratio: float = 0.08,
           shadow=None, outer=None, outer_ratio: float = 0.04) -> np.ndarray:
    """fill: (r, g, b) or ((top rgb), (bottom rgb)). shadow: (dx, dy, (r, g, b)) in font px.

    outer: a second rim of that colour around the stroke (outer_ratio of the font size).
    """
    f = ImageFont.truetype(str(font), size)
    sw = round(size * stroke_ratio) if stroke else 0
    ow = sw + max(1, round(size * outer_ratio)) if outer else sw
    pad = ow + size // 4 + (max(abs(shadow[0]), abs(shadow[1])) if shadow else 0)
    l, t, r, b = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=f, stroke_width=ow)
    w, h = r - l + 2 * pad, b - t + 2 * pad
    origin = (pad - l, pad - t)

    def mask(stroke_width):
        m = Image.new("L", (w, h))
        ImageDraw.Draw(m).text(origin, text, font=f, fill=255, stroke_width=stroke_width, stroke_fill=255)
        return np.asarray(m).astype(np.float64) / 255

    inner, ring = mask(0), mask(sw)
    if isinstance(fill[0], (tuple, list)):
        rows = np.nonzero(inner.any(1))[0]
        k = np.clip((np.arange(h) - rows[0]) / max(rows[-1] - rows[0], 1), 0, 1)[:, None, None]
        colour = np.array(fill[0]) * (1 - k) + np.array(fill[1]) * k
        colour = np.broadcast_to(colour, (h, w, 3))
    else:
        colour = np.broadcast_to(np.array(fill, np.float64), (h, w, 3))
    edge = np.broadcast_to(np.array(stroke or (0, 0, 0), np.float64), (h, w, 3))
    rgb = colour * inner[..., None] + edge * (1 - inner[..., None])
    alpha = ring
    if outer:
        rim = mask(ow)
        rgb = rgb * ring[..., None] + np.array(outer, np.float64) * (1 - ring[..., None])
        alpha = rim
    if shadow:
        dx, dy, sc = shadow
        sh = np.roll(np.roll(alpha, dy, 0), dx, 1)
        rgb = rgb * alpha[..., None] + np.array(sc, np.float64) * (sh * (1 - alpha))[..., None]
        alpha = alpha + sh * (1 - alpha)
        rgb = rgb / np.maximum(alpha[..., None], 1e-9)
    img = np.zeros((h, w, 4), np.uint8)
    img[..., :3] = np.clip(np.rint(rgb), 0, 255)
    img[..., 3] = np.clip(np.rint(alpha * 255), 0, 255)
    x0, y0, x1, y1 = artfit.content_box(img)
    return img[y0:y1, x0:x1]


def _depth(mask: np.ndarray, limit: int = 24) -> np.ndarray:
    """How many 4-neighbour erosions each mask pixel survives (1 = on the edge)."""
    depth = np.zeros(mask.shape, np.int32)
    cur = mask.copy()
    for d in range(1, limit + 1):
        if not cur.any():
            break
        depth[cur] = d
        p = np.pad(cur, 1)
        cur = cur & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return depth


def sample_style(img: np.ndarray) -> dict:
    """Guess render options (gradient fill, outline colour and width) from original text art.

    The outline is the ring of pixels at the edge of the opaque shape; the fill starts at the
    first depth whose colour clearly differs from it. Fill top/bottom are the mean colours of
    the top and bottom quarter of the fill.
    """
    mask = img[..., 3] > 200
    depth = _depth(mask)
    rgb = img[..., :3].astype(np.float64)
    ring = [rgb[depth == d].mean(0) if (depth == d).any() else None for d in range(depth.max() + 1)]

    def change(start, ref):  # first depth from start whose colour clearly differs from ref
        d = start
        while d < depth.max() and np.abs(ring[d] - ref).max() < 60:
            d += 1
        return d

    ys = np.nonzero(mask.any(1))[0]
    height = ys[-1] - ys[0] + 1
    edge = np.median(rgb[depth == 1], 0)
    inner = change(2, edge)
    extra = {}
    if edge.mean() > 200 and inner < depth.max() and ring[inner].mean() < edge.mean() - 100:
        rim_w, edge = inner - 1, ring[inner]  # bright rim around a dark outline
        start = inner
        inner = change(inner + 1, edge)
        extra = dict(outer=tuple(int(v) for v in np.rint(np.median(rgb[depth == 1], 0))),
                     outer_ratio=max(0.02, rim_w / height))
        sw = inner - start
    else:
        sw = inner - 1
    fill = depth >= inner
    if not fill.any():
        fill = mask
    rows = np.nonzero(fill.any(1))[0]
    q = max(1, (rows[-1] - rows[0] + 1) // 4)
    top = rgb[fill & (np.arange(len(fill))[:, None] < rows[0] + q)].mean(0)
    bottom = rgb[fill & (np.arange(len(fill))[:, None] > rows[-1] - q)].mean(0)
    return dict(fill=(tuple(int(v) for v in np.rint(top)), tuple(int(v) for v in np.rint(bottom))),
                stroke=tuple(int(v) for v in np.rint(edge)),
                stroke_ratio=min(0.15, max(0.04, sw / height)), **extra)


def line_boxes(img: np.ndarray, max_gap: int = 6) -> list[tuple[int, int, int, int]]:
    """(left, top, right, bottom) of each text line of an RGBA image, top to bottom."""
    solid = img[..., 3] > artfit.ALPHA_MIN
    out = []
    for y0, y1 in artfit._runs(solid.any(1), max_gap):
        xs = np.nonzero(solid[y0:y1].any(0))[0]
        out.append((int(xs.min()), int(y0), int(xs.max()) + 1, int(y1)))
    return out


def compose(lines: list[np.ndarray], width: int, height: int, boxes, align: str = "center") -> np.ndarray:
    if len(lines) != len(boxes):
        raise ValueError(f"줄 수 불일치: 글자 {len(lines)}줄, 원본 {len(boxes)}줄")
    out = np.zeros((height, width, 4), np.uint8)
    for art, box in zip(lines, boxes):
        _over(out, artfit.fit(art, width, height, box, align=align))
    return out


def _over(out: np.ndarray, layer: np.ndarray) -> None:
    a = layer[..., 3:] / 255
    out[..., :3] = np.rint(layer[..., :3] * a + out[..., :3] * (1 - a))
    out[..., 3] = np.maximum(out[..., 3], layer[..., 3])


def overlay(base: np.ndarray, erase=(), texts=()) -> np.ndarray:
    """Copy of base with each (rect, rgb) erase filled, then each text drawn into its box.

    A text is dict(text, font, box, fill, stroke=None, stroke_ratio, align="center").
    """
    out = base.copy()
    for (x0, y0, x1, y1), colour in erase:  # rgb, rgba (sets transparency) or "above"
        if colour == "above":  # repeat the row above: hides text on horizontal gradients
            out[y0:y1, x0:x1] = out[y0 - 1, x0:x1]
        else:
            out[y0:y1, x0:x1, :len(colour)] = colour
    h, w = out.shape[:2]
    for t in texts:
        art = render(t["text"], t["font"], 160, t["fill"], t.get("stroke"),
                     t.get("stroke_ratio", 0.08))
        _over(out, artfit.fit(art, w, h, t["box"], align=t.get("align", "center")))
    return out
