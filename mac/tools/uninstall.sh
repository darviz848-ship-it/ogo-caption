#!/bin/bash
# OgoCaption - o'chirish (macOS)
if [ -z "${BASH_VERSION:-}" ]; then exec /bin/bash "$0" "$@"; fi

echo
echo "  === OgoCaption o'chirish ==="
echo

APPSUP="$HOME/Library/Application Support"
DEST="$APPSUP/OgoCaption"
CEP="$APPSUP/Adobe/CEP/extensions/OgoCaption"

echo "  Quyidagilar o'chiriladi:"
echo "    $CEP"
echo "    $DEST   (AI modellar bilan birga: ~2 GB, tarjima modeli bo'lsa +2.95 GB)"
echo
read -r -p "  Davom etamizmi? (ha/yo'q) " A
case "$A" in
    ha|Ha|HA|h|H|y|Y|yes) ;;
    *) echo "  Bekor qilindi."; read -r -p "Enter bosing " _; exit 0 ;;
esac

if pgrep -f "Adobe Premiere Pro" >/dev/null 2>&1; then
    echo "  [!] Premiere Pro ochiq - avval yoping (Cmd+Q)."
    read -r -p "  Yopgach Enter bosing " _
fi

for p in "$CEP" "$DEST"; do
    if [ -e "$p" ]; then
        if rm -rf "$p"; then echo "  [OK]  o'chirildi: $p"; else echo "  [XATO] o'chmadi: $p"; fi
    else
        echo "  [ - ] yo'q edi: $p"
    fi
done

echo
echo "  Eslatma: com.adobe.CSXS.* dagi PlayerDebugMode tegilmadi"
echo "  (boshqa CEP panellar uchun kerak bo'lishi mumkin)."
echo "  Eski panel zaxiralari (bo'lsa): $APPSUP/Adobe/CEP/OgoCaption.backup-*"
echo
read -r -p "Yopish uchun Enter bosing " _
