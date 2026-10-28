"""CRILAYLA decompression (CRI's backward-LZ codec)."""
import struct

MAGIC = b"CRILAYLA"
_RAW_HEADER = 0x100
_VLE_WIDTHS = (2, 3, 5, 8)


def decompress(src: bytes) -> bytes:
    if src[:8] != MAGIC:
        raise ValueError(f"not CRILAYLA data: {src[:8]!r}")
    size, header_off = struct.unpack("<II", src[8:16])
    out = bytearray(size + _RAW_HEADER)
    out[:_RAW_HEADER] = src[0x10 + header_off:0x10 + header_off + _RAW_HEADER]

    # The bitstream is read backwards from just before the raw header, MSB first.
    in_pos = len(src) - _RAW_HEADER - 1
    pool = bits_left = 0

    def bits(n: int) -> int:
        nonlocal in_pos, pool, bits_left
        value = 0
        while n:
            if bits_left == 0:
                pool, bits_left = src[in_pos], 8
                in_pos -= 1
            take = min(bits_left, n)
            value = (value << take) | ((pool >> (bits_left - take)) & ((1 << take) - 1))
            bits_left -= take
            n -= take
        return value

    end = _RAW_HEADER + size - 1
    written = 0
    while written < size:
        if bits(1):
            ref = end - written + bits(13) + 3
            length = 3
            for width in _VLE_WIDTHS:
                v = bits(width)
                length += v
                if v != (1 << width) - 1:
                    break
            else:
                while True:
                    v = bits(8)
                    length += v
                    if v != 0xFF:
                        break
            for _ in range(length):
                out[end - written] = out[ref]
                ref -= 1
                written += 1
        else:
            out[end - written] = bits(8)
            written += 1
    return bytes(out)
