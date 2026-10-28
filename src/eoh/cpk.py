"""CRI CPK archive reading (incl. CRILAYLA and DPK-chunked entries) and uncompressed writing.

The writer mirrors the layout of the game's own update CPKs (CPKMC2.45.00):
header @0, TOC @0x800, 2048-aligned content, TOC sorted by upper-cased full path.
"""
import posixpath
import struct
from dataclasses import dataclass
from pathlib import Path

from eoh import crilayla, utf_table
from eoh.utf_table import Column, UtfTable

ALIGN = 2048
TOC_OFFSET = 0x800
_COPYRIGHT = b"(c)CRI"

_HEADER_COLUMNS = [
    ("UpdateDateTime", 0x56), ("FileSize", 0x16), ("ContentOffset", 0x56), ("ContentSize", 0x56),
    ("TocOffset", 0x56), ("TocSize", 0x56), ("TocCrc", 0x14), ("HtocOffset", 0x16),
    ("HtocSize", 0x16), ("EtocOffset", 0x16), ("EtocSize", 0x16), ("ItocOffset", 0x16),
    ("ItocSize", 0x16), ("ItocCrc", 0x14), ("GtocOffset", 0x16), ("GtocSize", 0x16),
    ("GtocCrc", 0x14), ("HgtocOffset", 0x16), ("HgtocSize", 0x16), ("EnabledPackedSize", 0x56),
    ("EnabledDataSize", 0x56), ("TotalDataSize", 0x16), ("Tocs", 0x14), ("Files", 0x54),
    ("Groups", 0x54), ("Attrs", 0x54), ("TotalFiles", 0x14), ("Directories", 0x14),
    ("Updates", 0x14), ("Version", 0x52), ("Revision", 0x52), ("Align", 0x52), ("Sorted", 0x52),
    ("EnableFileName", 0x52), ("EID", 0x12), ("CpkMode", 0x54), ("Tvers", 0x5A),
    ("Comment", 0x1A), ("Codec", 0x54), ("DpkItoc", 0x54), ("EnableTocCrc", 0x52),
    ("EnableFileCrc", 0x52), ("CrcMode", 0x54), ("CrcTable", 0x5B),
]
_TOC_COLUMNS = [
    ("DirName", 0x5A), ("FileName", 0x5A), ("FileSize", 0x54), ("ExtractSize", 0x54),
    ("FileOffset", 0x56), ("ID", 0x54), ("UserString", 0x1A),
]
_HEADER_FIXED = {
    "UpdateDateTime": 0, "Groups": 0, "Attrs": 0, "Version": 7, "Revision": 11, "Align": ALIGN,
    "Sorted": 1, "EnableFileName": 1, "CpkMode": 1, "Tvers": "CPKMC2.45.00, DLL3.15.00",
    "Codec": 0x20000, "DpkItoc": 0, "EnableTocCrc": 0, "EnableFileCrc": 0, "CrcMode": 0,
    "CrcTable": b"",
}


@dataclass(frozen=True)
class Entry:
    path: str
    size: int          # stored size
    extract_size: int  # size after decompression
    offset: int        # absolute offset in the archive


class CpkArchive:
    def __init__(self, path):
        self.path = Path(path)
        with open(self.path, "rb") as f:
            self.header = _read_packet(f, 0, b"CPK ").rows[0]
            toc_off = self.header["TocOffset"]
            toc = _read_packet(f, toc_off, b"TOC ")
        base = min(toc_off, self.header.get("ContentOffset") or toc_off)
        self.entries = [
            Entry(posixpath.join(r["DirName"] or "", r["FileName"]), r["FileSize"],
                  r["ExtractSize"], r["FileOffset"] + base)
            for r in toc.rows
        ]
        self._by_path = {e.path: e for e in self.entries}

    def entry(self, path: str) -> Entry:
        return self._by_path[path]

    def read(self, path: str) -> bytes:
        e = self.entry(path)
        with open(self.path, "rb") as f:
            f.seek(e.offset)
            raw = f.read(e.size)
        if e.size == e.extract_size:
            return raw
        if raw[:4] == b"CPK ":
            return _unpack_dpk(raw)
        return crilayla.decompress(raw)


