"""Korean lines written over the tip pictures (ui/tips_cmn, 256x256 screenshots) by retext.

TIPS: PNG file stem -> [(rect around one original line, Korean text, options)].
Options go to eoh.retext (align, polarity, clip, fill, stroke); art=(png, line index or None)
pastes that piece of a finished Korean picture instead of drawing the text. Only lines readable at 256 px
are rewritten; tiny list text is left as it is. Wording follows the message translations.
"""
L, R, C = dict(), dict(align="right"), dict(align="center")
DARK = dict(polarity="dark")
CLIP = dict(clip=True)

_CUSTOMIZE_TOP = [
    ((38, 84, 113, 97), "캐릭터 편집", L),
    ((63, 107, 202, 120), "듀얼 콤보·승리 세트 편집", L),
    ((63, 130, 129, 143), "프리셋 편집", L),
]
_TRADE = [
    ((115, 41, 137, 52), "전체", C),
    *[((38, y, 57, y + 9), "승률", DARK) for y in (74, 111, 149, 186)],
    *[((125, y, 170, y + 9), "죠죠리티", DARK) for y in (83, 120, 158, 195)],
    ((120, 208, 152, 217), "잠금 수", dict(fill=(255, 255, 255))),
    ((155, 226, 256, 235), "열람할 트레이드 카드를 선택해 주십시오.", CLIP),
]
_RETRY = [
    ((110, 110, 146, 120), "재도전", C),
    ((78, 122, 178, 132), "캐릭터 선택으로", C),
    ((91, 133, 165, 143), "모드 선택으로", C),
]
_PARTS = ["팬텀 블러드", "전투조류", "스타더스트 크루세이더즈", "다이아몬드는 부서지지 않는다",
          "황금의 바람", "스톤 오션", "스틸 볼 런", "죠죠리온"]
_POKER = "ui/adv/jpn/adv_poker_txt/"
_PART_ROWS = [53, 70, 86, 102, 118, 135, 151, 167]

