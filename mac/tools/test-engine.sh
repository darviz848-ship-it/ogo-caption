#!/bin/bash
# OgoCaption - o'rnatilgan enjinni tekshirish (macOS)
if [ -z "${BASH_VERSION:-}" ]; then exec /bin/bash "$0" "$@"; fi

if [ -t 1 ]; then
    C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'; C_GRAY=$'\033[90m'; C_OFF=$'\033[0m'
else
    C_CYAN=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_GRAY=""; C_OFF=""
fi
ok()      { printf '  %s[OK]%s   %s\n' "$C_GREEN" "$C_OFF" "$1"; }
bad()     { printf '  %s[XATO]%s %s\n' "$C_RED" "$C_OFF" "$1"; FAIL=$((FAIL + 1)); }
warn()    { printf '  %s[!]%s    %s\n' "$C_YELLOW" "$C_OFF" "$1"; }
section() { printf '\n  %s%s%s\n' "$C_CYAN" "$1" "$C_OFF"; }

echo
printf '  %s=== OgoCaption tekshiruvi (macOS) ===%s\n' "$C_CYAN" "$C_OFF"

APPSUP="$HOME/Library/Application Support"
DEST="$APPSUP/OgoCaption"
CEP="$APPSUP/Adobe/CEP/extensions/OgoCaption"
FAIL=0

section "1. Papkalar"
for p in "$DEST" "$CEP" "$DEST/Engine" "$DEST/mogrts" "$DEST/runtime"; do
    if [ -d "$p" ]; then ok "$p"; else bad "topilmadi: $p"; fi
done

section "2. Panel fayllari"
for f in index.html js/main.js js/CSInterface.js jsx/hostscript.jsx CSXS/manifest.xml css/style.css; do
    if [ -f "$CEP/$f" ]; then ok "$f"; else bad "yo'q: $f"; fi
done

section "3. AI modellar"
for m in uzbek_model multi_model; do
    BIN="$DEST/Engine/$m/model.bin"
    if [ -f "$BIN" ]; then ok "$m - $(( $(wc -c < "$BIN") / 1048576 )) MB"; else bad "$m/model.bin yo'q"; fi
    if [ ! -f "$DEST/Engine/$m/tokenizer.json" ]; then
        warn "$m/tokenizer.json yo'q (internetsiz ishlamasligi mumkin)"
    fi
done

section "4. PlayerDebugMode (imzosiz panelga ruxsat)"
ON=0
for v in 9 10 11 12 13 14 15 16 17 18 19 20; do
    [ "$(defaults read "com.adobe.CSXS.$v" PlayerDebugMode 2>/dev/null)" = "1" ] && ON=$((ON + 1))
done
if [ "$ON" -gt 0 ]; then ok "$ON ta CSXS domenida yoqilgan"; else bad "PlayerDebugMode yoqilmagan - panel Premiere'da ko'rinmaydi. INSTALL.command ni qayta ishga tushiring"; fi

section "5. macOS karantini (Gatekeeper)"
Q=$(xattr -r "$DEST" "$CEP" 2>/dev/null | grep -c "com.apple.quarantine")
if [ "$Q" -gt 0 ]; then
    xattr -r -d com.apple.quarantine "$DEST" "$CEP" 2>/dev/null
    ok "$Q ta faylda karantin bor edi - olib tashlandi"
else
    ok "karantin yo'q"
fi

section "6. Python enjin"
# main.js dagi bilan bir xil tartib: python-path.txt -> portativ -> tizim
PY=""
CFG="$DEST/python-path.txt"
if [ -f "$CFG" ]; then
    C="$(head -n 1 "$CFG" | tr -d '"\r')"
    if [ -n "$C" ] && [ -e "$C" ]; then PY="$C"; ok "python-path.txt: $C"; fi
fi
if [ -z "$PY" ] && [ -e "$DEST/runtime/bin/python3" ]; then
    PY="$DEST/runtime/bin/python3"; ok "portativ Python: $PY"
fi
if [ -z "$PY" ]; then
    for c in /opt/homebrew/bin/python3 /usr/local/bin/python3 \
             /Library/Frameworks/Python.framework/Versions/3.1[0-4]/bin/python3; do
        if [ -e "$c" ]; then PY="$c"; warn "tizim Python ishlatilmoqda: $c"; break; fi
    done
fi
if [ -z "$PY" ]; then
    bad "Python topilmadi (portativ ham, tizimda ham)"
else
    OUT="$("$PY" -c "import faster_whisper, ctranslate2, numpy, av, tokenizers; print('IMPORT-OK faster-whisper', faster_whisper.__version__, '| ctranslate2', ctranslate2.__version__, '| int8:', 'int8' in ctranslate2.get_supported_compute_types('cpu'))" 2>&1)"
    LINE="$(printf '%s\n' "$OUT" | grep 'IMPORT-OK' | tail -n 1)"
    if [ -n "$LINE" ]; then ok "${LINE#IMPORT-OK }"; else bad "import xatosi:"; printf '%s\n' "$OUT" | tail -n 8; fi
fi

section "7. Haqiqiy transkripsiya (internetsiz, 2 soniyalik test audio)"
if [ -n "$PY" ] && [ -f "$DEST/Engine/transcribe.py" ]; then
    mkdir -p "$DEST/temp"
    WAV="$DEST/temp/selftest.wav"
    "$PY" - "$WAV" <<'PYEOF'
import math, struct, sys, wave
fr = 16000
w = wave.open(sys.argv[1], "wb")
w.setnchannels(1); w.setsampwidth(2); w.setframerate(fr)
w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(i / 18.0))) for i in range(fr * 2)))
w.close()
PYEOF
    if [ -f "$WAV" ]; then
        OUT="$(cd "$DEST/Engine" && HF_HUB_OFFLINE=1 "$PY" transcribe.py "$WAV" uz 2>&1)"
        case "$OUT" in
            *'"success"'*) ok "uzbek_model internetsiz yuklandi va ishladi" ;;
            *) bad "transcribe.py xatosi:"; printf '%s%s%s\n' "$C_GRAY" "$OUT" "$C_OFF" | tail -n 12 ;;
        esac
        rm -f "$WAV"
    else
        bad "test audio yasalmadi"
    fi
