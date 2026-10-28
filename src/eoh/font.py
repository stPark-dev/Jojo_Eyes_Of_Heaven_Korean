"""nuccChunkFont (NFH) bitmap fonts, e.g. data/ui/font/jpn/xfgame_cmn.fnt.xfbin.

Chunk payload (big-endian), right after the 12-byte NUCC chunk header:
    u32 nfh_size, u16 64, u16 96,
    NFH header (0x50 bytes: 'NFH\\0', u32 height, u32 glyph count, u32 0, name, style),
    256 x s32 lookup table indexed by code >> 8:
        first glyph index of that high byte minus (its code & 0xFF), 0x80000001 when empty,
    glyph records (0x20 each, sorted by code), see Glyph,
    NTP3 texture: 0x60-byte header then one DXT5 atlas (glyph coverage in alpha).
"""
import bisect
import struct
from dataclasses import dataclass, replace

import numpy as np

from eoh import dxt5

JPN_FONT = "data/ui/font/jpn/xfgame_cmn.fnt.xfbin"
EMPTY_SLOT = -0x7FFFFFFF  # 0x80000001
_NFH_HEADER = 0x50
_TEX_HEADER = 0x60
_RECORD = struct.Struct(">HHHH6hBBHBBHI")
_GAP = 2  # texels between glyphs, matching the game's own atlas spacing


class AtlasFull(Exception):
    pass


@dataclass(frozen=True)
class Glyph:
    code: int
    x: int
    y: int
    w: int
    h: int
    metrics: tuple  # FreeType-style, 1/64 px: horiBearingX/Y, horiAdvance, vertBearingX/Y, vertAdvance

    def pack(self, pos: int, remaining: int) -> bytes:
        return _RECORD.pack(0x1111, 2, self.x, self.y, *self.metrics, self.w, self.h, self.code,
                            pos, remaining, 0, 0)

    @staticmethod
    def unpack(raw: bytes) -> "Glyph":
        magic, kind, x, y, *rest = _RECORD.unpack(raw)
        metrics, (w, h, code, _pos, _rem, z1, z2) = tuple(rest[:6]), rest[6:]
        if magic != 0x1111 or kind != 2 or z1 or z2:
            raise ValueError(f"unexpected glyph record {raw.hex()}")
        return Glyph(code, x, y, w, h, metrics)


@dataclass(frozen=True)
class FontFile:
    prefix: bytes
    chunk_meta: bytes
    unknown: bytes
    nfh_header: bytes
    table: list[int]
    glyphs: list[Glyph]
    tex_header: bytes
    texture: bytes
    suffix: bytes

    @property
    def width(self) -> int:
        return struct.unpack_from(">H", self.tex_header, 0x24)[0]

    @property
    def height(self) -> int:
        return struct.unpack_from(">H", self.tex_header, 0x26)[0]

    def free_top(self) -> int:
        bottom = max(g.y + g.h for g in self.glyphs)
        return -(-bottom // 4) * 4


def parse(buf: bytes) -> FontFile:
    nfh = buf.index(b"NFH\0")
    size_off = nfh - 0x14
    chunk_size, = struct.unpack_from(">I", buf, size_off)
    nfh_size, = struct.unpack_from(">I", buf, nfh - 8)
    count, = struct.unpack_from(">I", buf, nfh + 8)
    table = list(struct.unpack_from(">256i", buf, nfh + _NFH_HEADER))
    rec0 = nfh + _NFH_HEADER + 0x400
    if nfh_size != _NFH_HEADER + 0x400 + count * _RECORD.size:
        raise ValueError("NFH size does not match glyph count")
    glyphs = [Glyph.unpack(buf[rec0 + i * _RECORD.size:rec0 + (i + 1) * _RECORD.size])
              for i in range(count)]
    tex = nfh + nfh_size
    if buf[tex:tex + 4] != b"NTP3":
        raise ValueError("NTP3 texture not found after glyph records")
    data_size, = struct.unpack_from(">I", buf, tex + 0x18)
    end = tex + _TEX_HEADER + data_size
    if size_off + 12 + chunk_size != end:
        raise ValueError("chunk size does not match font payload")
    return FontFile(buf[:size_off], buf[size_off + 4:size_off + 12], buf[nfh - 4:nfh],
                    buf[nfh:nfh + _NFH_HEADER], table, glyphs, buf[tex:tex + _TEX_HEADER],
                    buf[tex + _TEX_HEADER:end], buf[end:])


def build_table(glyphs: list[Glyph]) -> list[int]:
    table = [EMPTY_SLOT] * 256
    for i, g in enumerate(glyphs):
        hi = g.code >> 8
        if table[hi] == EMPTY_SLOT:
            table[hi] = i - (g.code & 0xFF)
    return table


def _records(glyphs: list[Glyph]) -> bytes:
    out, i = bytearray(), 0
    while i < len(glyphs):
        hi = glyphs[i].code >> 8
        j = i
        while j < len(glyphs) and glyphs[j].code >> 8 == hi:
            j += 1
        for pos, g in enumerate(glyphs[i:j]):
            out += g.pack(pos, j - i - 1 - pos)
        i = j
    return bytes(out)


def serialize(f: FontFile) -> bytes:
    header = bytearray(f.nfh_header)
    struct.pack_into(">I", header, 8, len(f.glyphs))
    nfh = bytes(header) + struct.pack(">256i", *f.table) + _records(f.glyphs)
    payload = struct.pack(">I", len(nfh)) + f.unknown + nfh + f.tex_header + f.texture
    return f.prefix + struct.pack(">I", len(payload)) + f.chunk_meta + payload + f.suffix


def lookup(f: FontFile, code: int) -> Glyph:
    codes = [g.code for g in f.glyphs]
    i = bisect.bisect_left(codes, code)
    if i == len(codes) or codes[i] != code:
        raise KeyError(hex(code))
    return f.glyphs[i]


def texture_region(f: FontFile, x0: int, y0: int, w: int, h: int) -> bytes:
    bw = f.width // 4
    return b"".join(f.texture[((y0 // 4 + r) * bw + x0 // 4) * 16:
                              ((y0 // 4 + r) * bw + (x0 + w) // 4) * 16] for r in range(h // 4))


def add_glyphs(f: FontFile, new) -> FontFile:
    """new: iterable of (code, alpha ndarray HxW, metrics). Packs them below the used area."""
    existing = {g.code for g in f.glyphs}
    new = list(new)
    codes = [c for c, _, _ in new]
    if len(set(codes)) != len(codes) or existing & set(codes):
        raise ValueError("glyph codes must be new and unique")
    texture, placed = f.texture, []
    x, y, row_h = _GAP, f.free_top() + _GAP, 0
    for code, alpha, metrics in new:
        h, w = alpha.shape
        if x + w + _GAP > f.width:
            x, y, row_h = _GAP, y + row_h + _GAP, 0
        if y + h > f.height:
            raise AtlasFull(f"atlas full after {len(placed)} new glyphs")
        texture = dxt5.blit(texture, f.width, np.asarray(alpha, np.uint8), x, y)
        placed.append(Glyph(code, x, y, w, h, tuple(metrics)))
        x += w + _GAP
        row_h = max(row_h, h)
    glyphs = sorted(f.glyphs + placed, key=lambda g: g.code)
    return replace(f, glyphs=glyphs, table=build_table(glyphs), texture=texture)
