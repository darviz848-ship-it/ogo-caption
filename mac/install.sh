#!/bin/bash
# =============================================================
#  OgoCaption - Premiere Pro AI subtitr paneli
#  O'rnatuvchi skript (macOS, admin paroli shart emas)
#
#  Ishga tushirish: INSTALL.command ga ikki marta bosing
#  yoki Terminal'da:  bash install.sh
# =============================================================

# zsh/sh bilan ochilsa - bash'da qayta ishga tushamiz (read -p va h.k. uchun)
if [ -z "${BASH_VERSION:-}" ]; then exec /bin/bash "$0" "$@"; fi

FORCE=0        # --force     : savol bermasdan o'rnatadi
NOPAUSE=0      # --no-pause  : oxirida "Enter bosing" so'ramaydi
TEST_ROOT=""   # --test-root=DIR : ichki, sinov uchun boshqa papkaga o'rnatadi
for arg in "$@"; do
    case "$arg" in
        --force)       FORCE=1 ;;
        --no-pause)    NOPAUSE=1 ;;
        --test-root=*) TEST_ROOT="${arg#--test-root=}" ;;
    esac
done

if [ -t 1 ]; then
    C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
    C_RED=$'\033[31m'; C_GRAY=$'\033[90m'; C_BOLD=$'\033[1m'; C_OFF=$'\033[0m'
else
    C_CYAN=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_GRAY=""; C_BOLD=""; C_OFF=""
fi

say()     { printf '%s\n' "$1"; }
section() { printf '\n  %s%s%s\n' "$C_CYAN" "$1" "$C_OFF"; }
ok()      { printf '  %s[OK]%s  %s\n' "$C_GREEN" "$C_OFF" "$1"; }
warn()    { printf '  %s[!]%s   %s\n' "$C_YELLOW" "$C_OFF" "$1"; }
gray()    { printf '%s%s%s\n' "$C_GRAY" "$1" "$C_OFF"; }
pause_end() { if [ "$NOPAUSE" = 0 ]; then read -r -p "Yopish uchun Enter bosing " _; fi; }
die() {
    printf '\n  %s[XATO]%s %s\n\n' "$C_RED" "$C_OFF" "$1"
    pause_end
    exit 1
}
ask() { REPLY=""; read -r -p "  $1 " REPLY; }
gb()  { awk -v k="$1" 'BEGIN { printf "%.2f", k / 1048576 }'; }

printf '\n  %s===========================================================%s\n' "$C_CYAN" "$C_OFF"
printf '    %sOgoCaption  ::  Premiere Pro uchun offline AI subtitr%s\n' "$C_BOLD" "$C_OFF"
gray "    O'rnatuvchi (macOS)"
printf '  %s===========================================================%s\n' "$C_CYAN" "$C_OFF"

# ---------- 0. Paket joyi ----------
ROOT="$(cd "$(dirname "$0")" && pwd)"
PAYLOAD="$ROOT/payload"
[ -d "$PAYLOAD" ] || die "payload papkasi topilmadi. install.sh va payload bir papkada turishi kerak."
for part in panel Engine mogrts presets; do
    [ -d "$PAYLOAD/$part" ] || die "payload/$part topilmadi. Paket to'liq ko'chirilmagan."
done

IS_MAC=0
[ "$(uname -s)" = "Darwin" ] && IS_MAC=1
if [ "$IS_MAC" = 0 ] && [ -z "$TEST_ROOT" ]; then
    die "Bu o'rnatuvchi faqat macOS uchun. Windows'da OgoCaption-Setup (INSTALL.bat) ishlatiladi."
fi
if [ "$IS_MAC" = 1 ]; then
    MACOS_VER="$(sw_vers -productVersion 2>/dev/null)"
    MACOS_MAJOR="${MACOS_VER%%.*}"
    if [ -n "$MACOS_MAJOR" ] && [ "$MACOS_MAJOR" -lt 11 ] 2>/dev/null; then
        die "macOS $MACOS_VER juda eski. Kamida macOS 11 (Big Sur) kerak."
    fi
fi

