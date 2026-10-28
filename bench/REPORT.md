# OgoCaption — 28.10.2026 hisoboti

Lochin, qisqasi:

- **Vazifa 1 (yangi alifbo) — tayyor.** Panelda «Alifbo: joriy / yangi» tanlovi bor, testlar o'tdi. Premiere'da hali sinalmagan — pastdagi ro'yxat bo'yicha tekshirib ko'r.
- **Vazifa 2 (o'zbekcha xatolar) — o'lchov stendi tayyor, lekin WER/CER/RTF raqamlari YO'Q.** Cloud muhitda `huggingface.co` yopiq (proxy 403 qaytardi), shuning uchun `Kotib/uzbek_stt_v1` modelini yuklab bo'lmadi. Model bo'lmasa o'lchab bo'lmaydi, o'lchanmagan narsani esa Engine'ga qo'shmaslik kerak. Shuning uchun `transcribe.py` dagi dekodlash sozlamalariga **tegmadim**.
- **Tarmoqni ochish:** cloud muhit sozlamasida (sessiya sarlavhasidagi muhit menyusi → Edit → Network access) `huggingface.co` ni Allowed domains ga qo'sh (yoki kengroq daraja tanla), «Allow package managers» belgisi turaversin. Yo'riqnoma: https://code.claude.com/docs/en/cloud-environments#network-access. Keyin yangi sessiyada `sh bench/run_all.sh` hammasini o'zi o'lchaydi.

---

## Vazifa 1 — yangi o'zbek alifbosi

### Nima qilindi

Panelda «Ovozni aniqlash sozlamalari» kartasida, «Til» ostida yangi tanlov:

| Tanlov | Nima bo'ladi |
|---|---|
| **Joriy (o', g', sh, ch)** — default | Hammasi avvalgidek. Natija eski versiya bilan baytma-bayt bir xil. |
| **Yangi (ó, ǵ, ş, ç)** | oʻ→ó, gʻ→ǵ, sh→ş, ch→ç; Oʻ→Ó, Gʻ→Ǵ, Sh/SH→Ş, Ch/CH→Ç. `ng` va tutuq belgisi o'zgarmaydi. |

Oxirgi tanlov eslab qolinadi (localStorage) — Premiere'ni yopib ochsang ham turadi.

Yangi alifbo **faqat o'zbekcha matnga** qo'llanadi:

1. o'zbekcha transkripsiya SRT'si (til «uz» yoki «auto» da o'zbek aniqlansa);
2. → o'zbek tiliga tarjima natijasi;
3. «Tayyor SRT faylni tarjima qilish», maqsad til o'zbek bo'lsa.

Rus/ingliz SRT'ga tegilmaydi. Tarjimaga (MADLAD) esa doim **joriy yozuvdagi** matn ketadi — model yangi alifboni deyarli ko'rmagan. Shu sababli `translate.py` ga ham kichik qo'shimcha: yangi alifbodagi tayyor SRT'ni rus/ingliz tiliga tarjima qilsang, matn modelga avval joriy yozuvga o'girib beriladi (ó→o', ş→sh ...). Bu faqat matnda ó/ǵ/ş/ç bo'lib, sh/ch/o'/g' umuman bo'lmaganda ishlaydi — joriy alifbodagi SRT o'zgarmaydi.

Konversiya `mergeWords` dan keyin bo'ladi: «qo» + «'shiq» avval «qo'shiq» bo'lib qo'shiladi, keyin «qóşiq».

### Qiyin joylar qanday hal qilindi (misollar testdan)

| Kirish | Natija | Izoh |
|---|---|---|
| `o'zbek`, `oʻzbek`, `o‘zbek`, `o’zbek`, `` o`zbek `` | `ózbek` | apostrofning 5 xil varianti (+ ʼ va ´ ham) |
| `O'ZBEKISTON` | `ÓZBEKISTON` | katta harf |
| `tog'`, `bog‘da` | `toǵ`, `boǵda` | so'z oxirida va o'rtasida gʻ |
| `Shahar`, `SHAHAR`, `Choy`, `CHOY` | `Şahar`, `ŞAHAR`, `Çoy`, `ÇOY` | Sh/SH→Ş, Ch/CH→Ç |
| `Is'hoq`, `as'hob`, `IS'HOQ` | o'zgarmaydi | s+h orasida tutuq — ş emas |
| `ma'no`, `san'at`, `taʼlim`, `e'tibor` | o'zgarmaydi | boshqa harfdan keyingi apostrof — tutuq |
| `she'r` | `şe'r` | sh + tutuq |
| `2-o'rin`, `1-chorakda`, `100%` | `2-órin`, `1-çorakda`, `100%` | raqam bilan aralash |
| `tong`, `ming` | o'zgarmaydi | ng |
| `шаҳар` | o'zgarmaydi | kirillga tegilmaydi |

Jami **57 holat** (`tools/alphabet_cases.json`), ikkala `main.js` da bir xil natija. Konvertorni ikki marta qo'llash natijani o'zgartirmaydi.

Bilib qo'y: o'zbekcha matn ichidagi inglizcha so'z ham o'zgaradi: `show` → `şow`, `Chicago` → `Çicago`. Bu alifbo qoidasining o'zi.

### MOGRT shriftlari va ǵ / Ǵ gliflari

`.mogrt` ichidan topilgan shriftlar (shriftning o'zi MOGRT ichida yo'q — kompyuterdagi shrift ishlatiladi). Gliflarni Google Fonts'dagi hozirgi versiyada tekshirdim (fontsource 5.3.0: Montserrat v31, Bebas Neue v16):

| MOGRT | Shrift | ó Ó ş Ş ç Ç | **ǵ Ǵ** | ʻ (U+02BB) |
|---|---|---|---|---|
| bounce | Montserrat SemiBold | bor | **bor** | bor |
| fade | Bebas Neue Regular | bor | **YO'Q** | yo'q |
| trend | Bebas Neue Regular (fade bilan aynan bir xil fayl) | bor | **YO'Q** | yo'q |

Demak, fade/trend uslubida yangi alifboda «ǵ» chiqmaydi (bo'sh kvadrat yoki boshqa shrift). Variantlar: (1) fade/trend uchun ǵ bor shrift tanlash (Montserrat, Arial va h.k.); (2) Bebas Neue'da «G + U+0301 (qo'shiluvchi urg'u)» bor va shriftda mark-joylash jadvali bor — Premiere uni Ǵ qilib chizishi mumkin, lekin bu sinalmagan, kodga qo'shmadim. Hozirgi panel MOGRT'ni ishlatmaydi (faqat SRT), SRT'da Premiere'ning caption shrifti ishlatiladi — uni ham tekshirish kerak.

Sening kompyuteringdagi Montserrat/Bebas Neue boshqa versiya bo'lishi mumkin — pastdagi tekshiruv ro'yxatida bor.

### Tekshiruv natijalari (shu muhitda, Premiere'siz)

| Buyruq | Natija |
|---|---|
| `cmp` win/mac: transcribe.py, translate.py, get_translate_model.py, index.html, style.css, manifest.xml, CSInterface.js | bir xil |
| `node tools/test_mainjs.js win/payload/panel/js/main.js win` | 8 eski + 9 alifbo stsenariysi — o'tdi |
| `node tools/test_mainjs.js mac/payload/panel/js/main.js mac` | 10 eski + 18 alifbo (Mac va Windows rejimi) — o'tdi |
| `node tools/test_jsx.js mac/payload/panel/jsx/hostscript.jsx` | o'tdi (hostscript o'zgarmagan) |
| `node tools/test_alphabet.js` | 57 holat × 2 ta main.js — o'tdi |
| `python3 tools/test_translate_alphabet.py` | 128 tekshiruv × 2 ta translate.py — o'tdi |
| eski va yangi `translate.py`, 300 ta tasodifiy joriy alifbo kirishi | 300 / 300 bir xil JSON |
| yangi `test_mainjs.js` eski `main.js` da | alifbo stsenariysi yiqiladi (test haqiqatan tekshiradi), «default joriy» — o'tadi (natija bir xil) |

Yo'l-yo'lakay tuzatildi: `test_mainjs.js` Linux/Mac'da Windows yo'llarini (`\tmp\...`) joriy papkada g'alati nomli fayl qilib yaratar va tozalamasdi — shu sababli eski kod bilan ham 2 ta test yiqilardi. Endi bu yo'llar vaqtinchalik papkaga tushadi, Windows'da xatti-harakat o'zgarmagan.

---

## Vazifa 2 — o'zbekcha xatolarni kamaytirish

### Holat: o'lchab bo'lmadi

`huggingface.co:443` — proxy 403 (tarmoq siyosati rad etdi). Shu sababli:

- `Kotib/uzbek_stt_v1` ni yuklab, CT2 ga o'girib bo'lmadi;
- boshqa o'zbekcha modellarni (large-v3-turbo fine-tune'lar) qidirib, litsenziyasini ko'rib bo'lmadi;
- **birorta ham WER/CER/RTF raqami yo'q.** Pastdagi jadval — bo'sh shablon, uni o'ylab to'ldirmadim.

