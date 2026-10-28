"""Where local game data lives. Game data is never committed.

Each path comes from, in order: an environment variable, the git-ignored
`eoh.local.toml` at the repository root, then the default.

    # eoh.local.toml
    rpcs3_usrdir = "C:/rpcs3/dev_hdd0/game/BLJS10318/USRDIR"
    disc_sim = "D:/eoh/game/PS3_GAME/USRDIR/data/sim"
"""
import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_CONFIG = ROOT / "eoh.local.toml"


def _local() -> dict:
    if not LOCAL_CONFIG.exists():
        return {}
    with LOCAL_CONFIG.open("rb") as f:
        return tomllib.load(f)


def _pick(env: str, key: str, default: Path) -> Path:
    value = os.environ.get(env) or _local().get(key)
    return Path(value) if value else default


DISC_SIM = _pick("EOH_DISC_SIM", "disc_sim", ROOT / "game/PS3_GAME/USRDIR/data/sim")
RPCS3_USRDIR = _pick("EOH_RPCS3_USRDIR", "rpcs3_usrdir",
                     Path.home() / ".config/rpcs3/dev_hdd0/game/BLJS10318/USRDIR")
PATCH_ROOT = _pick("EOH_PATCH_ROOT", "patch_root", RPCS3_USRDIR / "data/patch")
