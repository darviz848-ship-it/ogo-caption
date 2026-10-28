"""Windows uchun kichik yangilash paketi: faqat o'zgargan panel / Engine fayllari + YANGILASH.bat.

  python3 tools/build_update_win.py --out <papka> [--base origin/main] [--zip]

--base dan beri o'zgargan win/payload/panel/* va win/payload/Engine/* fayllar olinadi.
Paket ichida: YANGILASH.bat, ORQAGA-QAYTARISH.bat, update.ps1, OQING.txt, files/...
update.ps1 har fayl uchun eski (base) va yangi SHA256 ni biladi: o'rnatmadagi faylning
versiyasini aytadi, eskisini Documents/OgoCaption/update-backup/<vaqt> ga zaxiralaydi.
Modellar, runtime, mogrts tegilmaydi. .bat / .ps1 / .txt - CRLF, ASCII.
"""
import argparse
import datetime
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TPL = os.path.join(HERE, "update_win")
PAYLOAD = "win/payload/"


def git(*args, binary=False):
    out = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True, check=True)
    return out.stdout if binary else out.stdout.decode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dest_expr(rel):
    """files/ ichidagi nisbiy yo'l -> update.ps1 dagi o'rnatma yo'li ifodasi."""
    parts = rel.split("/")
    if parts[0] == "panel":
        expr, rest = "$cep", parts[1:]
    elif parts[0] == "Engine":
        expr, rest = "$dest", parts
    else:
        raise ValueError(rel)
    for p in rest:
        expr = '(J %s "%s")' % (expr, p)
    return expr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--title", default="Yangi o'zbek alifbosi tanlovi (2021-yil loyihasi)")
    ap.add_argument("--old-label", default="2026-10-15 paketi", help="o'rnatmadagi eski versiya nomi")
    ap.add_argument("--zip", action="store_true")
    a = ap.parse_args()

    changed = [p for p in git("diff", "--name-only", a.base, "HEAD", "--", PAYLOAD + "panel", PAYLOAD + "Engine").split("\n") if p]
    changed += [p for p in git("diff", "--name-only", "--", PAYLOAD + "panel", PAYLOAD + "Engine").split("\n") if p and p not in changed]
    if not changed:
        sys.exit("O'zgargan fayl yo'q (%s..HEAD)" % a.base)
    base_label = a.old_label

    name = "OgoCaption-Yangilash-" + a.date
    pkg = os.path.join(a.out, name)
    if os.path.exists(pkg):
        shutil.rmtree(pkg)
    os.makedirs(os.path.join(pkg, "files"))

    items = []
    for path in sorted(changed):
        rel = path[len(PAYLOAD):]
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            print("o'chirilgan fayl, paketga kirmaydi:", path)
            continue
        data = open(full, "rb").read()
        try:
            old = sha(git("show", "%s:%s" % (a.base, path), binary=True))
        except subprocess.CalledProcessError:
            old = "yo'q"
        dst = os.path.join(pkg, "files", *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(data)
        items.append('    @{ Rel = "%s"; Name = "%s"; Dst = %s; Old = "%s"; New = "%s"; OldLabel = "%s" }'
                     % (rel, rel, dest_expr(rel), old, sha(data), base_label))
        print("  %-28s %s -> %s" % (rel, old[:12], sha(data)[:12]))

    def crlf(text):
        return text.replace("\r\n", "\n").replace("\n", "\r\n").encode("ascii")

    ps1 = open(os.path.join(TPL, "update.ps1.in"), "rb").read().decode("ascii")
    ps1 = ps1.replace("@@DATE@@", a.date).replace("@@TITLE@@", a.title).replace("@@ITEMS@@", ",\r\n".join(items))
    open(os.path.join(pkg, "update.ps1"), "wb").write(crlf(ps1))
    for bat in ("YANGILASH.bat", "ORQAGA-QAYTARISH.bat"):
        shutil.copy(os.path.join(TPL, bat), os.path.join(pkg, bat))

    readme = """OgoCaption - yangilash %s
==================================
%s

Bu kichik paket faqat o'zgargan fayllarni almashtiradi:
%s
Modellar, Python runtime, MOGRT va sozlamalar TEGILMAYDI.
Eski fayllar zaxiraga olinadi:
  Hujjatlar\\OgoCaption\\update-backup\\<sana-vaqt>\\

O'RNATISH
  1. Premiere Pro ni yop.
  2. YANGILASH.bat ga ikki marta bos, ko'rsatmaga amal qil.
  3. Premiere Pro ni och: Window -> Extensions -> ogo caption.
     "Ovozni aniqlash sozlamalari" kartasida "Alifbo: joriy / yangi"
     tanlovi paydo bo'ladi. Default - joriy (hammasi avvalgidek).

ORQAGA QAYTARISH
  Premiere Pro ni yop, ORQAGA-QAYTARISH.bat ga ikki marta bos -
  oxirgi zaxira joyiga qaytadi.

Talab: OgoCaption oldin to'liq paket (OgoCaption-Setup\\INSTALL.bat)
bilan o'rnatilgan bo'lishi kerak. Internet kerak emas.
""" % (a.date, a.title, "".join("  - %s\n" % i.split('"')[1] for i in items))
    open(os.path.join(pkg, "OQING.txt"), "wb").write(crlf(readme))
    print("paket:", pkg)

    if a.zip:
        z = shutil.make_archive(pkg, "zip", a.out, name)
        print("zip:", z, "(%.0f KB)" % (os.path.getsize(z) / 1024.0))


if __name__ == "__main__":
    main()
