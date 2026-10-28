"""Oflayn tarjima modelini o'rnatish (translate.py uchun).

Model: MADLAD-400-3B-MT, CTranslate2 int8 (Google, Apache 2.0), 2.95 GB.
Asosiy o'rnatish paketiga sig'maydi (Telegram 2 GB chegarasi), shuning uchun alohida keladi:
  1) lokal nusxa - --source bilan berilgan papkalardan birinchi to'liq `translate_model`
     (fleshka / tashqi disk; internet kerak emas);
  2) topilmasa - HuggingFace'dan yuklash (Nextcloud-AI/madlad400-3b-mt-ct2-int8).
Ikkala holda ham fayllar avval <dest>.part ga yoziladi, hajmi va SHA256 tekshiriladi,
shundan keyingina <dest> ga ko'chiriladi - chala model hech qachon "o'rnatilgan" bo'lib qolmaydi.
Yuklash uzilsa - qayta ishga tushirilganda davom etadi.

Ishlatish:
  python get_translate_model.py [--dest DIR] [--source DIR ...] [--download ask|yes|no]
Chiqish kodi: 0 - model joyida, 3 - o'rnatilmadi (manba yo'q / rad etildi), 1 - xato.
"""
import argparse
import hashlib
import os
import shutil
import sys
import time

REPO = "Nextcloud-AI/madlad400-3b-mt-ct2-int8"
REVISION = "aa32bbdeba7880eff2096ec044cb155a340a9400"   # 2024-07-15, shu nusxa sinalgan (15.10.2026)

# fayl -> (hajm, sha256 yoki None). translate.py ga birinchi to'rttasi kerak.
FILES = {
    "model.bin": (2950208329, "77b9fd9ab97c1259d07089b5f854393dad81bc5fb5647d3f9a5d101c94f40daa"),
    "config.json": (224, "90fb54962455a4e0a0bc7235c0f063d7e46d9c1a1ae003af8059809abd6aeece"),
    "shared_vocabulary.json": (5477099, "c327551ce3ca6efc7b437e11a267f79979893332dda8a1d146e2c950815193f8"),
    "tokenizer.json": (16629031, "a2799ccc696b752ba00c34f58726bfe253a04921ceb6cfc620400f560474790b"),
    "README.md": (10014, None),   # litsenziya (Apache 2.0) ma'lumoti
    "added_tokens.json": (4, None),
    "generation_config.json": (142, None),
    "special_tokens_map.json": (414, None),
    "tokenizer_config.json": (830, None),
}
REQUIRED = ("model.bin", "config.json", "shared_vocabulary.json", "tokenizer.json")
NEED_FREE = 3.2 * 1024 ** 3


def say(msg):
    print(msg, flush=True)


def gb(n):
    return "%.2f GB" % (n / 1024.0 ** 3)


def is_complete(d, check_hash=False):
    """Papkada translate.py uchun kerakli fayllar to'liq bormi (hajm bo'yicha, ixtiyoriy SHA256)."""
    for name in REQUIRED:
        p = os.path.join(d, name)
        size, digest = FILES[name]
        if not os.path.isfile(p) or os.path.getsize(p) != size:
            return False
        if check_hash and digest and sha256(p) != digest:
            return False
    return True


def sha256(path, label=None):
    h = hashlib.sha256()
    total = os.path.getsize(path)
    done, last = 0, -1
    with open(path, "rb") as f:
        while True:
            buf = f.read(8 * 1024 * 1024)
            if not buf:
                break
            h.update(buf)
            done += len(buf)
            pct = int(done * 100 / total) if total else 100
            if label and pct // 10 != last // 10:
                say("    %s tekshirilmoqda: %d%%" % (label, pct))
                last = pct
    return h.hexdigest()


def verify(d):
    """Hamma fayl hajmi + SHA256. Xato bo'lsa sababini qaytaradi, to'g'ri bo'lsa None."""
    for name in REQUIRED:
        p = os.path.join(d, name)
        size, digest = FILES[name]
        if not os.path.isfile(p):
            return "%s yo'q" % name
        if os.path.getsize(p) != size:
            return "%s hajmi noto'g'ri (%d / %d bayt)" % (name, os.path.getsize(p), size)
        if digest and sha256(p, name if name == "model.bin" else None) != digest:
            return "%s buzilgan (SHA256 mos emas)" % name
    return None


