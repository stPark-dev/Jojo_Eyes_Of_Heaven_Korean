"""messageInfo / battleChara `.bin.xfbin` text tables (NUCC binary chunk, big-endian).

Binary chunk payload:
    u32 0x3E9, u32 count, u32 4,
    count x 0x18 entries: u32 hash, u32 0, u32 text ptr (relative to its own field, 0 = none),
                          u32 0, 8 bytes extra (voice/flags; preserved verbatim),
    UTF-8 strings in entry order, NUL-terminated and zero-padded to 4 bytes.
Chunk header (12 bytes before the payload size word): u32 chunk size (= payload size + 4),
u32 type index, u16 version, u16 0; then u32 payload size.
"""
import struct
from dataclasses import dataclass, replace

_MAGIC = b"\x00\x00\x03\xe9"
_ENTRY = 0x18


@dataclass(frozen=True)
class Entry:
    hash: int
    text: str | None
    extra: bytes


@dataclass(frozen=True)
class MessageFile:
    prefix: bytes      # everything before the binary chunk header
    chunk_meta: bytes  # type index + version (8 bytes)
    table_word: int
    entries: list[Entry]
    suffix: bytes      # chunks following the binary chunk

    def with_text(self, hash_: int, text: str | None) -> "MessageFile":
        if not any(e.hash == hash_ for e in self.entries):
            raise KeyError(f"{hash_:#010x}")
        return replace(self, entries=[replace(e, text=text) if e.hash == hash_ else e
                                      for e in self.entries])


def _find_table(buf: bytes) -> int:
    pos = buf.find(_MAGIC, 16)
    while pos != -1:
        if pos >= 16:
            chunk_size, = struct.unpack_from(">I", buf, pos - 16)
            inner, = struct.unpack_from(">I", buf, pos - 4)
            if chunk_size == inner + 4 and pos + inner <= len(buf):
                return pos
        pos = buf.find(_MAGIC, pos + 1)
    raise ValueError("no message table chunk found")


def parse(buf: bytes) -> MessageFile:
    start = _find_table(buf)
    inner, = struct.unpack_from(">I", buf, start - 4)
    count, table_word = struct.unpack_from(">II", buf, start + 4)
    entries = []
    for k in range(count):
        e = start + 12 + k * _ENTRY
        hash_, pad1, rel, pad2 = struct.unpack_from(">IIII", buf, e)
        if pad1 or pad2:
            raise ValueError(f"unexpected non-zero entry padding at {e:#x}")
        text = None
        if rel:
            t = e + 8 + rel
            text = buf[t:buf.index(b"\0", t)].decode("utf-8")
        entries.append(Entry(hash_, text, buf[e + 16:e + _ENTRY]))
    return MessageFile(buf[:start - 16], buf[start - 12:start - 4], table_word, entries,
                       buf[start + inner:])


def serialize(mf: MessageFile) -> bytes:
    pool_start = 12 + len(mf.entries) * _ENTRY
    table, pool = bytearray(), bytearray()
    for k, e in enumerate(mf.entries):
        field = 12 + k * _ENTRY + 8
        rel = 0
        if e.text is not None:
            rel = pool_start + len(pool) - field
            s = e.text.encode("utf-8") + b"\0"
            pool += s + bytes(-len(s) % 4)
        table += struct.pack(">IIII", e.hash, 0, rel, 0) + e.extra
    payload = _MAGIC + struct.pack(">II", len(mf.entries), mf.table_word) + table + pool
    header = struct.pack(">I", len(payload) + 4) + mf.chunk_meta + struct.pack(">I", len(payload))
    return mf.prefix + header + payload + mf.suffix
