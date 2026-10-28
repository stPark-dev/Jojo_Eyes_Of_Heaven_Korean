"""CRI @UTF table reader/writer (big-endian), byte-exact for CPK header/TOC tables."""
import struct
from dataclasses import dataclass, field
from typing import Any

STORAGE_ZERO, STORAGE_CONST, STORAGE_ROW, STORAGE_CONST2 = 0x10, 0x30, 0x50, 0x70
TYPE_STRING, TYPE_DATA = 0xA, 0xB
_NUM_FMT = {0: ">B", 1: ">b", 2: ">H", 3: ">h", 4: ">I", 5: ">i",
            6: ">Q", 7: ">q", 8: ">f", 9: ">d"}
_HEADER = struct.Struct(">IIIIHHI")  # rows/strings/data/name offsets, ncols, row_len, nrows


@dataclass
class Column:
    name: str
    flags: int
    const: Any = None

    @property
    def storage(self) -> int:
        return self.flags & 0xF0

    @property
    def type(self) -> int:
        return self.flags & 0x0F


@dataclass
class UtfTable:
    name: str
    columns: list[Column]
    rows: list[dict[str, Any]]
    encoding: int = 0  # high half of the rows-offset word: 0 = Shift-JIS, 1 = UTF-8
    padding: int = field(default=8, repr=False)


def _value_size(ty: int) -> int:
    if ty == TYPE_STRING:
        return 4
    if ty == TYPE_DATA:
        return 8
    return struct.calcsize(_NUM_FMT[ty])


def parse(buf: bytes) -> UtfTable:
    if buf[:4] != b"@UTF":
        raise ValueError(f"not a @UTF table: {buf[:4]!r}")
    size, = struct.unpack(">I", buf[4:8])
    body = buf[8:8 + size]
    rows_word, str_off, data_off, name_off, ncols, row_len, nrows = _HEADER.unpack_from(body)
    rows_off, encoding = rows_word & 0xFFFF, rows_word >> 16
    codec = _codec(encoding)

    def string(off: int) -> str:
        start = str_off + off
        return body[start:body.index(b"\0", start)].decode(codec)

    def read(ty: int, pos: int) -> Any:
        if ty == TYPE_STRING:
            return string(struct.unpack_from(">I", body, pos)[0])
        if ty == TYPE_DATA:
            off, length = struct.unpack_from(">II", body, pos)
            return body[data_off + off:data_off + off + length]
        return struct.unpack_from(_NUM_FMT[ty], body, pos)[0]

    columns, pos = [], _HEADER.size
    for _ in range(ncols):
        flags = body[pos]
        col = Column(string(struct.unpack_from(">I", body, pos + 1)[0]), flags)
        pos += 5
        if col.storage in (STORAGE_CONST, STORAGE_CONST2):
            col.const = read(col.type, pos)
            pos += _value_size(col.type)
        columns.append(col)

    rows = []
    for r in range(nrows):
        pos, row = rows_off + r * row_len, {}
        for col in columns:
            if col.storage == STORAGE_ROW:
                row[col.name] = read(col.type, pos)
                pos += _value_size(col.type)
            else:
                row[col.name] = col.const
        rows.append(row)
    return UtfTable(string(name_off), columns, rows, encoding=encoding)


def serialize(table: UtfTable) -> bytes:
    codec = _codec(table.encoding)
    pool, pool_index = bytearray(), {}
    data = bytearray()

    def intern(s: str) -> int:
        if s not in pool_index:
            pool_index[s] = len(pool)
            pool.extend(s.encode(codec) + b"\0")
        return pool_index[s]

    def pack(ty: int, value: Any) -> bytes:
        if ty == TYPE_STRING:
            return struct.pack(">I", intern(value))
        if ty == TYPE_DATA:
            if not value:
                return struct.pack(">II", 0, 0)
            off = len(data)
            data.extend(value)
            return struct.pack(">II", off, len(value))
        return struct.pack(_NUM_FMT[ty], value)

    intern("<NULL>")
    name_off = intern(table.name)
    col_bytes = bytearray()
    for col in table.columns:
        col_bytes += bytes([col.flags]) + struct.pack(">I", intern(col.name))
        if col.storage in (STORAGE_CONST, STORAGE_CONST2):
            col_bytes += pack(col.type, col.const)

    row_cols = [c for c in table.columns if c.storage == STORAGE_ROW]
    row_len = sum(_value_size(c.type) for c in row_cols)
    row_bytes = bytearray()
    for row in table.rows:
        for col in row_cols:
            row_bytes += pack(col.type, row[col.name])

    rows_off = _HEADER.size + len(col_bytes)
    str_off = rows_off + len(row_bytes)
    data_off = _align(str_off + len(pool), table.padding)
    size = _align(data_off + len(data), table.padding)
    header = _HEADER.pack((table.encoding << 16) | rows_off, str_off, data_off, name_off,
                          len(table.columns), row_len, len(table.rows))
    body = bytearray(header + col_bytes + row_bytes + pool)
    body += bytes(data_off - len(body)) + data
    body += bytes(size - len(body))
    return b"@UTF" + struct.pack(">I", size) + bytes(body)


def _codec(encoding: int) -> str:
    return "utf-8" if encoding == 1 else "cp932"


def _align(n: int, a: int) -> int:
    return (n + a - 1) // a * a
