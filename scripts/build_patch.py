"""Build the Korean patch from translation/ and install it into RPCS3's patch/5.

    python3 scripts/build_patch.py check      # build only, report what would change
    python3 scripts/build_patch.py install    # build and merge into patch/5 (backs up official)
    python3 scripts/build_patch.py uninstall  # restore the official patch/5
    add --release to require every entry to be distribution_eligible (images: done/keep_original)

Korean image art goes in translation/images_ko/<png path from translation/images.json>;
art repainted over game pictures (scripts/auto_images.py) goes in the git-ignored work/images_ko/.

The default (dev) policy applies any Korean text present and keeps the original elsewhere.
Install always mirrors the current translations: with nothing to apply it restores the
official patch/5, so a previous PoC or build does not linger.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eoh import build, images, merge, textdb  # noqa: E402
from eoh.glyph_render import Renderer  # noqa: E402
from eoh.layers import GameFs  # noqa: E402
from eoh.paths import DISC_SIM, PATCH_ROOT, RPCS3_USRDIR  # noqa: E402

STORE_DIR = ROOT / "translation"
KOREAN_FONT = ROOT / "fonts/SourceHanSerifKR-Heavy.otf"  # SIL OFL, see fonts/LICENSE.txt
IMAGE_MANIFEST = STORE_DIR / "images.json"
IMAGE_DIRS = [STORE_DIR / "images_ko", ROOT / "work/images_ko"]  # 2nd: art derived from game pictures
OUT = ROOT / "build/patch"


def official_fs() -> GameFs:
    layers = [DISC_SIM / f"{n}.cpk" for n in ("data0", "data1", "dataRegion0", "dataRegion1")]
    for n in range(1, 6):
        p = PATCH_ROOT / str(n) / "data.cpk"
        backup = p.with_name(p.name + ".kr-backup")
        layers.append(backup if backup.exists() else p)
    return GameFs(layers)


def load_stores() -> dict:
    stores = {}
    for path in sorted(STORE_DIR.glob("*.json")):
        if path.name in ("glossary.json", "images.json"):
            continue
        store = json.loads(path.read_text("utf-8"))
        stores[store["file"]] = store
    return stores


def run_build(policy: str):
    fs = official_fs()
    try:
        files, report = build.build(fs, load_stores(), policy, Renderer(KOREAN_FONT, size=24))
        manifest = json.loads(IMAGE_MANIFEST.read_text("utf-8"))["images"]
        image_files, image_report = images.build(fs, manifest, IMAGE_DIRS, policy)
    except (build.BuildError, textdb.TranslationError, images.ImageError) as e:
        raise SystemExit(f"빌드 실패 ({policy}):\n{e}")
    overlap = {p for p, _ in files} & {p for p, _ in image_files}
    if overlap:
        raise SystemExit(f"빌드 실패: 텍스트와 이미지가 같은 파일을 바꿈 {sorted(overlap)}")
    files += image_files
    print(f"정책 {policy}: 번역 적용 {report['applied']}문장, "
          f"원문 그대로 {report['kept_source']}문장 (미번역 + 원문 유지 승인)")
    print(f"이미지 교체 {image_report['applied']}장, 원본 그대로 {image_report['missing']}장")
    print(f"바뀌는 파일 {len(files)}개, 추가 글자 {len(report['glyphs'])}자 {report['glyphs']}")
    for path, data in files:
        print(f"  {path} ({len(data):,} bytes)")
    return files


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["check", "install", "uninstall"])
    ap.add_argument("--release", action="store_true")
    args = ap.parse_args()
    policy = "release" if args.release else "dev"

    if args.command == "uninstall":
        merge.uninstall(RPCS3_USRDIR)
        print("공식 patch/5/data.cpk 복원")
        return
    files = run_build(policy)
    if args.command == "check":
        return
    if not files:
        merge.uninstall(RPCS3_USRDIR)
        print("적용할 번역이 없어 공식 patch/5/data.cpk로 되돌림")
        return
    print("설치:", merge.install(RPCS3_USRDIR, files, OUT))


if __name__ == "__main__":
    main()
