"""Extract the BLJS10318 disc image into game/ (the layout tests and scripts expect).

    python3 scripts/extract_disc.py DISC.iso                 # already-decrypted image
    python3 scripts/extract_disc.py DISC.iso --key DISC.dkey # Redump (encrypted) image
    python3 scripts/extract_disc.py DISC.iso --out D:/eoh/game

The output folder is what RPCS3 boots (game/PS3_GAME/USRDIR/EBOOT.BIN).
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eoh import ps3iso  # noqa: E402

TITLE_ID = b"BLJS10318"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("iso", type=Path)
    ap.add_argument("--key", type=Path, help="disc key (.key 16 bytes or .dkey hex)")
    ap.add_argument("--out", type=Path, default=ROOT / "game")
    args = ap.parse_args()

    if (args.out / "PS3_GAME").exists():
        raise SystemExit(f"{args.out / 'PS3_GAME'} already exists; remove it first")
    key = ps3iso.read_key(args.key) if args.key else None
    with ps3iso.Ps3Iso(args.iso, key) as iso:
        try:
            entries = iso.extract(args.out, progress=lambda e: print(f"{e.size:>12,}  {e.path}"))
        except ValueError as e:
            raise SystemExit(f"{e} (pass --key)")
    sfo = (args.out / "PS3_GAME/PARAM.SFO").read_bytes()
    if TITLE_ID not in sfo:
        print(f"warning: PARAM.SFO does not name {TITLE_ID.decode()}", file=sys.stderr)
    files = [e for e in entries if not e.is_dir]
    print(f"{len(files)} files, {sum(e.size for e in files):,} bytes -> {args.out}")


if __name__ == "__main__":
    main()
