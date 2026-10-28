===============================================================
  OgoCaption  --  Premiere Pro uchun offline AI subtitr paneli
  Ko'chma o'rnatish paketi
===============================================================

NIMA BU
  Premiere Pro ichida ishlaydigan panel. Timeline'dagi audioni
  o'zi eksport qiladi, AI bilan matnga aylantiradi va subtitrni
  sequence'ga qo'yadi. Hammasi INTERNETSIZ, lokal ishlaydi.

  Tillar  : o'zbek (lotin), rus, ingliz, avto
  Chiqish : oddiy subtitr (SRT) yoki MOGRT shablon (bounce/fade/trend)
  Tarjima : rus / ingliz / o'zbek tiliga, internetsiz (ixtiyoriy,
            alohida model kerak - pastda "OFLAYN TARJIMA" bo'limi)


TALABLAR
  - Windows 10 / 11 (64-bit)
  - Adobe Premiere Pro 2022 yoki yangiroq
  - ~2.2 GB bo'sh joy (paketning o'zi ~2.0 GB)
    + tarjima modeli kerak bo'lsa yana ~3 GB
  - Admin huquqi SHART EMAS
  - Internet SHART EMAS (o'rnatishda ham, ishlatishda ham).
    Faqat tarjima modelini yuklab olish uchun bir marta kerak
    (yoki modelni fleshkada olib keling - pastga qarang)


O'RNATISH
  1. Butun "OgoCaption-Setup" papkasini yangi kompyuterga ko'chir
     (fleshka, tashqi disk yoki tarmoq orqali - farqi yo'q).
  2. Premiere Pro ochiq bo'lsa - yop.
  3. INSTALL.bat ga ikki marta bos.
  4. Ekrandagi ko'rsatmaga amal qil (~2-5 daqiqa, modellar katta).
     Oxirida tarjima modeli so'raladi - pastga qarang.
  5. Premiere Pro ni och:  Window -> Extensions -> ogo caption


ISHLATISH
  1. Premiere'da sequence och (audio bo'lgan).
  2. Panelda tilni tanla (uz / ru / en / auto).
  3. Bir qatordagi so'z sonini sozla.
  4. Uslubni tanla: SRT yoki MOGRT (bounce / fade / trend).
  5. Tugmani bos. Birinchi marta model yuklanishi 20-40 soniya oladi.
  6. Alifbo: "Joriy" yoki "Yangi" (2021-yil loyihasi). Panel oxirgi
     tanlovni eslab qoladi. Faqat o'zbekcha matnga ta'sir qiladi:
     o'zbekcha subtitr va o'zbek tiliga tarjima. Fade / trend MOGRT
     shriftida (Bebas Neue) yangi g harfi (g akut) yo'q - Montserrat
     (bounce) yoki boshqa shrift tanlang.


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
     INSTALL.bat oxirida "Modelni internetdan yuklab olamizmi?" deb
     so'raydi -> h. Yoki keyinroq: tools\INSTALL-TRANSLATE-MODEL.bat
     HuggingFace'dan yuklanadi (Nextcloud-AI/madlad400-3b-mt-ct2-int8),
     tez internetda ~3-10 daqiqa. Uzilsa - qayta ishga tushir, davom
     etadi.

  b) Internetsiz (fleshka):
     Model o'rnatilgan kompyuterdan
       Hujjatlar\OgoCaption\Engine\translate_model
     papkasini butunligicha OgoCaption-Setup ichiga (INSTALL.bat
     yoniga) ko'chir. INSTALL.bat yoki INSTALL-TRANSLATE-MODEL.bat
     uni o'zi topadi va ko'chiradi. Shu papka Mac paketi uchun ham
     aynan bir xil.

  Ikkala holda ham fayllar hajmi va SHA256 tekshiriladi - chala yoki
  buzilgan model o'rnatilmaydi.

  Sifat va tezlik (15.10.2026 sinovi, 32 yadroli CPU):
  - uz -> ru inglizcha orqali tarjima qilinadi (to'g'ridan-to'g'ri
    model diniy matnlarga "og'ib ketardi"); asl matnda yo'q diniy
    so'z chiqsa gap boshqa yo'l bilan qayta tarjima qilinadi.
  - -> o'zbek tiliga tarjima ZAIF: qisqa gaplarda ma'no buzilishi
    mumkin, albatta ko'zdan kechiring.
  - 55 soniyalik ovoz: uz -> ru ~24 s, uz -> en ~14 s. Sekin
    kompyuterda bir necha barobar ko'proq.
  - Tarjima jarayoni ~5.3 GB operativ xotira oladi (o'lchangan).
    Premiere bilan birga ishlashi uchun 16 GB RAM tavsiya etiladi;
    8 GB li kompyuterda tarjima xotira yetmay to'xtashi mumkin.


PAKET ICHIDA NIMA BOR
  INSTALL.bat            o'rnatishni boshlaydi
  install.ps1            asosiy o'rnatuvchi skript
  README.txt             shu fayl
  VERSION.txt            versiyalar va o'zgarishlar
  payload\panel\         Premiere paneli (CEP kengaytma)
  payload\Engine\        AI enjin + modellar (1.9 GB)
                           transcribe.py          - ovoz -> matn
                           translate.py           - oflayn tarjima
                           get_translate_model.py - tarjima modelini o'rnatadi
                           uzbek_model  - 1.5 GB, lotin o'zbek
                           multi_model  - 483 MB, ru / en / auto
  payload\mogrts\        3 ta subtitr shabloni
  payload\runtime.zip    portativ Python 3.14 + faster-whisper
                           (zip holida - fleshkada joy va vaqt tejaydi,
                            o'rnatuvchi o'zi ochib qo'yadi)
  tools\TEST-ENGINE.bat  o'rnatilgandan keyin tekshirish
  tools\INSTALL-TRANSLATE-MODEL.bat  tarjima modelini o'rnatish
  tools\UNINSTALL.bat    to'liq o'chirish
  (translate_model\)     ixtiyoriy - fleshka orqali olib kelingan model


O'RNATUVCHI NIMA QILADI
  1. panel  -> %APPDATA%\Adobe\CEP\extensions\OgoCaption
  2. Engine, mogrts, runtime -> Hujjatlar\OgoCaption\
  3. HKCU\Software\Adobe\CSXS.9..20 -> PlayerDebugMode = 1
     (imzosiz panel Premiere'da ko'rinishi uchun)
  4. Python enjinini va modellarni tekshiradi
  5. Tarjima modeli: paket yonida translate_model bo'lsa ko'chiradi,
     bo'lmasa internetdan yuklashni taklif qiladi (rad etsang ham
     caption ishlayveradi)

  Eski o'rnatma bo'lsa - panel zaxiraga olinadi
  (OgoCaption.backup-<sana>), o'chirilmaydi.


MUAMMO BO'LSA
  Panel Window > Extensions da ko'rinmayapti
    - Premiere butunlay yopilib qayta ochilganiga ishonch hosil qil
      (Task Manager'da "Adobe Premiere Pro" jarayoni qolmasin)
    - tools\TEST-ENGINE.bat ni ishga tushir, 4-bandga qara

  "Python enjini topilmadi"
    - INSTALL.bat ni qayta ishga tushir
    - yoki Hujjatlar\OgoCaption\python-path.txt fayl yasab, ichiga
      python.exe ning to'liq yo'lini yoz (bitta qator). Bu Python'da
      faster-whisper o'rnatilgan bo'lishi kerak.

  "Waveform Audio preseti topilmadi"
    - Premiere Pro standart o'rnatilmagan bo'lishi mumkin.
      Panel Premiere papkasini o'zi qidiradi; topolmasa
      Premiere'ni odatiy joyga o'rnatish kerak.

  Subtitr chiqmadi / bo'sh
    - Timeline'da ovoz bor-yo'qligini tekshir
    - tools\TEST-ENGINE.bat -> 6-band haqiqiy transkripsiyani sinaydi

  "Tarjima modeli o'rnatilmagan"
    - tools\INSTALL-TRANSLATE-MODEL.bat ni ishga tushir (yuqoriga qara)
    - tools\TEST-ENGINE.bat -> 7-band tarjimani sinaydi

  Tarjima modeli yuklanmayapti / uzildi
    - INSTALL-TRANSLATE-MODEL.bat ni qayta ishga tushir - davom etadi
    - internet yo'q bo'lsa - fleshka yo'li (b)


ESLATMA
  Panel imzosiz (unsigned) CEP kengaytma. Shuning uchun
  PlayerDebugMode kerak. Bu Adobe'ning rasmiy debug rejimi,
  boshqa panellarga zarar qilmaydi.
