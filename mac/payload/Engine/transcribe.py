import sys
import json
import warnings
import os
warnings.filterwarnings("ignore")

try:
    from faster_whisper import WhisperModel
except ImportError:
    print(json.dumps({"error": "faster_whisper o'rnatilmagan. Iltimos kuting yoki o'rnating."}))
    sys.exit(1)

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

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
    i = 0
    while i < len(text):
        char = text[i]
        if char in ('Е', 'е'):
            is_word_start = (i == 0) or (not text[i-1].isalpha())
            is_after_vowel = False
            if i > 0:
                prev = text[i-1].lower()
                is_after_vowel = prev in ('а', 'е', 'ё', 'и', 'о', 'у', 'э', 'ю', 'я', 'ў')
            if is_word_start or is_after_vowel:
                res.append('Ye' if char == 'Е' else 'ye')
            else:
                res.append('E' if char == 'Е' else 'e')
        else:
            res.append(mapping.get(char, char))
        i += 1
    return "".join(res)

def has_uzbek_cyrillic(text):
    uzbek_chars = set(u'ўқғҳЎҚҒҲ')
    return any(char in uzbek_chars for char in text)

# ---------------- Son-so'zlarni raqamga aylantirish (uz / ru / en) ----------------
# Whisper sonlarni ko'pincha so'z bilan yozadi ("yigirma besh", "двадцать пять").
# Quyidagi blok ketma-ket kelgan son-so'zlarni bitta raqamli so'zga birlashtiradi
# ("25"), timestampni birinchi so'z boshidan oxirgi so'z oxirigacha oladi.

_APOSTROPHES = u"‘’ʻʼ`´"

