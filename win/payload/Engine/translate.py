import sys
import json
import os
import re
import html
import warnings
warnings.filterwarnings("ignore")

# Oflayn tarjima: MADLAD-400-3B-MT (Google, Apache 2.0), CTranslate2 int8 formatida.
# Ishlatish:  python translate.py <kirish.json>
# kirish.json:
#   {"mode": "words", "words": [{"word","start","end"}, ...], "source": "uz", "target": "ru", "words_per_line": 3}
#   {"mode": "srt",   "srt_path": "C:/.../captions.srt",    "target": "ru", "words_per_line": 3}
# "source" berilmasa matndan taxminlanadi (uz / ru / en).
# Chiqish (stdout): PROGRESS:<foiz> qatorlari, oxirida bitta JSON:
#   {"success": true, "blocks": [{"text","start","end"}, ...], "sentences": N}

try:
    import ctranslate2
    import tokenizers
except ImportError:
    print(json.dumps({"error": "ctranslate2 / tokenizers o'rnatilmagan."}))
    sys.exit(1)


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


MODEL_DIR = os.path.join(get_base_path(), "translate_model")

# Gap shu belgilardan biri bilan tugasa — jumla tugadi (oxiridagi qo'shtirnoq/qavs hisobga olinmaydi)
_SENT_END = re.compile(u"[.!?…]+[\"'»”)\\]]*$")
# Panel bilan bir xil: tinish belgisidan keyin yangi SRT blok
_BLOCK_END = re.compile(u"[.,!?:;…]$")

MAX_PAUSE = 1.2        # shundan uzun pauza — yangi jumla
MAX_SENT_WORDS = 40    # jumla juda uzun bo'lsa majburan bo'linadi
SOFT_SENT_WORDS = 20   # shundan uzun bo'lsa vergulda ham bo'linadi


def cyrillic_to_latin(text):
    mapping = {
        'А': 'A', 'а': 'a', 'Б': 'B', 'б': 'b', 'В': 'V', 'в': 'v',
        'Г': 'G', 'г': 'g', 'Д': 'D', 'д': 'd', 'Е': 'E', 'е': 'e',
        'Ё': 'Yo', 'ё': 'yo', 'Ж': 'J', 'ж': 'j', 'З': 'Z', 'з': 'z',
        'И': 'I', 'и': 'i', 'Й': 'Y', 'й': 'y', 'К': 'K', 'к': 'k',
        'Л': 'L', 'л': 'l', 'М': 'M', 'м': 'm', 'Н': 'N', 'н': 'n',
        'О': 'O', 'о': 'o', 'П': 'P', 'п': 'p', 'Р': 'R', 'р': 'r',
        'С': 'S', 'с': 's', 'Т': 'T', 'т': 't', 'У': 'U', 'у': 'u',
        'Ф': 'F', 'ф': 'f', 'Х': 'X', 'х': 'x', 'Ц': 'Ts', 'ц': 'ts',
        'Ч': 'Ch', 'ч': 'ch', 'Ш': 'Sh', 'ш': 'sh', 'Ъ': "'", 'ъ': "'",
        'Ь': '', 'ь': '', 'Э': 'E', 'э': 'e', 'Ю': 'Yu', 'ю': 'yu',
        'Я': 'Ya', 'я': 'ya', 'Ў': "O'", 'ў': "o'", 'Қ': 'Q', 'қ': 'q',
        'Ғ': "G'", 'ғ': "g'", 'Ҳ': 'H', 'ҳ': 'h'
    }
    res = []
    for i, char in enumerate(text):
        if char in ('Е', 'е'):
            prev = text[i - 1].lower() if i > 0 else ''
            if i == 0 or not text[i - 1].isalpha() or prev in u'аеёиоуэюяў':
                res.append('Ye' if char == 'Е' else 'ye')
            else:
                res.append('E' if char == 'Е' else 'e')
        else:
            res.append(mapping.get(char, char))
    return "".join(res)


