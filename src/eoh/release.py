"""Build the distributable patch package (no game files in it, only a VCDIFF delta).

The delta turns the official 1.05 patch/5/data.cpk into the Korean one; the install scripts
(release/install.sh, install.ps1 + install.bat) check the player's 1.05 layers, back up
patch/5, decode with xdelta3 and check the result, and can verify and restore. Values the
scripts and documents need ({{KEY}}) are filled in from the actual files.
"""
import hashlib
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[2] / "release"
FONT_LICENSES = Path(__file__).resolve().parents[2] / "fonts"
PATCH_FILE = "eoh-ko.vcdiff"
SCRIPTS = ("install.sh", "install.ps1", "install.bat")
DOCS = ("README.md", "빠른_사용법.txt", "CHANGELOG.md", "CREDITS.md", "DISTRIBUTION_NOTICE.md",
        "THIRD_PARTY_NOTICES.txt")
_KEY = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def fill(text: str, values: dict) -> str:
    missing = sorted({k for k in _KEY.findall(text) if k not in values})
    if missing:
        raise KeyError(", ".join(missing))
    return _KEY.sub(lambda m: str(values[m.group(1)]), text)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def checksums(root: Path) -> str:
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256")
    return "".join(f"{sha256(p)}  {p.relative_to(root).as_posix()}\n" for p in files)


def _delta(official: Path, target: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    # no secondary compression: any xdelta3 decoder (3.0.x Linux packages, 3.2.x Windows) reads it
    subprocess.run(["xdelta3", "-e", "-9", "-S", "none", "-f", "-s", str(official), str(target),
                    str(out)], check=True)
    check = out.with_suffix(".check")
    try:
        subprocess.run(["xdelta3", "-d", "-f", "-s", str(official), str(out), str(check)], check=True)
        if sha256(check) != sha256(target):
            raise RuntimeError("차이 패치를 풀어 본 결과가 한글 data.cpk와 다름")
    finally:
        check.unlink(missing_ok=True)


def make_package(pkg: Path, official: Path, target: Path, layers: dict, version: str, author: str,
                 decoder: Path | None, decoder_license: Path | None = None) -> dict:
    """layers: {1..4: official patch/N/data.cpk}. decoder: Windows xdelta3decode.exe to ship."""
    if pkg.exists():
        shutil.rmtree(pkg)
    payload = pkg / "patch" / PATCH_FILE
    _delta(official, target, payload)
    values = {"VERSION": version, "AUTHOR": author, "DATE": date.today().isoformat(),
              "PATCH_FILE": PATCH_FILE,
              "OFFICIAL_SHA256": sha256(official), "OFFICIAL_SIZE": official.stat().st_size,
              "TARGET_SHA256": sha256(target), "TARGET_SIZE": target.stat().st_size,
              "PATCH_SHA256": sha256(payload), "PATCH_SIZE": payload.stat().st_size}
    for n, path in layers.items():
        values[f"LAYER{n}_SHA256"], values[f"LAYER{n}_SIZE"] = sha256(path), path.stat().st_size
    for name in SCRIPTS + DOCS:
        text = fill((TEMPLATES / name).read_text("utf-8"), values)
        if name == "install.ps1":  # Windows PowerShell 5.1 reads BOM-less scripts as ANSI
            (pkg / name).write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
        elif name == "install.bat":
            (pkg / name).write_bytes(text.replace("\n", "\r\n").encode("ascii"))
        else:
            (pkg / name).write_text(text, "utf-8", newline="\n")
    (pkg / "VERSION.txt").write_text(version + "\n", "utf-8")
    lic = pkg / "licenses"
    lic.mkdir()
    shutil.copy(FONT_LICENSES / "LICENSE.txt", lic / "SourceHanSerif-OFL-1.1.txt")
    shutil.copy(FONT_LICENSES / "NanumSquareRound-LICENSE.txt", lic / "NanumSquareRound-OFL-1.1.txt")
    if decoder is not None:
        (pkg / "tools").mkdir()
        shutil.copy(decoder, pkg / "tools/xdelta3decode.exe")
        shutil.copy(decoder_license, lic / "xdelta3-Apache-2.0.txt")
    (pkg / "CHECKSUMS.sha256").write_text(checksums(pkg), "utf-8", newline="\n")
    return values
