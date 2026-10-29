"""Put Korean image art into the game's texture files.

Each translation/images.json entry names one texture (file, index, size, format, SHA-1 of
the official pixel data) and its PNG path. A Korean PNG at <ko_dir>/<png> with exactly the
texture's size replaces that texture; textures without one keep the original. The dev
policy applies whatever exists; the release policy requires every entry to be `done` (with
its PNG) or `keep_original`.
"""
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

from eoh import texture

FORMATS = {"DXT1": texture.DXT1, "DXT5": texture.DXT5}


class ImageError(Exception):
    pass


def _check_policy(entry: dict, has_png: bool, policy: str) -> None:
    if policy not in ("dev", "release"):
        raise ValueError(policy)
    if policy == "release" and entry["state"] != "keep_original" and \
            not (entry["state"] == "done" and has_png):
        raise ImageError(f"{entry['png']}: 배포 가능 상태가 아님 ({entry['state']})")


def _apply(buf: bytes, entry: dict, png: Path) -> bytes:
    if entry["format"] == "PNG":
        return png.read_bytes()
    im = Image.open(png).convert("RGBA")
    if im.size != (entry["width"], entry["height"]):
        raise ImageError(f"{png}: 크기 {im.width}x{im.height}, "
                         f"필요 {entry['width']}x{entry['height']}")
    data = texture.encode(np.asarray(im), FORMATS[entry["format"]])
    return texture.replace(buf, entry["index"], data)


def _official_sha1(buf: bytes, entry: dict) -> str:
    raw = buf if entry["format"] == "PNG" else texture.find_textures(buf)[entry["index"]].data
    return hashlib.sha1(raw).hexdigest()


def build(fs, entries: list[dict], ko_dir: Path, policy: str):
    """Return ([(path, bytes)], report) for the files whose textures changed."""
    out: dict[str, bytes] = {}
    applied = missing = 0
    for entry in entries:
        png = Path(ko_dir) / entry["png"]
        _check_policy(entry, png.exists(), policy)
        if not png.exists() or entry["state"] == "keep_original":
            missing += entry["state"] != "keep_original"
            continue
        buf = out.get(entry["file"]) or fs.read(entry["file"])
        if _official_sha1(fs.read(entry["file"]), entry) != entry["src_sha1"]:
            raise ImageError(f"{entry['png']}: 원본 텍스처가 바뀜 (extract_images.py 다시 실행 후 확인)")
        out[entry["file"]] = _apply(buf, entry, png)
        applied += 1
    return list(out.items()), {"applied": applied, "missing": missing}
