import struct

import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from eoh import ps3iso

S = ps3iso.SECTOR
KEY = bytes(range(16))
PLAIN_END = 31  # sectors 0..31 plain, file data after it encrypted
EBOOT = b"SCE\x00" + b"e" * 100
BIG = [b"a" * S, b"b" * 10]  # one file stored as two extents


def _rec(name: str, lba: int, size: int, flags: int = 0) -> bytes:
    raw = {".": b"\x00", "..": b"\x01"}.get(name) or name.encode("utf-16-be")
    ln = 33 + len(raw) + (len(raw) + 1) % 2
    r = bytearray(ln)
    r[0] = ln
    r[2:10] = struct.pack("<I", lba) + struct.pack(">I", lba)
    r[10:18] = struct.pack("<I", size) + struct.pack(">I", size)
    r[25], r[32] = flags, len(raw)
    r[33:33 + len(raw)] = raw
    return bytes(r)


def _dir(lba: int, parent: int, children) -> bytes:
    body = _rec(".", lba, S, 2) + _rec("..", parent, S, 2) + b"".join(children)
    return body.ljust(S, b"\x00")


def _image(encrypted: bool) -> bytes:
    sectors = {}
    head = struct.pack(">I", 1) + b"\x00" * 4 + struct.pack(">II", 0, PLAIN_END)
    sectors[0] = head
    root = _rec(".", 20, S, 2)
    pvd = bytearray(S)
    pvd[0], pvd[1:6], pvd[156:190] = 1, b"CD001", root[:34]
    svd = bytearray(pvd)
    svd[0], svd[88:91] = 2, b"%/E"
    sectors[16], sectors[17] = bytes(pvd), bytes(svd)
    sectors[18] = b"\xffCD001"
    sectors[20] = _dir(20, 20, [_rec("PS3_GAME", 21, S, 2)])
    sectors[21] = _dir(21, 20, [_rec("USRDIR", 22, S, 2)])
    sectors[22] = _dir(22, 21, [_rec("EBOOT.BIN", 40, len(EBOOT)),
                                _rec("data0.cpk", 41, len(BIG[0]), 0x80),
                                _rec("data0.cpk", 42, len(BIG[1])),
                                _rec("disc", 23, S, 2)])
    sectors[23] = _dir(23, 22, [])
    sectors[40], sectors[41], sectors[42] = EBOOT, BIG[0], BIG[1]
    img = bytearray(43 * S)
    for n, data in sectors.items():
        blk = data.ljust(S, b"\x00")
        if encrypted and n > PLAIN_END:
            e = Cipher(algorithms.AES(KEY), modes.CBC(n.to_bytes(16, "big"))).encryptor()
            blk = e.update(blk) + e.finalize()
        img[n * S:(n + 1) * S] = blk
    return bytes(img)


@pytest.fixture
def iso(tmp_path):
    def make(encrypted=False):
        p = tmp_path / ("enc.iso" if encrypted else "dec.iso")
        p.write_bytes(_image(encrypted))
        return p
    return make


def test_extracts_joliet_names_empty_dirs_and_joined_extents(iso, tmp_path):
    with ps3iso.Ps3Iso(iso()) as disc:
        disc.extract(tmp_path / "game")
    usr = tmp_path / "game/PS3_GAME/USRDIR"
    assert (usr / "EBOOT.BIN").read_bytes() == EBOOT
    assert (usr / "data0.cpk").read_bytes() == b"".join(BIG)
    assert (usr / "disc").is_dir() and not any((usr / "disc").iterdir())


def test_already_decrypted_image_is_detected_despite_region_table(iso):
    with ps3iso.Ps3Iso(iso()) as disc:
        assert disc.plain == [(0, PLAIN_END)]
        assert not disc.needs_key(disc.entries())


def test_encrypted_image_requires_key_then_decrypts(iso, tmp_path):
    with ps3iso.Ps3Iso(iso(encrypted=True)) as disc:
        with pytest.raises(ValueError, match="disc key"):
            disc.extract(tmp_path / "nokey")
    with ps3iso.Ps3Iso(iso(encrypted=True), KEY) as disc:
        disc.extract(tmp_path / "game")
    usr = tmp_path / "game/PS3_GAME/USRDIR"
    assert (usr / "EBOOT.BIN").read_bytes() == EBOOT
    assert (usr / "data0.cpk").read_bytes() == b"".join(BIG)


def test_read_key_accepts_binary_and_hex(tmp_path):
    (tmp_path / "a.key").write_bytes(KEY)
    (tmp_path / "a.dkey").write_text(KEY.hex().upper() + "\n")
    assert ps3iso.read_key(tmp_path / "a.key") == KEY
    assert ps3iso.read_key(tmp_path / "a.dkey") == KEY
