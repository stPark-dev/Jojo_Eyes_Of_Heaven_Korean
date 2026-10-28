"""Overlay of the game's CPK layers: base disc archives, then update patches in order."""
from pathlib import Path

from eoh.cpk import CpkArchive


class GameFs:
    def __init__(self, layers):
        self._owner: dict[str, CpkArchive] = {}
        for path in layers:
            arc = CpkArchive(path)
            for e in arc.entries:
                self._owner[e.path] = arc

    def paths(self) -> list[str]:
        return sorted(self._owner)

    def source(self, path: str) -> Path:
        return self._owner[path].path

    def read(self, path: str) -> bytes:
        return self._owner[path].read(path)
