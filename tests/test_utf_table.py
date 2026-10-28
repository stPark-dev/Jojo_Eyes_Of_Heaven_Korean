import struct

import pytest

from conftest import BASE_CPKS, PATCH_LAYERS
from eoh import utf_table
from eoh.utf_table import Column, UtfTable


def _table_bytes(buf: bytes, offset: int) -> bytes:
    """Raw @UTF table (magic + size + body) at offset."""
    size, = struct.unpack(">I", buf[offset + 4:offset + 8])
    return buf[offset:offset + 8 + size]


def _cpk_tables(path):
    with open(path, "rb") as f:
        head = f.read(0x800)
        hdr = _table_bytes(head, 16)
        toc_off = utf_table.parse(hdr).rows[0]["TocOffset"]
        f.seek(toc_off)
        toc_head = f.read(16)
        toc_len, = struct.unpack("<Q", toc_head[8:16])
        toc = _table_bytes(f.read(toc_len), 0)
    return hdr, toc


def test_parse_reads_columns_and_rows():
    t = UtfTable("T", [Column("A", 0x54), Column("S", 0x5A), Column("K", 0x32, 7)],
                 [{"A": 1, "S": "x", "K": 7}, {"A": 2, "S": "y", "K": 7}])
    back = utf_table.parse(utf_table.serialize(t))
    assert back.name == "T"
    assert [c.name for c in back.columns] == ["A", "S", "K"]
    assert back.rows == t.rows


def test_zero_storage_column_reads_none():
    t = UtfTable("T", [Column("Z", 0x14), Column("A", 0x54)], [{"Z": None, "A": 5}])
    assert utf_table.parse(utf_table.serialize(t)).rows == [{"Z": None, "A": 5}]


def test_strings_are_deduplicated_in_first_use_order():
    t = UtfTable("T", [Column("D", 0x5A), Column("F", 0x5A)],
                 [{"D": "dir", "F": "a"}, {"D": "dir", "F": "b"}])
    raw = utf_table.serialize(t)
    assert raw.count(b"dir\0") == 1
    assert raw.index(b"a\0") < raw.index(b"b\0")


def test_data_column_roundtrip():
    t = UtfTable("T", [Column("B", 0x5B)], [{"B": b"\x01\x02\x03"}, {"B": b""}])
    assert utf_table.parse(utf_table.serialize(t)).rows == [{"B": b"\x01\x02\x03"}, {"B": b""}]


def test_rejects_non_utf_magic():
    with pytest.raises(ValueError):
        utf_table.parse(b"XXXX" + bytes(64))


@pytest.mark.parametrize("layer", PATCH_LAYERS)
def test_patch_cpk_tables_roundtrip_bytes(patch_cpk, layer):
    for raw in _cpk_tables(patch_cpk(layer)):
        assert utf_table.serialize(utf_table.parse(raw)) == raw


@pytest.mark.parametrize("name", BASE_CPKS)
def test_base_cpk_tables_roundtrip_bytes(base_cpk, name):
    for raw in _cpk_tables(base_cpk(name)):
        assert utf_table.serialize(utf_table.parse(raw)) == raw
