"""DXT5 (BC3) helpers for the font atlas: glyph coverage lives in alpha, colour is white.

Blocks are 16 bytes in row-major block order: 8 bytes alpha (a0, a1, 16 x 3-bit indices,
little-endian), then 8 bytes colour (c0, c1 RGB565 LE, 16 x 2-bit indices).
"""
import numpy as np

EMPTY_COLOR = bytes.fromhex("0100000055555555")  # what the game's atlas uses for blank texels
WHITE_COLOR = bytes.fromhex("ffff000000000000")


def _palette(a0: int, a1: int) -> list[int]:
    if a0 > a1:
        return [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
    return [a0, a1] + [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255]


def _encode_alpha_block(block: np.ndarray) -> bytes:
    hi, lo = int(block.max()), int(block.min())
    if hi == lo:
        return bytes([hi, lo]) + bytes(6)
    pal = np.array(_palette(hi, lo))
    idx = np.abs(block.reshape(16, 1).astype(int) - pal).argmin(axis=1)
    bits = 0
    for i, v in enumerate(idx):
        bits |= int(v) << (3 * i)
    return bytes([hi, lo]) + bits.to_bytes(6, "little")


def _decode_alpha_block(block: bytes) -> np.ndarray:
    pal = _palette(block[0], block[1])
    bits = int.from_bytes(block[2:8], "little")
    return np.array([pal[(bits >> (3 * i)) & 7] for i in range(16)], np.uint8).reshape(4, 4)


def encode(alpha: np.ndarray) -> bytes:
    h, w = alpha.shape
    if h % 4 or w % 4:
        raise ValueError(f"size must be a multiple of 4, got {w}x{h}")
    out = bytearray()
    for by in range(0, h, 4):
        for bx in range(0, w, 4):
            block = alpha[by:by + 4, bx:bx + 4]
            out += _encode_alpha_block(block)
            out += WHITE_COLOR if block.any() else EMPTY_COLOR
    return bytes(out)


def decode_alpha(data: bytes, w: int, h: int) -> np.ndarray:
    out = np.zeros((h, w), np.uint8)
    bw = w // 4
    for by in range(h // 4):
        for bx in range(bw):
            off = (by * bw + bx) * 16
            out[by * 4:by * 4 + 4, bx * 4:bx * 4 + 4] = _decode_alpha_block(data[off:off + 8])
    return out


def blit(data: bytes, width: int, patch: np.ndarray, x: int, y: int) -> bytes:
    """Draw patch at (x, y), re-encoding only the blocks it touches (overwriting their texels)."""
    ph, pw = patch.shape
    x0, y0 = x // 4 * 4, y // 4 * 4
    x1, y1 = -(-(x + pw) // 4) * 4, -(-(y + ph) // 4) * 4
    bw = width // 4
    region = np.zeros((y1 - y0, x1 - x0), np.uint8)
    for by in range(y0 // 4, y1 // 4):
        for bx in range(x0 // 4, x1 // 4):
            off = (by * bw + bx) * 16
            region[by * 4 - y0:by * 4 - y0 + 4, bx * 4 - x0:bx * 4 - x0 + 4] = \
                _decode_alpha_block(data[off:off + 8])
    region[y - y0:y - y0 + ph, x - x0:x - x0 + pw] = patch
    encoded = encode(region)
    out = bytearray(data)
    rw = (x1 - x0) // 4
    for i in range((y1 - y0) // 4):
        dst = ((y0 // 4 + i) * bw + x0 // 4) * 16
        out[dst:dst + rw * 16] = encoded[i * rw * 16:(i + 1) * rw * 16]
    return bytes(out)
