# 인수인계 (2026-10-28 기준)

다른 컴퓨터에서 이어서 작업하기 위한 문서입니다. 결정 사항·환경 준비·다음 작업·주의 사항을 모두 여기에 모았습니다.
(작업 PC의 Claude 메모리와 `work/` 폴더는 git에 올라가지 않으므로, 필요한 내용은 이 문서에 옮겨 두었습니다.)

## 1. 현재 상태 한눈에 보기

| 항목 | 상태 |
|---|---|
| 대상 | PS3 일본판 `BLJS10318` + 공식 업데이트 1.05, **RPCS3 전용** |
| 패치 적용 방식 | 공식 `patch/5/data.cpk`에 한글 파일 병합 (인게임 확인 ✅) |
| 텍스트 교체 | 길이 변경 포함 인게임 확인 ✅ |
| 한글 폰트 | 게임 폰트 아틀라스에 한글 추가 → "불러오는 중…", "결정", "돌아가기" 인게임 확인 ✅ |
| 번역 파일 | `translation/` 88개 파일, 26,610문장 (원문 미포함). 의성어 415개는 원문 유지 처리 완료 |
| 용어집 | `translation/glossary.json` 후보 277개 생성, **표기 조사 진행 중** (아래 4-1) |
| 이미지 | 넣기·ChatGPT·자동 생성 도구 완료, 131장 한글화 (아래 4-3) |
| 테스트 | pytest 81개 통과 |
| 60fps | **제외** (투사체 속도 2배·전투 전 대사 끊김 → 밸런스 훼손) |

## 2. 사용자 결정 사항 (변경 시 사용자 확인 필요)

1. **대상 환경**: RPCS3 전용. 실기(PS3) 미지원.
2. **60fps 패치 철회**: 게임 밸런스·진행에 해가 되면 철회한다는 기준에 따라 제외.
3. **번역 방식**: Claude가 초안 → 사람이 검수.
4. **고유명사 기준 (우선순위, 2026-10-28 확정)** — 상세는 `translation/glossary.json`의 `policy`
   1. **애니북스 정식판 만화** (8부 죠죠리온은 **문학동네** 정식판도 동일 1순위) — 인명, 스탠드명, 기술명, 지명, 설정 용어
   2. 애니메이션 국내판 — 말투, 대사 분위기, 만화판 표기가 불명확한 항목
   3. 원작 일본어 — 두 판본이 충돌하거나 오역이 의심될 때 의미 확인
   - **DIO**: 1부 '디오', 3부 이후 'DIO'. 회상·특수 대사는 장면 맥락으로 판단
   - **쇄별 표기**: 최신 쇄 정정 표기 우선. 변경 사례('기둥 속 사내', '신사폭풍')는 실제 최신 쇄 확인 후 반영, 기존 표기는 별칭(alt)
   - **3부 스탠드명**: 단행본 본문 확인 후 확정 (책 소개 영문 표기만으로 확정 금지)
   - 공식 표기 미확인 항목은 임의 확정 금지 / 게임 전체 표기 일관성 유지 / 예외는 사유 기록
   - 이미 번역된 문자열도 확정 용어집으로 일괄 검사: `python3 scripts/textdb.py check-glossary`
5. **의성어(擬音)**: 일본어 그대로 둔다.
6. **한글 글꼴**: 본명조 Heavy (Source Han Serif KR Heavy, SIL OFL), 24px, 글꼴 자체 자간(고정 26px은 너무 벌어져 보여 기각).
7. **응답 언어**: 사용자에게 보이는 모든 글(진행 메시지·명령 설명 포함)은 한국어.
8. **게임 원문 비공개**: 일본어 대본은 저장소에 올리지 않는다 (번역 파일에는 원문 SHA-1만).

## 3. 새 컴퓨터 환경 준비

### 3-1. 저장소와 Python
```bash
git clone https://github.com/stPark-dev/Jojo_Eyes_Of_Heaven_Korean.git jojo
cd jojo
pip install cryptography numpy pillow pytest fonttools
```

### 3-2. 게임 디스크
- 본인 소유 디스크 덤프 ISO를 `game/`에 풀어 둡니다 (`game/PS3_GAME/...`, `game/PS3_DISC.SFB`).
  - `7z x -ogame "<ISO 경로>"` — PS3 디스크 특성상 7-Zip이 "Headers Error"를 내지만 파일은 정상입니다(크기 대조로 확인함).
- RPCS3: **File → Add Games** 로 `game/` 폴더 등록.

