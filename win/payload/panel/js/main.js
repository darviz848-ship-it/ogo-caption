const fs = require('fs');
const path = require('path');
const { exec, spawn } = require('child_process');
let csInterface;

// Tarjima tillari (translate.py dagi MADLAD kodlari bilan bir xil)
const TRANSLATE_LANG_NAMES = { ru: "rus", en: "ingliz", uz: "o'zbek" };

window.onload = function() {
    try {
        csInterface = new CSInterface();
        updateThemeWithAppSkinInfo(csInterface.hostEnvironment.appSkinInfo);
        csInterface.addEventListener(CSInterface.THEME_COLOR_CHANGED_EVENT, onAppThemeColorChanged);
    } catch (e) {
        console.log("Adobe interfeysi topilmadi.");
    }
    setupUI();
};

function getDocPath() {
    return path.join(csInterface.getSystemPath(SystemPath.MY_DOCUMENTS), "OgoCaption");
}

// ---------------------------------------------------------------------------
// Python enjinini topish (Windows).
// Tartib: 1) python-path.txt da ko'rsatilgan yo'l (qo'lda override)
//         2) paket bilan o'rnatilgan portativ Python (Documents/OgoCaption/runtime)
//         3) tizimdagi odatiy Python o'rnatmalari
// Shu sabab plagin istalgan kompyuterda ishlaydi - yo'l qotib qolmagan.
// ---------------------------------------------------------------------------
function resolvePythonExe(docPath) {
    const candidates = [];

    // 1) Qo'lda ko'rsatilgan yo'l
    try {
        const cfg = path.join(docPath, "python-path.txt");
        if (fs.existsSync(cfg)) {
            const custom = fs.readFileSync(cfg, "utf8").trim().replace(/^"|"$/g, "");
            if (custom) candidates.push(custom);
        }
    } catch (e) {}

    // 2) Paket bilan kelgan portativ Python
    candidates.push(path.join(docPath, "runtime", "python.exe"));

    // 3) Tizimdagi Python (faster-whisper o'rnatilgan bo'lishi shart)
    const localApp = process.env.LOCALAPPDATA || "";
    const progFiles = process.env.ProgramFiles || "";
    const sysDrive = (process.env.SystemDrive || "C:") + path.sep;
    const versions = ["Python314", "Python313", "Python312", "Python311", "Python310"];
    for (let i = 0; i < versions.length; i++) {
        const v = versions[i];
        if (localApp) candidates.push(path.join(localApp, "Programs", "Python", v, "python.exe"));
        candidates.push(path.join(sysDrive, v, "python.exe"));
        if (progFiles) candidates.push(path.join(progFiles, v, "python.exe"));
    }

    for (let i = 0; i < candidates.length; i++) {
        try {
            if (candidates[i] && fs.existsSync(candidates[i])) return candidates[i];
        } catch (e) {}
    }
    return null;
}

// Tarjima modeli (2.95 GB) asosiy paketga sig'maydi - alohida o'rnatiladi:
// tools\INSTALL-TRANSLATE-MODEL.bat (Engine\get_translate_model.py)
function translateModelReady() {
    return fs.existsSync(path.join(getDocPath(), "Engine", "translate_model", "model.bin"));
}
const TRANSLATE_MODEL_MISSING = "Tarjima modeli o'rnatilmagan. OgoCaption-Setup papkasidagi "
    + "tools\\INSTALL-TRANSLATE-MODEL.bat ni ishga tushiring (bir marta, ~3 GB). Tarjimasiz caption ishlayveradi.";

