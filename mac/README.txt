===============================================================
  OgoCaption  --  Premiere Pro uchun offline AI subtitr paneli
  macOS uchun o'rnatish paketi
===============================================================

NIMA BU
  Premiere Pro ichida ishlaydigan panel. Timeline'dagi audioni
  o'zi eksport qiladi, AI bilan matnga aylantiradi va subtitrni
  (SRT) loyihaga qo'shadi. Hammasi INTERNETSIZ, lokal ishlaydi.

  Tillar : o'zbek (lotin), rus, ingliz, avto
  Tarjima: rus / ingliz / o'zbek tiliga, internetsiz (ixtiyoriy,
           alohida model kerak - pastda "OFLAYN TARJIMA" bo'limi)


TALABLAR
  - macOS 11 (Big Sur) yoki yangiroq
  - Apple Silicon (M1/M2/M3/M4) YOKI Intel Mac - ikkalasi ham
    (o'rnatuvchi o'zi aniqlaydi)
  - Adobe Premiere Pro 2022 yoki yangiroq
  - ~2.5 GB bo'sh joy (+ tarjima modeli kerak bo'lsa yana ~3 GB)
  - Admin paroli SHART EMAS
  - Internet SHART EMAS (o'rnatishda ham, ishlatishda ham).
    Faqat tarjima modelini yuklab olish uchun bir marta kerak
    (yoki modelni fleshkada olib keling - pastga qarang)
  - Python, Homebrew o'rnatish SHART EMAS - hammasi paket ichida


O'RNATISH
  1. OgoCaption-Mac-Setup.zip ga ikki marta bos - papka ochiladi.
  2. Premiere Pro ochiq bo'lsa - yop (Cmd+Q).
  3. Papka ichidagi INSTALL.command ga ikki marta bos.
     Terminal oynasi ochiladi, ko'rsatmaga amal qil
     (~2-5 daqiqa: modellar katta, oxirida AI sinovi ham bor).
     Eng oxirida tarjima modeli so'raladi - pastga qarang.
     macOS "Terminal Downloads papkasiga kirmoqchi" deb so'rasa -
     Allow (Ruxsat berish) ni bos.
  4. Premiere Pro ni och:  Window -> Extensions -> ogo caption

  macOS "ochib bo'lmaydi / tasdiqlanmagan dasturchi" desa:
    Bu normal - paket App Store'dan emas. Uch yo'l bor:
    a) macOS 15 va yangi: System Settings -> Privacy & Security ->
       pastda "INSTALL.command was blocked" -> "Open Anyway".
    b) macOS 14 va eski: INSTALL.command ustida o'ng tugma
       (yoki Control + bosish) -> Open -> Open.
    c) Har doim ishlaydigan yo'l (Terminal):
       - Terminal'ni och (Cmd+Space -> "Terminal")
       - "bash " deb yoz (oxirida bo'sh joy bilan)
       - install.sh faylini sichqoncha bilan Terminal oynasiga tashla
       - Enter bos


ISHLATISH
  1. Premiere'da sequence och (audio bo'lgan).
  2. Panelda tilni tanla (uz / ru / en / auto).
  3. Bir qatordagi so'z sonini sozla.
  4. "Caption Yaratish" tugmasini bos.
     Birinchi marta model yuklanishi 20-40 soniya oladi.
  5. Tayyor SRT Project panelda paydo bo'ladi - timeline'ga tort.
     SRT fayl loyiha (.prproj) turgan papkaga ham yoziladi.