def _read_packet(f, offset: int, magic: bytes) -> UtfTable:
    f.seek(offset)
    head = f.read(16)
    if head[:4] != magic:
        raise ValueError(f"expected {magic!r} at {offset:#x}, got {head[:4]!r}")
    length, = struct.unpack("<Q", head[8:16])
    return utf_table.parse(f.read(length))


def _unpack_dpk(raw: bytes) -> bytes:
    """An entry stored as a nested ID-only CPK whose ITOC lists compressed chunks in ID order."""
    header = utf_table.parse(raw[16:]).rows[0]
    itoc_off = header["ItocOffset"]
    length, = struct.unpack("<Q", raw[itoc_off + 8:itoc_off + 16])
    itoc = utf_table.parse(raw[itoc_off + 16:itoc_off + 16 + length]).rows[0]
    chunks = []
    for key in ("DataL", "DataH"):
        if itoc.get(key):
            chunks += utf_table.parse(itoc[key]).rows
    chunks.sort(key=lambda r: r["ID"])
    out, pos = bytearray(), header["ContentOffset"]
    for c in chunks:
        data = raw[pos:pos + c["FileSize"]]
        out += data if c["FileSize"] == c["ExtractSize"] else crilayla.decompress(data)
        pos = _align(pos + c["FileSize"], header["Align"])
    return bytes(out)


def write(files, out_path) -> None:
    """Write an uncompressed CPK from (path, bytes) pairs."""
    files = sorted(files, key=lambda f: f[0].upper())
    paths = [p for p, _ in files]
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate paths in CPK input")

    def toc_table(content_off: int) -> UtfTable:
        rows, pos = [], content_off
        for i, (path, data) in enumerate(files):
            rows.append({"DirName": posixpath.dirname(path), "FileName": posixpath.basename(path),
                         "FileSize": len(data), "ExtractSize": len(data),
                         "FileOffset": pos - TOC_OFFSET, "ID": i, "UserString": None})
            pos = _align(pos + len(data), ALIGN)
        return UtfTable("CpkTocInfo", [Column(n, fl) for n, fl in _TOC_COLUMNS], rows)

    # TOC size does not depend on offsets (fixed-width fields), so one sizing pass suffices.
    toc_size = 16 + len(utf_table.serialize(toc_table(TOC_OFFSET)))
    content_off = _align(TOC_OFFSET + toc_size, ALIGN)
    toc_bytes = _packet(b"TOC ", utf_table.serialize(toc_table(content_off)))

    total = sum(len(d) for _, d in files)
    content_end = content_off
    for _, data in files:
        content_end = _align(content_end, ALIGN) + len(data)
    values = dict(_HEADER_FIXED, ContentOffset=content_off,
                  ContentSize=_align(content_end, ALIGN) - content_off,
                  TocOffset=TOC_OFFSET, TocSize=toc_size, EnabledPackedSize=2 * total,
                  EnabledDataSize=2 * total, Files=len(files))
    header = UtfTable("CpkHeader", [Column(n, fl) for n, fl in _HEADER_COLUMNS],
                      [{n: values.get(n) for n, _ in _HEADER_COLUMNS}])
    head = bytearray(_packet(b"CPK ", utf_table.serialize(header)))
    head += bytes(TOC_OFFSET - len(_COPYRIGHT) - len(head)) + _COPYRIGHT

    with open(out_path, "wb") as f:
        f.write(head)
        f.write(toc_bytes)
        for _, data in files:
            f.write(bytes(_align(f.tell(), ALIGN) - f.tell()))
            f.write(data)


def _packet(magic: bytes, table: bytes) -> bytes:
    return magic + b"\xff\x00\x00\x00" + struct.pack("<Q", len(table)) + table


def _align(n: int, a: int) -> int:
    return (n + a - 1) // a * a