FLEURS ma'lumotini esa Google'ning asl arxividan oldim (`storage.googleapis.com/xtreme_translations/FLEURS102/uz_uz.tar.gz` — HF'dagi `google/fleurs` aynan shu yozuvlar, litsenziya CC-BY-4.0, repoga kirmaydi).

| | Qiymat |
|---|---|
| FLEURS uz_uz test | 862 yozuv, **345 noyob gap**, 68,6 daqiqa |
| Qisqa to'plam (`--set short`) | birinchi 150 gap, 29,9 daqiqa, 2808 so'z (normalizatsiyadan keyin) |
| Uzun to'plam (`--set long`) | 10 fayl × ~4,5 daqiqa = 45,3 daqiqa: boshqa 190 gap + sukut (0,3–2,5 s) + har 5 gapdan keyin 4–8 s sintetik musiqa, boshida 6 s musiqa |

Uzun to'plam nega kerak: FLEURS gaplari qisqa (≤30 s, bitta oyna), u yerda `condition_on_previous_text` va gallyutsinatsiyaga qarshi sozlamalar deyarli ta'sir qilmaydi. Sening 7:15 lik VO kabi uzun faylda va musiqa ustida esa ta'sir qiladi. Uzun fayllarda har bo'lakning vaqti ma'lum, shuning uchun stend yana ikki narsani sanaydi: **musiqa/sukut ustida chiqqan so'zlar** (gallyutsinatsiya) va **o'z gapi vaqtidan 0,5 s dan ko'p siljigan so'zlar** (SRT sinxroni).

### Jadval (model ochilgach to'ldiriladi)

Plagin bugun: `initial_prompt="salom, qandaysiz, привет, hello"`, beam 5, temperature fallback, `condition_on_previous_text=True`, VAD yo'q.

| Sozlama | WER % | CER % | RTF | Izoh |
|---|---:|---:|---:|---|
| base (plagin bugun) | o'lchanmagan | — | — | 15.10 dagi mijoz VO: 11,4 / 5,6 (asl model) |
| prompt_uz (oʻ, gʻ, -ning, -dagi bilan) | o'lchanmagan | | | |
| prompt_none | o'lchanmagan | | | |
| cond_off | o'lchanmagan | | | |
| hst2 (hallucination_silence_threshold=2) | o'lchanmagan | | | |
| crt2.0 / nst0.4 | o'lchanmagan | | | |
| beam1 / beam3 / beam8 / temp0 | o'lchanmagan | | | |
| reppen1.1 / nrng4 | o'lchanmagan | | | |
| vad / vad500 (faqat Win) | o'lchanmagan | | | |
| pp_premerge / pp_dedup / pp_noise | o'lchanmagan | | | |

### Modelsiz topilgan narsalar (kod tahlili va unit-test)

1. **«qo» + «'yaman» bo'linishining sababi topildi.** faster-whisper so'zlarni ajratganda apostrof tokenini alohida «so'z» deb oladi (`split_tokens_on_spaces`: tinish belgisi = yangi so'z), keyin `'yaman` ni keyingi bo'lakka yopishtiradi. Panel `mergeWords` buni keyin tuzatadi.
2. **Shu sababli sonlar buziladi.** `merge_number_words` (Engine) `mergeWords` (panel) dan OLDIN ishlaydi. Model «yigirma to» + «'rt» bersa, hozir SRT'da **«20 to'rt»** chiqadi, to'g'risi **«24»**. Apostrofli hamma son-so'zlar xavf ostida: o'n, o'ttiz, to'rt, to'qqiz, to'qson. Unit-test buni ko'rsatadi (`bench/test_bench_lib.py`). Tuzatish tayyor — `pp_premerge` (bo'shliqsiz boshlangan bo'lakni son yig'ishdan oldin qo'shish), lekin qoida bo'yicha avval o'lchab, keyin Engine'ga qo'shamiz.
3. **«10 ming» → «10 1000».** `merge_number_words` raqam + «ming» ni yig'olmaydi. FLEURS etalonida ham bor («10 ming yilcha avval»). Model shunday yozsa, SRT'da «10 1000» chiqadi. Tuzatish kerak, o'lchov bilan birga.
4. **Panel `mergeWords` faqat ' ‘ ’ va - ni biladi**, ʻ (U+02BB) va `` ` `` ni bilmaydi. Model ʻ bilan bo'lsa, bo'lingan bo'lak qo'shilmay qoladi. Stend buni sanaydi (`apos_split_per_1k`) — model kelgach ko'ramiz.
5. **PyAV 19+ faster-whisper 1.2.1 ni buzadi** (`av.open(..., metadata_errors=)` olib tashlangan; 18.1 gacha ishlaydi — tekshirdim). Runtime qayta yig'ilsa `av<19` qoldir. Mac paketida 14.1 / 18.1 — joyida; Win runtime'dagi av versiyasi VERSION.txt da yozilmagan — `python -c "import av; print(av.__version__)"` bilan ko'rib qo'y.
6. Asl `uzbek_model` config'i Whisper Medium'ga mos (24 qatlam, OpenAI medium alignment boshlari), `multi_model` — Whisper Small. Fine-tune'larda alignment boshlari ko'pincha yo'qoladi — `convert_model.py` buni tekshiradi va asl modeldagiga tenglaydi (so'z vaqtlari uchun muhim).

### Stend tarkibi (`bench/`)

| Fayl | Vazifasi |
|---|---|
| `run_all.sh` | hammasi bitta buyruqda: paketlar, FLEURS, model o'girish, 19 ta sozlama × 2 to'plam, jadval |
| `prepare_fleurs.py` | FLEURS (HF yoki Google arxivi), qisqa va uzun to'plamlar |
| `convert_model.py` | HF → CT2 float16, litsenziya tekshiruvi (faqat apache/mit/bsd), tokenizer.json, alignment boshlari |
| `run_bench.py` | o'lchov: WER, CER, RTF, S/D/I, «-ning→-ni» soni, musiqa ustidagi so'zlar, vaqt siljishi; `--engine` — Engine'ning o'zi (subprocess) |
| `bench_lib.py` | plagin zanjiri (Engine `merge_number_words` to'g'ridan-to'g'ri import + panel `mergeWords` nusxasi), normalizatsiya |
| `summarize.py` | natijalardan Markdown jadval |
| `find_models.py` | HF'dagi o'zbekcha Whisper modellar, litsenziya bo'yicha saralangan |
| `make_dummy_model.py` | stend kodini modelsiz sinash uchun tasodifiy kichik model (natijasi ma'nosiz) |
| `test_bench_lib.py` | 6 test, jumladan Python `mergeWords` = JS `mergeWords` (300 tasodifiy kirish, ikkala main.js) |
| `requirements.txt` | faqat stend uchun (plagin runtime'iga qo'shilmaydi) |

Normalizatsiya ikki tomonga bir xil: etalon ham, model natijasi ham `mergeWords` + `merge_number_words` dan o'tadi, apostrof variantlari `'` ga birxillanadi, tinish belgilari va katta harf olib tashlanadi, «10 000» → «10000». So'z oxiridagi gʻ (tog') saqlanadi.

Stend kodi tasodifiy model bilan oxirigacha sinaldi (qisqa, uzun, VAD, beam, post-processing, Engine subprocess) — xatosiz ishladi. Bu raqamlar ma'nosiz, hisobotga kiritilmagan.

### Model ochilgach ish tartibi

1. `sh bench/run_all.sh` — `bench/out/kotib_ct2_f16/table.md` da 19 ta sozlama (qisqa va uzun to'plam). 4 yadroli CPU'da taxminan bir necha soat.
2. Yaxshilaganlarini birlashtirib o'lchash (`--config base+...`), so'z vaqti siljishi va musiqa ustidagi so'zlar oshmaganini tekshirish.
3. Faqat yaxshilaganini `transcribe.py` ga (win va mac, bir xil) qo'shish; VAD — faqat onnxruntime bo'lsa, yo'q bo'lsa jim o'chadi.
4. `run_bench.py --engine win/payload/Engine` — Engine'ning o'zi bilan yakuniy o'lchov.
5. `python3 bench/find_models.py` → tijoriy litsenziyali o'zbekcha modellarni `MODEL_REPO=... TAG=... sh bench/run_all.sh` bilan o'lchash (WER, RTF, hajm). Modelni almashtirmayman — faqat tavsiya.

---

## O'zgargan fayllar

| Fayl | O'zgarish |
|---|---|
| `win/payload/panel/index.html`, `mac/...` (bir xil) | «Alifbo» tanlovi |
| `win/payload/panel/js/main.js` | konvertor, localStorage, 3 joyda qo'llash |
| `mac/payload/panel/js/main.js` | xuddi shu, mac kodiga alohida kiritilgan (konvertor bloki win bilan aynan bir xil) |
| `win/payload/Engine/translate.py`, `mac/...` (bir xil) | yangi alifbodagi kirish → joriy yozuvda MADLAD'ga |
| `win/VERSION.txt`, `win/README.txt` (CRLF) | 2026-10-28 bo'limi |
| `mac/VERSION.txt`, `mac/README.txt` (LF) | 2026-10-28 bo'limi |
| `tools/test_mainjs.js` | alifbo stsenariylari; Linux/Mac'da Windows yo'llari tuzatildi |
| `tools/test_alphabet.js`, `tools/alphabet_cases.json`, `tools/test_translate_alphabet.py` | yangi testlar |
| `bench/*` | yangi o'lchov stendi |

`transcribe.py`, `hostscript.jsx`, `style.css`, o'rnatuvchilar — o'zgarmagan. Yangi pip paket plaginga kerak emas.

---

## Kompyuterga o'rnatish (yangilash paketi)

`python3 tools/build_update_win.py --out <papka> --zip` — Windows uchun kichik paket yig'adi: `OgoCaption-Yangilash-<sana>.zip` (~21 KB). Ichida faqat o'zgargan 3 fayl (panel `index.html`, `js/main.js`, Engine `translate.py`), `YANGILASH.bat` va `ORQAGA-QAYTARISH.bat`. Modellar, runtime, MOGRT tegilmaydi; eski fayllar `Hujjatlar\OgoCaption\update-backup\<sana-vaqt>\` ga zaxiralanadi. Skript o'rnatmadagi har faylning versiyasini SHA256 bo'yicha aytadi (15.10 paketi / allaqachon yangi / qo'lda o'zgartirilgan). `tools/test_update_win.sh` — 9 stsenariy (PowerShell 7.4 da, Linux'da; Windows PowerShell 5.1 da hali sinalmagan).

## Lochinning kompyuterida tekshirish kerak

**Premiere'da (Windows, keyin Mac):**

1. Panelda «Alifbo» tanlovi ko'rinadimi, «Yangi (ó, ǵ, ş, ç)» yozuvi to'g'ri chiqadimi.
2. «Yangi» ni tanla → Premiere'ni yop-och → hali ham «Yangi» turibdimi (CEP localStorage saqlayaptimi).
3. **Joriy rejim o'zgarmaganini isbotlash:** bitta sequence'da eski paket va yangi paket bilan SRT yarat, ikkalasini solishtir: `fc /b eski.srt yangi.srt` (Windows) yoki `cmp eski.srt yangi.srt` (Mac) — farq bo'lmasligi kerak.
4. «Yangi» bilan o'zbekcha caption: «qo'shiq», «Toshkent», «choy», «Is'hoq», «tog'», «O'ZBEKISTON» kabi so'zlar → «qóşiq», «Toşkent», «çoy», «Is'hoq», «toǵ», «ÓZBEKISTON».
5. Caption track'da ó ǵ ş ç to'g'ri chiziladimi (Premiere caption shrifti). Kompyuteringdagi Montserrat va Bebas Neue'da ǵ bor-yo'qligi: Premiere'da matnga «ǵ Ǵ» yozib ko'r (Bebas Neue'da yo'q deb kutyapmiz).
6. → o'zbek tarjima va «Tayyor SRT → uz» — yangi alifboda chiqadimi. Yangi alifbodagi tayyor SRT'ni → rus tarjima qil: joriy alifbodagi xuddi shu SRT tarjimasi bilan bir xil sifatdami.

**Asl uzbek_model bilan (Vazifa 2, HF ochilgandan keyin):** stendni sening kompyuteringda asl model bilan yurgizamiz — Kotib bilan 96% so'zma-so'z bir xil, lekin yakuniy raqam asl modelniki bo'lishi kerak:

```
python bench\run_bench.py --model "%USERPROFILE%\Documents\OgoCaption\Engine\uzbek_model" --tag asl --set short --config base
python bench\run_bench.py --model "%USERPROFILE%\Documents\OgoCaption\Engine\uzbek_model" --tag asl --set long --config base
```

(FLEURS ma'lumoti `bench/data/` ga `prepare_fleurs.py` bilan yuklanadi; portativ runtime'da `rapidfuzz` yo'q — stend sekinroq, lekin natija bir xil.)