OFLAYN TARJIMA (ixtiyoriy)
  Panelda "Tarjima (internetsiz)" kartasi bor:
  - Tilni tanlab "Caption Yaratish" bossang - asl SRT bilan birga
    <sequence>_captions_<til>.srt ham loyihaga qo'shiladi.
  - "Tayyor SRT faylni tarjima qilish" - qo'lda tuzatilgan SRT ni
    tarjima qiladi (<nom>_<til>.srt yonida yaratiladi). ASR xatolari
    tuzatilgandan keyin tarjima sifatliroq chiqadi.

  Model: MADLAD-400-3B-MT (Google, Apache 2.0 - tijoriy ishga ham
  mumkin), 2.95 GB. Paketga SIG'MAYDI (Telegram 2 GB chegarasi),
  shuning uchun alohida o'rnatiladi. Ikki yo'l:

  a) Internet orqali (eng oson):
     INSTALL.command oxirida "Modelni internetdan yuklab olamizmi?"
     deb so'raydi -> h. Yoki keyinroq:
     tools/INSTALL-TRANSLATE-MODEL.command
     HuggingFace'dan yuklanadi (Nextcloud-AI/madlad400-3b-mt-ct2-int8),
     tez internetda ~3-10 daqiqa. Uzilsa - qayta ishga tushir, davom
     etadi.

  b) Internetsiz (fleshka):
     Model o'rnatilgan kompyuterdagi translate_model papkasini
       Windows: Hujjatlar\OgoCaption\Engine\translate_model
       Mac:     ~/Library/Application Support/OgoCaption/Engine/translate_model
     butunligicha OgoCaption-Mac-Setup ichiga (INSTALL.command
     yoniga) ko'chir. O'rnatuvchi uni o'zi topadi va ko'chiradi.
     Model fayllari Windows va Mac uchun aynan bir xil.

  Ikkala holda ham fayllar hajmi va SHA256 tekshiriladi - chala yoki
  buzilgan model o'rnatilmaydi.

  Sifat va tezlik:
  - uz -> ru inglizcha orqali tarjima qilinadi (to'g'ridan-to'g'ri
    model diniy matnlarga "og'ib ketardi"); asl matnda yo'q diniy
    so'z chiqsa gap boshqa yo'l bilan qayta tarjima qilinadi.
  - -> o'zbek tiliga tarjima ZAIF: qisqa gaplarda ma'no buzilishi
    mumkin, albatta ko'zdan kechiring.
  - Windows'da (32 yadro) 55 soniyalik ovoz: uz -> ru ~24 s.
    Mac'da tezlik o'lchanmagan.
  - Tarjima jarayoni ~5.3 GB operativ xotira oladi (Windows'da
    o'lchangan). 8 GB li Mac'da Premiere bilan birga xotira
    yetmasligi mumkin (panel "SIGKILL" deydi) - 16 GB tavsiya etiladi.


PAKET ICHIDA NIMA BOR
  INSTALL.command          o'rnatishni boshlaydi (ikki marta bosiladi)
  install.sh               asosiy o'rnatuvchi skript
  README.txt               shu fayl
  VERSION.txt              versiyalar va Windows paketidan farqi
  payload/panel/           Premiere paneli (CEP kengaytma)
  payload/Engine/          AI enjin + modellar (2 GB)
                             transcribe.py          - ovoz -> matn
                             translate.py           - oflayn tarjima
                             get_translate_model.py - tarjima modelini o'rnatadi
                             uzbek_model - 1.5 GB, lotin o'zbek
                             multi_model - 483 MB, ru / en / auto
  payload/mogrts/          3 ta subtitr shabloni
  payload/presets/         audio eksport preseti (zaxira nusxa)
  payload/runtime-arm64.tar.gz    portativ Python (Apple Silicon)
  payload/runtime-x86_64.tar.gz   portativ Python (Intel)
  tools/TEST-ENGINE.command   o'rnatilgandan keyin tekshirish
  tools/INSTALL-TRANSLATE-MODEL.command   tarjima modelini o'rnatish
  tools/UNINSTALL.command     to'liq o'chirish
  (translate_model/)          ixtiyoriy - fleshka orqali olib kelingan model


O'RNATUVCHI NIMA QILADI
  1. panel  -> ~/Library/Application Support/Adobe/CEP/extensions/OgoCaption
  2. Engine, mogrts, presets, runtime ->
             ~/Library/Application Support/OgoCaption/
     (Documents emas: iCloud yoqilgan bo'lsa 2 GB modelni bulutga
      yuklab, bepul 5 GB joyni to'ldirib qo'ymasin)
  3. Mac'ingga mos Python'ni ochadi (Apple Silicon yoki Intel)
  4. macOS karantin belgisini olib tashlaydi - aks holda macOS
     imzosiz Python'ni ishga tushirishni bloklaydi
  5. defaults write com.adobe.CSXS.9..20 PlayerDebugMode 1
     (imzosiz panel Premiere'da ko'rinishi uchun)
  6. Python enjinini, modellarni tekshiradi va 2 soniyalik test
     audio bilan haqiqiy AI sinovini o'tkazadi
  7. Tarjima modeli: paket yonida translate_model bo'lsa ko'chiradi,
     bo'lmasa internetdan yuklashni taklif qiladi (rad etsang ham
     caption ishlayveradi)

  Eski o'rnatma bo'lsa - panel zaxiraga olinadi
  (~/Library/Application Support/Adobe/CEP/OgoCaption.backup-<sana>),
  o'chirilmaydi.

  ~/Library papkasi Finder'da yashirin. Ochish uchun:
  Finder -> Go -> Go to Folder (Cmd+Shift+G) -> ~/Library/Application Support/OgoCaption


MUAMMO BO'LSA
  Panel Window > Extensions da ko'rinmayapti
    - Premiere'ni Cmd+Q bilan butunlay yopib, qayta och
    - tools/TEST-ENGINE.command ni ishga tushir, 4-bandga qara

  "Python enjini topilmadi"
    - INSTALL.command ni qayta ishga tushir

  "macOS ruxsat bermadi" / "SIGKILL" / Python ishga tushmayapti
    - tools/TEST-ENGINE.command ni ishga tushir - u karantin
      belgisini o'zi tuzatadi (5-band)

  "Waveform Audio preseti topilmadi"
    - Panel Premiere papkasini o'zi qidiradi, topolmasa paketdagi
      zaxira nusxani ishlatadi. Baribir chiqsa - INSTALL.command
      ni qayta ishga tushir.

  Subtitr chiqmadi / bo'sh
    - Timeline'da ovoz bor-yo'qligini tekshir
    - tools/TEST-ENGINE.command -> 7-band haqiqiy transkripsiyani sinaydi

  "Tarjima modeli o'rnatilmagan"
    - tools/INSTALL-TRANSLATE-MODEL.command ni ishga tushir
    - tools/TEST-ENGINE.command -> 8-band tarjimani sinaydi

  Tarjima modeli yuklanmayapti / uzildi
    - INSTALL-TRANSLATE-MODEL.command ni qayta ishga tushir - davom etadi
    - internet yo'q bo'lsa - fleshka yo'li (b)

  Tarjima paytida "SIGKILL"
    - xotira yetmadi: boshqa dasturlarni (brauzer va h.k.) yop,
      Premiere'ni qayta ochib, "Tayyor SRT faylni tarjima qilish"
      bilan qayta urin (caption allaqachon tayyor bo'ladi)


ESLATMA
  Panel imzosiz (unsigned) CEP kengaytma. Shuning uchun
  PlayerDebugMode kerak. Bu Adobe'ning rasmiy debug rejimi,
  boshqa panellarga zarar qilmaydi.
