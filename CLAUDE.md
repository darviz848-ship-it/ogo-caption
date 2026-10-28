# OgoCaption — Claude uchun kontekst

OgoCaption — Premiere Pro uchun lokal (internetsiz) AI caption CEP paneli: faster-whisper → so'z vaqtlari → SRT → Premiere'ga import (MOGRT stillari bilan). Ixtiyoriy oflayn tarjima (MADLAD-400-3B).

Egasi — **Lochinbek**, montajor, kod yozmaydi. Hisobotni **o'zbekcha (lotin)**, oddiy tilda yoz, "sen" deb murojaat qil. Natijani raqamda ko'rsat (WER, CER, soniya), "yaxshilandi" degan quruq gap kerak emas.

## Repo tuzilishi

- `win/` — Windows o'rnatish paketi (`D:\det\OgoCaption-Setup` nusxasi), `mac/` — Mac paketi (`D:\det\OgoCaption-Mac-Setup`).
- **Repoda YO'Q** (Lochinning kompyuterida qoladi): modellar (`model.bin`), Python runtime (`runtime.zip`, `runtime-*.tar.gz`), tarjima modeli (`translate_model/`). Ularni repoga qo'shma — GitHub chegarasi 100 MB.
- `win/payload/Engine/*.py` va `mac/payload/Engine/*.py` **baytma-bayt bir xil**. Birini o'zgartirsang, ikkinchisiga ham nusxala. Panelda `index.html`, `css/`, `CSXS/`, `CSInterface.js` ham bir xil.
- `main.js` va `hostscript.jsx` paketlarda **farq qiladi**: win'da Python yo'li `resolvePythonExe()` orqali topiladi (python-path.txt → portativ runtime → tizim Python), mac'dagisi universal (Win+Mac). Panel o'zgarishini ikkala `main.js` ga alohida kirit, ko'r-ko'rona almashtirma.
- `tools/` — `test_mainjs.js <main.js> mac|win` (soxta CEP muhitida stsenariylar), `test_jsx.js`, `build_zip.py`, `build_runtime.py`, `verify_macho.py`.
- `.gitattributes` — `* -text`: `.sh`/`.command` LF, `.bat`/`.ps1` CRLF holida qolishi shart. Qator oxirlarini o'zgartirma.

## Engine hozir qanday ishlaydi

`transcribe.py <wav> <uz|ru|en|auto>` → stdout'ga `PROGRESS:n` qatorlari, oxirida JSON: `{success, words:[{word,start,end}], language}`.

