#!/bin/bash
# tools/build_update_win.py paketidagi update.ps1 ni soxta o'rnatma (TestRoot) ustida sinash.
#   PWSH=/yo'l/pwsh bash tools/test_update_win.sh      (PowerShell 7 Linux/Mac'da ham ishlaydi)
set -u
R="$(cd "$(dirname "$0")/.." && pwd)"
PW="${PWSH:-pwsh}"
S="$(mktemp -d)"
trap 'rm -rf "$S"' EXIT
python3 -B "$R/tools/build_update_win.py" --out "$S/upd" --date test > /dev/null || exit 1
PKG="$S/upd/OgoCaption-Yangilash-test"
T=$S/troot
CEP="$T/AppData/Adobe/CEP/extensions/OgoCaption"
ENG="$T/Documents/OgoCaption/Engine"
fail=0
check() { if [ "$1" = "$2" ]; then echo "OK   $3"; else echo "XATO $3 ($1 != $2)"; fail=1; fi; }
h() { sha256sum "$1" 2>/dev/null | cut -c1-12; }
old_install() {
  rm -rf "$T"; mkdir -p "$CEP/js" "$CEP/css" "$ENG"
  git -C $R show ${BASE:-origin/main}:win/payload/panel/index.html > "$CEP/index.html"
  git -C $R show ${BASE:-origin/main}:win/payload/panel/js/main.js > "$CEP/js/main.js"
  git -C $R show ${BASE:-origin/main}:win/payload/Engine/translate.py > "$ENG/translate.py"
  echo "css" > "$CEP/css/style.css"
}
run() { $PW -NoProfile -File "$PKG/update.ps1" -TestRoot "$T" -Force -NoPause "$@" > $S/upd.log 2>&1; echo $?; }
NEW_MAIN=$(h $R/win/payload/panel/js/main.js); NEW_IDX=$(h $R/win/payload/panel/index.html); NEW_TR=$(h $R/win/payload/Engine/translate.py)
OLD_MAIN=$(git -C $R show ${BASE:-origin/main}:win/payload/panel/js/main.js | sha256sum | cut -c1-12)
OLD_TR=$(git -C $R show ${BASE:-origin/main}:win/payload/Engine/translate.py | sha256sum | cut -c1-12)

# 1) 15.10 o'rnatma -> yangilash
old_install
check "$(run)" 0 "1) yangilash: chiqish kodi 0"
check "$(h $CEP/js/main.js) $(h $CEP/index.html) $(h $ENG/translate.py)" "$NEW_MAIN $NEW_IDX $NEW_TR" "1) uchala fayl yangi"
grep -q "oldingi versiya (2026-10-15 paketi) - yangilanadi" $S/upd.log && echo "OK   1) eski versiya tanildi" || { echo "XATO 1) log"; cat $S/upd.log; fail=1; }
B=$(ls -d "$T/Documents/OgoCaption/update-backup/"*/ | head -1)
check "$(h ${B}panel/js/main.js) $(h ${B}Engine/translate.py)" "$OLD_MAIN $OLD_TR" "1) zaxirada eski fayllar"
check "$(cat $CEP/css/style.css)" "css" "1) boshqa fayllarga tegilmagan"
# 2) qayta ishga tushirish -> hech narsa
check "$(run)" 0 "2) qayta: chiqish kodi 0"
grep -q "Hamma fayl allaqachon yangi" $S/upd.log && echo "OK   2) allaqachon yangi" || { echo "XATO 2)"; cat $S/upd.log; fail=1; }
check "$(ls "$T/Documents/OgoCaption/update-backup" | wc -l)" 1 "2) yangi zaxira yaratilmadi"
# 3) orqaga qaytarish
check "$(run -Restore)" 0 "3) qaytarish: chiqish kodi 0"
check "$(h $CEP/js/main.js) $(h $ENG/translate.py)" "$OLD_MAIN $OLD_TR" "3) eski fayllar qaytdi"
check "$(ls "$T/Documents/OgoCaption/update-backup" | wc -l)" 0 "3) ishlatilgan zaxira o'chirildi"
# 4) qo'lda o'zgartirilgan main.js -> ogohlantirish, zaxira, almashtirish
old_install; echo "// qo'lda" >> "$CEP/js/main.js"; MOD=$(h $CEP/js/main.js)
check "$(run)" 0 "4) o'zgartirilgan: chiqish kodi 0"
grep -q "BOSHQA versiya" $S/upd.log && echo "OK   4) boshqa versiya haqida ogohlantirdi" || { echo "XATO 4)"; cat $S/upd.log; fail=1; }
B=$(ls -d "$T/Documents/OgoCaption/update-backup/"*/ | head -1)
check "$(h ${B}panel/js/main.js)" "$MOD" "4) qo'lda o'zgartirilgan fayl zaxirada"
run -Restore >/dev/null; check "$(h $CEP/js/main.js)" "$MOD" "4) qaytarishda o'sha fayl qaytdi"
# 5) translate.py yo'q (tarjimasiz eski o'rnatma) -> qo'shiladi, qaytarishda o'chiriladi
old_install; rm "$ENG/translate.py"
check "$(run)" 0 "5) translate.py yo'q: chiqish kodi 0"
check "$(h $ENG/translate.py)" "$NEW_TR" "5) translate.py qo'shildi"
run -Restore >/dev/null; [ ! -e "$ENG/translate.py" ] && echo "OK   5) qaytarishda o'chirildi" || { echo "XATO 5)"; fail=1; }
# 6) panel o'rnatilmagan -> xato, kod 1, hech narsa yozilmaydi
rm -rf "$T"; mkdir -p "$ENG"
check "$(run)" 1 "6) panel yo'q: chiqish kodi 1"
grep -q "Panel topilmadi" $S/upd.log && echo "OK   6) tushunarli xabar" || { echo "XATO 6)"; cat $S/upd.log; fail=1; }
# 7) paket buzilgan (fayl o'zgargan) -> xato, o'rnatma tegilmaydi
old_install; cp "$PKG/files/panel/js/main.js" $S/main.bak; echo x >> "$PKG/files/panel/js/main.js"
check "$(run)" 1 "7) buzilgan paket: chiqish kodi 1"
check "$(h $CEP/js/main.js)" "$OLD_MAIN" "7) o'rnatma tegilmadi"
cp $S/main.bak "$PKG/files/panel/js/main.js"
# 8) zaxira yo'q holda qaytarish -> xato
old_install; rm -rf "$T/Documents/OgoCaption/update-backup"
check "$(run -Restore)" 1 "8) zaxirasiz qaytarish: chiqish kodi 1"
# 9) papka nomida apostrof va bo'shliq
T="$S/troot/Lochin's O'zbek dir"; CEP="$T/AppData/Adobe/CEP/extensions/OgoCaption"; ENG="$T/Documents/OgoCaption/Engine"
old_install
check "$(run)" 0 "9) apostrofli yo'l: chiqish kodi 0"
check "$(h "$CEP/js/main.js")" "$NEW_MAIN" "9) apostrofli yo'lda yangilandi"
rm -rf $S/troot
[ $fail = 0 ] && echo && echo "HAMMASI O'TDI (update.ps1)" || exit 1
