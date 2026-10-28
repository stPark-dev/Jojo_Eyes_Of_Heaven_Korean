"""NTP3 textures inside .xfbin files and DXT1/DXT5 decoding to RGBA.

NTP3 block (big-endian): 'NTP3', u16 0x0100, u16 texture count, 8 bytes pad, then per
texture a header (u32 total size, u32 0, u32 data size, u16 header size, u16 0, u8 0,
u8 mip count, u8 0, u8 format, u16 width, u16 height, ...) followed by its data.
Formats seen in the game's images: 0 = DXT1, 2 = DXT5. DXT blocks are standard
little-endian BC1/BC3 blocks in row-major block order (see dxt5.py).
"""
import struct
from dataclasses import dataclass

import numpy as np

from eoh import dxt5

DXT1, DXT5 = 0, 2
FORMAT_NAMES = {DXT1: "DXT1", DXT5: "DXT5"}


@dataclass
class Texture:
    offset: int  # offset of the pixel data in the file
    width: int
    height: int
    fmt: int
    data: bytes


def find_textures(buf: bytes) -> list[Texture]:
    out = []
    i = buf.find(b"NTP3")
    while i >= 0:
        count, = struct.unpack_from(">H", buf, i + 6)
        o = i + 0x10
        for _ in range(count):
            total, _, size, head = struct.unpack_from(">IIIH", buf, o)
            fmt = buf[o + 0x13]
            w, h = struct.unpack_from(">HH", buf, o + 0x14)
            out.append(Texture(o + head, w, h, fmt, buf[o + head:o + head + size]))
            o += total
        i = buf.find(b"NTP3", o)
    return out


def _rgb565(c: np.ndarray) -> np.ndarray:
    r, g, b = (c >> 11) & 31, (c >> 5) & 63, c & 31
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], -1).astype(np.int32)


def _colors(blocks: np.ndarray, dxt1: bool) -> np.ndarray:
    """blocks: (n, 8) uint8 colour blocks -> (n, 16, 4) RGBA."""
    c0 = blocks[:, 0].astype(np.int32) | (blocks[:, 1].astype(np.int32) << 8)
    c1 = blocks[:, 2].astype(np.int32) | (blocks[:, 3].astype(np.int32) << 8)
    p0, p1 = _rgb565(c0), _rgb565(c1)
    four = (c0 > c1) if dxt1 else np.ones(len(c0), bool)
    p2 = np.where(four[:, None], (2 * p0 + p1) // 3, (p0 + p1) // 2)
    p3 = np.where(four[:, None], (p0 + 2 * p1) // 3, 0)
    alpha = np.full((len(c0), 4), 255, np.int32)
    alpha[:, 3] = np.where(four, 255, 0)
    pal = np.concatenate([np.stack([p0, p1, p2, p3], 1), alpha[..., None]], -1)  # (n, 4, 4)
    bits = blocks[:, 4:8].astype(np.uint32)
    bits = bits[:, 0] | (bits[:, 1] << 8) | (bits[:, 2] << 16) | (bits[:, 3] << 24)
    idx = (bits[:, None] >> (2 * np.arange(16, dtype=np.uint32))) & 3
    return np.take_along_axis(pal, idx[..., None].astype(np.intp).repeat(4, -1), 1)


def _alphas(blocks: np.ndarray) -> np.ndarray:
    """blocks: (n, 8) uint8 DXT5 alpha blocks -> (n, 16) alpha."""
    pal = np.array([dxt5._palette(int(a), int(b)) for a, b in blocks[:, :2]], np.int32)
    bits = np.zeros(len(blocks), np.uint64)
    for k in range(6):
        bits |= blocks[:, 2 + k].astype(np.uint64) << np.uint64(8 * k)
    idx = (bits[:, None] >> (np.uint64(3) * np.arange(16, dtype=np.uint64))) & np.uint64(7)
    return np.take_along_axis(pal, idx.astype(np.intp), 1)


def decode(tex: Texture) -> np.ndarray:
    """Return (height, width, 4) uint8 RGBA."""
    if tex.fmt not in FORMAT_NAMES:
        raise ValueError(f"unsupported texture format {tex.fmt}")
    bw, bh = (tex.width + 3) // 4, (tex.height + 3) // 4
    size = 8 if tex.fmt == DXT1 else 16
    raw = np.frombuffer(tex.data[:bw * bh * size], np.uint8).reshape(bw * bh, size)
    if tex.fmt == DXT1:
        px = _colors(raw, dxt1=True)
    else:
        px = _colors(raw[:, 8:], dxt1=False)
        px[..., 3] = _alphas(raw[:, :8])
    img = px.reshape(bh, bw, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(bh * 4, bw * 4, 4)
    return img[:tex.height, :tex.width].astype(np.uint8)