- `uz` → `Engine/uzbek_model` (CT2 Whisper Medium, faqat lotin o'zbekcha), qolganlari → `multi_model` (CT2, ~483 MB, ko'p tilli).
- `WhisperModel(..., device="cpu", compute_type="int8")`, `transcribe(word_timestamps=True, initial_prompt="salom, qandaysiz, привет, hello")`. `beam_size` default, VAD yo'q, `condition_on_previous_text` default.
- Kirill chiqsa → `cyrillic_to_latin`, so'ng `merge_number_words` (son-so'z → raqam: "yigirma besh" → "25").
- `main.js`: `mergeWords` (`'` bilan boshlangan bo'lakni oldingi so'zga qo'shadi), `wordsToBlocks` (tinish belgisida blok uziladi), `buildSrt`, `runEngine`.
- `translate.py <cfg.json>` (mode `words|srt`) — MADLAD CT2 int8; →uz natija kirillda keladi va lotinga o'giriladi.

## Qat'iy cheklovlar

- Plagin ishlayotganda **internetsiz** ishlashi shart: API, onlayn LLM, onlayn tarjima yo'q.
- Litsenziya tijoriy ishga mos bo'lishi kerak (Apache / MIT / BSD). CC-BY-NC (masalan, NLLB) — yo'q.
- Runtime: Win — Python 3.14.4, faster-whisper 1.2.1, ctranslate2 4.8.1, tokenizers 0.23.1, onnxruntime bor. Mac — CPython 3.13, ctranslate2 4.8.2, **onnxruntime YO'Q**, shuning uchun Silero VAD Mac'da ishlamaydi. VAD qo'shsang, onnxruntime bo'lmasa jim o'chsin, xato bermasin.
- Yangi pip paket kerak bo'lsa — qo'shma, hisobotda ayt: runtime Lochinning kompyuterida qayta yig'iladi.
- RAM: tarjima cho'qqisi 5,24 GB. Transkripsiyani og'irlashtirma.
- Bu muhitda Premiere, Windows va Mac yo'q. Panelni faqat `tools/test_mainjs.js` va `tools/test_jsx.js` bilan sina.
- Model kerak bo'lsa — HuggingFace'dan yukla (`bench/models/`, gitignore'da). HF'ga ulanib bo'lmasa, to'xta va hisobotda ayt: cloud muhit sozlamasida tarmoqni ochish kerak.

## Vazifa 1 — yangi o'zbek alifbosi (Lochin tasdiqlagan, 28.10.2026)

2021-yilgi loyiha: **oʻ → ó, gʻ → ǵ, sh → ş, ch → ç**. Katta harflar: Ó Ǵ Ş Ç; "Sh" va "SH" → "Ş", "Ch" va "CH" → "Ç". `ng` va tutuq belgisi (ʼ) o'zgarmaydi.

- Panelda tanlov: **«Alifbo: joriy / yangi»**, oxirgi tanlov eslab qolinadi (localStorage). Default — joriy.
- Qayerga ta'sir qiladi: o'zbekcha transkripsiya SRT'si, →uz tarjima natijasi, «Tayyor SRT faylni tarjima qilish» natijasi (maqsad til uz bo'lsa).
- **Joriy rejimdagi natija hozirgidan baytma-bayt farq qilmasin.**
- Qiyin joylar:
  - Morfema chegarasidagi s+h tutuq bilan yoziladi (Is'hoq, as'hob) — ş ga aylanmaydi.
  - Modeldan apostrofning har xil varianti keladi: `'` `ʻ` `‘` `’` `` ` ``. o/g dan keyin kelgani — oʻ/gʻ, boshqa harfdan keyingisi — tutuq (ma'no, san'at).
  - Konversiya `mergeWords` dan keyin bo'lsin («qo» + «'yaman» avval qo'shilsin).
- MOGRT shriftlarida ǵ/Ǵ (U+01F5/U+01F4) gliflari bo'lmasligi mumkin. `.mogrt` — zip: ichidan shrift nomlarini top va hisobotda yoz, glif bor-yo'qligini ham (aniqlab bo'lsa).
- Konvertor uchun unit-test — kamida 30 holat: katta/kichik harf, apostrof variantlari, Is'hoq, raqam bilan aralash so'z, so'z boshi va oxiri.

## Vazifa 2 — o'zbekcha xatolarni kamaytirish

Ma'lum o'lchov (15.10.2026, Texnoplov VO 7:15, 962 so'z, mijoz materiali — repoda yo'q): uzbek_model **WER 11,4% / CER 5,6%**. Tez-tez uchraydigan xatolar:
- «-ning» → «-ni»;
- musiqa ustida «musiqa musiqa», takrorlanadigan gallyutsinatsiya;
- apostrofli so'zning bo'linib qolishi («qo» + «'yaman»).

Ish tartibi:

1. **Avval o'lchov stendi** `bench/`: FLEURS `uz_uz` (google/fleurs, test split, kamida 150 gap) bo'yicha WER/CER va tezlik (RTF, CPU int8). Normalizatsiya ikkala tomonga bir xil: panel `mergeWords` + `merge_number_words`, apostrof variantlarini birxillash, tinish belgilari va katta-kichik harfni olib tashlash. Aks holda WER sun'iy oshadi (bo'lingan apostrof uni 33% gacha ko'targan).
2. **Model.** Asl `uzbek_model` ochiq joyda yo'q. O'rniga `Kotib/uzbek_stt_v1` (Whisper Medium, Apache 2.0) ni `ct2-transformers-converter --quantization float16` bilan CT2 ga o'gir — 15.10 da asl model bilan 96% so'zma-so'z bir xil natija bergan. Asl model bilan yakuniy tekshiruvni Lochinning kompyuterida qilamiz.
3. **Faqat dekodlash sozlamalari va post-processing** (GPU yo'q, qayta o'qitish yo'q):
   - `initial_prompt`: uz uchun aralash «salom, qandaysiz, привет, hello» o'rniga to'g'ri imloli o'zbekcha jumla (oʻ, gʻ, -ning, -dagi bilan); ru/en/auto uchun alohida prompt.
   - Gallyutsinatsiyaga qarshi: `condition_on_previous_text=False`, `hallucination_silence_threshold`, `compression_ratio_threshold`, `no_speech_threshold`, takror n-gramlarni kesish.
   - `beam_size`, `best_of`, temperature fallback.
   - VAD — faqat onnxruntime bor joyda (Win).
   - So'z vaqtlari buzilmasin: SRT sinxroni eng muhimi.
   - Lug'at yoki qoidaga asoslangan post-tuzatish — faqat o'lchovda foyda bersa.

   Har o'zgarishni alohida o'lcha va jadvalga yoz: «sozlama → WER / CER / RTF». Yaxshilamagan narsani kodga qo'shma.
4. **Boshqa model** (masalan, HF'dagi o'zbekcha large-v3-turbo fine-tune'lar): litsenziya tijoriy bo'lsa va CT2 ga o'girilsa, sinab ko'r. WER, RTF va hajmni yoz. Modelni o'zing almashtirma — tavsiya qil, Lochin hal qiladi.

## Topshirish

- `main` ga to'g'ridan yozma: alohida branch, oxirida PR.
- `bench/REPORT.md`: avval/keyin WER/CER/RTF jadvali, o'zgargan fayllar, Lochinning kompyuterida asl model va Premiere'da nimani tekshirish kerakligi.
- Tekshiruv: `win/` va `mac/` dagi Engine fayllari bir xil (`cmp`); `node tools/test_mainjs.js win/payload/panel/js/main.js win` va `... mac/payload/panel/js/main.js mac` — o'tsin (yangi alifbo stsenariysini ham qo'sh).
- Ikkala paketning `VERSION.txt` va `README.txt` fayliga o'zgarishlarni qo'sh.