// Enjin skriptini (transcribe.py / translate.py) ishga tushiradi va oxirgi JSON natijani qaytaradi
function runEngine(scriptName, args, onProgress) {
    return new Promise((resolve, reject) => {
        const isMac = csInterface.getOSInformation().indexOf("Mac") >= 0;
        const docPath = getDocPath();
        const engineDir = path.join(docPath, "Engine");
        const scriptPath = path.join(engineDir, scriptName);

        let child;
        if (isMac) {
            const quoted = [scriptPath].concat(args).map(a => `"${a}"`).join(" ");
            child = spawn('/bin/sh', ['-c', `export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH" && python3 ${quoted}`], {cwd: engineDir});
        } else {
            // Python enjini: portativ runtime yoki tizimdagi Python (yo'l qotib qolmagan)
            const pythonExe = resolvePythonExe(docPath);
            if (!pythonExe) {
                reject(new Error("Python enjini topilmadi. INSTALL.bat ni qayta ishga tushiring "
                    + "yoki Documents/OgoCaption/python-path.txt fayliga python.exe yo'lini yozing."));
                return;
            }
            child = spawn(pythonExe, [scriptPath].concat(args), {cwd: engineDir, windowsHide: true});
        }

        let stdoutData = "";
        let stderrData = "";

        // Chiqish oqimini real vaqt rejimida kuzatamiz (Real-time stdout Streaming)
        child.stdout.on('data', (data) => {
            const chunk = data.toString();
            stdoutData += chunk;
            for (let line of chunk.split("\n")) {
                line = line.trim();
                if (line.startsWith("PROGRESS:") && onProgress) {
                    onProgress(parseInt(line.split(":")[1]) || 0);
                }
            }
        });

        child.stderr.on('data', (data) => {
            stderrData += data.toString();
        });

        child.on('error', (err) => {
            reject(new Error("Dasturni ishga tushirib bo'lmadi: " + err.message));
        });

        child.on('close', (code) => {
            // stdout'da faqat so'nggi JSON bo'lishi kerak. Biz qidiramiz
            const lines = stdoutData.trim().split("\n");
            let jsonString = "";
            for (let i = lines.length - 1; i >= 0; i--) {
                const l = lines[i].trim();
                if (l.startsWith("{") && l.endsWith("}")) {
                    jsonString = l;
                    break;
                }
            }
            let data = null;
            try {
                data = JSON.parse(jsonString || stdoutData.trim());
            } catch (e) {}

            if (data && data.error) {
                reject(new Error("AI xatosi: " + data.error));
            } else if (code !== 0) {
                reject(new Error("Python xatosi (Code " + code + "): " + stderrData + "\n" + stdoutData));
            } else if (!data) {
                reject(new Error("Natijani o'qishda xatolik: " + stdoutData));
            } else {
                resolve(data);
            }
        });
    });
}

// Tarjima: sozlamani JSON faylga yozib translate.py ga beramiz (uzun matn buyruq qatoriga sig'maydi)
function runTranslate(cfg, onProgress) {
    const tempDir = path.join(getDocPath(), "temp");
    if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });
    const cfgPath = path.join(tempDir, "translate_input.json");
    fs.writeFileSync(cfgPath, JSON.stringify(cfg), 'utf8');
    return runEngine("translate.py", [cfgPath], onProgress);
}

function formatSrtTime(seconds) {
    let d = new Date(seconds * 1000);
    let hh = String(Math.floor(seconds / 3600)).padStart(2, '0');
    let mm = String(d.getUTCMinutes()).padStart(2, '0');
    let ss = String(d.getUTCSeconds()).padStart(2, '0');
    let ms = String(d.getUTCMilliseconds()).padStart(3, '0');
    return `${hh}:${mm}:${ss},${ms}`;
}

// [{text, start, end}] -> SRT matni
function buildSrt(blocks) {
    let srtContent = "";
    blocks.forEach((b, i) => {
        srtContent += `${i + 1}\n`;
        srtContent += `${formatSrtTime(b.start)} --> ${formatSrtTime(b.end)}\n`;
        srtContent += `${b.text}\n\n`;
    });
    return srtContent;
}

