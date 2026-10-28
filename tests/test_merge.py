import hashlib

import pytest

from eoh import cpk, merge


def _official(tmp_path, files=(("data/spc/a.bin", b"official-a"), ("data/m/t.bin", b"jp"))):
    usrdir = tmp_path / "USRDIR"
    target = usrdir / "data/patch/5/data.cpk"
    target.parent.mkdir(parents=True)
    cpk.write(list(files), target)
    return usrdir, hashlib.sha1(target.read_bytes()).hexdigest()


def test_merged_files_override_and_keep(tmp_path):
    usrdir, _ = _official(tmp_path)
    files = dict(merge.merged_files(usrdir / "data/patch/5/data.cpk", [("data/m/t.bin", b"ko"),
                                                                       ("data/new.bin", b"n")]))
    assert files == {"data/spc/a.bin": b"official-a", "data/m/t.bin": b"ko", "data/new.bin": b"n"}


def test_install_backs_up_official_and_replaces(tmp_path):
    usrdir, sha = _official(tmp_path)
    original = (usrdir / "data/patch/5/data.cpk").read_bytes()
    merge.install(usrdir, [("data/m/t.bin", b"ko")], tmp_path / "build", official_sha1=sha)
    target = usrdir / "data/patch/5/data.cpk"
    assert (usrdir / "data/patch/5/data.cpk.kr-backup").read_bytes() == original
    assert cpk.CpkArchive(target).read("data/m/t.bin") == b"ko"
    assert cpk.CpkArchive(target).read("data/spc/a.bin") == b"official-a"


def test_reinstall_merges_from_backup_not_from_patched_file(tmp_path):
    usrdir, sha = _official(tmp_path)
    merge.install(usrdir, [("data/m/t.bin", b"ko1"), ("data/x.bin", b"x")], tmp_path / "b", official_sha1=sha)
    merge.install(usrdir, [("data/m/t.bin", b"ko2")], tmp_path / "b", official_sha1=sha)
    arc = cpk.CpkArchive(usrdir / "data/patch/5/data.cpk")
    assert arc.read("data/m/t.bin") == b"ko2"
    assert "data/x.bin" not in [e.path for e in arc.entries]


def test_install_refuses_unknown_official_file(tmp_path):
    usrdir, _ = _official(tmp_path)
    with pytest.raises(RuntimeError):
        merge.install(usrdir, [("data/m/t.bin", b"ko")], tmp_path / "b", official_sha1="0" * 40)
    assert not (usrdir / "data/patch/5/data.cpk.kr-backup").exists()


def test_uninstall_restores_official(tmp_path):
    usrdir, sha = _official(tmp_path)
    original = (usrdir / "data/patch/5/data.cpk").read_bytes()
    merge.install(usrdir, [("data/m/t.bin", b"ko")], tmp_path / "b", official_sha1=sha)
    merge.uninstall(usrdir)
    assert (usrdir / "data/patch/5/data.cpk").read_bytes() == original
    assert not (usrdir / "data/patch/5/data.cpk.kr-backup").exists()


def test_uninstall_without_install_is_noop(tmp_path):
    usrdir, _ = _official(tmp_path)
    before = (usrdir / "data/patch/5/data.cpk").read_bytes()
    merge.uninstall(usrdir)
    assert (usrdir / "data/patch/5/data.cpk").read_bytes() == before
