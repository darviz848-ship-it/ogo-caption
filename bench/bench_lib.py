"""O'lchov stendi uchun umumiy qism: plagin post-processing'i, normalizatsiya, WER / CER, vaqt tekshiruvi.

Plagin bilan bir xil bo'lishi uchun Engine funksiyalari (cyrillic_to_latin, merge_number_words)
to'g'ridan-to'g'ri win/payload/Engine/transcribe.py dan import qilinadi; panel mergeWords esa
main.js dagi bilan aynan bir xil Python nusxasi (tools/../bench/test_bench_lib.py node orqali solishtiradi).
"""
import importlib.util
import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENGINE_PY = os.path.join(ROOT, "win", "payload", "Engine", "transcribe.py")

APOSTROPHES = u"‘’ʻʼ`´"


def load_engine(path=ENGINE_PY):
    """Engine transcribe.py ni modul sifatida yuklaydi (faster_whisper bo'lmasa - soxta modul)."""
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        stub = types.ModuleType("faster_whisper")
        stub.WhisperModel = None
        sys.modules["faster_whisper"] = stub
    spec = importlib.util.spec_from_file_location("ogo_engine_transcribe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------- Plagin zanjiri ----------------

def engine_words(eng, raw_words, is_uzbek=True):
    """transcribe.py dagi sikl: strip, kirill -> lotin, so'ng merge_number_words."""
    result = []
    for w in raw_words:
        word_text = w["word"].strip()
        if is_uzbek or eng.has_uzbek_cyrillic(word_text):
            if any(u'Ѐ' <= c <= u'ӿ' for c in word_text):
                word_text = eng.cyrillic_to_latin(word_text)
        result.append({"word": word_text, "start": w["start"], "end": w["end"]})
    return eng.merge_number_words(result)


def panel_merge_words(words):
    """main.js mergeWords: ' ‘ ’ yoki - bilan boshlangan bo'lak oldingi so'zga qo'shiladi."""
    merged = []
    for w in words:
        t = w["word"].strip()
        if t.startswith(("'", u"‘", u"’", "-")) and merged:
            merged[-1]["word"] += t
            merged[-1]["end"] = w["end"]
        else:
            merged.append({"word": t, "start": w["start"], "end": w["end"]})
    return merged


# ---------------- Sinovdagi post-processing (o'lchovda foyda bersa Engine'ga o'tadi) ----------------

def premerge(raw_words):
    """Bo'shliqsiz boshlangan bo'lak ("'yaman", "'rt") oldingi so'zga - merge_number_words DAN OLDIN.
    faster-whisper apostrofni alohida "so'z" deb ajratadi: " qo" + "'yaman". Panel buni keyinroq
    qo'shadi, lekin son-so'zlar ("yigirma to" + "'rt") o'sha paytda allaqachon noto'g'ri yig'ilgan bo'ladi."""
    out = []
    for w in raw_words:
        if out and not w["word"].startswith(" ") and w.get("seg") == out[-1].get("seg") and w["word"].strip():
            out[-1] = dict(out[-1], word=out[-1]["word"] + w["word"], end=w["end"])
        else:
            out.append(dict(w))
    return out


def _key(word):
    return re.sub(r"[^\w']", "", word.lower())


def dedup_repeats(words, min_run=3, max_n=4):
    """Ketma-ket >= min_run marta takrorlangan 1..max_n so'zli bo'lakni bitta qoldiradi
    ("musiqa musiqa musiqa" -> "musiqa"). 2 marta takror (ha ha) - tegilmaydi."""
    out = list(words)
    changed = True
    while changed:
        changed = False
        for n in range(1, max_n + 1):
            i = 0
            while i + n * min_run <= len(out):
                gram = [_key(w["word"]) for w in out[i:i + n]]
                if not all(gram):
                    i += 1
                    continue
                run = 1
                while out[i + run * n:i + (run + 1) * n] and [_key(w["word"]) for w in out[i + run * n:i + (run + 1) * n]] == gram:
                    run += 1
                if run >= min_run:
                    last = out[i + (run - 1) * n:i + run * n]
                    keep = [dict(w) for w in out[i:i + n]]
                    keep[-1]["end"] = last[-1]["end"]
                    out[i:i + run * n] = keep
                    changed = True
                i += 1
    return out


NOISE_TAGS = {"musiqa", "music", u"музыка", "kulgi", "qarsak", "applause", "laughter", u"смех", u"аплодисменты"}


def drop_noise_segments(raw_words):
    """Butun segment faqat "musiqa" / "[music]" kabi teglardan iborat bo'lsa - tashlanadi."""
    by_seg = {}
    for w in raw_words:
        by_seg.setdefault(w.get("seg"), []).append(w)
    bad = {s for s, ws in by_seg.items() if ws and all(_key(w["word"]) in NOISE_TAGS for w in ws)}
    return [w for w in raw_words if w.get("seg") not in bad]


# ---------------- Normalizatsiya (ikkala tomonga bir xil) ----------------

def norm_word(text):
    """Apostrof variantlari -> ', kichik harf, tinish belgilarisiz. Bir nechta token qaytishi mumkin."""
    t = text
    for a in APOSTROPHES:
        t = t.replace(a, "'")
    t = t.lower()
    t = re.sub(r"[^\w']+", " ", t).replace("_", " ")
    out = []
    for w in t.split():
        w = w.lstrip("'")
        # so'z oxiridagi ' - faqat o'/g' (tog', bog') bo'lsa qoladi, aks holda qo'shtirnoq
        while w.endswith("'") and not (len(w) >= 2 and w[-2] in "og"):
            w = w[:-1]
        if w:
            out.append(w)
    return out


def tokens(words):
    """[{word,start,end}] -> [(token, start, end)]; "10 000" kabi raqam guruhlari bitta tokenga."""
    toks = []
    for w in words:
        for t in norm_word(w["word"]):
            if toks and t.isdigit() and len(t) == 3 and toks[-1][0].isdigit() and toks[-1][3]:
                p = toks[-1]
                toks[-1] = (p[0] + t, p[1], w["end"], True)
            else:
                toks.append((t, w["start"], w["end"], t.isdigit()))
    return [(t, s, e) for t, s, e, _ in toks]


def ref_words(eng, text):
    """Etalon matn plagin natijasi bilan bir xil yo'ldan o'tadi: mergeWords + merge_number_words."""
    ws = [{"word": w, "start": 0.0, "end": 0.0} for w in text.split()]
    return eng.merge_number_words(panel_merge_words(ws))


# ---------------- WER / CER ----------------

try:
    from rapidfuzz.distance import Levenshtein as _Lev
except ImportError:   # sekinroq, lekin natija bir xil
    _Lev = None


def _editops(a, b):
    if _Lev is not None:
        return [(op.tag, op.src_pos, op.dest_pos) for op in _Lev.editops(a, b)]
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    ops, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
            if a[i - 1] != b[j - 1]:
                ops.append(("replace", i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append(("delete", i - 1, j))
            i -= 1
        else:
            ops.append(("insert", i, j - 1))
            j -= 1
    return ops[::-1]


def align(ref, hyp):
    """Tekislash: [(ref_i | None, hyp_j | None)] - mos/almashtirilgan juftlar, o'chirilgan, qo'shilgan."""
    ops = _editops(ref, hyp)
    pairs, i, j = [], 0, 0
    for tag, si, dj in ops + [("end", len(ref), len(hyp))]:
        while i < si and j < dj:
            pairs.append((i, j))
            i, j = i + 1, j + 1
        if tag == "replace":
            pairs.append((i, j))
            i, j = i + 1, j + 1
        elif tag == "delete":
            pairs.append((i, None))
            i += 1
        elif tag == "insert":
            pairs.append((None, j))
            j += 1
    return pairs


def score(ref_toks, hyp_toks):
    """Bitta yozuv: so'z va harf darajasidagi xatolar soni + xato turlari."""
    ref = [t[0] for t in ref_toks]
    hyp = [t[0] for t in hyp_toks]
    pairs = align(ref, hyp)
    s = sum(1 for i, j in pairs if i is not None and j is not None and ref[i] != hyp[j])
    d = sum(1 for i, j in pairs if j is None)
    ins = sum(1 for i, j in pairs if i is None)
    ning = sum(1 for i, j in pairs if i is not None and j is not None
               and ref[i].endswith("ning") and hyp[j] == ref[i][:-2])
    rs, hs = " ".join(ref), " ".join(hyp)
    if _Lev is not None:
        cdist = _Lev.distance(rs, hs)
    else:
        cdist = len(_editops(list(rs), list(hs)))
    return {"n_ref": len(ref), "sub": s, "del": d, "ins": ins, "ning_ni": ning,
            "chars": len(rs), "char_err": cdist, "pairs": pairs}


def aggregate(items):
    n = sum(x["n_ref"] for x in items) or 1
    c = sum(x["chars"] for x in items) or 1
    e = sum(x["sub"] + x["del"] + x["ins"] for x in items)
    return {"wer": 100.0 * e / n, "cer": 100.0 * sum(x["char_err"] for x in items) / c,
            "sub": sum(x["sub"] for x in items), "del": sum(x["del"] for x in items),
            "ins": sum(x["ins"] for x in items), "ning_ni": sum(x["ning_ni"] for x in items),
            "n_ref": n}


# ---------------- Uzun fayllar: so'z vaqtlari va musiqa ustidagi gallyutsinatsiya ----------------

def timing_check(segments, eng, hyp_toks, pairs_tol=0.5, edge=0.3):
    """segments - prepare_fleurs.py dagi bo'laklar. Qaytaradi:
    aligned  - etalon so'ziga tekislangan gipoteza so'zlari soni,
    off_sync - ulardan o'z gapi vaqt oralig'idan (+-pairs_tol s) tashqaridagilari,
    halluc   - o'rtasi musiqa/sukut ichida (nutq chegarasidan > edge s uzoqda) bo'lgan so'zlar."""
    ref_toks, owner = [], []
    for k, sg in enumerate(segments):
        if sg["type"] == "speech":
            for t in tokens(ref_words(eng, sg["text"])):
                ref_toks.append(t)
                owner.append(k)
    pairs = align([t[0] for t in ref_toks], [t[0] for t in hyp_toks])
    aligned = off = 0
    for i, j in pairs:
        if i is None or j is None:
            continue
        sg = segments[owner[i]]
        mid = (hyp_toks[j][1] + hyp_toks[j][2]) / 2.0
        aligned += 1
        if mid < sg["start"] - pairs_tol or mid > sg["end"] + pairs_tol:
            off += 1
    halluc = 0
    for _, s, e in hyp_toks:
        mid = (s + e) / 2.0
        for sg in segments:
            if sg["type"] != "speech" and sg["start"] + edge <= mid <= sg["end"] - edge:
                halluc += 1
                break
    bad_dur = sum(1 for _, s, e in hyp_toks if e < s)
    return {"aligned": aligned, "off_sync": off, "halluc": halluc, "bad_dur": bad_dur}