// So'zlarni tozalash (o', g' yoki tutuq belgisi (') sababli so'zlar bo'linib qolsa birlashtirish)
function mergeWords(words) {
    let mergedWords = [];
    for (let i = 0; i < words.length; i++) {
        let w = words[i];
        let t = w.word.trim();
        if ((t.startsWith("'") || t.startsWith("‘") || t.startsWith("’") || t.startsWith("-")) && mergedWords.length > 0) {
            mergedWords[mergedWords.length - 1].word += t;
            mergedWords[mergedWords.length - 1].end = w.end;
        } else {
            mergedWords.push({ word: t, start: w.start, end: w.end });
        }
    }
    return mergedWords;
}

// So'zlarni SRT bloklarga bo'lish
function wordsToBlocks(mergedWords, wordsPerLine) {
    let blocks = [];
    let currentLineWords = [];
    let lineStartTime = 0;

    for (let i = 0; i < mergedWords.length; i++) {
        let wordObj = mergedWords[i];
        if (currentLineWords.length === 0) {
            lineStartTime = wordObj.start;
        }
        currentLineWords.push(wordObj.word);

        // Tinish belgisi (. , ! ? : ; …) bilan tugagan so'zdan keyin yangi blok boshlanadi
        const endsSentence = /[.,!?:;…]$/.test(wordObj.word);

        if (currentLineWords.length >= wordsPerLine || i === mergedWords.length - 1 || endsSentence) {
            blocks.push({ text: currentLineWords.join(" "), start: lineStartTime, end: wordObj.end });
            currentLineWords = [];
        }
    }
    return blocks;
}

// ---------------------------------------------------------------------------
// Yangi o'zbek alifbosi (2021-yil loyihasi): oʻ -> ó, gʻ -> ǵ, sh -> ş, ch -> ç
// (Oʻ -> Ó, Gʻ -> Ǵ, Sh/SH -> Ş, Ch/CH -> Ç). ng va tutuq belgisi o'zgarmaydi.
// o/g dan keyingi apostrof (' ʻ ‘ ’ ` ʼ ´) - oʻ/gʻ belgisi; boshqa harfdan keyingisi -
// tutuq (ma'no, san'at). Is'hoq, as'hob - s va h orasida tutuq bor, ş bo'lmaydi.
// Faqat o'zbekcha matnga va mergeWords dan keyin ("qo" + "'yaman" avval qo'shiladi).
// ---------------------------------------------------------------------------
const ALPHABET_STORAGE_KEY = "ogoCaption.alphabet";
const UZ_APOSTROPHES = "'ʻ‘’`ʼ´";
const NEW_ALPHABET_PAIRS = { o: "ó", O: "Ó", g: "ǵ", G: "Ǵ", s: "ş", S: "Ş", c: "ç", C: "Ç" };

function toNewAlphabet(text) {
    let out = "";
    for (let i = 0; i < text.length; i++) {
        const c = text[i];
        const next = i + 1 < text.length ? text[i + 1] : "";
        if ((c === "o" || c === "O" || c === "g" || c === "G") && next && UZ_APOSTROPHES.indexOf(next) >= 0) {
            out += NEW_ALPHABET_PAIRS[c];
            i++;
        } else if ((c === "s" || c === "S" || c === "c" || c === "C") && (next === "h" || next === "H")) {
            out += NEW_ALPHABET_PAIRS[c];
            i++;
        } else {
            out += c;
        }
    }
    return out;
}

// O'zbekcha SRT bloklariga tanlangan alifboni qo'llaydi. Joriy alifboda bloklar
// o'zi qaytadi - natija avvalgisi bilan baytma-bayt bir xil.
function applyUzAlphabet(blocks, alphabet) {
    if (alphabet !== "new") return blocks;
    return blocks.map(b => Object.assign({}, b, { text: toNewAlphabet(b.text) }));
}

