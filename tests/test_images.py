import hashlib
import struct

import numpy as np
import pytest
from PIL import Image

from eoh import images, texture

PATH = "data/ui/title/jpn/title_txt.xfbin"


def _ntp3(w, h, fmt, data):
    head = struct.pack(">IIIHHBBBBHH", 0x50 + len(data), 0, len(data), 0x50, 0, 0, 1, 0, fmt, w, h)
    return b"NTP3" + struct.pack(">HH", 0x0100, 1) + b"\0" * 8 + head.ljust(0x50, b"\0") + data


class FakeFs:
    def __init__(self, files):
        self.files = files

    def read(self, path):
        return self.files[path]


def _setup(tmp_path, state="todo", ko=True, size=(8, 4)):
    data = texture.encode(np.zeros((4, 8, 4), np.uint8), texture.DXT5)
    fs = FakeFs({PATH: b"xfbin" + _ntp3(8, 4, texture.DXT5, data)})
    entry = {"file": PATH, "index": 0, "width": 8, "height": 4, "format": "DXT5",
             "src_sha1": hashlib.sha1(data).hexdigest(), "png": "ui/title/jpn/title_txt/00_a.png",
             "state": state}
    if ko:
        png = tmp_path / entry["png"]
        png.parent.mkdir(parents=True)
        Image.new("RGBA", size, (255, 0, 0, 255)).save(png)
    return fs, entry


def test_korean_png_replaces_texture(tmp_path):
    fs, entry = _setup(tmp_path)
    files, report = images.build(fs, [entry], tmp_path, "dev")
    assert [p for p, _ in files] == [PATH] and report == {"applied": 1, "missing": 0}
    tex = texture.find_textures(files[0][1])[0]
    assert tuple(texture.decode(tex)[0, 0]) == (255, 0, 0, 255)
    assert files[0][1][:5] == b"xfbin"


def test_missing_png_keeps_original_in_dev(tmp_path):
    fs, entry = _setup(tmp_path, ko=False)
    assert images.build(fs, [entry], tmp_path, "dev") == ([], {"applied": 0, "missing": 1})


def test_wrong_size_is_rejected(tmp_path):
    fs, entry = _setup(tmp_path, size=(12, 4))
    with pytest.raises(images.ImageError, match="8x4"):
        images.build(fs, [entry], tmp_path, "dev")


def test_changed_official_texture_is_rejected(tmp_path):
    fs, entry = _setup(tmp_path)
    entry["src_sha1"] = "0" * 40
    with pytest.raises(images.ImageError, match="원본"):
        images.build(fs, [entry], tmp_path, "dev")


def test_release_requires_done_or_keep_original(tmp_path):
    fs, entry = _setup(tmp_path, state="needs_review")
    with pytest.raises(images.ImageError, match="needs_review"):
        images.build(fs, [entry], tmp_path, "release")
    fs, kept = _setup(tmp_path / "k", state="keep_original", ko=False)
    assert images.build(fs, [kept], tmp_path / "k", "release") == ([], {"applied": 0, "missing": 0})
    fs, done = _setup(tmp_path / "d", state="done")
    assert images.build(fs, [done], tmp_path / "d", "release")[1]["applied"] == 1


def test_several_textures_in_one_file_become_one_output(tmp_path):
    a = texture.encode(np.zeros((4, 4, 4), np.uint8), texture.DXT1)
    buf = (b"NTP3" + struct.pack(">HH", 0x0100, 2) + b"\0" * 8
           + b"".join(struct.pack(">IIIHHBBBBHH", 0x50 + len(a), 0, len(a), 0x50, 0, 0, 1, 0, 0, 4, 4)
                      .ljust(0x50, b"\0") + a for _ in range(2)))
    fs = FakeFs({PATH: buf})
    entries = []
    for i, colour in enumerate([(255, 0, 0, 255), (0, 0, 255, 255)]):
        e = {"file": PATH, "index": i, "width": 4, "height": 4, "format": "DXT1",
             "src_sha1": hashlib.sha1(a).hexdigest(), "png": f"t/{i}.png", "state": "todo"}
        (tmp_path / "t").mkdir(exist_ok=True)
        Image.new("RGBA", (4, 4), colour).save(tmp_path / e["png"])
        entries.append(e)
    files, _ = images.build(fs, entries, tmp_path, "dev")
    texs = texture.find_textures(files[0][1])
    assert len(files) == 1
    assert [tuple(texture.decode(t)[0, 0]) for t in texs] == [(255, 0, 0, 255), (0, 0, 255, 255)]


def test_png_file_entry_is_copied_as_is(tmp_path):
    raw = b"\x89PNG official"
    fs = FakeFs({"data/save/PS3/JP/ICON0.PNG": raw})
    entry = {"file": "data/save/PS3/JP/ICON0.PNG", "index": 0, "width": 4, "height": 4,
             "format": "PNG", "src_sha1": hashlib.sha1(raw).hexdigest(), "png": "s/ICON0.png",
             "state": "todo"}
    (tmp_path / "s").mkdir()
    Image.new("RGBA", (4, 4), (1, 2, 3, 255)).save(tmp_path / entry["png"])
    files, _ = images.build(fs, [entry], tmp_path, "dev")
    assert files == [(entry["file"], (tmp_path / entry["png"]).read_bytes())]
