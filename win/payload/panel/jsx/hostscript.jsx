// Premiere Pro uchun asosiy skript fayli

function exportAudioToTemp() {
    try {
        var activeSeq = app.project.activeSequence;
        if (!activeSeq) {
            return "ERROR: Faol ketma-ketlik (Timeline) topilmadi!";
        }
        // Papka va fayllarni tayyorlash (Mac va Windows uchun universal)
        var sep = ($.os.indexOf("Windows") > -1) ? "\\" : "/";
        var folderPath = Folder.myDocuments.fsName + sep + "OgoCaption" + sep + "temp";
        var folder = new Folder(folderPath);
        if (!folder.exists) {
            folder.create();
        }

        var outPath = folderPath + sep + "temp_audio.wav";
        var outObj = new File(outPath);
        if (outObj.exists) {
            outObj.remove(); // Eskisini o'chiramiz
        }

        // EPR (Preset) ni topish - Premiere Pro qaysi yil/qaysi diskda bo'lsa ham topadi
        var presetPath = "";
        var presetFile = null;
        var relPreset = "\\MediaIO\\systempresets\\3F3F3F3F_57415645\\Waveform Audio 48kHz 16-bit.epr";
        if ($.os.indexOf("Windows") > -1) {
            var candidates = [];

            // 1) Ishlab turgan Premiere Pro papkasidan olamiz (eng ishonchli usul)
            try {
                if (Folder.startup && Folder.startup.fsName) {
                    candidates.push(Folder.startup.fsName + relPreset);
                }
            } catch (e) {}

            // 2) Odatiy o'rnatish papkalari
            var bases = [];
            var pfw = $.getenv("ProgramW6432");
            if (pfw) bases.push(pfw + "\\Adobe");
            var pf = $.getenv("ProgramFiles");
            if (pf) bases.push(pf + "\\Adobe");
            bases.push("C:\\Program Files\\Adobe");

            var pproYears = ["2028", "2027", "2026", "2025", "2024", "2023", "2022"];
            for (var b = 0; b < bases.length; b++) {
                for (var y = 0; y < pproYears.length; y++) {
                    candidates.push(bases[b] + "\\Adobe Premiere Pro " + pproYears[y] + relPreset);
                }
            }

            for (var c = 0; c < candidates.length; c++) {
                presetPath = candidates[c];
                presetFile = new File(presetPath);
                if (presetFile.exists) break;
            }
        } else {
            // Mac uchun preset joylashuvi
            presetPath = "/Applications/Adobe Premiere Pro 2024/Adobe Premiere Pro 2024.app/Contents/MediaIO/systempresets/3F3F3F3F_57415645/Waveform Audio 48kHz 16-bit.epr";
            var presetFile = new File(presetPath);
            if (!presetFile.exists) {
                presetPath = "/Applications/Adobe Premiere Pro 2025/Adobe Premiere Pro 2025.app/Contents/MediaIO/systempresets/3F3F3F3F_57415645/Waveform Audio 48kHz 16-bit.epr";
                presetFile = new File(presetPath);
            }
        }
        
        if (!presetFile.exists) {
             return "ERROR: Audio eksport qilish uchun Premiere Pro 'Waveform Audio' preseti topilmadi. " + presetPath;
        }

        // Timeline ni eksport qilish (In to Out, yoki butun ketma-ketlik)
        activeSeq.exportAsMediaDirect(outPath, presetPath, app.encoder.ENCODE_ENTIRE);

        // Tugagandan so'ng yo'li va sequence nomini qaytaramiz (ajratuvchi: | )
        return outPath + "|" + activeSeq.name;
    } catch (e) {
        return "ERROR: " + e.toString();
    }
}

// Matnlarni SRT orqali loyihaga kiritish
function importCaptions(srtPath) {
    try {
        var seq = app.project.activeSequence;
        if (!seq) return "ERROR: Faol ketma-ketlik yo'q.";
        
        var file = new File(srtPath);
        if (!file.exists) {
            return "ERROR: SRT fayli topilmadi.";
        }

        // Project panelga import qilish
        app.project.importFiles([srtPath], false, app.project.rootItem, false);

        return "SUCCESS";
    } catch (e) {
        return "ERROR: " + e.toString();
    }
}

// Sequence haqida ma'lumot (XML uchun)
function getSequenceInfo() {
    try {
        var seq = app.project.activeSequence;
        if (!seq) return "ERROR: No active sequence";
        
        var w = parseInt(seq.frameSizeHorizontal);
        var h = parseInt(seq.frameSizeVertical);
        
        // FPS ni aniqlash
        var ticksPerSecond = 254016000000;
        var ticksPerFrame = seq.videoDisplayFormat; // fallback
        var fps = 30;
        try {
            // Sequence timebase dan FPS hisoblash
            var oneFrame = new Time();
            oneFrame.ticks = String(seq.getSettings().videoFrameRate.ticks);
            fps = Math.round(1.0 / oneFrame.seconds);
        } catch(e2) {
            fps = 30; // default
        }
        
        return w + "|" + h + "|" + fps;
    } catch(e) {
        return "ERROR: " + e.toString();
    }
}

