"""Manage translation stores for every 1.05 message file.

    python3 scripts/textdb.py sync     # create/update translation/*.json (no source text)
    python3 scripts/textdb.py export   # work/translate/*.jsonl with source text (git-ignored)
    python3 scripts/textdb.py status   # entry counts per state
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eoh import message, textdb  # noqa: E402
from eoh.layers import GameFs  # noqa: E402

MSG_DIR = "data/message/PS3/jpn/"
STORE_DIR = ROOT / "translation"
WORK_DIR = ROOT / "work/translate"
DISC_SIM = ROOT / "game/PS3_GAME/USRDIR/data/sim"
PATCH_ROOT = Path.home() / ".config/rpcs3/dev_hdd0/game/BLJS10318/USRDIR/data/patch"


def official_fs() -> GameFs:
    layers = [DISC_SIM / f"{n}.cpk" for n in ("data0", "data1", "dataRegion0", "dataRegion1")]
    for n in range(1, 6):
        p = PATCH_ROOT / str(n) / "data.cpk"
        backup = p.with_name(p.name + ".kr-backup")
        layers.append(backup if backup.exists() else p)
    return GameFs(layers)


def store_path(file: str) -> Path:
    return STORE_DIR / (Path(file).name.removesuffix(".bin.xfbin") + ".json")


def load(path: Path):
    return json.loads(path.read_text("utf-8")) if path.exists() else None


def message_files(fs):
    return [(p, message.parse(fs.read(p))) for p in fs.paths() if p.startswith(MSG_DIR)]


def cmd_sync():
    STORE_DIR.mkdir(exist_ok=True)
    for file, mf in message_files(official_fs()):
        path = store_path(file)
        store = textdb.sync(load(path), file, mf)
        path.write_text(json.dumps(store, ensure_ascii=False, indent=1) + "\n", "utf-8")
    cmd_status()


def cmd_export():
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    for file, mf in message_files(official_fs()):
        store = load(store_path(file))
        if store is None:
            raise SystemExit(f"{file}: run sync first")
        by_id = {e["id"]: e for e in store["entries"]}
        with open(WORK_DIR / (store_path(file).stem + ".jsonl"), "w", encoding="utf-8") as f:
            for e in mf.entries:
                if e.text is None:
                    continue
                rec = by_id[f"0x{e.hash:08x}"]
                f.write(json.dumps({"id": rec["id"], "src": e.text, "ko": rec["ko"],
                                    "state": rec["state"]}, ensure_ascii=False) + "\n")
    print("exported to", WORK_DIR)


def cmd_status():
    states, files = Counter(), 0
    for path in sorted(STORE_DIR.glob("*.json")):
        if path.name == "glossary.json":
            continue
        files += 1
        states.update(e["state"] for e in load(path)["entries"])
    print(f"files {files}, entries {sum(states.values())}")
    for s in textdb.STATES:
        print(f"  {s:24} {states.get(s, 0)}")


if __name__ == "__main__":
    {"sync": cmd_sync, "export": cmd_export, "status": cmd_status}.get(
        sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
