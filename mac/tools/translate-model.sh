#!/bin/bash
# OgoCaption - oflayn tarjima modelini o'rnatish (macOS, ixtiyoriy, 2.95 GB)
# Lokal nusxa (translate_model papkasi) bo'lsa - ko'chiradi, bo'lmasa internetdan yuklaydi.
if [ -z "${BASH_VERSION:-}" ]; then exec /bin/bash "$0" "$@"; fi

NOPAUSE=0      # --no-pause        : oxirida "Enter bosing" so'ramaydi
DOWNLOAD=ask   # --download=yes|no : internetdan yuklashni so'ramasdan hal qiladi
TEST_ROOT=""   # --test-root=DIR   : ichki, sinov o'rnatmasi uchun
for arg in "$@"; do
    case "$arg" in
        --no-pause)    NOPAUSE=1 ;;
        --download=*)  DOWNLOAD="${arg#--download=}" ;;
        --test-root=*) TEST_ROOT="${arg#--test-root=}" ;;
    esac
done

if [ -t 1 ]; then
    C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'; C_GRAY=$'\033[90m'; C_OFF=$'\033[0m'
else
    C_CYAN=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_GRAY=""; C_OFF=""
fi
ok()   { printf '  %s[OK]%s   %s\n' "$C_GREEN" "$C_OFF" "$1"; }
bad()  { printf '  %s[XATO]%s %s\n' "$C_RED" "$C_OFF" "$1"; }
warn() { printf '  %s[!]%s    %s\n' "$C_YELLOW" "$C_OFF" "$1"; }
finish() {
    echo
    if [ "$NOPAUSE" = 0 ]; then read -r -p "Yopish uchun Enter bosing " _; fi
    exit "$1"
}

echo
printf '  %s=== OgoCaption: oflayn tarjima modeli (MADLAD-400-3B, 2.95 GB) ===%s\n' "$C_CYAN" "$C_OFF"
echo

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOME_DIR="$HOME"
if [ -n "$TEST_ROOT" ]; then
    HOME_DIR="$TEST_ROOT"
    printf '  %s(SINOV REJIMI: %s)%s\n' "$C_YELLOW" "$TEST_ROOT" "$C_OFF"
fi
DEST="$HOME_DIR/Library/Application Support/OgoCaption"
ENGINE="$DEST/Engine"

if [ ! -f "$ENGINE/translate.py" ]; then
    bad "Tarjimali OgoCaption o'rnatilmagan ($ENGINE/translate.py yo'q)."
    printf '         %sAvval paketdagi INSTALL.command ni ishga tushiring.%s\n' "$C_GRAY" "$C_OFF"
    finish 1
fi

# main.js dagi bilan bir xil tartib: python-path.txt -> portativ runtime
PY=""
CFG="$DEST/python-path.txt"
if [ -f "$CFG" ]; then
    C="$(head -n 1 "$CFG" | tr -d '"\r')"
    if [ -n "$C" ] && [ -e "$C" ]; then PY="$C"; fi
fi
if [ -z "$PY" ] && [ -e "$DEST/runtime/bin/python3" ]; then PY="$DEST/runtime/bin/python3"; fi
if [ -n "${OGO_TEST_PY:-}" ]; then PY="$OGO_TEST_PY"; fi   # ichki sinov uchun
if [ -z "$PY" ]; then bad "Python topilmadi. INSTALL.command ni qayta ishga tushiring."; finish 1; fi

GETTER="$ENGINE/get_translate_model.py"
[ -f "$GETTER" ] || GETTER="$ROOT/payload/Engine/get_translate_model.py"

say_gray() { printf '  %s%s%s\n' "$C_GRAY" "$1" "$C_OFF"; }
say_gray "Qayerga : $ENGINE/translate_model"
say_gray "Manba   : paket yonidagi translate_model papkasi, bo'lmasa internet (HuggingFace)"
echo
"$PY" "$GETTER" --dest "$ENGINE/translate_model" \
    --source "$ROOT/translate_model" \
    --source "$ROOT/payload/Engine/translate_model" \
    --source "$(dirname "$ROOT")/translate_model" \
    --download "$DOWNLOAD"
CODE=$?

echo
if [ "$CODE" = 0 ]; then
    ok "Tayyor. Premiere'da panelni qayta oching -> 'Tarjima (internetsiz)' kartasida tilni tanlang."
elif [ "$CODE" = 3 ]; then
    warn "Model o'rnatilmadi. Caption tarjimasiz ishlayveradi."
else
    bad "Model o'rnatilmadi (yuqoridagi xatoga qarang). Qayta ishga tushirsangiz - yuklash davom etadi."
fi
finish "$CODE"