### 3-3. 펌웨어
- 게임이 4.76 이상을 요구합니다. 디스크에 들어 있는 `game/PS3_UPDATE/PS3UPDAT.PUP`(4.76)를 **File → Install Firmware** 로 설치하면 됩니다.

### 3-4. 공식 업데이트 1.01 ~ 1.05
- 목록: `https://a0.ww.np.dl.playstation.net/tpl/np/BLJS10318/BLJS10318-ver.xml` (소니 자체 인증서라 `curl -k` 필요)
- 각 PKG는 `http://b0.ww.np.dl.playstation.net/tppkg/np/BLJS10318/BLJS10318_T5/a2134ee5fa32df60/JP0700-BLJS10318_00-JOJOEOH000000000-A01NN-V0100-PE.pkg` (NN = 01~05)
- 검증: XML의 sha1sum은 **PKG 마지막 32바이트를 뺀** 내용의 SHA-1입니다. `head -c -32 파일 | sha1sum`
  - 01 `36a616f0…` / 02 `d2bf43df…` / 03 `414c9822…` / 04 `194234a0…` / 05 `18b4ad20…`
- RPCS3 **File → Install Packages/Raps/Edats** 로 5개를 한 번에 설치 → 게임 목록에 01.05로 표시되면 정상.
- 첫 실행 시 게임이 데이터 설치(약 2.7GB, `dev_hdd0/.../USRDIR/data/sim/`)를 합니다.

### 3-5. 테스트
```bash
python3 -m pytest -q        # 81 passed 가 정상 (게임 데이터 없으면 해당 테스트는 skip)
```
- 테스트는 `game/PS3_GAME/USRDIR/data/sim/*.cpk` 와 `~/.config/rpcs3/dev_hdd0/game/BLJS10318/USRDIR/data/patch/N/data.cpk` 를 읽습니다. 경로가 다르면 `EOH_DISC_SIM`, `EOH_PATCH_ROOT` 환경 변수로 지정.
- `patch/5`에 병합본이 설치돼 있어도 `data.cpk.kr-backup`(공식 원본)을 자동으로 기준으로 삼습니다.

### 3-6. 작업용 원문 파일 다시 만들기
```bash
python3 scripts/textdb.py sync     # translation/ 갱신 (원문 변경 감지)
python3 scripts/textdb.py export   # work/translate/*.jsonl (원문+번역, git 제외)
python3 scripts/textdb.py status
```

## 4. 진행 중 / 다음 작업

### 4-1. 용어집 (조사 완료, 사용자 승인 대기)
- `translation/glossary.json` 277개 전부 조사 반영: **verified 125 / derived 45 / unverified 107**. 모든 항목 `state=unresolved`.
- 분류: 인물 161, 스탠드 64, 지명 21, 파트 제목 16, 기타 15.
- 3부 스탠드 18개에는 `needs_book_check` 표시 (정책상 단행본 본문 확인 전 확정 금지).
- 2026-10-28 미결 질문 7건 결정 → `resolved_questions`에 기록 (8부 죠스케 구분, 은두르, 나르시소 안나수이, 9영신 '신/여신' 붙임, D4C 영문+정발 번역 병기, 스탠드 유저, 부 제목 반각 Part·5부도 Part5). 승인 6개(T0051, T0052, T0066, T0125, T0278, T0279). 남은 `open_questions` 2건은 근거 재확인 작업.
- 2026-10-28 정발 근거 `verified` 112개 일괄 승인 (`needs_book_check` 3부 스탠드 10개 제외) → 승인 118 / 미승인 161 (단행본 확인 대기 10, derived·unverified 등).
- (이전) `open_questions`에 결정이 필요한 9건 기록 (定助/仗助 구분, 은두루/은두르, D4C 영문 유지 여부, 이집트 9영신 '신' 포함 여부, '스탠드 유저' 띄어쓰기 등).
- 근거 주의: 일부 인용문은 웹 요약 결과라 원문 글자 대조가 안 됨 → 승인 전 URL 재확인 권장. yes24 일부 페이지는 자동 수집이 막힘.
- 다음: 사용자가 항목별로 `state`를 `approved`로 바꾸면 `python3 scripts/textdb.py check-glossary`가 번역 전체에 일관성 검사를 적용.