def clean_uzbek(text):
    # Kirill qolgan bo'lsa lotinchaga, barcha tutuq/o'-belgilarini oddiy ' ga (shriftlarda ʻ bo'lmasligi mumkin)
    if any(u'\u0400' <= c <= u'\u04FF' for c in text):
        text = cyrillic_to_latin(text)
    return re.sub(u"[‘’ʻʼ`´]", "'", text)


# Yangi alifbo (2021 loyihasi: ó ǵ ş ç) dagi o'zbekcha matn MADLAD'ga joriy yozuvda beriladi -
# model shu yozuvni biladi. Joriy alifbodagi matn o'zgarmaydi.
_NEW_TO_CURRENT = {u"ó": u"o'", u"Ó": u"O'", u"ǵ": u"g'", u"Ǵ": u"G'", u"ş": u"sh", u"ç": u"ch"}
_NEW_LETTERS = re.compile(u"[óÓǵǴşŞçÇ]")
_CURRENT_MARKS = re.compile(u"[sScC][hH]|[oOgG]['‘’ʻʼ`´]")


def is_new_alphabet(texts):
    """Yangi alifbo: ó ǵ ş ç bor, joriy yozuvdagi sh / ch / oʻ / gʻ esa butun matnda yo'q."""
    s = " ".join(texts)
    return _NEW_LETTERS.search(s) is not None and _CURRENT_MARKS.search(s) is None


def from_new_alphabet(text):
    res = []
    for i, char in enumerate(text):
        if char in (u"Ş", u"Ç"):
            nxt = text[i + 1] if i + 1 < len(text) else ''
            prev = text[i - 1] if i > 0 else ''
            # "ŞAHAR" -> "SHAHAR", "Şahar" -> "Shahar", "TOŞ" -> "TOSH"
            upper = nxt.isupper() or (not nxt.isalpha() and prev.isupper())
            res.append((u"S" if char == u"Ş" else u"C") + (u"H" if upper else u"h"))
        else:
            res.append(_NEW_TO_CURRENT.get(char, char))
    return "".join(res)


# ---------------- Kirishni o'qish ----------------

def _parse_srt_time(t):
    h, m, rest = t.strip().replace('.', ',').split(':')
    s, ms = rest.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def read_srt(path):
    with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
        raw = f.read().replace('\r\n', '\n').replace('\r', '\n')
    units = []
    for block in re.split(r'\n\s*\n', raw.strip()):
        lines = [l for l in block.split('\n') if l.strip()]
        ti = next((i for i, l in enumerate(lines) if '-->' in l), -1)
        if ti < 0:
            continue
        a, b = lines[ti].split('-->')
        text = " ".join(l.strip() for l in lines[ti + 1:])
        text = re.sub(r'<[^>]+>', '', text).strip()   # <i>, <font> teglari
        if text:
            units.append({"text": text, "start": _parse_srt_time(a), "end": _parse_srt_time(b.split()[0])})
    return units


def group_sentences(units):
    """units: [{text,start,end}] (so'z yoki SRT blok) -> jumlalar ro'yxati (har biri units bo'lagi)."""
    sents, cur, nwords = [], [], 0
    for i, u in enumerate(units):
        cur.append(u)
        nwords += len(u["text"].split())
        nxt = units[i + 1] if i + 1 < len(units) else None
        t = u["text"].strip()
        brk = (
            nxt is None
            or _SENT_END.search(t) is not None
            or (nxt["start"] - u["end"]) > MAX_PAUSE
            or nwords >= MAX_SENT_WORDS
            or (nwords >= SOFT_SENT_WORDS and t.endswith((',', ';', ':')))
        )
        if brk:
            sents.append(cur)
            cur, nwords = [], 0
    return sents


# ---------------- Vaqtni qayta taqsimlash ----------------

