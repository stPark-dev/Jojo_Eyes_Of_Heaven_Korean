import pytest

from eoh import cpk, install


def _game_dir(tmp_path, version="5"):
    usrdir = tmp_path / "BLJS10318/USRDIR"
    (usrdir / "data/system").mkdir(parents=True)
    (usrdir / "data/system/version.txt").write_bytes(version.encode() + b"\r\n")
    for n in range(1, int(version) + 1):
        (usrdir / f"data/patch/{n}").mkdir(parents=True)
    return usrdir


def test_build_layer_writes_cpk(tmp_path):
    out = install.build_layer([("data/x", b"1")], tmp_path / "out", layer=6)
    assert out == tmp_path / "out/USRDIR/data/patch/6/data.cpk"
    assert cpk.CpkArchive(out).read("data/x") == b"1"


def test_install_copies_layer_and_bumps_version(tmp_path):
    usrdir = _game_dir(tmp_path)
    built = install.build_layer([("data/x", b"1")], tmp_path / "out", layer=6)
    install.install(built, usrdir, layer=6)
    assert (usrdir / "data/patch/6/data.cpk").read_bytes() == built.read_bytes()
    assert (usrdir / "data/system/version.txt").read_bytes() == b"6\r\n"
    assert (usrdir / "data/system/version.txt.kr-backup").read_bytes() == b"5\r\n"


def test_install_refuses_unexpected_base_version(tmp_path):
    usrdir = _game_dir(tmp_path, version="4")
    built = install.build_layer([("data/x", b"1")], tmp_path / "out", layer=6)
    with pytest.raises(RuntimeError):
        install.install(built, usrdir, layer=6)
    assert not (usrdir / "data/patch/6").exists()


def test_uninstall_restores_original_state(tmp_path):
    usrdir = _game_dir(tmp_path)
    built = install.build_layer([("data/x", b"1")], tmp_path / "out", layer=6)
    install.install(built, usrdir, layer=6)
    install.uninstall(usrdir, layer=6)
    assert (usrdir / "data/system/version.txt").read_bytes() == b"5\r\n"
    assert not (usrdir / "data/patch/6").exists()
    assert not (usrdir / "data/system/version.txt.kr-backup").exists()


def test_reinstall_over_existing_layer_keeps_original_backup(tmp_path):
    usrdir = _game_dir(tmp_path)
    built = install.build_layer([("data/x", b"1")], tmp_path / "out", layer=6)
    install.install(built, usrdir, layer=6)
    install.install(built, usrdir, layer=6)
    assert (usrdir / "data/system/version.txt.kr-backup").read_bytes() == b"5\r\n"