### 4-2. 번역
1. 용어집 승인 → 2. `messageInfo_common`(UI) 초안 → 3. 스토리(`messageInfo_adv`), 전투(`messageInfo_btl`), 캐릭터 대사(`EoH_battleChara_*`) 순.
- 번역은 `work/translate/*.jsonl`에서 작업 후 `translation/*.json`의 `ko`/`state`/`note`에만 반영 (원문·`src_sha1` 수정 금지).
  - 반영: `python3 scripts/textdb.py import work/translate/drafts/<파일명>.jsonl` (원문 지문·태그 검사, 초안은 `distribution_eligible`로 올릴 수 없음, 원문 유지 항목 보호)
  - 2026-10-28: `messageInfo_common` 시스템 문구 103개 초안 반영 (needs_review 99, 게임 제목·약칭 4개 needs_human_review).
  - 2026-10-28: `messageInfo_common` 나머지 10,389문장 초안 반영 (서브에이전트 8개 병렬, `work/translate/STYLE.md` 지침). 파일 전체 초안 완료: needs_review 9,188 / needs_human_review 1,304 / 의성어 원문 유지 415. 같은 원문은 같은 번역으로 통일, 묶음 간 표기 차이는 STYLE.md 6절 표기로 통일(용어집 미확정). 빌드 시 한글 1,176자 추가(용량 약 1,700자 안).
  - 2026-10-28: 나머지 87개 파일 초안 완료 (중복 제거 12,475문장을 서브에이전트 9개로 병렬 번역, UI 동일 원문 711문장 재사용). 게임 전체: needs_review 23,528 / needs_human_review 2,207 / 의성어 원문 유지 415 / 미번역 460(개발용 임시 문구, 원문 유지 결정). 빌드 시 폰트 추가 1,268자 (실측 용량 2,046자).
  - 통일 결정은 `translation/STYLE.md` 6·8절 (전투 용어, 시게치 '~다구' 말투, 임시 문구 원문 유지 등). 다음 단계: 사람 검수(needs_human_review 우선), 미승인 용어 161개 검토, 인게임 줄 넘침 확인.
  - 용어집 `src_exclude`: 용어를 포함하지만 그 용어가 아닌 긴 단어(ミスター, サンディエゴ, ジョセフミ, トルネーディオーバードライブ)를 검사에서 제외.
- 태그 규칙: `<string />`, `<icon …>`, `<color …>…</color>`, `<system …>`, `<progress>`는 **반드시 보존**(순서는 바뀌어도 됨). `<ruby 읽기>글자</ruby>`는 빼거나 바꿔도 되지만 짝은 맞아야 함. 「<１>」 같은 전각 숫자는 태그가 아님.
- 상태: `untranslated → in_progress → needs_review → (needs_human_review) → distribution_eligible`. 배포 빌드는 전부 `distribution_eligible`일 때만 통과.
- 원문 유지 예외는 `keep_source: "사유"` (번역문과 동시 지정 불가).