# ---------- 1. Protsessor (Apple Silicon yoki Intel) ----------
ARCH="x86_64"
if [ "$(sysctl -n hw.optional.arm64 2>/dev/null)" = "1" ]; then ARCH="arm64"; fi
if [ -n "${OGO_ARCH:-}" ]; then ARCH="$OGO_ARCH"; fi   # ichki sinov uchun
RT_TGZ="$PAYLOAD/runtime-$ARCH.tar.gz"
[ -f "$RT_TGZ" ] || die "payload/runtime-$ARCH.tar.gz topilmadi. Paket to'liq ko'chirilmagan."
if [ "$ARCH" = "arm64" ]; then CPU_NAME="Apple Silicon (M1/M2/M3/M4)"; else CPU_NAME="Intel"; fi

# ---------- 2. Maqsad papkalar ----------
HOME_DIR="$HOME"
if [ -n "$TEST_ROOT" ]; then
    HOME_DIR="$TEST_ROOT"
    printf '  %s(SINOV REJIMI: %s)%s\n' "$C_YELLOW" "$TEST_ROOT" "$C_OFF"
fi
APPSUP="$HOME_DIR/Library/Application Support"
DEST="$APPSUP/OgoCaption"
CEP_PARENT="$APPSUP/Adobe/CEP"
CEP="$CEP_PARENT/extensions/OgoCaption"

section "Qayerga o'rnatiladi"
say "    Panel      : $CEP"
say "    Enjin      : $DEST"
say "    Protsessor : $CPU_NAME${MACOS_VER:+, macOS $MACOS_VER}"

# ---------- 3. Bo'sh joy ----------
mkdir -p "$APPSUP" 2>/dev/null
NEED_KB=$(du -sk "$PAYLOAD/panel" "$PAYLOAD/Engine" "$PAYLOAD/mogrts" "$PAYLOAD/presets" 2>/dev/null | awk '{ s += $1 } END { print s + 0 }')
RT_KB=$(du -sk "$RT_TGZ" | awk '{ print $1 }')
NEED_KB=$((NEED_KB + RT_KB * 4))   # ochilgan runtime arxivdan ~3-4 barobar katta
FREE_KB=$(df -Pk "$APPSUP" | awk 'NR == 2 { print $4 }')
section "Joy"
say "    Kerak : $(gb "$NEED_KB") GB"
say "    Bo'sh : $(gb "$FREE_KB") GB"
if [ -n "$FREE_KB" ] && [ "$FREE_KB" -lt "$NEED_KB" ]; then die "Diskda joy yetarli emas."; fi

# ---------- 4. Premiere ochiqmi ----------
if pgrep -f "Adobe Premiere Pro" >/dev/null 2>&1; then
    warn "Premiere Pro ochiq. O'rnatishdan oldin uni yoping (Cmd+Q)."
    if [ "$FORCE" = 0 ]; then
        ask "Premiere yopilgach Enter bosing (bekor qilish uchun N):"
        case "$REPLY" in N|n) die "Bekor qilindi." ;; esac
    fi
fi

# ---------- 5. Tasdiq ----------
if [ "$FORCE" = 0 ]; then
    echo
    ask "O'rnatishni boshlaymizmi? (Enter = ha, N = yo'q)"
    case "$REPLY" in N|n|"yo'q"|no) die "Bekor qilindi." ;; esac
fi

# Paketning o'zidan ham karantinni olamiz - tools/*.command keyin bemalol ochilsin
if [ "$IS_MAC" = 1 ] && command -v xattr >/dev/null 2>&1; then
    xattr -r -d com.apple.quarantine "$ROOT" 2>/dev/null
fi

# ---------- 6. Eski o'rnatmani zaxiralash ----------
STAMP="$(date +%Y%m%d-%H%M%S)"
section "Eski o'rnatmani tekshirish"
if [ -d "$CEP" ]; then
    # MUHIM: zaxira "extensions" papkasidan TASHQARIGA chiqariladi,
    # aks holda Premiere uni ikkinchi (dublikat) panel deb ko'radi.
    BAK="$CEP_PARENT/OgoCaption.backup-$STAMP"
    mv "$CEP" "$BAK" || die "Eski panelni zaxiraga olib bo'lmadi: $CEP"
    ok "Eski panel zaxiraga olindi: $BAK"
else
    say "    Eski panel yo'q - toza o'rnatish."
fi

# ---------- 7. Nusxalash ----------
copy_tree() {
    say "    $3 ..."
    mkdir -p "$2" || die "$3: papka yaratilmadi ($2)"
    cp -R "$1/." "$2/" || die "$3 nusxalanmadi"
    ok "$3"
}

