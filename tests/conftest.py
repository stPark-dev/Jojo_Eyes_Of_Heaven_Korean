"""Shared fixtures. Game data is never committed; tests that need it skip when absent."""
from pathlib import Path

import pytest

from eoh.paths import DISC_SIM, PATCH_ROOT

BASE_CPKS = ["data0", "data1", "dataRegion0", "dataRegion1"]
PATCH_LAYERS = [1, 2, 3, 4, 5]


def official_patch(n: int) -> Path:
    """Official update archive for layer n, even while our merged copy is installed."""
    path = PATCH_ROOT / str(n) / "data.cpk"
    backup = path.with_name(path.name + ".kr-backup")
    return backup if backup.exists() else path


def _require(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"game data not available: {path}")
    return path


@pytest.fixture
def patch_cpk():
    return lambda n: _require(official_patch(n))


@pytest.fixture
def base_cpk():
    return lambda name: _require(DISC_SIM / f"{name}.cpk")


@pytest.fixture(scope="session")
def game_fs():
    from eoh.layers import GameFs
    layers = [DISC_SIM / f"{n}.cpk" for n in BASE_CPKS]
    layers += [official_patch(n) for n in PATCH_LAYERS]
    for p in layers:
        _require(p)
    return GameFs(layers)