def _build_num_vocab():
    v = {}
    # Birliklar (0-9)
    for w, n in {
        "nol": 0, "bir": 1, "ikki": 2, "uch": 3, "to'rt": 4, "besh": 5,
        "olti": 6, "yetti": 7, "sakkiz": 8, "to'qqiz": 9,
        u"ноль": 0, u"нуль": 0, u"один": 1, u"одна": 1, u"одно": 1,
        u"два": 2, u"две": 2, u"двух": 2, u"три": 3, u"трёх": 3, u"трех": 3,
        u"четыре": 4, u"четырёх": 4, u"четырех": 4, u"пять": 5, u"пяти": 5,
        u"шесть": 6, u"шести": 6, u"семь": 7, u"семи": 7,
        u"восемь": 8, u"восьми": 8, u"девять": 9, u"девяти": 9,
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9,
    }.items():
        v[w] = ("unit", n)
    # 10-19 (to'liq qiymat — keyin birlik qo'shilmaydi)
    for w, n in {
        u"десять": 10, u"десяти": 10, u"одиннадцать": 11, u"одиннадцати": 11,
        u"двенадцать": 12, u"двенадцати": 12, u"тринадцать": 13, u"тринадцати": 13,
        u"четырнадцать": 14, u"четырнадцати": 14, u"пятнадцать": 15, u"пятнадцати": 15,
        u"шестнадцать": 16, u"шестнадцати": 16, u"семнадцать": 17, u"семнадцати": 17,
        u"восемнадцать": 18, u"восемнадцати": 18, u"девятнадцать": 19, u"девятнадцати": 19,
        "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    }.items():
        v[w] = ("teen", n)
    # O'nliklar (keyin birlik qo'shilishi mumkin: "yigirma besh" = 25)
    for w, n in {
        "o'n": 10, "yigirma": 20, "o'ttiz": 30, "qirq": 40, "ellik": 50,
        "oltmish": 60, "yetmish": 70, "sakson": 80, "to'qson": 90,
        u"двадцать": 20, u"двадцати": 20, u"тридцать": 30, u"тридцати": 30,
        u"сорок": 40, u"сорока": 40, u"пятьдесят": 50, u"пятидесяти": 50,
        u"шестьдесят": 60, u"шестидесяти": 60, u"семьдесят": 70, u"семидесяти": 70,
        u"восемьдесят": 80, u"восьмидесяти": 80, u"девяносто": 90, u"девяноста": 90,
        "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
        "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    }.items():
        v[w] = ("ten", n)
    # Ruscha yuzliklar (to'g'ridan-to'g'ri qiymat)
    for w, n in {
        u"сто": 100, u"ста": 100, u"двести": 200, u"двухсот": 200,
        u"триста": 300, u"трёхсот": 300, u"трехсот": 300,
        u"четыреста": 400, u"четырёхсот": 400, u"четырехсот": 400,
        u"пятьсот": 500, u"пятисот": 500, u"шестьсот": 600, u"шестисот": 600,
        u"семьсот": 700, u"семисот": 700, u"восемьсот": 800, u"восьмисот": 800,
        u"девятьсот": 900, u"девятисот": 900,
    }.items():
        v[w] = ("hund", n)
    # "yuz"/"hundred" — oldingi songa ko'paytiriladi ("besh yuz" = 500)
    for w in ("yuz", "hundred"):
        v[w] = ("hundmult", 100)
    # Ming / million / milliard
    for w, n in {
        "ming": 1000, u"тысяча": 1000, u"тысячи": 1000, u"тысяч": 1000,
        u"тысячу": 1000, u"тысяче": 1000, "thousand": 1000,
        "million": 10**6, u"миллион": 10**6, u"миллиона": 10**6, u"миллионов": 10**6,
        "milliard": 10**9, "billion": 10**9, u"миллиард": 10**9, u"миллиарда": 10**9,
        u"миллиардов": 10**9,
    }.items():
        v[w] = ("scale", n)
    return v

_NUM_VOCAB = _build_num_vocab()

# Yolg'iz kelganda matnligicha qoldiriladigan so'zlar ("bir kuni", "one of them").
# Hammasini majburan raqam qilish uchun bu to'plamni bo'shatib qo'ying: set()
_LONE_KEEP = {"bir", u"один", u"одна", u"одно", "one"}

# Ruscha tartib sonlar: o'zak + sifat qo'shimchasi ("двадцать пятый год" -> "25 год")
_RU_ORD_STEMS = {
    u"перв": 1, u"втор": 2, u"трет": 3, u"четверт": 4, u"четвёрт": 4,
    u"пят": 5, u"шест": 6, u"седьм": 7, u"восьм": 8, u"девят": 9, u"десят": 10,
    u"одиннадцат": 11, u"двенадцат": 12, u"тринадцат": 13, u"четырнадцат": 14,
    u"пятнадцат": 15, u"шестнадцат": 16, u"семнадцат": 17, u"восемнадцат": 18,
    u"девятнадцат": 19, u"двадцат": 20, u"тридцат": 30, u"сороков": 40,
    u"пятидесят": 50, u"шестидесят": 60, u"семидесят": 70, u"восьмидесят": 80,
    u"девяност": 90, u"сот": 100, u"тысячн": 1000,
}
_RU_ADJ_ENDINGS = sorted(
    {u"ый", u"ий", u"ой", u"ая", u"яя", u"ое", u"ее", u"ые", u"ие",
     u"ого", u"его", u"ому", u"ему", u"ым", u"им", u"ом", u"ем", u"ей",
     u"ую", u"юю", u"ых", u"их", u"ыми", u"ими",
     u"ье", u"ья", u"ью", u"ьего", u"ьему", u"ьем", u"ьей", u"ьим", u"ьих"},
    key=len, reverse=True)

def _classify_numword(raw):
    """So'zni tahlil qiladi: son bo'lsa (turkum, qiymat, qo'shimchalar), aks holda None."""
    t = raw.strip().lower()
    for ap in _APOSTROPHES:
        t = t.replace(ap, "'")
    lead, trail = "", ""
    while t and not (t[0].isalpha() or t[0] == "'"):
        lead += t[0]
        t = t[1:]
    while t and not (t[-1].isalpha() or t[-1] == "'"):
        trail = t[-1] + trail
        t = t[:-1]
    if not t:
        return None
    kind = val = None
    is_ta = False
    ord_type = None  # None | "uz" | "ru"
    base = t
    if t in _NUM_VOCAB:
        kind, val = _NUM_VOCAB[t]
    elif t.endswith("inchi") and t[:-5] in _NUM_VOCAB:
        base = t[:-5]
        kind, val = _NUM_VOCAB[base]
        ord_type = "uz"
    elif t.endswith("nchi") and t[:-4] in _NUM_VOCAB:
        base = t[:-4]
        kind, val = _NUM_VOCAB[base]
        ord_type = "uz"
    elif t.endswith("ta") and t[:-2] in _NUM_VOCAB:
        base = t[:-2]
        kind, val = _NUM_VOCAB[base]
        is_ta = True
    else:
        # Ruscha tartib son: "пятый", "двадцатом", "третьего"...
        for end in _RU_ADJ_ENDINGS:
            if t.endswith(end) and t[:-len(end)] in _RU_ORD_STEMS:
                base = t[:-len(end)]
                val = _RU_ORD_STEMS[base]
                ord_type = "ru"
                if val >= 1000:
                    kind = "scale"
                elif val >= 100:
                    kind = "hund"
                elif val >= 20:
                    kind = "ten"
                elif val >= 10:
                    kind = "teen"
                else:
                    kind = "unit"
                break
        if kind is None and "-" in t:
            # Inglizcha defisli ko'rinish: "twenty-five"
            p = t.split("-")
            if (len(p) == 2 and p[0] in _NUM_VOCAB and p[1] in _NUM_VOCAB
                    and _NUM_VOCAB[p[0]][0] == "ten" and _NUM_VOCAB[p[1]][0] == "unit"):
                kind = "tenunit"
                val = _NUM_VOCAB[p[0]][1] + _NUM_VOCAB[p[1]][1]
        if kind is None:
            return None
    return {"kind": kind, "val": val, "ta": is_ta, "ord": ord_type,
            "lead": lead, "trail": trail, "base": base}

def _fmt_number(n):
    # 10 000 dan katta sonlarni o'qish oson bo'lishi uchun guruhlab yozamiz
    if n >= 10000:
        return "{:,}".format(n).replace(",", " ")
    return str(n)

def merge_number_words(words):
    """Ketma-ket son-so'zlarni bitta raqamli so'zga yig'adi (timestamplari bilan)."""
    out = []
    i = 0
    n = len(words)
    while i < n:
        first = _classify_numword(words[i].get("word", ""))
        if first is None:
            out.append(words[i])
            i += 1
            continue
        total = 0
        current = 0
        used = set()
        last_scale = None
        infos = []
        j = i
        while j < n:
            inf = first if j == i else _classify_numword(words[j].get("word", ""))
            if inf is None:
                break
            # Yangi ochuvchi belgi ("(", '"') — son shu yerda uzildi (defis davomga ruxsat)
            if j > i and inf["lead"] and inf["lead"] != "-":
                break
            k, v = inf["kind"], inf["val"]
            if k == "unit":
                ok = not (used & {"unit", "teen"})
            elif k == "teen":
                ok = not (used & {"unit", "teen", "ten"})
            elif k in ("ten", "tenunit"):
                ok = not (used & {"unit", "teen", "ten"})
            elif k == "hund":
                ok = not (used & {"unit", "teen", "ten", "hund"})
            elif k == "hundmult":
                ok = "hund" not in used and not (used & {"teen", "ten"})
            else:  # scale
                ok = last_scale is None or v < last_scale
            if not ok:
                break
            if k == "hundmult":
                current = (current if current else 1) * 100
                used.add("hund")
                used.discard("unit")
            elif k == "scale":
                total += (current if current else 1) * v
                current = 0
                last_scale = v
                used.clear()
            else:
                current += v
                if k == "tenunit":
                    used.update(("ten", "unit"))
                else:
                    used.add(k)
            infos.append(inf)
            j += 1
            # Tartib son, "-ta" yoki tinish belgisi — son shu so'zda tugadi
            if inf["ta"] or inf["ord"] or inf["trail"]:
                break
        value = total + current
        f_inf, l_inf = infos[0], infos[-1]
        if len(infos) == 1 and f_inf["base"] in _LONE_KEEP and not (f_inf["ta"] or f_inf["ord"]):
            # "bir kuni", "one of them" — bu yerda "bir" son emas, aniqlovchi
            out.append(words[i])
        else:
            txt = _fmt_number(value)
            if l_inf["ta"]:
                txt += " ta"
            if l_inf["ord"] == "uz":
                txt += "-"
            txt = f_inf["lead"] + txt + l_inf["trail"]
            out.append({
                "word": txt,
                "start": words[i]["start"],
                "end": words[j - 1]["end"],
            })
        i = j
    return out

def transcribe(audio_path, language="uz"):
    if not os.path.exists(audio_path):
        print(json.dumps({"error": f"Fayl topilmadi: {audio_path}"}))
        sys.exit(1)

    try:
        # Agar til "auto" bo'lsa, Whisper avtomatik aniqlashi uchun None yuboramiz
        whisper_lang = None if language == "auto" else language

        if language == "uz":
            # Lokal maxsus o'zbek modeli (faqat lotincha)
            model_size = os.path.join(get_base_path(), "uzbek_model")
            if not os.path.exists(os.path.join(os.path.join(get_base_path(), "uzbek_model"), "config.json")):
                model_size = "base"
        else:
            # Rus, Ingliz yoki Avtomatik aniqlash uchun ko'p tilli model
            model_size = os.path.join(get_base_path(), "multi_model") 
            if not os.path.exists(os.path.join(os.path.join(get_base_path(), "multi_model"), "config.json")):
                # Agar papka yo'q bo'lsa yoki ichida model fayllari bo'lmasa, "base" ga o'tadi (HuggingFace dan yuklanadi)
                model_size = "base"

        # Kompyuter kuchi yetarli bo'lsa cuda, bo'lmasa cpu. 
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        # Initial prompt orqali Whisper'ni faqat o'zbek, rus va ingliz tillariga yo'naltiramiz (English bias kamaytirildi)
        prompt_seed = "salom, qandaysiz, привет, hello"

        segments, info = model.transcribe(
            audio_path, 
            language=whisper_lang, 
            word_timestamps=True,
            initial_prompt=prompt_seed
        )
        
        # Agar "auto" rejimida o'zbek, rus yoki ingliz bo'lmagan mutlaqo boshqa yot til aniqlansa (shovqin/musiqa xatosi)
        if language == "auto" and info and info.language not in ["uz", "ru", "en"]:
            # O'zbek tiliga majburlab qaytadan tahlil qilamiz
            segments, info = model.transcribe(
                audio_path, 
                language="uz", 
                word_timestamps=True,
                initial_prompt=prompt_seed
            )

        total_duration = info.duration if info and info.duration else 1.0

        # O'zbek tili tanlanganini yoki avtomatik aniqlanganini aniqlash
        is_uzbek = (language == "uz") or (language == "auto" and info and info.language == "uz")

        result = []
        for segment in segments:
            # Hisoblash va real vaqtda progress yuborish
            percent = min(100, int((segment.end / total_duration) * 100))
            print(f"PROGRESS:{percent}", flush=True)

            for word in segment.words:
                word_text = word.word.strip()
                
                # Agar o'zbek tili bo'lsa yoki tarkibida o'zbek kirill harflari bo'lsa lotinchaga o'giramiz
                if is_uzbek or has_uzbek_cyrillic(word_text):
                    if any(u'\u0400' <= char <= u'\u04FF' for char in word_text):
                        word_text = cyrillic_to_latin(word_text)

                result.append({
                    "word": word_text,
                    "start": word.start,
                    "end": word.end
                })

        # Son-so'zlarni raqamga aylantiramiz ("yigirma besh" -> "25")
        result = merge_number_words(result)

        # language — "auto" rejimida tarjima uchun asl tilni bilish kerak
        print(json.dumps({"success": True, "words": result, "language": info.language if info else language}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Audio fayl manzili berilmadi."}))
        sys.exit(1)
    
    audio_file = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else "uz"
    transcribe(audio_file, lang)
