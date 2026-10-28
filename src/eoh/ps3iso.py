"""PS3 disc image (.iso) reading and extraction.

Sector 0 holds the plain-region table: a big-endian count, then (start, end) sector pairs
that are stored unencrypted. Redump images keep the other sectors AES-128-CBC encrypted
with the disc key (IV = sector number, big-endian); some distributed images are already
decrypted but keep the table, so `needs_key` checks real file data instead of trusting it.

Names come from the Joliet tree. The primary ISO9660 tree has mangled names
(`GRD00_TEX.XFBIN` for `grd00.tex.xfbin`), and the game opens files by their real,
lowercase names, so extracting from it makes the game fail to boot. Empty directories
(`data/disc`, `data/sound/PS3`) are part of the disc and are created too.
"""
import struct
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

SECTOR = 0x800
_CHUNK = 2048  # sectors per read while extracting (4 MiB)


@dataclass
class Entry:
    path: str
    is_dir: bool
    extents: list = field(default_factory=list)  # [(lba, size)], several for multi-extent files

    @property
    def size(self) -> int:
        return sum(s for _, s in self.extents)


class Ps3Iso:
    def __init__(self, path, key: bytes | None = None):
        self.f = open(path, "rb")
        self.key = key
        head = self._raw(0, 1)
        n = struct.unpack(">I", head[:4])[0]
        b = struct.unpack(f">{n * 2}I", head[8:8 + n * 8])
        self.plain = [(b[i], b[i + 1]) for i in range(0, len(b), 2)]

    def close(self):
        self.f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _raw(self, sector: int, count: int) -> bytes:
        self.f.seek(sector * SECTOR)
        return self.f.read(count * SECTOR)

    def is_plain(self, sector: int) -> bool:
        return any(a <= sector <= b for a, b in self.plain)

    def read(self, sector: int, count: int) -> bytes:
        data = self._raw(sector, count)
        if self.key is None:
            return data
        out = bytearray(data)
        for i in range(count):
            s = sector + i
            if not self.is_plain(s):
                d = Cipher(algorithms.AES(self.key), modes.CBC(s.to_bytes(16, "big"))).decryptor()
                out[i * SECTOR:(i + 1) * SECTOR] = d.update(data[i * SECTOR:(i + 1) * SECTOR]) + d.finalize()
        return bytes(out)

    def entries(self) -> list[Entry]:
        for s in range(16, 64):
            vd = self._raw(s, 1)
            if vd[1:6] != b"CD001" or vd[0] == 255:
                break
            if vd[0] == 2 and vd[88:90] == b"%/":  # Joliet supplementary descriptor
                root = vd[156:190]
                return self._walk(struct.unpack("<I", root[2:6])[0], struct.unpack("<I", root[10:14])[0])
        raise ValueError("no Joliet volume descriptor")

    def _walk(self, lba: int, size: int, prefix: str = "") -> list[Entry]:
        data = self.read(lba, (size + SECTOR - 1) // SECTOR)
        pos, out = 0, []
        while pos < size:
            ln = data[pos]
            if ln == 0:  # records never cross a sector; skip the padding
                pos = (pos // SECTOR + 1) * SECTOR
                continue
            rec = data[pos:pos + ln]
            pos += ln
            raw = rec[33:33 + rec[32]]
            if raw in (b"\x00", b"\x01"):
                continue
            path = prefix + raw.decode("utf-16-be").split(";")[0]
            elba, esize, flags = struct.unpack("<I", rec[2:6])[0], struct.unpack("<I", rec[10:14])[0], rec[25]
            if flags & 2:
                out.append(Entry(path, True))
                out += self._walk(elba, esize, path + "/")
            elif out and out[-1].path == path and not out[-1].is_dir:
                out[-1].extents.append((elba, esize))
            else:
                out.append(Entry(path, False, [(elba, esize)]))
        return out

    def needs_key(self, entries: list[Entry]) -> bool:
        """True if file data sits in an encrypted region and does not read as plain."""
        for e in entries:
            if e.path.endswith("EBOOT.BIN") and not self.is_plain(e.extents[0][0]):
                return self._raw(e.extents[0][0], 1)[:4] != b"SCE\x00"
        return False

    def extract(self, out, progress=None) -> list[Entry]:
        out = Path(out)
        entries = self.entries()
        if self.key is None and self.needs_key(entries):
            raise ValueError("image is encrypted; a disc key is required")
        for e in entries:
            dst = out / e.path
            if e.is_dir:
                dst.mkdir(parents=True, exist_ok=True)
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            with open(dst, "wb") as w:
                for lba, size in e.extents:
                    left = size
                    while left > 0:
                        n = min(left, _CHUNK * SECTOR)
                        count = (n + SECTOR - 1) // SECTOR
                        w.write(self.read(lba, count)[:n])
                        lba += count
                        left -= n
            if progress:
                progress(e)
        return entries


def read_key(path) -> bytes:
    """Disc key from a 16-byte binary .key or a 32-digit hex .dkey file."""
    data = Path(path).read_bytes()
    if len(data) == 16:
        return data
    key = bytes.fromhex(data.decode("ascii").strip())
    if len(key) != 16:
        raise ValueError(f"disc key must be 16 bytes: {path}")
    return key
