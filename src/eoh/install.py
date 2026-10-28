"""Build the Korean patch as an extra update layer and install it into an RPCS3 game dir.

The game mounts USRDIR/data/patch/1..N where N comes from data/system/version.txt
(hypothesis under PoC test). The official updates stop at 5, so the patch is layer 6.
"""
import shutil
from pathlib import Path

from eoh import cpk

BASE_VERSION = "5"
_BACKUP_SUFFIX = ".kr-backup"


def build_layer(files, out_root, layer: int) -> Path:
    out = Path(out_root) / f"USRDIR/data/patch/{layer}/data.cpk"
    out.parent.mkdir(parents=True, exist_ok=True)
    cpk.write(files, out)
    return out


def install(built_cpk, usrdir, layer: int) -> None:
    usrdir = Path(usrdir)
    version = usrdir / "data/system/version.txt"
    backup = version.with_name(version.name + _BACKUP_SUFFIX)
    current = version.read_text().strip()
    if not backup.exists():
        if current != BASE_VERSION:
            raise RuntimeError(f"expected game version {BASE_VERSION} (1.05), found {current!r}")
        shutil.copy2(version, backup)
    dest = usrdir / f"data/patch/{layer}"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built_cpk, dest / "data.cpk")
    version.write_bytes(f"{layer}\r\n".encode())


def uninstall(usrdir, layer: int) -> None:
    usrdir = Path(usrdir)
    version = usrdir / "data/system/version.txt"
    backup = version.with_name(version.name + _BACKUP_SUFFIX)
    shutil.rmtree(usrdir / f"data/patch/{layer}", ignore_errors=True)
    if backup.exists():
        shutil.move(backup, version)