TIPS = {
    "00_tips_customize_00_00": _CUSTOMIZE_TOP + [
        ((95, 222, 256, 235), "듀얼 콤보·승리 연출 시 캐릭터의 포즈와 대사·의성어를 설정합니다.", CLIP)],
    "01_tips_customize_00_01": _CUSTOMIZE_TOP + [
        ((71, 222, 256, 235), "캐릭터의 코스튬·컬러·듀얼 콤보·승리 세트 프리셋 리스트를 작성·관리합니다.", CLIP)],
    "00_tips_customize_03_00": [
        ((0, 21, 78, 32), "플레이어 카드 편집", dict(align="right", clip=True)),
        ((185, 70, 217, 78), "쿠죠 죠타로", R),
        ((170, 87, 217, 94), "이거 참 골치 아프군", R),
        ((38, 151, 56, 159), "승리 수", L), ((38, 165, 56, 173), "패배 수", L),
        ((38, 178, 56, 186), "대전 수", L), ((38, 191, 73, 199), "총 플레이 시간", L),
        ((135, 151, 160, 159), "끊김 횟수", L), ((135, 178, 174, 186), "죠죠리티", L),
        ((0, 224, 80, 234), "…을 선택해 주십시오.", dict(align="right", clip=True)),
    ],
    "00_tips_customize_05_00": [
        ((99, 18, 205, 29), "플레이어 카드 편집", L),
        *[((86, y, 221, y + 10), t, L) for y, t in zip(_PART_ROWS, _PARTS)],
        ((43, 210, 216, 220), "캐릭터의 카드 배경을 선택해 주십시오.", C),
    ],
    "00_tips_customize_07_00": _TRADE,
    "01_tips_customize_07_01": _TRADE,
    "00_tips_network_00_00": [
        ((41, 99, 124, 111), "온라인 배틀", L),
        ((71, 124, 157, 136), "플레이어 매치", L),
        ((71, 150, 136, 161), "랭크 매치", L),
    ],
    "00_tips_network_01_00": [
        ((9, 98, 92, 110), "온라인 배틀", L),
        ((38, 124, 124, 135), "플레이어 매치", L),
        ((66, 150, 244, 162), "싱글 플레이(VS 1USER)", L),
        ((66, 175, 236, 187), "더블 플레이(VS 2USER)", L),
    ],
    "00_tips_network_02_00": [
        ((81, 101, 176, 115), "퀵 매치", C),
        ((81, 119, 176, 133), "커스텀 매치", C),
        ((75, 136, 182, 150), "크리에이트 매치", C),
    ],
    "01_tips_network_02_01": [
        ((0, 57, 82, 67), "플레이어 매치", dict(DARK, align="right", clip=True)),
        ((91, 85, 155, 97), "참가자 1/2", dict(DARK, align="center")),
        ((8, 128, 31, 137), "대전 수", DARK), ((8, 139, 31, 149), "승패 수", DARK),
        ((8, 150, 38, 159), "끊김 횟수", DARK), ((126, 161, 175, 169), "죠죠리티", DARK),
    ],
    "03_tips_network_03_01": [
        ((0, 77, 83, 88), "플레이어 매치", dict(DARK, align="right", clip=True)),
        ((91, 105, 155, 117), "참가자 1/4", dict(DARK, align="center")),
        ((126, 138, 175, 147), "죠죠리티", DARK),
    ],
    "00_tips_network_04_00": [
        ((103, 100, 154, 108), "커스텀 매치", C),
        ((30, 120, 62, 128), "지역", L), ((171, 120, 209, 128), "같은 지역", C),
        ((30, 131, 67, 139), "배틀 타임", L), ((175, 131, 205, 139), "지정 안 함", C),
        ((30, 142, 60, 150), "상대의 강함", L), ((175, 142, 205, 150), "상관없음", C),
    ],
    "00_tips_network_06_00": [
        ((98, 99, 159, 108), "크리에이트 매치", C),
        ((30, 120, 62, 128), "지역", L), ((171, 120, 209, 128), "같은 지역", C),
        ((30, 131, 72, 138), "팀 배정", L), ((175, 131, 205, 138), "셔플", C),
        ((30, 142, 79, 149), "세션 타입", L), ((175, 142, 205, 149), "퍼블릭", C),
        ((30, 152, 67, 160), "배틀 타임", L),
    ],
    "00_tips_story_02_00": [((90, 120, 188, 133), "공격: 파괴한다", L)],
    "00_tips_story_06_00": [
        ((48, 86, 95, 93), "카이로 시가지 옥상", DARK), ((46, 99, 82, 108), "콜로세움", DARK),
        ((143, 202, 211, 213), "카이로 시가지 옥상", DARK), ((143, 223, 193, 233), "콜로세움", DARK),
    ],
    "00_tips_story_09_00": _RETRY,
    "01_tips_story_09_01": _RETRY,
    "00_tips_story_10_00": [
        ((81, 85, 152, 94), "불길한 예감이 든다…", L),
        ((81, 95, 175, 104), "이대로 머무르시겠습니까?", L),
        ((120, 111, 138, 119), "예", C), ((116, 122, 141, 130), "아니요", C),
    ],
    "00_tips_story_15_00": [((111, 30, 184, 44), "붙잡는다", L)],
    "01_tips_story_16_01": [
        ((92, 155, 132, 164), "소지 칩", DARK), ((163, 155, 204, 164), "베팅 칩", DARK),
        ((92, 188, 148, 197), "속임수 난이도", DARK),
        ((90, 220, 173, 240), "속임수 「가」능!", dict(art=(_POKER + "21_tex21.png", 1))),
    ],
    "02_tips_story_16_02": [
        ((150, 47, 188, 63), "레이즈", dict(DARK, align="center", art=(_POKER + "13_tex13.png", 0)))],
    "03_tips_story_16_03": [
        ((77, 103, 177, 143), "콜", dict(DARK, align="center", art=(_POKER + "13_tex13.png", 1)))],
    "04_tips_story_16_04": [
        ((51, 7, 251, 53), "죠타로 속임수 발동!", dict(polarity="diff", align="center",
                                                   art=(_POKER + "19_tex19.png", None))),
        ((41, 136, 205, 147), "제한 시간 내에 순서대로 버튼을 누르자!", C)],
    "05_tips_story_16_05": [
        ((53, 63, 240, 110), "죠타로 블러프 발동!", dict(polarity="diff", align="center",
                                                   art=(_POKER + "01_tex01.png", None)))],
    "01_tips_story_10_01": [
        ((17, 55, 240, 172), "강적 출현!!", dict(DARK, align="center", within=200,
                                              art=("ui/adv/jpn/adv_encounter_txt/00_adv_encount_txt.png", None)))],
    "00_tips_story_14_00": [
        ((10, 32, 137, 87), "맘마미아!", dict(polarity="diff", align="center",
                                           art=("ui/adv/jpn/adv_crowd_txt/01_btl_combo_txt.png", 4)))],
}

