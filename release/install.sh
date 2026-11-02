#!/bin/sh
# 죠죠의 기묘한 모험 아이즈 오브 헤븐 한글 패치 v{{VERSION}} - Linux 설치 스크립트
#
#   sh install.sh install <폴더>   설치 (설치 전 patch/5/data.cpk 백업)
#   sh install.sh verify  <폴더>   설치 상태 확인
#   sh install.sh restore <폴더>   설치 직전 상태로 되돌리기
#
# <폴더>: dev_hdd0가 들어 있는 RPCS3 폴더 또는 dev_hdd0/game/BLJS10318
# xdelta3가 필요합니다 (예: sudo apt install xdelta3).
set -eu

VERSION='{{VERSION}}'
OFFICIAL_SHA='{{OFFICIAL_SHA256}}'
TARGET_SHA='{{TARGET_SHA256}}'
PATCH_SHA='{{PATCH_SHA256}}'
LAYERS='1:{{LAYER1_SHA256}} 2:{{LAYER2_SHA256}} 3:{{LAYER3_SHA256}} 4:{{LAYER4_SHA256}}'
BACKUP='data.cpk.before-eoh-ko'
STATE='eoh-ko-state.txt'
HERE=$(cd "$(dirname "$0")" && pwd)
PAYLOAD="$HERE/patch/{{PATCH_FILE}}"

die() { echo "오류: $*" >&2; exit 1; }
sha() { sha256sum "$1" | cut -d' ' -f1; }

find_title() {
    for c in "$1" "$1/dev_hdd0/game/BLJS10318" "$1/game/BLJS10318" "$1/BLJS10318"; do
        if [ -f "$c/USRDIR/data/patch/5/data.cpk" ]; then
            (cd "$c" && pwd)
            return 0
        fi
    done
    return 1
}

check_layers() {
    for pair in $LAYERS; do
        n=${pair%%:*}
        f="$TITLE/USRDIR/data/patch/$n/data.cpk"
        [ -f "$f" ] && [ "$(sha "$f")" = "${pair#*:}" ] ||
            die "공식 업데이트 1.05(BLJS10318)가 아닙니다 (patch/$n/data.cpk 불일치). 일본판 BLJS10318에 공식 업데이트 01.05를 설치해 주세요."
    done
}

check_closed() {
    [ "${EOH_SKIP_PROCESS_CHECK:-}" = 1 ] && return 0
    if pgrep -x rpcs3 >/dev/null 2>&1 || pgrep -f 'rpcs3[^ ]*\.AppImage' >/dev/null 2>&1; then
        die "RPCS3가 실행 중입니다. RPCS3를 완전히 종료한 뒤 다시 실행해 주세요."
    fi
}

# official patch/5: the current file, or a copy beside it (left by another patch's installer)
find_official() {
    for f in "$DIR/data.cpk" "$DIR"/data.cpk.*; do
        [ -f "$f" ] && [ "$(sha "$f")" = "$OFFICIAL_SHA" ] && { echo "$f"; return 0; }
    done
    return 1
}

state_get() { sed -n "s/^$1=//p" "$DIR/$STATE"; }

do_install() {
    command -v xdelta3 >/dev/null 2>&1 || die "xdelta3가 필요합니다 (예: sudo apt install xdelta3)."
    [ "$(sha "$PAYLOAD")" = "$PATCH_SHA" ] || die "패치 파일이 손상되었습니다. 배포 ZIP을 다시 받아 주세요."
    cur=$(sha "$DIR/data.cpk")
    if [ "$cur" = "$TARGET_SHA" ]; then
        echo "이미 한글 패치 v$VERSION이 설치되어 있습니다."
        return 0
    fi
    src=$(find_official) || die "공식 1.05 patch/5 원본(data.cpk, SHA-256 $OFFICIAL_SHA)을 찾지 못했습니다. 다른 패치를 쓰고 있다면 그 패치의 복원 기능으로 공식 상태로 되돌린 뒤 다시 시도해 주세요."
    if [ ! -f "$DIR/$STATE" ]; then  # an older version of this patch keeps its first backup
        cp "$DIR/data.cpk" "$DIR/$BACKUP.tmp"
        mv "$DIR/$BACKUP.tmp" "$DIR/$BACKUP"
        printf 'previous_sha256=%s\nversion=%s\n' "$cur" "$VERSION" > "$DIR/$STATE"
    fi
    new="$DIR/data.cpk.eoh-ko-new"
    rm -f "$new"
    xdelta3 -d -f -s "$src" "$PAYLOAD" "$new" || { rm -f "$new"; die "차이 패치 적용에 실패했습니다."; }
    [ "$(sha "$new")" = "$TARGET_SHA" ] || { rm -f "$new"; die "만들어진 파일이 예상과 다릅니다. 설치하지 않았습니다."; }
    mv -f "$new" "$DIR/data.cpk"
    echo "설치 완료: 한글 패치 v$VERSION"
    echo "백업: $DIR/$BACKUP (복원에 필요하니 지우지 마세요)"
}

do_verify() {
    if [ "$(sha "$DIR/data.cpk")" = "$TARGET_SHA" ]; then
        echo "정상: 한글 패치 v$VERSION이 설치되어 있습니다."
        [ -f "$DIR/$BACKUP" ] && echo "백업: 있음" || echo "백업: 없음 (복원 불가)"
        return 0
    fi
    echo "한글 패치 v$VERSION이 설치되어 있지 않습니다."
    return 1
}

do_restore() {
    [ -f "$DIR/$STATE" ] && [ -f "$DIR/$BACKUP" ] || die "복원할 백업이 없습니다."
    prev=$(state_get previous_sha256)
    cur=$(sha "$DIR/data.cpk")
    [ "$cur" = "$TARGET_SHA" ] || [ "$cur" = "$prev" ] ||
        die "data.cpk가 설치 후 다른 프로그램에 의해 바뀌었습니다. 덮어쓰지 않았습니다."
    [ "$(sha "$DIR/$BACKUP")" = "$prev" ] || die "백업 파일이 손상되었습니다. 덮어쓰지 않았습니다."
    cp "$DIR/$BACKUP" "$DIR/data.cpk.eoh-ko-restore"
    mv -f "$DIR/data.cpk.eoh-ko-restore" "$DIR/data.cpk"
    rm -f "$DIR/$BACKUP" "$DIR/$STATE"
    echo "복원 완료: 한글 패치 설치 직전 상태로 되돌렸습니다."
}

[ $# -eq 2 ] || die "사용법: sh install.sh install|verify|restore <RPCS3 폴더 또는 dev_hdd0/game/BLJS10318>"
TITLE=$(find_title "$2") || die "게임 폴더를 찾지 못했습니다: $2 (dev_hdd0가 들어 있는 RPCS3 폴더 또는 dev_hdd0/game/BLJS10318을 지정해 주세요)"
DIR="$TITLE/USRDIR/data/patch/5"
case "$1" in
    install) check_closed; check_layers; do_install ;;
    verify) do_verify ;;
    restore) check_closed; do_restore ;;
    *) die "알 수 없는 명령: $1 (install, verify, restore 중 하나)" ;;
esac
