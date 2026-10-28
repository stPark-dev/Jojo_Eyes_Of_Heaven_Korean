import struct

import pytest

from eoh import message
from eoh.message import Entry, MessageFile

MSG_DIR = "data/message/PS3/jpn/"


def _sample() -> MessageFile:
    return MessageFile(
        prefix=b"NUCC-PREFIX", suffix=b"\x00\x00\x00\x08-SUFFIX",
        chunk_meta=b"\x00\x00\x00\x01\x00\x79\x00\x00", table_word=4,
        entries=[Entry(0x11111111, "はい", b"\xff" * 6 + b"\0\0"),
                 Entry(0x22222222, None, b"\xff" * 6 + b"\0\0"),
                 Entry(0x33333333, "abc", b"\xff\xff\x00\x0e\x00\xd2\0\0")])


def test_serialize_then_parse_roundtrip():
    mf = _sample()
    assert message.parse(message.serialize(mf)) == mf


def test_strings_are_nul_terminated_and_4_aligned():
    raw = message.serialize(_sample())
    # "abc" (3 bytes) + NUL is exactly 4; "はい" (6 bytes) needs 2 bytes of padding.
    assert b"\xe3\x81\xaf\xe3\x81\x84\x00\x00abc\x00" in raw


def test_null_text_has_zero_pointer():
    raw = message.serialize(_sample())
    table = raw.index(b"\x00\x00\x03\xe9")
    second = table + 12 + 0x18
    assert struct.unpack(">I", raw[second + 8:second + 12])[0] == 0


def test_chunk_size_fields_track_text_length():
    mf = _sample()
    longer = message.serialize(mf.with_text(0x11111111, "아주 긴 한국어 문장입니다"))
    table = longer.index(b"\x00\x00\x03\xe9")
    chunk_size, = struct.unpack(">I", longer[table - 16:table - 12])
    inner, = struct.unpack(">I", longer[table - 4:table])
    assert chunk_size == inner + 4
    assert longer[table + inner:] == mf.suffix


def test_with_text_is_immutable_and_rejects_unknown_hash():
    mf = _sample()
    changed = mf.with_text(0x33333333, "xyz")
    assert mf.entries[2].text == "abc" and changed.entries[2].text == "xyz"
    with pytest.raises(KeyError):
        mf.with_text(0xDEADBEEF, "x")


def test_parse_rejects_file_without_table():
    with pytest.raises(ValueError):
        message.parse(b"NUCC" + bytes(300))


def test_all_final_message_files_roundtrip_bytes(game_fs):
    paths = [p for p in game_fs.paths() if p.startswith(MSG_DIR)]
    assert len(paths) == 88
    for path in paths:
        raw = game_fs.read(path)
        assert message.serialize(message.parse(raw)) == raw, path


def test_real_file_edit_keeps_other_entries(game_fs):
    raw = game_fs.read(MSG_DIR + "messageInfo_common.bin.xfbin")
    mf = message.parse(raw)
    target = next(e for e in mf.entries if e.text == "オプション")
    edited = message.parse(message.serialize(mf.with_text(target.hash, "옵션 설정 테스트")))
    assert [e.hash for e in edited.entries] == [e.hash for e in mf.entries]
    diffs = [(a, b) for a, b in zip(mf.entries, edited.entries) if a != b]
    assert len(diffs) == 1 and diffs[0][1].text == "옵션 설정 테스트"
