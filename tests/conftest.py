"""Shared fixtures. Game data is never committed; tests that need it skip when absent."""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DISC_SIM = Path(os.environ.get("EOH_DISC_SIM", ROOT / "game/PS3_GAME/USRDIR/data/sim"))
PATCH_ROOT = Path(os.environ.get(
    "EOH_PATCH_ROOT",
    Path.home() / ".config/rpcs3/dev_hdd0/game/BLJS10318/USRDIR/data/patch"))

BASE_CPKS = ["data0", "data1", "dataRegion0", "dataRegion1"]
PATCH_LAYERS = [1, 2, 3, 4, 5]


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"game data not available: {path}")
    return path


@pytest.fixture
def patch_cpk():
    return lambda n: _require(PATCH_ROOT / str(n) / "data.cpk")


@pytest.fixture
def base_cpk():
    return lambda name: _require(DISC_SIM / f"{name}.cpk")


@pytest.fixture(scope="session")
def game_fs():
    from eoh.layers import GameFs
    layers = [DISC_SIM / f"{n}.cpk" for n in BASE_CPKS]
    layers += [PATCH_ROOT / str(n) / "data.cpk" for n in PATCH_LAYERS]
    for p in layers:
        _require(p)
    return GameFs(layers)
