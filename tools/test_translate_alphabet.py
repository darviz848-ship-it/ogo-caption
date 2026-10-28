"""translate.py: yangi alifbodagi (ó ǵ ş ç) o'zbekcha kirish MADLAD'ga joriy yozuvda berilishini sinash.

Ishlatish:  python3 tools/test_translate_alphabet.py [Engine/translate.py ...]
            default: win va mac paketlaridagi translate.py
Model kerak emas: ctranslate2 / tokenizers soxta modul bilan almashtiriladi, tarjima o'rniga
translate_texts() ga nima kelganini yozib olamiz.
"""
import importlib.util
import io
import json
import os
import sys
import tempfile
import types
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = sys.argv[1:] or [os.path.join(ROOT, p, "payload", "Engine", "translate.py") for p in ("win", "mac")]
CASES = json.load(open(os.path.join(ROOT, "tools", "alphabet_cases.json"), encoding="utf-8"))["cases"]
APOS = u"'ʻ‘’`ʼ´"
NEW_LETTERS = set(u"óÓǵǴşŞçÇ")


def load(path):
    for name in ("ctranslate2", "tokenizers"):
        sys.modules.setdefault(name, types.ModuleType(name))
    spec = importlib.util.spec_from_file_location("translate_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def canon(text):
    """o/g dan keyingi har xil apostrofni ' ga birxillash (teskari o'girish natijasi shunday bo'ladi)."""
    out = []
    for i, c in enumerate(text):
        out.append("'" if c in APOS and i > 0 and text[i - 1] in "oOgG" else c)
    return "".join(out)


def run_main(mod, cfg):
    """main() ni soxta tarjima bilan ishga tushiradi: (translate_texts ga kelgan matnlar, manba til, JSON)."""
    seen = {}

    def fake_translate(texts, source, target):
        seen["texts"], seen["source"] = list(texts), source
        return ["T%d" % i for i in range(len(texts))], 0

    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "m"))
        open(os.path.join(tmp, "m", "model.bin"), "w").close()
        mod.MODEL_DIR = os.path.join(tmp, "m")
        mod.translate_texts = fake_translate
        if "srt" in cfg:
            p = os.path.join(tmp, "in.srt")
            with open(p, "w", encoding="utf-8") as f:
                f.write(cfg.pop("srt"))
            cfg["srt_path"] = p
        cp = os.path.join(tmp, "cfg.json")
        with open(cp, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        buf = io.StringIO()
        with redirect_stdout(buf):
            mod.main(cp)
    out = json.loads(buf.getvalue().strip().splitlines()[-1])
    return seen["texts"], seen["source"], out


SRT_NEW = (u"1\n00:00:00,000 --> 00:00:01,500\nBugun Toşkentda havo yaxşi.\n\n"
           u"2\n00:00:01,600 --> 00:00:03,000\nÇoyxonada ózbekça qóşiq eşitdik,\n\n"
           u"3\n00:00:03,100 --> 00:00:04,000\nIs'hoq aka toǵga ketdi.\n\n")
SRT_CUR = (u"1\n00:00:00,000 --> 00:00:01,500\nBugun Toshkentda havo yaxshi.\n\n"
           u"2\n00:00:01,600 --> 00:00:03,000\nChoyxonada o'zbekcha qo'shiq eshitdik,\n\n"
           u"3\n00:00:03,100 --> 00:00:04,000\nIs'hoq aka tog'ga ketdi.\n\n")


def check(path):
    mod = load(path)
    n = 0
    for inp, expected, note, roundtrip in CASES:
        # Joriy alifbodagi matn (yangi harflarsiz) - aynan o'zi qaytadi
        if not (set(inp) & NEW_LETTERS):
            assert mod.from_new_alphabet(inp) == inp, (inp, note)
            n += 1
        if roundtrip:
            got = mod.from_new_alphabet(expected)
            assert got == canon(inp), (expected, got, canon(inp), note)
            n += 1
    for new, cur in [(u"ŞAHAR", "SHAHAR"), (u"TOŞ", "TOSH"), (u"Ş", "Sh"), (u"ÇOY ÇIROYLI", "CHOY CHIROYLI"),
                     (u"Ózbekiston", "O'zbekiston"), (u"ǴALABA", "G'ALABA"), (u"façade", "fachade")]:
        assert mod.from_new_alphabet(new) == cur, (new, mod.from_new_alphabet(new), cur)
        n += 1

    # Yangi alifbodagi tayyor SRT -> ru: manba til "uz" aniqlanadi, MADLAD'ga joriy yozuv ketadi
    texts, source, out = run_main(mod, {"mode": "srt", "srt": SRT_NEW, "target": "ru", "words_per_line": 3})
    assert source == "uz", source
    assert texts == ["Bugun Toshkentda havo yaxshi.", "Choyxonada o'zbekcha qo'shiq eshitdik, Is'hoq aka tog'ga ketdi."], texts
    # Joriy alifbodagi xuddi shu SRT - aynan shu matnlar (ikki yo'l bir xil natija beradi)
    texts_cur, source_cur, out_cur = run_main(mod, {"mode": "srt", "srt": SRT_CUR, "target": "ru", "words_per_line": 3})
    assert (texts_cur, source_cur) == (texts, source)
    assert out_cur["blocks"] == out["blocks"]
    # words rejimi (panel joriy yozuvni yuboradi) - matn o'zgarmaydi
    words = [{"word": w, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, w in enumerate("Salom, bugun o'zbek tilida.".split())]
    texts_w, source_w, _ = run_main(mod, {"mode": "words", "words": words, "source": "uz", "target": "en", "words_per_line": 3})
    assert texts_w == ["Salom, bugun o'zbek tilida."] and source_w == "uz", texts_w
    # Joriy alifbodagi o'zbekcha SRT ichida ş/ç li xorijiy nom (Çelik) - matn aynan o'zgarmaydi
    srt_mixed = u"1\n00:00:00,000 --> 00:00:01,000\nBugun Toshkentga Çelik ham keldi va biz bilan gaplashdi.\n\n"
    texts_m, source_m, _ = run_main(mod, {"mode": "srt", "srt": srt_mixed, "target": "ru", "words_per_line": 3})
    assert texts_m == [u"Bugun Toshkentga Çelik ham keldi va biz bilan gaplashdi."] and source_m == "uz", (texts_m, source_m)
    assert mod.is_new_alphabet([u"Bugun Toşkentda"]) and mod.is_new_alphabet([u"Is'hoq aka toǵga ketdi."])
    assert not mod.is_new_alphabet([u"Bugun Toshkentda", u"Çelik"]) and not mod.is_new_alphabet([u"o'zbek Ózbek"])
    assert not mod.is_new_alphabet([u"Salom, bugun"]) and not mod.is_new_alphabet([u"Привет"])
    n += 6
    # Inglizcha SRT dagi ç (façade) ga tegilmaydi
    texts_en, source_en, _ = run_main(mod, {"mode": "srt", "srt": u"1\n00:00:00,000 --> 00:00:01,000\nThe façade of the building is new.\n\n",
                                            "target": "ru", "words_per_line": 3})
    assert source_en == "en" and texts_en == [u"The façade of the building is new."], (source_en, texts_en)
    n += 4
    print("OK  %s: %d ta tekshiruv (from_new_alphabet, srt/words rejimi)" % (os.path.relpath(path, ROOT), n))


if __name__ == "__main__":
    for f in FILES:
        check(f)
    print("\nHAMMASI O'TDI (translate.py, yangi alifbo kirishi)")