// XML faylni import qilish (FCP7 XML)
function importXMLCaptions(xmlPath) {
    try {
        var file = new File(xmlPath);
        if (!file.exists) return "ERROR: XML fayli topilmadi.";
        
        app.project.importFiles([xmlPath], false, app.project.rootItem, false);
        return "SUCCESS";
    } catch(e) {
        return "ERROR: " + e.toString();
    }
}

// JSON orqali har bir so'zga MOGRT qo'yish (1-Usul)
function importMogrtCaptions(jsonString, mogrtFileName) {
    try {
        var seq = app.project.activeSequence;
        if (!seq) return "ERROR: Faol ketma-ketlik yo'q.";

        // MOGRT fayl yo'lini aniqlash (Mac va Windows uchun universal)
        var sep = ($.os.indexOf("Windows") > -1) ? "\\" : "/";
        var mogrtPath = Folder.myDocuments.fsName + sep + "OgoCaption" + sep + "mogrts" + sep + mogrtFileName;
        var mogrtFile = new File(mogrtPath);
        if (!mogrtFile.exists) {
            return "ERROR: MOGRT fayli topilmadi: " + mogrtPath + "\nIltimos Premiere'da bitta chiroyli yozuv yasab, MOGRT qilib shu joyga saqlang.";
        }

        // JSON matnini obyektga o'girish
        var captions = eval("(" + jsonString + ")"); 

        // Video track index ni topish (eng tepa track ga qo'yish uchun)
        var videoTrackIndex = seq.videoTracks.numTracks - 1; // 0-indexed, so we can place it on the top track
        
        // Agar yangi track qo'shish kerak bo'lsa, qilib qo'yish mumkin (faqat qo'lda qo'shish ishonchliroq)

        app.enableQE(); // QE DOM ni yoqamiz, ba'zi xususiyatlar uchun

        for (var i = 0; i < captions.length; i++) {
            var wordData = captions[i];
            var wordText = wordData.word; // Python scriptdan keladigan 'word' kaliti
            var start = wordData.start; // soniyalarda (seconds)
            var end = wordData.end;

            // Start time yaratamiz
            var timeStart = new Time();
            timeStart.seconds = start;

            // MOGRT ni import qilamiz
            var newTrackItem = seq.importMGT(mogrtPath, timeStart.ticks, videoTrackIndex, 0);

            if (newTrackItem) {
                // Uzunligini (out point) to'g'rilaymiz
                var timeEnd = new Time();
                timeEnd.seconds = end;
                newTrackItem.end = timeEnd;

                // MOGRT ichidagi matnni almashtirish
                var mgtComp = newTrackItem.getMGTComponent();
                if (mgtComp) {
                    var params = mgtComp.properties;
                    var textChanged = false;
                    
                    // DEBUG: Barcha parametr nomlarini faylga yozib ko'ramiz
                    if (i === 0) {
                        try {
                            var logFile = new File(Folder.myDocuments.fsName + sep + "OgoCaption" + sep + "temp" + sep + "mogrt_debug.txt");
                            logFile.open("w");
                            logFile.writeln("MOGRT Properties (numItems: " + params.numItems + "):");
                            for (var pIdx = 0; pIdx < params.numItems; pIdx++) {
                                logFile.writeln(pIdx + ": " + params[pIdx].displayName + " | Value: " + params[pIdx].getValue());
                            }
                            logFile.close();
                        } catch(e) {}
                    }
                    
                    // 1-qadam: Avval aniq nomlar bilan qidiramiz
                    var possibleNames = ["Source Text", "Text", "Matn", "ASDADAS", "asdadas"];
                    for (var k = 0; k < possibleNames.length; k++) {
                        var p = params.getParamForDisplayName(possibleNames[k]);
                        if (p) {
                            p.setValue(wordText);
                            textChanged = true;
                            break;
                        }
                    }

                    // 2-qadam: Agar topilmasa, Premiere'dan qilingan MOGRT larda birinchi parametr matn bo'ladi.
                    // Yoki hammasini ko'rib chiqib, qiymati string bo'lgan birinchi parametrni almashtiramiz
                    if (!textChanged) {
                        for (var k = 0; k < params.numItems; k++) {
                            try {
                                var p = params[k];
                                p.setValue(wordText); // O'zgartirib ko'ramiz
                                textChanged = true;
                                break; // birinchisini o'zgartirgach to'xtaymiz
                            } catch (err) {}
                        }
                    }
                }
            }
        }

        return "SUCCESS";
    } catch (e) {
        return "ERROR: " + e.toString();
    }
}

// Loyiha fayli turgan papkani olish
function getProjectFolder() {
    try {
        if (app.project && app.project.path && app.project.path.length > 0) {
            var projectFile = new File(app.project.path);
            if (projectFile.parent) {
                return projectFile.parent.fsName;
            }
        }
        return "";
    } catch(e) {
        return "ERROR: " + e.toString();
    }
}