function loadAlphabet() {
    try {
        return window.localStorage.getItem(ALPHABET_STORAGE_KEY) === "new" ? "new" : "current";
    } catch (e) {
        return "current";
    }
}

function saveAlphabet(value) {
    try {
        window.localStorage.setItem(ALPHABET_STORAGE_KEY, value === "new" ? "new" : "current");
    } catch (e) {}
}

function evalScriptAsync(script) {
    return new Promise(resolve => csInterface.evalScript(script, resolve));
}

// SRT saqlanadigan papka: loyiha fayli yonida, bo'lmasa Documents/OgoCaption/temp
async function getSrtDir() {
    const projFolder = await evalScriptAsync('getProjectFolder()');
    if (projFolder && projFolder !== "" && !projFolder.startsWith("ERROR")) {
        return projFolder;
    }
    return path.join(getDocPath(), "temp");
}

async function writeAndImportSrt(srtPath, srtContent) {
    try {
        fs.writeFileSync(srtPath, srtContent, 'utf8');
    } catch (writeErr) {
        throw new Error("SRT yozishda xatolik: " + writeErr.message);
    }
    // JSON.stringify - papka nomida ' yoki \ bo'lsa ham ExtendScript satri buzilmaydi
    const result = await evalScriptAsync(`importCaptions(${JSON.stringify(srtPath)})`);
    if (result && result.startsWith("ERROR:")) {
        throw new Error(result);
    }
}

