# 죠죠의 기묘한 모험 아이즈 오브 헤븐 한글 패치 v{{VERSION}}

일본판 PS3 게임 `BLJS10318` 공식 업데이트 1.05용 비공식 팬 한글 패치입니다. **RPCS3 전용**입니다(PS3 실기 미지원).

## 설치하기 — Windows

1. 배포 ZIP을 완전히 풉니다.
2. 게임을 저장하고 RPCS3를 완전히 종료합니다.
3. `install.bat`을 실행합니다.
4. `1`(설치)을 입력하고, 폴더 선택 창에서 `dev_hdd0`가 들어 있는 RPCS3 폴더(또는 `dev_hdd0\game\BLJS10318`)를 고릅니다.
5. "설치 완료"가 나오면 게임을 실행합니다.

명령줄로도 실행할 수 있습니다: `install.bat install D:\RPCS3` / `install.bat verify D:\RPCS3` / `install.bat restore D:\RPCS3`

## 설치하기 — Linux

`xdelta3`가 필요합니다 (예: `sudo apt install xdelta3`).

```sh
sh install.sh install ~/.config/rpcs3        # 설치
sh install.sh verify  ~/.config/rpcs3        # 확인
sh install.sh restore ~/.config/rpcs3        # 되돌리기
```

## 설치기가 하는 일

- 공식 업데이트 1.05의 `patch/1~4/data.cpk`가 맞는지 SHA-256으로 확인합니다. 다르면 아무것도 바꾸지 않고 멈춥니다.
- `patch/5/data.cpk`를 `data.cpk.before-eoh-ko`로 백업하고 `eoh-ko-state.txt`에 설치 전 상태를 기록합니다. **두 파일은 복원에 필요하니 지우지 마세요.**
- 공식 `patch/5/data.cpk`에 차이 패치(`patch/{{PATCH_FILE}}`)를 적용해 한글 `data.cpk`를 만들고, 결과의 SHA-256을 확인한 뒤 교체합니다.
- 다른 패치(영문 패치 등)가 설치되어 있어도, 같은 폴더에 공식 원본 사본(`data.cpk.old` 등)이 있으면 그것을 찾아 씁니다. 복원하면 설치 직전의 그 패치 상태로 돌아갑니다.
- 다른 한글 패치와 동시에 쓸 수 없습니다. 이 패치가 `patch/5/data.cpk`를 통째로 바꿉니다.

## 한글화 범위

- 메뉴·스토리 모드·전투 대사·도감 등 게임 문장 26,610개 중 25,735개를 한국어로 바꿨습니다. 나머지는 원문 그대로 두기로 한 의성어(ゴゴゴ 등) 415개와 화면에 나오지 않는 개발용 임시 문구 460개입니다.
- 이미지 속 글자 443장 중 272장을 한글화했습니다(캐릭터 이름, 메뉴, 전투 연출, 팁 화면, 타이틀 로고, 세이브 아이콘 등). 나머지 171장은 영어 장식 글자·부(Part) 로고·저작권 표기 등 원본을 유지하기로 한 것입니다.
- 한글 글꼴: 본명조 Heavy (Source Han Serif KR), 일부 이미지는 나눔스퀘어라운드.
- 고유명사는 애니북스·문학동네 정식판 표기를 우선했습니다. 정식판 표기를 확인하지 못한 이름도 있습니다.
- 번역 초안은 AI(Claude)로 만들고 AI(ChatGPT) 검수와 제작자 확인을 거쳤습니다. 어색한 문장이나 오역이 남아 있을 수 있습니다.
- 60fps 패치는 포함하지 않습니다(게임 속도·밸런스가 달라짐).

## 문제가 생기면

- **게임 폴더를 찾지 못함**: `dev_hdd0`가 들어 있는 RPCS3 폴더 또는 `dev_hdd0/game/BLJS10318`을 고르세요.
- **공식 업데이트 1.05가 아님**: RPCS3에서 일본판 BLJS10318에 공식 업데이트 01.05를 설치했는지 확인하세요.
- **공식 원본을 찾지 못함**: 다른 패치를 쓰고 있다면 그 패치의 복원 기능으로 먼저 공식 상태로 돌려 주세요.
- **RPCS3가 실행 중**: 작업 관리자에서도 RPCS3를 완전히 종료하세요.
- **Windows 보안 경고**: 서명되지 않은 팬 제작 스크립트입니다. `CHECKSUMS.sha256`으로 파일이 배포본과 같은지 확인할 수 있습니다.

제보할 때는 패치 버전, 장면·대사, 화면 캡처, 설치기에 나온 메시지를 함께 남겨 주세요. 게임 파일은 첨부하지 마세요.

## 무결성

| 파일 | SHA-256 |
| --- | --- |
| 공식 `patch/5/data.cpk` ({{OFFICIAL_SIZE}}바이트) | `{{OFFICIAL_SHA256}}` |
| 한글 `patch/5/data.cpk` ({{TARGET_SIZE}}바이트) | `{{TARGET_SHA256}}` |
| 차이 패치 `{{PATCH_FILE}}` | `{{PATCH_SHA256}}` |

배포 ZIP 안의 파일은 `CHECKSUMS.sha256`, ZIP 자체는 함께 배포되는 `.sha256` 파일로 확인합니다.

## 배포와 크레딧

제작: {{AUTHOR}}. 비공식·비상업 팬 패치이며 게임 파일은 포함하지 않습니다. 자세한 내용은 `DISTRIBUTION_NOTICE.md`, `CREDITS.md`, `THIRD_PARTY_NOTICES.txt`, `licenses` 폴더를 보세요.

이 프로젝트는 원작자, 슈에이샤, 반다이 남코, CyberConnect2, Sony, RPCS3와 관계가 없습니다.
