"""Release steps.

    python3 scripts/release.py promote   # reviewed text -> distribution_eligible, images -> done
    python3 scripts/build_patch.py install --release
    python3 scripts/release.py package   # dist/<name>/ + dist/<name>.zip + .sha256

package makes a VCDIFF delta from the official 1.05 patch/5/data.cpk to the release build and
writes the install scripts and documents (release/) around it. No game file goes in.
"""
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eoh import images, release, textdb  # noqa: E402
from eoh.paths import PATCH_ROOT  # noqa: E402

VERSION = "1.0.0-beta.1"
AUTHOR = "돈골"
NAME = f"JoJo-EoH-Korean-Patch-v{VERSION}"
STORE_DIR = ROOT / "translation"
MANIFEST = STORE_DIR / "images.json"
BUILT = ROOT / "build/patch/data/patch/5/data.cpk"
DIST = ROOT / "dist"
# official xdelta 3.2.2 Windows x86_64 release, unpacked into the git-ignored work/tools/
DECODER = ROOT / "work/tools/xdelta3-3.2.2-windows-x86_64/xdelta3decode.exe"
DECODER_LICENSE = ROOT / "work/tools/xdelta-LICENSE.txt"
REVIEWED_BY = "GPT 검수 기준 배포(2026-11-02 사용자 결정)"
KEEP_REASON = "개발용 임시 문구(번역 불필요, 화면에 나오지 않음) — 사용자 결정 2026-11-02"


def official(n: int) -> Path:
    path = PATCH_ROOT / str(n) / "data.cpk"
    backup = path.with_name(path.name + ".kr-backup")
    return backup if backup.exists() else path


def cmd_promote() -> None:
    stores = {}
    for path in sorted(STORE_DIR.glob("*.json")):
        if path.name in ("glossary.json", "images.json"):
            continue
        try:
            stores[path] = textdb.promote(json.loads(path.read_text("utf-8")), REVIEWED_BY, KEEP_REASON)
        except textdb.TranslationError as e:
            sys.exit(f"{path.name}: 승격 안 함\n{e}")
    data = json.loads(MANIFEST.read_text("utf-8"))
    try:
        data["images"] = images.promote(data["images"])
    except images.ImageError as e:
        sys.exit(str(e))
    for path, store in stores.items():
        path.write_text(json.dumps(store, ensure_ascii=False, indent=1) + "\n", "utf-8")
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", "utf-8", newline="\n")
    print(f"번역 파일 {len(stores)}개, 이미지 {len(data['images'])}장 승격")


def cmd_package() -> None:
    if not BUILT.exists():
        sys.exit(f"{BUILT}: 먼저 build_patch.py install --release")
    pkg = DIST / NAME
    values = release.make_package(pkg, official(5), BUILT, {n: official(n) for n in (1, 2, 3, 4)},
                                  VERSION, AUTHOR, DECODER, DECODER_LICENSE)
    archive = DIST / f"{NAME}.zip"
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(pkg.rglob("*")):
            if p.is_file():
                z.write(p, f"{NAME}/{p.relative_to(pkg).as_posix()}")
    (DIST / f"{NAME}.zip.sha256").write_text(f"{release.sha256(archive)}  {archive.name}\n", "utf-8")
    print(f"{archive} ({archive.stat().st_size:,} bytes)")
    print(f"한글 data.cpk {values['TARGET_SIZE']:,} bytes, 차이 패치 {values['PATCH_SIZE']:,} bytes")


if __name__ == "__main__":
    {"promote": cmd_promote, "package": cmd_package}.get(
        sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