function setupUI() {
    const wordsSlider = document.getElementById('wordsPerLine');
    const wordsVal = document.getElementById('wordsPerLineVal');
    wordsSlider.addEventListener('input', function() {
        wordsVal.textContent = this.value + " so'z";
    });

    const styleCards = document.querySelectorAll('.style-card');
    let selectedStyle = "srt";
    styleCards.forEach(card => {
        card.addEventListener('click', () => {
            styleCards.forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            selectedStyle = card.dataset.style;
        });
    });

    const generateBtn = document.getElementById('generateBtn');
    const btnText = generateBtn.querySelector('.btn-text');
    const loader = generateBtn.querySelector('.loader');
    const languageSelect = document.getElementById('languageSelect');
    const translateSelect = document.getElementById('translateSelect');
    const translateSrtBtn = document.getElementById('translateSrtBtn');
    const translateSrtLabel = translateSrtBtn.textContent;

    // Alifbo: joriy / yangi - oxirgi tanlov eslab qolinadi (default - joriy)
    const alphabetSelect = document.getElementById('alphabetSelect');
    if (alphabetSelect) {
        alphabetSelect.value = loadAlphabet();
        alphabetSelect.addEventListener('change', function() {
            saveAlphabet(this.value);
        });
    }
    const getAlphabet = () => (alphabetSelect && alphabetSelect.value === "new") ? "new" : "current";

    // Premium status alerts helper (Now with real-time percentage progress bar!)
    function updateStatus(text, type = 'info', percent = null) {
        const statusMsg = document.getElementById('statusMessage');
        if (!statusMsg) return;

        statusMsg.classList.remove('hidden');

        let textSpan = statusMsg.querySelector('.status-text');
        if (!textSpan) {
            statusMsg.innerHTML = '<div class="status-content-row"><div class="status-icon-container"></div><span class="status-text"></span></div><div class="progress-bar-container"><div class="progress-bar-fill"></div></div>';
            textSpan = statusMsg.querySelector('.status-text');
        }

        textSpan.textContent = text;

        // Progress bar visibility and progress update
        const progressBarContainer = statusMsg.querySelector('.progress-bar-container');
        const progressBarFill = statusMsg.querySelector('.progress-bar-fill');
        if (percent !== null && progressBarContainer && progressBarFill) {
            statusMsg.classList.add('has-progress');
            progressBarFill.style.width = percent + '%';
        } else if (progressBarContainer) {
            statusMsg.classList.remove('has-progress');
        }

        const iconContainer = statusMsg.querySelector('.status-icon-container');
        if (iconContainer) {
            if (type === 'success') {
                statusMsg.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                statusMsg.style.backgroundColor = 'rgba(16, 185, 129, 0.08)';
                iconContainer.style.color = '#10b981';
                iconContainer.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
                iconContainer.classList.remove('animate-pulse');
            } else if (type === 'error') {
                statusMsg.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                statusMsg.style.backgroundColor = 'rgba(239, 68, 68, 0.08)';
                iconContainer.style.color = '#ef4444';
                iconContainer.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
                iconContainer.classList.remove('animate-pulse');
            } else {
                statusMsg.style.borderColor = 'var(--card-border)';
                statusMsg.style.backgroundColor = 'rgba(13, 18, 30, 0.95)';
                iconContainer.style.color = 'var(--accent-color)';
                iconContainer.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>`;
                iconContainer.classList.add('animate-pulse');
            }
        }
    }

    const translateProgress = (p) => updateStatus(`Tarjima qilinmoqda (${p}%)... Model yuklanishi ~10 soniya.`, "info", p);

    function setBusy(text) {
        generateBtn.disabled = true;
        translateSrtBtn.disabled = true;
        btnText.textContent = text;
        loader.classList.remove('hidden');
    }

    generateBtn.addEventListener('click', function() {
        if (!csInterface) {
            alert("Bu tugma faqat Premiere Pro ichida ishlaydi!");
            return;
        }

        const target = translateSelect.value; // "" - tarjimasiz
        if (target && !translateModelReady()) {
            updateStatus(TRANSLATE_MODEL_MISSING, "error");
            return;
        }
        setBusy("Audio olinmoqda...");
        updateStatus("Timeline'dan audio ajratib olinmoqda...", "info");

        // 1. Audioni eksport qilish
        csInterface.evalScript('exportAudioToTemp()', async function(result) {
            try {
                if (result.startsWith("ERROR:")) {
                    throw new Error(result);
                }

                // result ichida audio yo'li va sequence nomi bor (ajratuvchi: |)
                const parts = result.split("|");
                const audioPath = parts[0];
                const seqName = parts.length > 1 ? parts[1] : "Sequence";

                // maxsus belgilarni tozalash (faqat harflar, raqamlar va chiziqlar qoladi)
                const cleanSeqName = seqName.replace(/[^a-zA-Z0-9_-]/g, "_");

                updateStatus("AI tahlil qilmoqda (Internetsiz)...", "info", 0);
                btnText.textContent = "Matn yozilmoqda...";

                // 2. Ovozni matnga aylantirish
                const lang = languageSelect.value; // "uz", "en", "ru", "auto"
                const data = await runEngine("transcribe.py", [audioPath, lang],
                    (percent) => updateStatus(`AI tahlil qilmoqda (${percent}%)...`, "info", percent));

                updateStatus("Matnlar Premiere'ga terilmoqda...", "info");

                // 3. SRT orqali kiritish (Eng tez va ishonchli)
                const wordsPerLine = parseInt(wordsSlider.value) || 1;
                const mergedWords = mergeWords(data.words);
                const alphabet = getAlphabet();
                // Yangi alifbo faqat o'zbekcha SRT ga. Tarjimaga joriy yozuvdagi so'zlar ketadi -
                // MADLAD shu yozuvni biladi.
                const isUzbek = lang === "uz" || (lang === "auto" && data.language === "uz");
                let blocks = wordsToBlocks(mergedWords, wordsPerLine);
                if (isUzbek) blocks = applyUzAlphabet(blocks, alphabet);
                const srtDir = await getSrtDir();
                await writeAndImportSrt(path.join(srtDir, cleanSeqName + "_captions.srt"),
                    buildSrt(blocks));

                let doneMsg = data.words.length + " ta so'z (SRT) kiritildi!";

                // 4. Tarjima (tanlangan bo'lsa) - asl SRT yonida alohida _<til>.srt
                if (target) {
                    const sourceLang = lang === "auto" ? data.language : lang;
                    if (sourceLang === target) {
                        doneMsg += " Tarjima qilinmadi: asl til ham " + TRANSLATE_LANG_NAMES[target] + ".";
                    } else {
                        btnText.textContent = "Tarjima qilinmoqda...";
                        translateProgress(0);
                        const tr = await runTranslate(
                            { mode: "words", words: mergedWords, source: sourceLang, target: target, words_per_line: wordsPerLine },
                            translateProgress);
                        await writeAndImportSrt(path.join(srtDir, `${cleanSeqName}_captions_${target}.srt`),
                            buildSrt(target === "uz" ? applyUzAlphabet(tr.blocks, alphabet) : tr.blocks));
                        doneMsg = `${data.words.length} ta so'z + ${TRANSLATE_LANG_NAMES[target]} tiliga tarjima (2 ta SRT) kiritildi!`;
                    }
                }

                updateStatus(doneMsg, "success");
                resetBtn();
            } catch (err) {
                showError(err.message);
            }
        });
    });

    // Tayyor (tuzatilgan) SRT faylni tarjima qilish - ASR xatolari tuzatilgandan keyin tarjima sifatliroq
    translateSrtBtn.addEventListener('click', async function() {
        if (!csInterface) {
            alert("Bu tugma faqat Premiere Pro ichida ishlaydi!");
            return;
        }
        const target = translateSelect.value;
        if (!target) {
            updateStatus("Avval yuqorida tarjima tilini tanlang.", "error");
            return;
        }
        if (!translateModelReady()) {
            updateStatus(TRANSLATE_MODEL_MISSING, "error");
            return;
        }

        const picked = window.cep.fs.showOpenDialogEx(false, false, "Tarjima qilinadigan SRT faylni tanlang", "", ["srt"]);
        if (!picked || picked.err !== 0 || !picked.data || picked.data.length === 0) {
            return;
        }
        const srcPath = picked.data[0];

        setBusy("Tarjima qilinmoqda...");
        translateSrtBtn.textContent = "Tarjima qilinmoqda...";
        translateProgress(0);
        try {
            const wordsPerLine = parseInt(wordsSlider.value) || 1;
            const tr = await runTranslate(
                { mode: "srt", srt_path: srcPath, target: target, words_per_line: wordsPerLine },
                translateProgress);
            const outPath = srcPath.replace(/\.srt$/i, "") + "_" + target + ".srt";
            await writeAndImportSrt(outPath,
                buildSrt(target === "uz" ? applyUzAlphabet(tr.blocks, getAlphabet()) : tr.blocks));
            updateStatus(`${tr.sentences} ta gap ${TRANSLATE_LANG_NAMES[target]} tiliga tarjima qilindi: ${path.basename(outPath)}`, "success");
            resetBtn();
        } catch (err) {
            showError(err.message);
        }
    });

    function showError(msg) {
        resetBtn();
        updateStatus(msg, "error");
    }

    function resetBtn() {
        generateBtn.disabled = false;
        translateSrtBtn.disabled = false;
        btnText.textContent = "✨ Caption Yaratish";
        translateSrtBtn.textContent = translateSrtLabel;
        loader.classList.add('hidden');
    }
}

function onAppThemeColorChanged(event) {
    let skinInfo = JSON.parse(window.__adobe_cep__.getHostEnvironment()).appSkinInfo;
    updateThemeWithAppSkinInfo(skinInfo);
}

function updateThemeWithAppSkinInfo(appSkinInfo) {
    let panelBackgroundColor = appSkinInfo.panelBackgroundColor.color;
    document.body.style.backgroundColor = `rgb(${Math.round(panelBackgroundColor.red)}, ${Math.round(panelBackgroundColor.green)}, ${Math.round(panelBackgroundColor.blue)})`;
}
