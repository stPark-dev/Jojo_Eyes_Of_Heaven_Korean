<p align="center">
  <img src="jojo_cover_ko.png" alt="죠죠의 기묘한 모험 Eyes of Heaven 한글화 표지" width="420">
</p>

<h1 align="center">죠죠의 기묘한 모험 Eyes of Heaven 한글화</h1>

<p align="center">
  PS3 일본판 <code>BLJS10318</code> · 1.05 업데이트 기반 · RPCS3 전용 비공식 한글 패치
</p>

---

> [!WARNING]
> **개발 중입니다.** 아직 배포 가능한 패치가 없습니다. 지금 저장소에는 분석·빌드 도구와 테스트만 있습니다.

## 목표

- 게임 내 **텍스트 전체 한글화**: 메뉴, 스토리, 전투 대사, 도감 설명 등 약 26,600개 항목
- **이미지 속 글자 한글화**: 캐릭터 이름 이미지, 팁 화면, 스토리 화면 등
- **1.05 업데이트를 기반으로** 동작하는 패치

### 범위에서 제외한 것

| 항목 | 이유 |
|---|---|
| 60fps 패치 | RPCS3용 60fps 패치는 작성자 안내에 따르면 **투사체 속도가 2배**가 되고 **전투 전 대사가 중간에 끊깁니다**. 게임 밸런스와 진행에 해가 되므로 넣지 않습니다. |
| PS3 실기 | RPCS3 에뮬레이터만 지원합니다. |

## 진행 상황

| 단계 | 상태 |
|---|---|
| 디스크·업데이트 구조 분석 | ✅ 완료 |
| CPK 아카이브 읽기/쓰기 (CRILAYLA, DPK 분할 압축 포함) | ✅ 완료 |
| 텍스트 추출·재삽입 (1.05 최종 텍스트 88개 파일 바이트 단위 왕복 일치) | ✅ 완료 |
| 패치 적용 방식 인게임 검증 (`patch/5` 병합) | ✅ 완료 |
| 한글 폰트 삽입 (NFH 비트맵 폰트, DXT5 아틀라스) | ✅ 인게임 표시 확인 |
| 번역 관리 파일 (88개 파일, 26,610문장, 원문 미포함) | ✅ 완료 |
| 용어집 확정 (국내 정식판 표기 기준) | ⏳ 예정 |
| 번역 (초안 → 검수) | ⏳ 예정 |
| 이미지 한글화 | ⏳ 예정 |
| 배포 패키지 | ⏳ 예정 |

## 동작 방식

1.05 실행 파일은 `USRDIR/data/patch/1` ~ `5`의 업데이트 아카이브만 고정으로 읽습니다(`patch/6`을 추가해도 무시됨을 RPCS3 로그로 확인). 그래서 한글 데이터를 **공식 `patch/5/data.cpk`에 병합**합니다. 원본은 `data.cpk.kr-backup`으로 보관하고, **게임 실행 파일(EBOOT)은 건드리지 않습니다.** 5번 레이어가 1~4번보다 우선하므로 텍스트·폰트 모두 교체됩니다.

```
dev_hdd0/game/BLJS10318/USRDIR/
├── EBOOT.BIN                     (1.05 공식, 변경 없음)
└── data/patch/
    ├── 1 … 4/data.cpk            (공식 업데이트)
    └── 5/data.cpk                (공식 5번 내용 + 한글 텍스트·폰트)
        data.cpk.kr-backup        (공식 원본 백업)
```

### 한글 폰트

게임 폰트(`FOT-ModeMinA Std`, 2048×2048 DXT5 아틀라스)의 빈 영역에 한글 글리프를 추가합니다. 글꼴은 **본명조 Heavy (Source Han Serif KR Heavy, SIL OFL 1.1)** 24px입니다. 라이선스는 [`fonts/LICENSE.txt`](fonts/LICENSE.txt)를 참고하세요.

## 사용 환경 (예정)

- [RPCS3](https://rpcs3.net/) 최신 버전
- PS3 펌웨어 **4.76 이상**
- 본인이 소유한 **일본판 디스크** 덤프 (`BLJS10318`)
- 공식 업데이트 **1.01 ~ 1.05** 순서대로 설치

## 개발

Python 3.11 이상이 필요합니다.

```bash
pip install cryptography numpy pillow pytest
python3 -m pytest
```

테스트와 스크립트는 아래 경로에서 게임 데이터를 찾습니다(테스트는 없으면 건너뜀). 환경 변수 → 저장소 루트의 `eoh.local.toml`(git 제외) → 기본값 순으로 정합니다.

| 환경 변수 | `eoh.local.toml` 키 | 기본값 | 내용 |
|---|---|---|---|
| `EOH_DISC_SIM` | `disc_sim` | `game/PS3_GAME/USRDIR/data/sim` | 디스크의 `data*.cpk` |
| `EOH_RPCS3_USRDIR` | `rpcs3_usrdir` | `~/.config/rpcs3/dev_hdd0/game/BLJS10318/USRDIR` | RPCS3에 설치된 게임(병합 설치 대상) |
| `EOH_PATCH_ROOT` | `patch_root` | `<rpcs3_usrdir>/data/patch` | 설치된 공식 업데이트 |

RPCS3를 포터블로 쓰는 윈도우 환경 예시:

```toml
# eoh.local.toml
rpcs3_usrdir = "C:/rpcs3/dev_hdd0/game/BLJS10318/USRDIR"
```

### 구조

```
src/eoh/
├── utf_table.py   CRI @UTF 테이블 읽기/쓰기
├── crilayla.py    CRILAYLA 압축 해제
├── cpk.py         CPK 읽기(분할 압축 포함)·쓰기
├── layers.py      디스크 + 업데이트 레이어 겹쳐 읽기
├── message.py     텍스트 테이블(.bin.xfbin) 파싱·재구성
├── merge.py       공식 patch/5에 병합 설치·제거 (원본 백업)
├── font.py        NFH 비트맵 폰트 파싱·재구성·글리프 추가
├── dxt5.py        DXT5 아틀라스 알파 인코딩/디코딩
├── glyph_render.py 아웃라인 폰트 → 글리프 비트맵·메트릭
├── textdb.py      번역 파일 동기화·태그 검사·적용
└── paths.py       로컬 게임 데이터 경로 (환경 변수 / eoh.local.toml)
scripts/
├── textdb.py      번역 파일 sync / export / status
├── poc_marker.py  텍스트 교체 검증용 PoC
└── poc_hangul.py  한글 폰트 표시 검증용 PoC
translation/       번역 파일 (원문 대신 원문 SHA-1만 저장)
fonts/             본명조 Heavy + OFL 라이선스
tests/             pytest
```

## 저작권 안내

- 이 저장소에는 **게임 데이터(디스크 이미지, 업데이트 파일, 추출한 리소스)가 포함되어 있지 않으며 앞으로도 포함하지 않습니다.** 정품을 소유한 분이 직접 덤프한 데이터에만 적용할 수 있습니다.
- 『죠죠의 기묘한 모험』 및 『ジョジョの奇妙な冒険 アイズオブヘブン』의 저작권은 ©荒木飛呂彦/集英社, ©BANDAI NAMCO Entertainment Inc. 등 각 권리자에게 있습니다. 표지 이미지는 공식 패키지 아트에 한글 로고를 합성한 것으로, 원본 아트의 권리는 권리자에게 있습니다.
- 비공식 팬 번역 프로젝트이며, 권리자와 관련이 없습니다.