### 4-3. 이미지 속 글자
- 일본어 전용 파일 224개 → 이미지 434장 (텍스처 432장: DXT5 335, DXT1 97 + 세이브 아이콘 PNG 2).
- **추출**: `python3 scripts/extract_images.py` → `work/images/` (git 제외)에 PNG, `work/images/_overview/NN.png`에 분류별 한눈에 보기(번호는 `NN.txt`에 PNG 경로). 약 20초.
- **작업 목록**: `translation/images.json` — 텍스처마다 파일·순번·크기·형식·원본 SHA-1·분류·PNG 경로·state(todo/in_progress/needs_review/done/keep_original)·note. 다시 추출해도 state/note 유지, 원본이 바뀌면 needs_review.
- 분류 집계 (2026-10-28): 캐릭터 이름 115 / 팁 화면 97 / UI 메뉴 96 / 전투 연출 55 / 스토리 UI 52 / 스토리 연출 14 / 타이틀 로고 3 / 세이브 아이콘 2. 팁 화면 일부는 「仮画像」 DLC 자리표시.
- **넣기 (2026-10-29)**: 한글 PNG를 `translation/images_ko/<images.json의 png 경로>`에 원본과 같은 크기로 두면 `build_patch.py`가 DXT1/DXT5로 인코딩해 텍스처를 교체(`src/eoh/images.py`, `texture.encode/replace`). 게임 텍스처 432장 재인코딩 오차 평균 1 미만. 밉맵 텍스처 2장은 미지원(오류). 크기 불일치·원본 변경은 빌드 실패, release는 `done`/`keep_original`만 통과.
- 제작 분담(사용자 결정 2026-10-29): 중요·큰 이미지(캐릭터 이름 포함)는 ChatGPT로 제작, 중요도 낮은 이미지는 Claude 자동 생성.
- `images.json` 항목에 `ko`(한글 문구, 여러 줄은 `\n`)와 `maker`(gpt/auto)를 기록 — `extract_images.py`를 다시 돌려도 유지.
- **ChatGPT 작업** (`scripts/gpt_images.py`): `pack <분류>` → `work/gpt/<분류>/`에 6줄씩 시트 프롬프트(`sheet_NN.txt`)와 `참고_원본스타일.png`. ChatGPT 웹 결과를 `out/sheet_NN.png`로 저장 후 `apply <분류>` → 줄 단위로 잘라(줄 수 지정, 투명 또는 #FF00FF 배경) 원본 글자 상자에 맞춰 `translation/images_ko/`에 저장, `needs_review`.
- **자동 생성** (`scripts/auto_images.py`): 명조체 계열 글자를 본명조 Heavy로 그려 원본 줄 상자에 맞춤. 스타일은 스크립트의 `STYLES`, 그림자 레이어는 `SILHOUETTES`.
- 2026-10-29 완료(인게임 확인): 캐릭터 이름 115장(ChatGPT, 고유 표기 83개), 타이틀 "아무 버튼이나 누르세요".
- 부팅 화면(`data/ui/boot/boot_logo.xfbin`, /jpn/ 밖이라 `extract_images.py`의 `EXTRA_FILES`로 추가): 「ご注意」(cesa, 나눔스퀘어라운드 B)·보잉고 만화 건강 주의(cautions, 본명조)는 `auto_images.py`의 `OVERLAYS`(지울 영역 + 줄별 상자)로 원본 위에 다시 씀. 결과에 게임 그림이 섞이므로 **git 제외 `work/images_ko/`**에 생성 — 새 PC에서는 `extract_images.py` → `auto_images.py` 순서로 다시 만들어야 빌드에 들어감. 로고 등 7장은 keep_original.
- 타이틀 로고(인게임 확인): ChatGPT 결과를 `gpt_images.py place <결과> <png> --glow 16`으로 반영(원본 비율 동일, 바깥 빛 번짐은 원본 측정값으로 보정). 자동 생성(설치, 인게임 확인 대기): 챕터 제목 12장, 「完」, 로드 완료 문구 2장. 새 번역 검수 필요: 흉성 / 유해를 건 게임 / 천국을 바란 남자 / 로드 완료다, 베이비.
- 스토리 UI(2026-10-29): 원본 유지 16 / 자동 5(선공·후공, 저지해라!, 포커 족보, 칩 라벨, 플레이 내용 평가 — 설치됨) / ChatGPT 31(`gpt_group`: 메뉴 제목 8, 관중 함성 2, 단독 21 — 작업 묶음 `work/gpt/스토리_UI/`, 결과 대기). 「グッド!」→「굿!」.
- `gpt_group`: 같은 스타일 줄을 시트로 묶음(`STYLES[group]`), `단독`은 이미지별 폴더(`원본_2배.png`, `프롬프트.txt` → `결과.png`). `ko` 줄 = 조각(위→아래); 조각이 여럿이면 원본 조각 상자(`artfit.row_boxes`)에 하나씩 맞춤.
- 자동 생성 추가 기능: `STYLES`의 `"sample"`(원본 색 측정 `textart.sample_style`, 흰 테두리+진한 외곽선 이중 테두리 인식), `LINE_STYLES`(줄별 색 지정), OVERLAYS의 `"above"`(위 행 복사로 글자 지우기)·투명 지우기·영어 줄 유지(None)·오른쪽 정렬.
- 분류:
  - 모드 선택 큰 글자(STORY 등): 영어 장식 → 유지
  - 타이틀 로고: 한글 로고로 교체 후보 (사용자 표지 이미지의 한글 로고 원본 확인 필요)
  - 저작권 표기: 원문 유지
  - 캐릭터 이름 이미지(손글씨풍, 약 115개): 용어집 확정 후 제작. **글꼴 방식 미정**(손글씨풍 vs 본명조 통일)
  - 팁 화면(게임 캡처 + 작은 일본어 UI, 약 84개): 번역 후 한글판 화면을 다시 캡처해 교체하는 방안
  - 나머지 약 220개(상점, 커맨드 목록, 전투 연출 등): 미분류

### 4-4. 폰트 용량
- 아틀라스 빈 영역은 y=1380 아래 약 670px → **약 1,700자**만 추가 가능 (한글 2,350자보다 적음).
- 방안: 번역에 실제로 쓰인 한글만 넣기(보통 1,000~1,500자). 부족하면 쓰이지 않는 한자 칸 재사용 검토.

### 4-5. 배포 빌드
- 개발용 빌드·설치는 구현됨: `python3 scripts/build_patch.py check | install | uninstall [--release]` (번역 적용 → 쓰인 한글만 폰트에 추가 → `patch/5` 병합). 2026-10-28 기준 한국어 번역문은 0문장이라 설치해도 화면 변화 없음.
- 배포물에 공식 파일(`6ddw01prm.bin.xfbin` 등)을 넣지 않으려면, 사용자 PC의 공식 patch/5에서 병합하는 설치기 형태가 필요.

## 5. 기술 메모

- **레이어**: 디스크 `data0/data1/dataRegion0/dataRegion1.cpk` → `patch/1..5/data.cpk` 순서로 덮어씀. 텍스트 88개 중 81개는 patch3, 7개(`messageInfo_common`, `messageInfo_btl` 등)는 patch4가 최종. 일본어 폰트는 patch1.
- **EBOOT는 patch/1~5만 연다** (`version.txt`를 6으로 바꿔도 patch/6은 열지 않음 — RPCS3 sys_fs 로그로 확인). 그래서 patch/5 병합.
- **CPK**: 압축 엔트리는 중첩 CPK(DPK, 128KiB CRILAYLA 청크). 우리 writer는 비압축, TOC는 `경로.upper()` 정렬. 공식 CPK 헤더 테이블 뒤 정체불명 4바이트는 0으로 써도 게임이 정상 동작.
- **텍스트 테이블**: 0x3E9 마커 뒤 count, 0x18바이트 엔트리(해시, 상대 포인터, 8바이트 부가정보), 4바이트 정렬 UTF-8 문자열 풀. 1.05 최종 88개 파일 모두 바이트 단위 왕복 일치.
- **폰트**: NFH, 256칸 조회 테이블(상위 바이트별 `첫 인덱스 - 첫 코드 하위바이트`), 0x20바이트 글리프 레코드(UCS-2, 아틀라스 좌표, FreeType 순서 메트릭 1/64px), NTP3 2048×2048 DXT5(알파=글자, RGB=흰색). 원본 글꼴명 `FOT-ModeMinA Std`.
- 한 번 "※Now Loading…"에서 멈춘 적이 있으나 재현 안 됨(GUI 재실행·헤드리스 모두 정상). 다시 생기면 RPCS3 로그 보관 후 추적.

## 6. 주의 사항 (실제로 겪은 것)

- `rpcs3 --help`처럼 RPCS3를 실행하기만 해도 `~/.cache/rpcs3/RPCS3.log`가 **새로 덮어써짐** → 필요한 로그는 먼저 복사.
- RPCS3 로그의 `ppu_loader ... import: [함수명]` 줄에 함수 이름이 미리 찍히므로, 로그로 진행 여부를 판정할 때 함수명만으로 찾으면 오판. 실제 호출 형태(`cellSaveDataAutoLoad2(version=`)로 찾을 것.
- `pkill -f "<패턴>"`은 그 명령을 실행한 셸 자체도 죽일 수 있음.
- RPCS3 헤드리스 실행: `rpcs3.AppImage --headless <game/PS3_GAME 경로>` (창 없이 부팅 검증 가능, 단 버튼 입력은 불가).
- 화면 캡처가 필요하면 바탕화면 전체가 아니라 게임 창만, 그리고 사용자에게 먼저 확인.
  - 창 캡처는 Vulkan 창이 갱신되지 않아 옛 화면이 찍힘 → RPCS3 자체 스크린샷(F12, `screenshots/BLJS10318/`)을 쓸 것.
  - 인게임 확인 스크린샷은 프로젝트의 `screenshots/ingame/<날짜>/`에 보관하고 git에 올린다.
- 커밋·푸시는 사용자가 요청할 때만. 커밋 메시지에 Co-Authored-By 넣지 않음(사용자 설정).
- 코드 수정 전 테스트 실행, 새 기능은 테스트 먼저(TDD) — 사용자 전역 규칙.

## 7. PoC 스크립트 (작업 PC의 RPCS3에는 현재 한글 PoC가 설치된 상태)

```bash
python3 scripts/poc_hangul.py install     # 한글 몇 줄 + 글리프를 patch/5에 병합 설치
python3 scripts/poc_hangul.py uninstall   # 공식 patch/5 복원 (data.cpk.kr-backup)
python3 scripts/poc_marker.py install     # 모든 공통 문구 앞에 ※ (텍스트 교체 확인용)
```
