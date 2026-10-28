import pytest

from conftest import PATCH_LAYERS
from eoh import cpk


def test_write_then_read_roundtrip(tmp_path):
    files = [("data/a/x.bin", b"hello"), ("data/a/y.bin", bytes(5000)), ("data/b/z.bin", b"z")]
    out = tmp_path / "t.cpk"
    cpk.write(files, out)
    arc = cpk.CpkArchive(out)
    assert [e.path for e in arc.entries] == [p for p, _ in files]
    for path, data in files:
        assert arc.read(path) == data


def test_write_aligns_file_offsets(tmp_path):
    out = tmp_path / "t.cpk"
    cpk.write([("d/a", b"1" * 3), ("d/b", b"2" * 3)], out)
    assert all(e.offset % 2048 == 0 for e in cpk.CpkArchive(out).entries)


def test_write_rejects_duplicate_paths(tmp_path):
    with pytest.raises(ValueError):
        cpk.write([("d/a", b"1"), ("d/a", b"2")], tmp_path / "t.cpk")


def test_read_missing_path_raises(tmp_path):
    out = tmp_path / "t.cpk"
    cpk.write([("d/a", b"1")], out)
    with pytest.raises(KeyError):
        cpk.CpkArchive(out).read("d/missing")


def test_rewrite_official_patch5_is_byte_identical(patch_cpk, tmp_path):
    src = patch_cpk(5)
    arc = cpk.CpkArchive(src)
    out = tmp_path / "p5.cpk"
    cpk.write([(e.path, arc.read(e.path)) for e in arc.entries], out)
    ours, theirs = out.read_bytes(), src.read_bytes()
    # Official CPKs carry 4 unexplained bytes right after the header @UTF table (not a
    # CRC32/Adler/MD5/SHA1 of header, TOC or content). We write zeros there; runtime
    # acceptance is checked by the in-game PoC, not here. Everything else must match.
    tail = 16 + int.from_bytes(theirs[8:16], "little")
    assert ours[tail:tail + 4] == bytes(4)
    assert ours[:tail] + ours[tail + 4:] == theirs[:tail] + theirs[tail + 4:]


@pytest.mark.parametrize("layer", PATCH_LAYERS)
def test_every_patch_entry_decompresses_to_declared_size(patch_cpk, layer):
    arc = cpk.CpkArchive(patch_cpk(layer))
    for e in arc.entries:
        assert len(arc.read(e.path)) == e.extract_size, e.path


def test_compressed_message_file_is_nucc(patch_cpk):
    arc = cpk.CpkArchive(patch_cpk(4))
    entry = arc.entry("data/message/PS3/jpn/messageInfo_common.bin.xfbin")
    assert entry.size < entry.extract_size
    assert arc.read(entry.path)[:4] == b"NUCC"
