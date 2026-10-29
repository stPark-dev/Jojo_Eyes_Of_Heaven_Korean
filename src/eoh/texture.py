"""NTP3 textures inside .xfbin files: DXT1/DXT5 decoding, encoding and in-place replacement.

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


def _headers(buf: bytes):
    """Yield (header offset, data offset, data size, mip count, format, width, height)."""
    i = buf.find(b"NTP3")
    while i >= 0:
        count, = struct.unpack_from(">H", buf, i + 6)
        o = i + 0x10
        for _ in range(count):
            total, _, size, head = struct.unpack_from(">IIIH", buf, o)
            w, h = struct.unpack_from(">HH", buf, o + 0x14)
            yield o, o + head, size, buf[o + 0x11], buf[o + 0x13], w, h
            o += total
        i = buf.find(b"NTP3", o)


def find_textures(buf: bytes) -> list[Texture]:
    return [Texture(data, w, h, fmt, buf[data:data + size])
            for _, data, size, _, fmt, w, h in _headers(buf)]


def replace(buf: bytes, index: int, data: bytes) -> bytes:
    """Return buf with texture `index`'s pixel data swapped for data (same size, one level)."""
    _, off, size, mips, _, _, _ = list(_headers(buf))[index]
    if mips != 1:
        raise ValueError(f"텍스처 {index}: 밉맵 {mips}단계는 아직 지원하지 않음")
    if len(data) != size:
        raise ValueError(f"텍스처 {index}: 크기 불일치 ({len(data)} != {size})")
    return buf[:off] + data + buf[off + size:]


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


def _to565(c: np.ndarray) -> np.ndarray:
    r, g, b = (np.clip(np.rint(c[..., k] * m / 255), 0, m).astype(np.int32)
               for k, m in ((0, 31), (1, 63), (2, 31)))
    return (r << 11) | (g << 5) | b


def _encode_colors(px: np.ndarray, opaque: np.ndarray, dxt1: bool) -> np.ndarray:
    """px: (n, 16, 3) RGB, opaque: (n, 16) bool -> (n, 8) uint8 colour blocks.

    Endpoints are the extremes of the visible pixels along their principal axis. DXT1 blocks
    with transparent pixels use the 3-colour mode (c0 <= c1) and index 3 for transparency.
    """
    n = len(px)
    p = px.astype(np.float64)
    w = np.where(opaque.any(1, keepdims=True), opaque, True).astype(np.float64)
    mean = (p * w[..., None]).sum(1) / w.sum(1, keepdims=True)
    d = (p - mean[:, None]) * w[..., None]
    cov = np.einsum("nki,nkj->nij", d, p - mean[:, None])
    axis = np.linalg.eigh(cov)[1][:, :, -1]
    t = np.einsum("nki,ni->nk", p - mean[:, None], axis)
    lo = np.where(w > 0, t, np.inf).min(1)
    hi = np.where(w > 0, t, -np.inf).max(1)
    c0, c1 = _to565(mean + axis * hi[:, None]), _to565(mean + axis * lo[:, None])
    punch = dxt1 & ~opaque.all(1)
    swap = np.where(punch, c0 > c1, c0 < c1)
    c0, c1 = np.where(swap, c1, c0), np.where(swap, c0, c1)
    p0, p1 = _rgb565(c0), _rgb565(c1)
    four = ~punch & (c0 > c1) if dxt1 else np.ones(n, bool)
    p2 = np.where(four[:, None], (2 * p0 + p1) // 3, (p0 + p1) // 2)
    p3 = np.where(four[:, None], (p0 + 2 * p1) // 3, p0)
    pal = np.stack([p0, p1, p2, p3], 1).astype(np.float64)  # (n, 4, 3)
    dist = ((p[:, :, None] - pal[:, None]) ** 2).sum(-1)  # (n, 16, 4)
    dist[:, :, 3] = np.where(four[:, None], dist[:, :, 3], np.inf)
    idx = dist.argmin(-1)
    if dxt1:
        idx = np.where(punch[:, None] & ~opaque, 3, idx)
    bits = (idx.astype(np.uint32) << (2 * np.arange(16, dtype=np.uint32))).sum(1, dtype=np.uint32)
    out = np.zeros((n, 8), np.uint8)
    out[:, 0], out[:, 1] = c0 & 255, c0 >> 8
    out[:, 2], out[:, 3] = c1 & 255, c1 >> 8
    for k in range(4):
        out[:, 4 + k] = (bits >> (8 * k)) & 255
    return out


def encode(rgba: np.ndarray, fmt: int) -> bytes:
    """(height, width, 4) uint8 RGBA -> one level of DXT1/DXT5 data."""
    if fmt not in FORMAT_NAMES:
        raise ValueError(f"unsupported texture format {fmt}")
    h, w = rgba.shape[:2]
    if h % 4 or w % 4:
        raise ValueError(f"size must be a multiple of 4, got {w}x{h}")
    blocks = rgba.reshape(h // 4, 4, w // 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 4)
    if fmt == DXT1:
        return _encode_colors(blocks[..., :3], blocks[..., 3] >= 128, True).tobytes()
    colors = _encode_colors(blocks[..., :3], blocks[..., 3] > 0, False)
    return np.concatenate([_encode_alphas(blocks[..., 3]), colors], 1).tobytes()


def _alpha_indices(a: np.ndarray, a0: np.ndarray, a1: np.ndarray):
    """Best indices and squared error for alpha (n, 16) with endpoints a0, a1 per block."""
    pal = np.array([dxt5._palette(int(x), int(y)) for x, y in zip(a0, a1)], np.int32)
    err = (a[:, :, None].astype(np.int32) - pal[:, None]) ** 2
    idx = err.argmin(-1)
    return idx, np.take_along_axis(err, idx[..., None], -1).sum((1, 2))


def _encode_alphas(a: np.ndarray) -> np.ndarray:
    """(n, 16) alpha -> (n, 8) blocks; tries the 8-level and the 6-level+0/255 modes."""
    a = a.astype(np.int32)
    hi, lo = a.max(1), a.min(1)
    mid = np.where((a > 0) & (a < 255), a, -1)
    m_hi = np.where(mid.max(1) >= 0, mid.max(1), 255)
    m_lo = np.where(mid.max(1) >= 0, np.where(mid >= 0, mid, 256).min(1), 0)
    idx8, err8 = _alpha_indices(a, hi, np.where(hi == lo, hi, lo))
    idx6, err6 = _alpha_indices(a, m_lo, m_hi)
    six = (err6 < err8) & (m_lo < m_hi)
    a0, a1 = np.where(six, m_lo, hi), np.where(six, m_hi, lo)
    idx = np.where(six[:, None], idx6, idx8).astype(np.uint64)
    bits = (idx << (np.uint64(3) * np.arange(16, dtype=np.uint64))).sum(1, dtype=np.uint64)
    out = np.zeros((len(a), 8), np.uint8)
    out[:, 0], out[:, 1] = a0, a1
    for k in range(6):
        out[:, 2 + k] = (bits >> np.uint64(8 * k)) & np.uint64(255)
    return out
