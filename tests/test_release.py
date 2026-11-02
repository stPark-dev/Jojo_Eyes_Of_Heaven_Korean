import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from eoh import release

ROOT = Path(__file__).resolve().parents[1]


def test_fill_replaces_every_key_and_rejects_leftovers():
    assert release.fill("v{{VERSION}} by {{AUTHOR}}", {"VERSION": "1", "AUTHOR": "돈골"}) == "v1 by 돈골"
    with pytest.raises(KeyError, match="SHA"):
        release.fill("{{SHA}}", {})


def test_checksums_list_every_file_but_the_list_itself(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"a")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub/b.bin").write_bytes(b"b")
    (tmp_path / "CHECKSUMS.sha256").write_text("old")
    text = release.checksums(tmp_path)
    assert text == (f"{hashlib.sha256(b'a').hexdigest()}  a.txt\n"
                    f"{hashlib.sha256(b'b').hexdigest()}  sub/b.bin\n")


# --- install.sh against a fake RPCS3 tree -------------------------------------------------

needs_xdelta = pytest.mark.skipif(shutil.which("xdelta3") is None, reason="xdelta3 없음")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def setup(tmp_path):
    """A package built from a tiny 'official' and 'korean' patch/5 and a fake RPCS3 folder."""
    official, korean = b"OFFICIAL" * 500, b"KOREAN!!" * 600
    layers = {n: f"layer{n}".encode() * 10 for n in (1, 2, 3, 4)}
    src, tgt = tmp_path / "official.cpk", tmp_path / "korean.cpk"
    src.write_bytes(official)
    tgt.write_bytes(korean)
    pkg = tmp_path / "pkg"
    release.make_package(pkg, src, tgt, layers={n: _write(tmp_path / f"l{n}", b) for n, b in layers.items()},
                         version="9.9.9-test", author="테스터", decoder=None)
    game = tmp_path / "RPCS3/dev_hdd0/game/BLJS10318/USRDIR/data/patch"
    for n, b in layers.items():
        _write(game / str(n) / "data.cpk", b)
    _write(game / "5/data.cpk", official)
    return pkg, tmp_path / "RPCS3", game / "5/data.cpk", official, korean


def _write(p: Path, b: bytes) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b)
    return p


def run(pkg, *args):
    return subprocess.run(["sh", str(pkg / "install.sh"), *args], capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin", "EOH_SKIP_PROCESS_CHECK": "1"})


@needs_xdelta
def test_install_verify_restore_round_trip(setup):
    pkg, rpcs3, cpk, official, korean = setup
    r = run(pkg, "install", str(rpcs3))
    assert r.returncode == 0, r.stdout + r.stderr
    assert cpk.read_bytes() == korean
    assert run(pkg, "verify", str(rpcs3)).returncode == 0
    again = run(pkg, "install", str(rpcs3))
    assert again.returncode == 0 and "이미" in again.stdout
    r = run(pkg, "restore", str(rpcs3))
    assert r.returncode == 0, r.stdout + r.stderr
    assert cpk.read_bytes() == official
    assert sorted(p.name for p in cpk.parent.iterdir()) == ["data.cpk"]
    assert run(pkg, "verify", str(rpcs3)).returncode != 0


@needs_xdelta
def test_install_accepts_the_title_folder_and_finds_an_official_copy_beside_a_mod(setup):
    pkg, rpcs3, cpk, official, korean = setup
    mod = b"SOME OTHER MOD" * 100
    cpk.write_bytes(mod)
    (cpk.parent / "data.cpk.old").write_bytes(official)
    title = rpcs3 / "dev_hdd0/game/BLJS10318"
    r = run(pkg, "install", str(title))
    assert r.returncode == 0, r.stdout + r.stderr
    assert cpk.read_bytes() == korean
    assert run(pkg, "restore", str(title)).returncode == 0
    assert cpk.read_bytes() == mod  # back to what was there before


@needs_xdelta
def test_install_refuses_without_the_official_source_or_with_other_updates(setup):
    pkg, rpcs3, cpk, official, korean = setup
    cpk.write_bytes(b"UNKNOWN")
    r = run(pkg, "install", str(rpcs3))
    assert r.returncode != 0 and "공식" in r.stdout + r.stderr
    assert cpk.read_bytes() == b"UNKNOWN"
    cpk.write_bytes(official)
    (cpk.parents[1] / "1/data.cpk").write_bytes(b"other version")
    r = run(pkg, "install", str(rpcs3))
    assert r.returncode != 0 and "1.05" in r.stdout + r.stderr
    assert cpk.read_bytes() == official


def test_windows_script_carries_the_same_hashes_and_a_utf8_bom(tmp_path):
    src, tgt = _write(tmp_path / "s", b"S" * 100), _write(tmp_path / "t", b"T" * 100)
    layers = {n: _write(tmp_path / f"l{n}", bytes([n]) * 10) for n in (1, 2, 3, 4)}
    if shutil.which("xdelta3") is None:
        pytest.skip("xdelta3 없음")
    release.make_package(tmp_path / "pkg", src, tgt, layers, "9.9.9-test", "테스터", decoder=None)
    ps1 = (tmp_path / "pkg/install.ps1").read_bytes()
    assert ps1.startswith(b"\xef\xbb\xbf")  # Windows PowerShell 5.1 reads BOM-less files as ANSI
    text = ps1.decode("utf-8-sig")
    assert _sha(tgt) in text and _sha(src) in text and "{{" not in text
    assert (tmp_path / "pkg/install.bat").read_bytes().isascii()
