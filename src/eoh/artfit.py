"""Turn generated art (e.g. ChatGPT sheets) into texture-sized RGBA images.

A sheet holds several lines of text art stacked vertically on a transparent or solid
magenta (#FF00FF) background. remove_background makes the magenta transparent, split_rows
cuts one image per line, and fit scales a line into the original texture's text box.
"""
import numpy as np
from PIL import Image

ALPHA_MIN = 32  # alpha at or below this counts as background when looking for content


def remove_background(img: np.ndarray) -> np.ndarray:
    """RGB or RGBA -> RGBA. Real transparency is kept; otherwise magenta is keyed out.

    A pixel is taken as foreground F blended over magenta: P = a*F + (1-a)*(255, 0, 255).
    With the art's dark outline at the edges, a = 1 - min(R, B)/255 + G/255 (clipped).
    """
    if img.shape[2] == 4 and (img[..., 3] < 255).any():
        return img.copy()
    p = img[..., :3].astype(np.float64)
    a = np.clip(1 - np.minimum(p[..., 0], p[..., 2]) / 255 + p[..., 1] / 255, 0, 1)
    key = np.array([255.0, 0, 255.0])
    f = np.where(a[..., None] > 0, (p - (1 - a[..., None]) * key) / np.maximum(a[..., None], 1e-9), 0)
    out = np.zeros(img.shape[:2] + (4,), np.uint8)
    out[..., :3] = np.clip(np.rint(f), 0, 255)
    out[..., 3] = np.floor(a * 255 + 1e-6)
    return out


def _runs(mask: np.ndarray, max_gap: int) -> list[tuple[int, int]]:
    """Index ranges [start, end) of True values, joining gaps up to max_gap."""
    idx = np.nonzero(mask)[0]
    if not len(idx):
        return []
    runs, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev > max_gap + 1:
            runs.append((start, prev + 1))
            start = i
        prev = i
    runs.append((start, prev + 1))
    return runs


def content_box(img: np.ndarray) -> tuple[int, int, int, int]:
    """(left, top, right, bottom) of the pixels with alpha above ALPHA_MIN."""
    solid = img[..., 3] > ALPHA_MIN
    ys, xs = np.nonzero(solid)
    if not len(ys):
        raise ValueError("빈 이미지")
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def split_rows(img: np.ndarray, max_gap: int = 8, count: int | None = None) -> list[np.ndarray]:
    """Cut a sheet into its text lines, each cropped to its content; specks are dropped.

    Without count, rows closer than max_gap belong to one line. With count, the smallest
    gaps are joined until exactly count lines remain (lines may sit almost touching).
    """
    solid = img[..., 3] > ALPHA_MIN
    rows = _runs(solid.any(1), 0 if count else max_gap)
    weight = [int(solid[a:b].sum()) for a, b in rows]
    rows = [r for r, w in zip(rows, weight) if w >= 0.005 * max(weight)] if rows else []
    if count:
        while len(rows) > count:
            i = min(range(len(rows) - 1), key=lambda k: rows[k + 1][0] - rows[k][1])
            rows[i:i + 2] = [(rows[i][0], rows[i + 1][1])]
    else:
        heights = [b - a for a, b in rows]
        rows = [r for r, h in zip(rows, heights) if h >= 0.25 * max(heights)] if rows else []
    parts = []
    for y0, y1 in rows:
        band = img[y0:y1]
        x0, t, x1, b = content_box(band)
        parts.append(band[t:b, x0:x1])
    return parts


def _crop(art: np.ndarray) -> np.ndarray:
    x0, t, x1, b = content_box(art)
    return art[t:b, x0:x1]


def _placement(art: np.ndarray, width: int, height: int, box, margin: int):
    """(scale, x, y) that fit cropped art to the box height within width - 2*margin."""
    h, w = art.shape[:2]
    left, top, right, bottom = box
    scale = min((bottom - top) / h, (width - 2 * margin) / w)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    x, y = round((left + right) / 2 - nw / 2), round((top + bottom) / 2 - nh / 2)
    return scale, min(max(x, margin), width - margin - nw), min(max(y, 0), height - nh)


def fit(art: np.ndarray, width: int, height: int, box, margin: int = 4) -> np.ndarray:
    """Scale art (cropped RGBA) to the box height, within width - 2*margin, centred in box."""
    art = _crop(art)
    return _paste(art, width, height, *_placement(art, width, height, box, margin))


def fit_like(art: np.ndarray, ref: np.ndarray, width: int, height: int, box,
             margin: int = 4) -> np.ndarray:
    """Place art with the scale and top-left that fit() would give ref (e.g. a shadow layer)."""
    return _paste(_crop(art), width, height, *_placement(_crop(ref), width, height, box, margin))


def _paste(art: np.ndarray, width: int, height: int, scale: float, x: int, y: int) -> np.ndarray:
    h, w = art.shape[:2]
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    im = Image.fromarray(art, "RGBA")
    # resize premultiplied so the transparent background colour does not bleed into edges
    pre = np.asarray(im).astype(np.float64)
    pre[..., :3] *= pre[..., 3:] / 255
    small = np.stack([np.asarray(Image.fromarray(pre[..., c].astype(np.float32), "F")
                                 .resize((nw, nh), Image.LANCZOS)) for c in range(4)], -1)
    small = np.clip(small, 0, 255)
    rgb = np.where(small[..., 3:] > 0, small[..., :3] * 255 / np.maximum(small[..., 3:], 1e-9), 0)
    cw, ch = min(nw, width - x), min(nh, height - y)  # a reference-sized layer may overhang
    out = np.zeros((height, width, 4), np.uint8)
    out[y:y + ch, x:x + cw, :3] = np.clip(np.rint(rgb[:ch, :cw]), 0, 255)
    out[y:y + ch, x:x + cw, 3] = np.rint(small[:ch, :cw, 3])
    return out
