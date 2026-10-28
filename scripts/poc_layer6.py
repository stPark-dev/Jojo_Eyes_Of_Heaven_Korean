"""PoC: does the game load an extra update layer (patch/6 + version.txt=6)?

Prefixes every messageInfo_common string with a marker glyph that already exists in the
Japanese font, so any common UI text visibly changes if the layer is mounted. This also
exercises length-changing reinsertion.

    python3 scripts/poc_layer6.py build      # -> build/poc/USRDIR/data/patch/6/data.cpk
    python3 scripts/poc_layer6.py install    # copy into RPCS3, version.txt 5 -> 6 (backed up)
    python3 scripts/poc_layer6.py uninstall  # restore version.txt, remove patch/6
"""
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eoh import install, message  # noqa: E402
from eoh.layers import GameFs  # noqa: E402

MARKER = "※"
TARGET = "data/message/PS3/jpn/messageInfo_common.bin.xfbin"
LAYER = 6
DISC_SIM = ROOT / "game/PS3_GAME/USRDIR/data/sim"
RPCS3_USRDIR = Path.home() / ".config/rpcs3/dev_hdd0/game/BLJS10318/USRDIR"
OUT = ROOT / "build/poc"


def build() -> Path:
    layers = [DISC_SIM / f"{n}.cpk" for n in ("data0", "data1", "dataRegion0", "dataRegion1")]
    layers += [RPCS3_USRDIR / f"data/patch/{n}/data.cpk" for n in range(1, 6)]
    mf = message.parse(GameFs(layers).read(TARGET))
    mf = replace(mf, entries=[replace(e, text=MARKER + e.text) if e.text else e
                              for e in mf.entries])
    return install.build_layer([(TARGET, message.serialize(mf))], OUT, layer=LAYER)


def main(cmd: str) -> None:
    built = OUT / f"USRDIR/data/patch/{LAYER}/data.cpk"
    if cmd == "build":
        print(build())
    elif cmd == "install":
        install.install(built, RPCS3_USRDIR, layer=LAYER)
        print("installed layer", LAYER, "into", RPCS3_USRDIR)
    elif cmd == "uninstall":
        install.uninstall(RPCS3_USRDIR, layer=LAYER)
        print("removed layer", LAYER)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