def copy_with_progress(src, dst):
    total = os.path.getsize(src)
    done, last = 0, -1
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        while True:
            buf = fi.read(16 * 1024 * 1024)
            if not buf:
                break
            fo.write(buf)
            done += len(buf)
            pct = int(done * 100 / total) if total else 100
            if total > 50 * 1024 * 1024 and pct // 5 != last // 5:
                say("    %s: %d%%" % (os.path.basename(src), pct))
                last = pct


def finalize(part, dest):
    err = verify(part)
    if err:
        shutil.rmtree(part, ignore_errors=True)   # keyingi urinish toza boshlansin
        raise RuntimeError("Model tekshiruvdan o'tmadi: %s. Qayta urinib ko'ring." % err)
    shutil.rmtree(os.path.join(part, ".cache"), ignore_errors=True)   # huggingface_hub metama'lumoti
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.replace(part, dest)


def check_space(dest, part):
    have = 0   # uzilgan yuklashdan qolgan qism ham hisobga olinadi
    for root, _, names in os.walk(part):
        have += sum(os.path.getsize(os.path.join(root, n)) for n in names)
    need = max(0, NEED_FREE - have)
    free = shutil.disk_usage(os.path.dirname(dest)).free
    if free < need:
        raise RuntimeError("Diskda joy yetarli emas: kerak %s, bo'sh %s" % (gb(need), gb(free)))


def from_local(src, dest, part):
    say("  Lokal nusxa topildi: " + src)
    check_space(dest, part)
    os.makedirs(part, exist_ok=True)
    for name in FILES:
        p = os.path.join(src, name)
        if os.path.isfile(p):
            copy_with_progress(p, os.path.join(part, name))
    finalize(part, dest)


def from_hf(dest, part):
    os.environ.pop("HF_HUB_OFFLINE", None)          # TEST-ENGINE uni yoqib qo'ygan bo'lishi mumkin
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        raise RuntimeError("huggingface_hub o'rnatilmagan - modelni internetdan yuklab bo'lmaydi.")
    check_space(dest, part)
    say("  HuggingFace'dan yuklanmoqda: %s (~3 GB)" % REPO)
    say("  Internet tezligiga qarab 5-30 daqiqa. Uzilsa - qayta ishga tushiring, davom etadi.")
    for attempt in range(1, 4):
        try:
            snapshot_download(REPO, revision=REVISION, local_dir=part, allow_patterns=list(FILES))
            break
        except Exception as e:   # tarmoq uzilishi - bir necha marta qayta urinamiz
            if attempt == 3:
                raise RuntimeError("Yuklab bo'lmadi (internetni tekshiring): %s" % e)
            say("  [!] Yuklash uzildi (%s). %d-urinish 10 soniyadan keyin..." % (type(e).__name__, attempt + 1))
            time.sleep(10)
    finalize(part, dest)


def ask(question):
    try:
        a = input("  %s " % question).strip().lower()
    except EOFError:
        return False
    return a in ("h", "ha", "y", "yes", "xa")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "translate_model"))
    ap.add_argument("--source", action="append", default=[])
    ap.add_argument("--download", choices=("ask", "yes", "no"), default="ask")
    a = ap.parse_args()

    dest = os.path.abspath(a.dest)
    part = dest + ".part"
    if not os.path.isdir(os.path.dirname(dest)):
        raise RuntimeError("Enjin papkasi topilmadi: %s. Avval asosiy o'rnatuvchini ishga tushiring." % os.path.dirname(dest))

    if is_complete(dest):
        say("  Tarjima modeli allaqachon o'rnatilgan: " + dest)
        return 0
    if os.path.exists(dest):
        say("  [!] Chala/buzilgan model papkasi almashtiriladi: " + dest)

    for s in a.source:
        s = os.path.abspath(s)
        if s != dest and is_complete(s):
            from_local(s, dest, part)
            say("  [OK] Tarjima modeli o'rnatildi: " + dest)
            return 0

    if a.download == "no":
        say("  Lokal nusxa topilmadi - model o'rnatilmadi.")
        return 3
    if a.download == "ask":
        say("  Lokal nusxa (translate_model papkasi) topilmadi.")
        if not ask("Modelni internetdan yuklab olamizmi? ~3 GB (h = ha, Enter = keyinroq):"):
            say("  Keyinroq o'rnatsa bo'ladi - tools papkasidagi INSTALL-TRANSLATE-MODEL orqali.")
            return 3
    from_hf(dest, part)
    say("  [OK] Tarjima modeli o'rnatildi: " + dest)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        say("\n  To'xtatildi. Qayta ishga tushirsangiz - davom etadi.")
        sys.exit(1)
    except Exception as e:
        say("  [XATO] %s" % e)
        sys.exit(1)
