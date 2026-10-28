"""PoC: does text merged into the official patch/5/data.cpk reach the screen?

Prefixes every messageInfo_common string with a marker glyph that already exists in the
Japanese font, so common UI text visibly changes if the merged archive is used. This also
exercises length-changing reinsertion.

    python3 scripts/poc_marker.py install        # back up patch/5/data.cpk, install merged copy
    python3 scripts/poc_marker.py install-plain  # same, but with the text left unmodified
    python3 scripts/poc_marker.py uninstall  # restore the official patch/5/data.cpk
"""
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eoh import merge, message  # noqa: E402
from eoh.layers import GameFs  # noqa: E402

MARKER = "※"
TARGET = "data/message/PS3/jpn/messageInfo_common.bin.xfbin"
DISC_SIM = ROOT / "game/PS3_GAME/USRDIR/data/sim"
RPCS3_USRDIR = Path.home() / ".config/rpcs3/dev_hdd0/game/BLJS10318/USRDIR"
OUT = ROOT / "build/poc"


def official_common() -> bytes:
    layers = [DISC_SIM / f"{n}.cpk" for n in ("data0", "data1", "dataRegion0", "dataRegion1")]
    layers += [RPCS3_USRDIR / f"data/patch/{n}/data.cpk" for n in range(1, 5)]
    # patch/5 may already hold our merged copy; it never carries this file officially.
    return GameFs(layers).read(TARGET)


def marked_common() -> bytes:
    mf = message.parse(official_common())
    mf = replace(mf, entries=[replace(e, text=MARKER + e.text) if e.text else e
                              for e in mf.entries])
    return message.serialize(mf)


def main(cmd: str) -> None:
    if cmd == "install":
        print(merge.install(RPCS3_USRDIR, [(TARGET, marked_common())], OUT))
    elif cmd == "install-plain":
        # Control run: same container, unmodified text — separates archive faults from text faults.
        print(merge.install(RPCS3_USRDIR, [(TARGET, official_common())], OUT))
    elif cmd == "uninstall":
        merge.uninstall(RPCS3_USRDIR)
        print("restored official patch/5/data.cpk")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