else
    bad "Python yoki transcribe.py yo'q - sinab bo'lmadi"
fi

section "8. Oflayn tarjima (ixtiyoriy)"
TR_BIN="$DEST/Engine/translate_model/model.bin"
if [ ! -f "$DEST/Engine/translate.py" ]; then
    bad "Engine/translate.py yo'q - INSTALL.command ni qayta ishga tushiring"
elif [ ! -f "$TR_BIN" ]; then
    warn "Tarjima modeli o'rnatilmagan (ixtiyoriy). Kerak bo'lsa: tools/INSTALL-TRANSLATE-MODEL.command"
elif [ -n "$PY" ]; then
    ok "translate_model - $(( $(wc -c < "$TR_BIN") / 1048576 )) MB"
    mkdir -p "$DEST/temp"
    TR_CFG="$DEST/temp/selftest_translate.json"
    cat > "$TR_CFG" <<'JSONEOF'
{"mode": "words", "source": "uz", "target": "en", "words_per_line": 8, "words": [{"word": "Salom,", "start": 0.0, "end": 0.5}, {"word": "bugun", "start": 0.6, "end": 1.0}, {"word": "havo", "start": 1.1, "end": 1.4}, {"word": "juda", "start": 1.5, "end": 1.8}, {"word": "yaxshi.", "start": 1.9, "end": 2.4}]}
JSONEOF
    printf '    %s%s%s\n' "$C_GRAY" "'Salom, bugun havo juda yaxshi.' -> ingliz tiliga (model yuklanishi 10-30 soniya)..." "$C_OFF"
    OUT="$(cd "$DEST/Engine" && "$PY" translate.py "$TR_CFG" 2>&1)"
    RES="$(printf '%s\n' "$OUT" | grep '^{' | tail -n 1 | "$PY" -c 'import json, sys
d = json.load(sys.stdin)
print(" ".join(b["text"] for b in d["blocks"]) if d.get("success") else "")' 2>/dev/null)"
    if [ -n "$RES" ]; then
        ok "tarjima ishladi: $RES"
    else
        bad "translate.py xatosi:"; printf '%s%s%s\n' "$C_GRAY" "$OUT" "$C_OFF" | tail -n 12
    fi
    rm -f "$TR_CFG"
fi

echo
if [ "$FAIL" = 0 ]; then
    printf '  %s==> HAMMASI JOYIDA. Premiere'"'"'ni qayta ochib: Window > Extensions > ogo caption%s\n' "$C_GREEN" "$C_OFF"
else
    printf '  %s==> %s ta muammo topildi. INSTALL.command ni qayta ishga tushirib ko'"'"'ring.%s\n' "$C_RED" "$FAIL" "$C_OFF"
fi
echo
read -r -p "Yopish uchun Enter bosing " _