section "Fayllar ko'chirilmoqda (modellar ~2 GB, biroz vaqt oladi)"
copy_tree "$PAYLOAD/panel"   "$CEP"           "Panel (CEP kengaytma)"
copy_tree "$PAYLOAD/Engine"  "$DEST/Engine"   "Enjin + AI modellar"
copy_tree "$PAYLOAD/mogrts"  "$DEST/mogrts"   "MOGRT shablonlar"
copy_tree "$PAYLOAD/presets" "$DEST/presets"  "Audio eksport preseti (zaxira)"

# Portativ Python arxivda keladi: symlink va ruxsatlar (chmod +x) buzilmasin,
# fleshka (exFAT) orqali ko'chirilsa ham.
say "    Portativ Python ($ARCH) ochilmoqda ..."
rm -rf "$DEST/runtime"
tar -xzf "$RT_TGZ" -C "$DEST" || die "runtime-$ARCH.tar.gz ochilmadi."
[ -e "$DEST/runtime/bin/python3" ] || die "Portativ Python ochilmadi: $DEST/runtime/bin/python3"
ok "Portativ Python 3.13 ($ARCH)"

mkdir -p "$DEST/temp"
ok "temp papka"

# ---------- 8. macOS karantini (Gatekeeper) ----------
# Internet/Telegram/AirDrop orqali kelgan fayllarda com.apple.quarantine bo'ladi -
# shu bilan qolsa, macOS imzosiz Python'ni ishga tushirishni bloklaydi.
section "macOS xavfsizlik belgilari"
if [ "$IS_MAC" = 1 ] && command -v xattr >/dev/null 2>&1; then
    xattr -r -d com.apple.quarantine "$DEST" "$CEP" 2>/dev/null
    ok "Karantin belgisi olib tashlandi (Gatekeeper Python'ni bloklamaydi)"
else
    warn "xattr yo'q (macOS emas) - o'tkazib yuborildi"
fi

# ---------- 9. Imzosiz panelga ruxsat ----------
section "Imzosiz CEP panelga ruxsat (PlayerDebugMode)"
if [ -n "$TEST_ROOT" ]; then
    warn "SINOV rejimi - defaults yozilmadi"
elif command -v defaults >/dev/null 2>&1; then
    N=0
    for v in 9 10 11 12 13 14 15 16 17 18 19 20; do
        defaults write "com.adobe.CSXS.$v" PlayerDebugMode 1 >/dev/null 2>&1 && N=$((N + 1))
    done
    ok "com.adobe.CSXS.9 - CSXS.20 ($N ta)"
else
    warn "defaults buyrug'i topilmadi - o'tkazib yuborildi"
fi

# ---------- 10. Tekshiruv ----------
section "Tekshiruv"
for m in uzbek_model multi_model; do
    for f in config.json model.bin tokenizer.json; do
        [ -f "$DEST/Engine/$m/$f" ] || die "Engine/$m/$f yo'q"
    done
    SRC_SIZE=$(wc -c < "$PAYLOAD/Engine/$m/model.bin")
    DST_SIZE=$(wc -c < "$DEST/Engine/$m/model.bin")
    [ "$SRC_SIZE" -eq "$DST_SIZE" ] || die "$m/model.bin to'liq ko'chmadi ($DST_SIZE / $SRC_SIZE bayt)"
    ok "$m ($((DST_SIZE / 1048576)) MB)"
done
for f in index.html js/main.js js/CSInterface.js jsx/hostscript.jsx CSXS/manifest.xml css/style.css; do
    [ -f "$CEP/$f" ] || die "Panel fayli yetishmayapti: $f"
done
ok "Panel fayllari joyida"
for f in transcribe.py translate.py get_translate_model.py; do
    [ -f "$DEST/Engine/$f" ] || die "Enjin fayli yetishmayapti: Engine/$f"
done
ok "Enjin skriptlari joyida"

PY="$DEST/runtime/bin/python3"
FAILED=0
if [ "$IS_MAC" = 1 ]; then
    OUT="$("$PY" -c "import faster_whisper, ctranslate2, numpy, av, tokenizers; print('ENGINE-OK faster-whisper', faster_whisper.__version__, '| int8:', 'int8' in ctranslate2.get_supported_compute_types('cpu'))" 2>&1)"
    LINE="$(printf '%s\n' "$OUT" | grep 'ENGINE-OK' | tail -n 1)"
    [ -n "$LINE" ] || die "Python enjin ishlamadi:
$OUT"
    ok "Python enjin: ${LINE#ENGINE-OK }"

    section "AI sinovi: 2 soniyalik test audio (internetsiz, 20-60 soniya)"
    TEST_WAV="$DEST/temp/selftest.wav"
    "$PY" - "$TEST_WAV" <<'PYEOF'
import math, struct, sys, wave
fr = 16000
w = wave.open(sys.argv[1], "wb")
w.setnchannels(1); w.setsampwidth(2); w.setframerate(fr)
w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(i / 18.0))) for i in range(fr * 2)))
w.close()
PYEOF
    OUT="$(cd "$DEST/Engine" && HF_HUB_OFFLINE=1 "$PY" transcribe.py "$TEST_WAV" uz 2>&1)"
    rm -f "$TEST_WAV"
    case "$OUT" in
        *'"success"'*) ok "uzbek_model internetsiz yuklandi va ishladi" ;;
        *) warn "AI sinovi o'tmadi. Oxirgi qatorlar:"
           printf '%s\n' "$OUT" | tail -n 6
           FAILED=1 ;;
    esac
else
    warn "SINOV rejimi (macOS emas): Python tekshiruvi o'tkazib yuborildi"
fi

# ---------- 11. Oflayn tarjima modeli (ixtiyoriy) ----------
# Model 2.95 GB - paketga sig'maydi. Lokal nusxa (translate_model papkasi) bo'lsa
# ko'chiriladi, bo'lmasa internetdan yuklash taklif qilinadi. Xato o'rnatishni to'xtatmaydi.
TR_OK=0
section "Oflayn tarjima modeli (ixtiyoriy, 2.95 GB)"
TR_PY="$PY"
if [ -n "${OGO_TEST_PY:-}" ]; then TR_PY="$OGO_TEST_PY"; fi   # ichki sinov uchun
if [ "$IS_MAC" = 1 ] || [ -n "${OGO_TEST_PY:-}" ]; then
    TR_MODE=ask
    [ "$FORCE" = 1 ] && TR_MODE=no
    if "$TR_PY" "$DEST/Engine/get_translate_model.py" --dest "$DEST/Engine/translate_model" \
            --source "$ROOT/translate_model" \
            --source "$(dirname "$ROOT")/translate_model" \
            --download "$TR_MODE"; then
        TR_OK=1
        ok "Tarjima modeli joyida"
    else
        warn "Tarjima modeli o'rnatilmadi - caption ishlaydi, tarjima yo'q. Keyin: tools/INSTALL-TRANSLATE-MODEL.command"
    fi
else
    warn "SINOV rejimi (macOS emas): o'tkazib yuborildi"
fi

# ---------- 12. Yakun ----------
echo
if [ "$FAILED" = 0 ]; then
    printf '  %s===========================================================%s\n' "$C_GREEN" "$C_OFF"
    printf '    %sTAYYOR! OgoCaption o'"'"'rnatildi.%s\n' "$C_GREEN" "$C_OFF"
    printf '  %s===========================================================%s\n' "$C_GREEN" "$C_OFF"
else
    printf '  %s===========================================================%s\n' "$C_YELLOW" "$C_OFF"
    printf '    %sFayllar o'"'"'rnatildi, lekin AI sinovi o'"'"'tmadi.%s\n' "$C_YELLOW" "$C_OFF"
    printf '    %stools/TEST-ENGINE.command ni ishga tushirib ko'"'"'ring.%s\n' "$C_YELLOW" "$C_OFF"
    printf '  %s===========================================================%s\n' "$C_YELLOW" "$C_OFF"
fi
echo
say "    Endi nima qilish kerak:"
say "      1. Premiere Pro ni butunlay yoping (Cmd+Q) va qaytadan oching"
say "      2. Window  ->  Extensions  ->  ogo caption"
say "      3. Timeline'da sequence ochib, 'Caption Yaratish' tugmasini bosing"
echo
[ "$TR_OK" = 1 ] || gray "    Tarjima kerak bo'lsa: tools/INSTALL-TRANSLATE-MODEL.command"
gray "    Ishlamasa: tools/TEST-ENGINE.command"
gray "    O'chirish uchun: tools/UNINSTALL.command"
echo
pause_end
exit "$FAILED"