def make_time_map(units):
    """Matn ulushi (0..1) -> vaqt. Asl so'zlarning vaqti bo'yicha, jumla ichidagi pauzalar hisobga olinadi."""
    weights = [max(1, len(u["text"])) + 1 for u in units]
    total = float(sum(weights))
    spans, acc = [], 0.0
    for u, w in zip(units, weights):
        spans.append((acc / total, (acc + w) / total, u["start"], u["end"]))
        acc += w

    def at(f):
        f = min(max(f, 0.0), 1.0)
        for a, b, s, e in spans:
            if f <= b or (a, b, s, e) == spans[-1]:
                k = 0.0 if b <= a else (f - a) / (b - a)
                return s + k * (e - s)
        return spans[-1][3]
    return at


def chunk_translation(text, units, words_per_line):
    words = text.split()
    if not words:
        return []
    time_at = make_time_map(units)
    lines, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        if len(cur) >= words_per_line or i == len(words) - 1 or _BLOCK_END.search(w):
            lines.append(cur)
            cur = []
    total = float(sum(len(w) + 1 for w in words))
    blocks, acc = [], 0.0
    for ln in lines:
        w = sum(len(x) + 1 for x in ln)
        start, end = time_at(acc / total), time_at((acc + w) / total)
        acc += w
        blocks.append({"text": " ".join(ln), "start": round(start, 3), "end": round(max(end, start + 0.05), 3)})
    # Bloklar bir-birini qoplamasin
    for a, b in zip(blocks, blocks[1:]):
        if a["end"] > b["start"]:
            a["end"] = b["start"]
    return blocks


# ---------------- Tarjima ----------------

# MADLAD o'zbek tilini asosan diniy parallel matnlarda ko'rgan: qisqa gaplarda
# "Аллах — Прощающий…" kabi gallyutsinatsiya beradi (15.10.2026 sinovida uz→ru 12 gapdan 2 tasi).
# Asl matnda yo'q shunday so'z chiqsa — gap boshqa yo'l bilan qayta tarjima qilinadi.
_RELIGIOUS = re.compile(
    u"(аллах|аллоҳ|alloh|allah|всевышн|поистине|господ|пророк|пайғамбар|payg'ambar|мўмин|mo'min|"
    u"верующ|праведн|худо|xudo|иймон|iymon|парвардигор|parvardigor|verily|prophet|believers|\\blord\\b|\\bgod\\b)",
    re.IGNORECASE)


def detect_language(texts):
    """SRT uchun asl tilni taxminlash: kirill -> ru, o'zbekcha belgilar -> uz, aks holda en."""
    s = " ".join(texts)
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return "en"
    cyr = sum(1 for c in letters if u'Ѐ' <= c <= u'ӿ')
    if cyr > len(letters) / 2:
        return "uz" if any(c in s for c in u"ўқғҳЎҚҒҲ") else "ru"
    low = " " + re.sub(u"[‘’ʻʼ`´]", "'", s.lower()) + " "
    uz_hits = len(re.findall(r"\b(va|bu|bilan|uchun|biz|siz|emas|yoki|ham|edi|bo'l\w*|qil\w*|\w+lar\w*)\b", low))
    uz_hits += len(re.findall(r"[og]'", low)) * 2
    return "uz" if uz_hits > len(low.split()) * 0.15 else "en"


