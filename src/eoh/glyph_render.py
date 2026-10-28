"""Rasterise glyphs from an outline font into tight 8-bit coverage bitmaps plus NFH metrics."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class Renderer:
    def __init__(self, path, size: int, index: int = 0, advance: int | None = None):
        self.font = ImageFont.truetype(str(path), size, index=index)
        self.size = size
        self.advance = advance  # fixed advance in px (full-width), or None for the font's own

    def render(self, ch: str):
        """Return (alpha HxW uint8, metrics) with metrics in 1/64 px, FreeType order."""
        pad = self.size
        canvas = Image.new("L", (self.size * 3, self.size * 3), 0)
        origin = (pad, pad * 2)  # left/baseline
        ImageDraw.Draw(canvas).text(origin, ch, font=self.font, fill=255, anchor="ls")
        advance = self.advance if self.advance is not None else round(self.font.getlength(ch))
        box = canvas.getbbox()
        if box is None:
            return np.zeros((0, 0), np.uint8), (0, 0, advance * 64, 0, 0, advance * 64)
        left, top, right, bottom = box
        alpha = np.array(canvas.crop(box))
        w, h = right - left, bottom - top
        metrics = ((left - origin[0]) * 64, (origin[1] - top) * 64, advance * 64,
                   -(w // 2) * 64, max(0, (advance - h) // 2) * 64, advance * 64)
        return alpha, metrics
