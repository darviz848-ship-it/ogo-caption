"""bench_lib unit-testlari (model kerak emas):  python3 bench/test_bench_lib.py

- normalizatsiya: apostrof variantlari, tinish belgilari, so'z oxiridagi gʻ, raqam guruhlari;
- WER/CER: qo'lda hisoblangan misollar, -ning -> -ni hisoblagichi;
- panel_merge_words: main.js dagi mergeWords bilan bir xil (node orqali tasodifiy kirishlarda);
- premerge / dedup_repeats / drop_noise_segments / timing_check.
"""
import json
import os
import random
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_lib as B  # noqa: E402

eng = B.load_engine()
W = lambda *ws: [{"word": w, "start": float(i), "end": float(i) + 0.5} for i, w in enumerate(ws)]
T = lambda words: [t for t, _, _ in B.tokens(words)]


def test_norm():
    assert B.norm_word(u"Oʻzbekiston,") == ["o'zbekiston"]
    assert B.norm_word(u"“Salom”") == ["salom"]
    assert B.norm_word(u"tog‘") == ["tog'"]                       # so'z oxiridagi gʻ qoladi
    assert B.norm_word(u"'salom'") == ["salom"]                  # qo'shtirnoq olib tashlanadi
    assert B.norm_word(u"'kino'") == ["kino'"]                   # o dan keyingi ' - oʻ deb qoladi (ikki tomonda bir xil)
    assert B.norm_word(u"sa'y-harakat") == ["sa'y", "harakat"]
    assert B.norm_word(u"ma’no.") == ["ma'no"]
    assert B.norm_word(u"(1995-yil)") == ["1995", "yil"]
    assert B.norm_word(u"—") == []
    assert T(W("10 000", "so'm")) == ["10000", "so'm"]            # _fmt_number guruhlashi
    assert T(W("10", "000")) == ["10000"]
    assert T(W("Salom,", "QO'SHIQ!")) == ["salom", "qo'shiq"]


def test_ref_numbers():
    r = [w["word"] for w in B.ref_words(eng, u"Atigi ikki hafta ichida yigirma besh kishi")]
    assert r == ["Atigi", "2", "hafta", "ichida", "25", "kishi"], r


def test_score():
    ref = B.tokens(W("bu", "kitobning", "muqovasi", "qizil"))
    hyp = B.tokens(W("bu", "kitobni", "muqovasi", "juda", "qizil"))
    s = B.score(ref, hyp)
    assert (s["n_ref"], s["sub"], s["del"], s["ins"], s["ning_ni"]) == (4, 1, 0, 1, 1), s
    s = B.score(B.tokens(W("a", "b", "c")), B.tokens(W("a", "c")))
    assert (s["sub"], s["del"], s["ins"]) == (0, 1, 0)
    agg = B.aggregate([B.score(ref, hyp), B.score(ref, ref)])
    assert abs(agg["wer"] - 100.0 * 2 / 8) < 1e-9, agg
    s = B.score(B.tokens(W("abc")), B.tokens(W("abd")))
    assert s["chars"] == 3 and s["char_err"] == 1
    # rapidfuzz va sof Python bir xil
    if B._Lev is not None:
        rnd = random.Random(1)
        for _ in range(200):
            a = [rnd.choice("abcde") for _ in range(rnd.randint(0, 12))]
            b = [rnd.choice("abcde") for _ in range(rnd.randint(0, 12))]
            lev, B._Lev = B._Lev, None
            slow = len(B._editops(a, b))
            B._Lev = lev
            assert slow == len(B._editops(a, b)), (a, b)