_ADV = "ui/adv/jpn/"


def _title(rect, text, png):
    """A story-menu title drawn as art: paste the finished Korean title over it."""
    return rect, text, dict(polarity="diff", align="left", art=(png, None))


TIPS.update({
    "00_tips_customize_01_00": [
        ((106, 74, 197, 83), "듀얼 콤보·승리 세트 편집", L), ((113, 90, 137, 96), "쿠죠 죠타로", C)],
    "00_tips_customize_02_00": [((108, 66, 150, 74), "프리셋 편집", L)],
    "01_tips_customize_03_01": [((100, 71, 161, 79), "플레이어 카드 편집", L)],
    "00_tips_customize_04_00": [
        ((102, 66, 165, 73), "플레이어 카드 편집", L), ((146, 79, 216, 86), "스타더스트 크루세이더즈", L)],
    "02_tips_network_03_00": [((125, 70, 165, 76), "플레이어 매치", DARK)],
    "00_tips_network_05_00": [((110, 81, 146, 87), "세션 목록", dict(DARK, align="center"))],
    "00_tips_network_07_00": [((108, 87, 148, 94), "BP 랭킹", dict(polarity="diff", align="center"))],
    "01_tips_network_07_01": [((108, 87, 148, 94), "BP 랭킹", dict(polarity="diff", align="center"))],
    "00_tips_story_04_00": [_title((23, 17, 103, 43), "어빌리티 트리", _ADV + "adv_skill_txt/00_adv_skill_txt.png")],
    "01_tips_story_04_01": [_title((18, 65, 101, 88), "어빌리티 트리", _ADV + "adv_skill_txt/00_adv_skill_txt.png")],
    "00_tips_story_05_00": [_title((8, 63, 57, 80), "신뢰도", _ADV + "adv_storymenu_txt/03_adv_storymenu_trust_txt.png")],
    "02_tips_story_07_02": [_title((10, 65, 87, 80), "서포트 아이템 사용",
                                   "ui/supportitem_menu/jpn/supportitem_menu_txt/02_supportitem_menu_title_txt.png")],
    "00_tips_story_12_00": [_title((20, 65, 96, 84), "시련을 기다리는 빛",
                                   _ADV + "adv_btlmemory_txt/00_adv_mission_title_txt.png")],
    "01_tips_story_14_01": [_title((8, 65, 66, 82), "캐릭터 체인지", _ADV + "adv_csel_txt/00_adv_csel_title_change_txt.png")],
    "00_tips_story_20_00": [_title((3, 58, 64, 80), "줄거리", _ADV + "adv_storymenu_txt/01_adv_storymenu_synopsis_txt.png")],
})
TIPS["00_tips_story_06_00"] = [_title((31, 8, 151, 37), "스테이지 이동",
                                      _ADV + "adv_stagechange_txt/00_adv_stagechange_title_txt.png")] + TIPS["00_tips_story_06_00"]