def tidy(text, target):
    text = html.unescape(text)
    q_open, q_close = (u"«", u"»") if target == "ru" else ('"', '"')
    text = re.sub(r'"\s*([^"]+?)\s*"', q_open + r"\1" + q_close, text)
    text = re.sub(u"\\s+([.,!?:;…%])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text[:1].upper() + text[1:]


class Engine:
    def __init__(self):
        self.tok = tokenizers.Tokenizer.from_file(os.path.join(MODEL_DIR, "tokenizer.json"))
        threads = max(1, min(16, (os.cpu_count() or 4)))
        self.tr = ctranslate2.Translator(MODEL_DIR, device="cpu", compute_type="int8", intra_threads=threads)

    def run(self, texts, target, on_batch=None):
        src = [self.tok.encode(u"<2%s> %s" % (target, t)).tokens for t in texts]
        out = [None] * len(texts)
        # Uzunligi yaqin jumlalarni birga yuborish tezroq
        order = sorted(range(len(texts)), key=lambda i: len(src[i]))
        batch = 8
        for k in range(0, len(order), batch):
            idx = order[k:k + batch]
            res = self.tr.translate_batch(
                [src[i] for i in idx],
                beam_size=4,
                max_decoding_length=256,
                repetition_penalty=1.05,
                no_repeat_ngram_size=4,
            )
            for i, r in zip(idx, res):
                ids = [self.tok.token_to_id(t) for t in r.hypotheses[0]]
                out[i] = self.tok.decode([x for x in ids if x is not None], skip_special_tokens=True).strip()
            if on_batch:
                on_batch(min(len(order), k + batch) / float(len(order)))
        return out


def translate_texts(texts, source, target):
    eng = Engine()
    print("PROGRESS:10", flush=True)
    progress = lambda lo, hi: (lambda f: print("PROGRESS:%d" % (lo + int((hi - lo) * f)), flush=True))

    def direct(items, lo, hi):
        return eng.run(items, target, progress(lo, hi))

    def pivot(items, lo, hi):
        mid = (lo + hi) // 2
        return eng.run(eng.run(items, "en", progress(lo, mid)), target, progress(mid, hi))

    # Sinovda eng toza yo'llar: uz→ru inglizcha orqali, qolganlari to'g'ridan-to'g'ri
    use_pivot = source == "uz" and target == "ru"
    first, second = (pivot, direct) if use_pivot else (direct, pivot)
    if source == "en" or target == "en":
        second = None   # ingliz tili o'zi oraliq til — boshqa yo'l yo'q

    out = first(texts, 10, 85)

    bad = [i for i, (s, t) in enumerate(zip(texts, out)) if _RELIGIOUS.search(t) and not _RELIGIOUS.search(s)]
    if bad and second:
        retry = second([texts[i] for i in bad], 85, 99)
        for i, t in zip(bad, retry):
            if not _RELIGIOUS.search(t):
                out[i] = t
    print("PROGRESS:100", flush=True)
    return [tidy(t, target) for t in out], len(bad)


def main(cfg_path):
    with open(cfg_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    target = cfg.get("target", "ru")
    wpl = max(1, int(cfg.get("words_per_line", 3)))

    if not os.path.exists(os.path.join(MODEL_DIR, "model.bin")):
        raise RuntimeError("Tarjima modeli topilmadi: " + MODEL_DIR)

    if cfg.get("mode") == "srt":
        units = read_srt(cfg["srt_path"])
    else:
        units = [{"text": w["word"].strip(), "start": w["start"], "end": w["end"]}
                 for w in cfg.get("words", []) if w.get("word", "").strip()]
    if not units:
        raise RuntimeError("Tarjima qilinadigan matn yo'q.")

    sents = group_sentences(units)
    texts = []
    for s in sents:
        t = re.sub(u"\\s+([.,!?:;…%])", r"\1", " ".join(u["text"] for u in s))
        texts.append(t[:1].upper() + t[1:])   # ASR kichik harf beradi — gap boshi katta bo'lsa nomlar yaxshiroq tarjima bo'ladi

    current = [from_new_alphabet(t) for t in texts] if is_new_alphabet(texts) else texts
    source = cfg.get("source") or detect_language(current)
    if source == "uz":
        texts = current
    if source == target:
        raise RuntimeError("Matn allaqachon shu tilda (%s)." % target)
    print("PROGRESS:2", flush=True)
    translated, retried = translate_texts(texts, source, target)

    blocks = []
    for s, tr in zip(sents, translated):
        if target == "uz":
            tr = clean_uzbek(tr)
        blocks.extend(chunk_translation(tr, s, wpl))

    print(json.dumps({"success": True, "blocks": blocks, "sentences": len(sents), "source": source,
                      "retried": retried, "pairs": [[a, b] for a, b in zip(texts, translated)]}))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Sozlama fayli berilmadi."}))
        sys.exit(1)
    try:
        main(sys.argv[1])
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