def test_premerge_dedup_noise():
    raw = [{"word": " yigirma", "start": 0, "end": 1, "seg": 0}, {"word": " to", "start": 1, "end": 1.2, "seg": 0},
           {"word": "'rt", "start": 1.2, "end": 1.5, "seg": 0}, {"word": " kishi", "start": 1.6, "end": 2, "seg": 0}]
    # Hozirgi plagin: son "to" + "'rt" da uziladi -> "20 to'rt"
    now = [w["word"] for w in B.panel_merge_words(B.engine_words(eng, raw))]
    assert now == ["20", "to'rt", "kishi"], now
    fixed = [w["word"] for w in B.panel_merge_words(B.engine_words(eng, B.premerge(raw)))]
    assert fixed == ["24", "kishi"], fixed
    # segment chegarasida qo'shilmaydi
    raw2 = [{"word": " salom", "start": 0, "end": 1, "seg": 0}, {"word": "dunyo", "start": 1, "end": 2, "seg": 1}]
    assert len(B.premerge(raw2)) == 2
    d = [w["word"] for w in B.dedup_repeats(W("musiqa", "musiqa", "musiqa", "musiqa", "salom"))]
    assert d == ["musiqa", "salom"], d
    d = B.dedup_repeats(W("ha", "ha", "keldi"))                       # 2 marta - tegilmaydi
    assert [w["word"] for w in d] == ["ha", "ha", "keldi"]
    d = [w["word"] for w in B.dedup_repeats(W("rahmat", "sizga.", "rahmat", "sizga.", "rahmat", "sizga.", "Xayr"))]
    assert d == ["rahmat", "sizga.", "Xayr"], d
    d = B.dedup_repeats(W("a", "a", "a"))
    assert len(d) == 1 and d[0]["start"] == 0.0 and d[0]["end"] == 2.5
    raw3 = [{"word": " Musiqa", "start": 0, "end": 1, "seg": 0}, {"word": " Salom", "start": 2, "end": 3, "seg": 1},
            {"word": " musiqa", "start": 3, "end": 4, "seg": 1}]
    assert [w["word"] for w in B.drop_noise_segments(raw3)] == [" Salom", " musiqa"]


def test_timing():
    segs = [{"type": "music", "start": 0.0, "end": 5.0},
            {"type": "speech", "start": 5.0, "end": 8.0, "id": "1", "text": "bugun havo yaxshi"},
            {"type": "silence", "start": 8.0, "end": 10.0},
            {"type": "speech", "start": 10.0, "end": 12.0, "id": "2", "text": "rahmat"}]
    hyp = [("musiqa", 2.0, 2.5), ("bugun", 5.2, 5.6), ("havo", 5.7, 6.0), ("yaxshi", 6.1, 6.5), ("rahmat", 3.0, 3.4)]
    tc = B.timing_check(segs, eng, hyp)
    assert tc == {"aligned": 4, "off_sync": 1, "halluc": 2, "bad_dur": 0}, tc


def test_panel_parity():
    """Python panel_merge_words == main.js mergeWords (ikkala paket)."""
    if shutil.which("node") is None:
        print("  (node yo'q - mergeWords mosligi tekshirilmadi)")
        return
    rnd = random.Random(5)
    pieces = ["salom", "'yaman", "‘ga", "’lim", "-sinf", "-", "'", " o", "ʻzbek", "`x", "qo", "  -da ", "5", "o'n"]
    cases = [[{"word": rnd.choice(pieces), "start": i * 0.5, "end": i * 0.5 + 0.4} for i in range(rnd.randint(0, 9))]
             for _ in range(300)]
    root = os.path.dirname(HERE)
    for pkg in ("win", "mac"):
        js = os.path.join(root, pkg, "payload", "panel", "js", "main.js")
        prog = ("const vm=require('vm'),fs=require('fs');const c={window:{},console,require:()=>({}),process:{platform:'win32',env:{}}};"
                "vm.createContext(c);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);"
                "const cases=JSON.parse(fs.readFileSync(0,'utf8'));"
                "process.stdout.write(JSON.stringify(cases.map(w=>c.mergeWords(w))));")
        out = subprocess.run(["node", "-e", prog, js], input=json.dumps(cases), capture_output=True, text=True, check=True)
        js_res = json.loads(out.stdout)
        py_res = [B.panel_merge_words(c) for c in cases]
        assert js_res == py_res, pkg


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("OK ", name)
    print("\nHAMMASI O'TDI (bench_lib, %d ta test)" % n)
