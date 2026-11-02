"""Swap a logo baked into a picture (save icon, save background) for the Korean logo.

The picture holds the original logo scaled by (sx, sy) at (x, y). Everything under the old logo
is inpainted from the picture around it (or cleared, on a picture with transparency), so no
old colour leaks into what the new logo leaves open; then the new logo is drawn at the same
placement.
"""
import cv2
import numpy as np

HOLE_ALPHA = 15


def _place(logo: np.ndarray, sx: float, sy: float, x: int, y: int, h: int, w: int) -> np.ndarray:
    t = cv2.resize(logo, (round(logo.shape[1] * sx), round(logo.shape[0] * sy)),
                   interpolation=cv2.INTER_AREA)
    out = np.zeros((h, w, 4), np.uint8)
    x1, y1 = min(w, x + t.shape[1]), min(h, y + t.shape[0])
    out[y:y1, x:x1] = t[:y1 - y, :x1 - x]
    return out


def _over(dst: np.ndarray, src: np.ndarray) -> np.ndarray:
    sa, da = src[..., 3:] / 255.0, dst[..., 3:] / 255.0
    a = sa + da * (1 - sa)
    rgb = (src[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(a, 1e-6)
    return np.concatenate([rgb, a * 255], -1).round().astype(np.uint8)


def swap(img: np.ndarray, old: np.ndarray, new: np.ndarray,
         sx: float, sy: float, x: int, y: int) -> np.ndarray:
    h, w = img.shape[:2]
    o, n = _place(old, sx, sy, x, y, h, w), _place(new, sx, sy, x, y, h, w)
    hole = cv2.dilate((o[..., 3] > HOLE_ALPHA).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    base = img.copy()
    if (img[..., 3] < 255).any():
        base[hole] = 0
    else:
        base[..., :3] = cv2.inpaint(np.ascontiguousarray(img[..., :3]), hole.astype(np.uint8) * 255,
                                    5, cv2.INPAINT_TELEA)
    return _over(base, n)
