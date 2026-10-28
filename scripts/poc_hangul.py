"""PoC: Hangul glyphs added to the game font render in game.

Replaces a handful of always-visible common strings with Korean, adds exactly the Hangul
those strings use to the Japanese font atlas, and merges both files into patch/5.

    python3 scripts/poc_hangul.py install    # also writes build/poc/hangul_preview.png
    python3 scripts/poc_hangul.py uninstall
"""
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image  # noqa: E402

from eoh import dxt5, font, merge, message  # noqa: E402
from eoh.glyph_render import Renderer  # noqa: E402
from eoh.layers import GameFs  # noqa: E402
from eoh.paths import DISC_SIM, RPCS3_USRDIR  # noqa: E402

COMMON = "data/message/PS3/jpn/messageInfo_common.bin.xfbin"
KOREAN_FONT = ROOT / "fonts/SourceHanSerifKR-Heavy.otf"  # SIL OFL, see fonts/LICENSE.txt
OUT = ROOT / "build/poc"
KOREAN = {
    "はい": "예", "いいえ": "아니요", "決定": "결정", "キャンセル": "취소", "戻る": "돌아가기",
    "スキップ": "건너뛰기", "Now Loading…": "불러오는 중…", "ストーリーモード": "스토리 모드",
    "フリーバトル": "프리 배틀", "オプション": "옵션", "ギャラリー": "갤러리", "ショップ": "숍",
}


def official_fs() -> GameFs:
    layers = [DISC_SIM / f"{n}.cpk" for n in ("data0", "data1", "dataRegion0", "dataRegion1")]
    # patch/5 may hold our merged copy; neither file is in the official patch/5.
    layers += [RPCS3_USRDIR / f"data/patch/{n}/data.cpk" for n in range(1, 5)]
    return GameFs(layers)


def build():
    fs = official_fs()
    mf = message.parse(fs.read(COMMON))
    mf = replace(mf, entries=[replace(e, text=KOREAN[e.text]) if e.text in KOREAN else e
                              for e in mf.entries])
    fnt = font.parse(fs.read(font.JPN_FONT))
    have = {g.code for g in fnt.glyphs}
    needed = sorted({c for t in KOREAN.values() for c in t} - {chr(c) for c in have})
    unsupported = [c for c in needed if not ("가" <= c <= "힣")]
    if unsupported:
        raise SystemExit(f"characters missing from font and not Hangul: {unsupported}")
    r = Renderer(KOREAN_FONT, size=24)
    fnt = font.add_glyphs(fnt, [(ord(c), *r.render(c)) for c in needed])
    preview(fnt, needed)
    return [(COMMON, message.serialize(mf)), (font.JPN_FONT, font.serialize(fnt))], needed


def preview(fnt, chars):
    top = fnt.free_top() // 4 * 4
    for g in fnt.glyphs:
        if chr(g.code) in chars:
            top = min(top, g.y // 4 * 4)
    region = dxt5.decode_alpha(font.texture_region(fnt, 0, top, 512, 32), 512, 32)
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(region).resize((1024, 64), Image.NEAREST).save(OUT / "hangul_preview.png")


def main(cmd: str) -> None:
    if cmd == "install":
        files, chars = build()
        print("added glyphs:", "".join(chars))
        print(merge.install(RPCS3_USRDIR, files, OUT))
    elif cmd == "uninstall":
        merge.uninstall(RPCS3_USRDIR)
        print("restored official patch/5/data.cpk")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
