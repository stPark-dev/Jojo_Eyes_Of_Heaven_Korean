"""Install by merging patch files into the official top update archive (patch/5/data.cpk).

The 1.05 EBOOT opens patch/1..5 only (seen in RPCS3 sys_fs logs; version.txt is never
read), so an extra layer is not mounted. The official archive is backed up once and every
install rebuilds from that backup, so reinstalling never stacks on a patched file.
"""
import hashlib
import shutil
from pathlib import Path

from eoh import cpk

OFFICIAL_PATCH5_SHA1 = "772e39cc3e0f41ad6dc8707886569826e751966c"
_TARGET = "data/patch/5/data.cpk"
_BACKUP_SUFFIX = ".kr-backup"


def merged_files(official_cpk, ours):
    arc = cpk.CpkArchive(official_cpk)
    files = {e.path: arc.read(e.path) for e in arc.entries}
    files.update(dict(ours))
    return list(files.items())


def install(usrdir, ours, build_dir, official_sha1: str = OFFICIAL_PATCH5_SHA1) -> Path:
    target = Path(usrdir) / _TARGET
    backup = target.with_name(target.name + _BACKUP_SUFFIX)
    if not backup.exists():
        digest = hashlib.sha1(target.read_bytes()).hexdigest()
        if digest != official_sha1:
            raise RuntimeError(f"{target} is not the official 1.05 file (sha1 {digest})")
        shutil.copy2(target, backup)
    built = Path(build_dir) / _TARGET
    built.parent.mkdir(parents=True, exist_ok=True)
    cpk.write(merged_files(backup, ours), built)
    shutil.copy2(built, target)
    return built


def uninstall(usrdir) -> None:
    target = Path(usrdir) / _TARGET
    backup = target.with_name(target.name + _BACKUP_SUFFIX)
    if backup.exists():
        shutil.move(backup, target)
