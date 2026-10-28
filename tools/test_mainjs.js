// main.js ni soxta CEP + Premiere muhitida end-to-end sinash (caption + oflayn tarjima)
// Ishlatish:
//   node test_mainjs.js <Mac paket main.js>  mac   - universal panel (Mac va Windows rejimi)
//   node test_mainjs.js <Win paket main.js>  win   - Windows paketi (resolvePythonExe, exportAudioToTemp())
const realFs = require('fs');
const path = require('path');
const vm = require('vm');
const os = require('os');
const assert = require('assert');
const { EventEmitter } = require('events');

const SRC = realFs.readFileSync(process.argv[2], 'utf8');
const KIND = process.argv[3] || 'mac';
const TMP = realFs.mkdtempSync(path.join(os.tmpdir(), 'ogo-mainjs-')).replace(/\\/g, '/');
// Windows rejimidagi yo'llar (\tmp\...\Documents) Linux/Mac'da joriy papkada "\" li nomli
// fayl bo'lib qolmasin va testlar orasida tozalansin: fs chaqiruvining birinchi argumenti
// (yo'l) haqiqiy TMP papkaga o'giriladi. Windows'da fs o'zgarmaydi.
const fs = process.platform === 'win32' ? realFs : new Proxy(realFs, {
    get(t, k) {
        const v = t[k];
        if (typeof v !== 'function') return v;
        return (p, ...rest) => v.call(t, typeof p === 'string' ? p.replace(/\\/g, '/') : p, ...rest);
    },
});

const WORDS = [
    { word: "Salom,", start: 0.0, end: 0.4 }, { word: "bugun", start: 0.5, end: 0.8 },
    { word: "yigirma", start: 0.9, end: 1.2 }, { word: "5", start: 1.2, end: 1.4 },
    { word: "o", start: 1.5, end: 1.6 }, { word: "'zbek", start: 1.6, end: 1.9 }, { word: "tilida.", start: 2.0, end: 2.5 },
];
const SRT_BODY =
    "1\n00:00:00,000 --> 00:00:00,400\nSalom,\n\n" +
    "2\n00:00:00,500 --> 00:00:01,400\nbugun yigirma 5\n\n" +
    "3\n00:00:01,500 --> 00:00:02,500\no'zbek tilida.\n\n";
const TR_BLOCKS = [{ text: "Привет,", start: 0.0, end: 0.4 }, { text: "сегодня на узбекском.", start: 0.5, end: 2.5 }];
const TR_BODY = "1\n00:00:00,000 --> 00:00:00,400\nПривет,\n\n2\n00:00:00,500 --> 00:00:02,500\nсегодня на узбекском.\n\n";

// Alifbo stsenariylari: sh/ch, bo'lingan apostrof ("qo" + "'shiq", "tog" + "‘ga"), tutuq, katta harf
const WORDS_UZ = [
    { word: "Choyxonada", start: 0.0, end: 0.6 }, { word: "qo", start: 0.7, end: 0.8 }, { word: "'shiq", start: 0.8, end: 1.1 },
    { word: "eshitdik.", start: 1.2, end: 1.6 }, { word: "Is'hoq", start: 1.7, end: 2.0 }, { word: "aka", start: 2.0, end: 2.2 },
    { word: "tog", start: 2.3, end: 2.5 }, { word: "‘ga", start: 2.5, end: 2.7 }, { word: "ketdi,", start: 2.8, end: 3.1 },
    { word: "ma'no", start: 3.2, end: 3.5 }, { word: "O'ZBEKISTON", start: 3.6, end: 4.2 },
];
const SRT_UZ_CURRENT =
    "1\n00:00:00,000 --> 00:00:01,600\nChoyxonada qo'shiq eshitdik.\n\n" +
    "2\n00:00:01,700 --> 00:00:02,700\nIs'hoq aka tog‘ga\n\n" +
    "3\n00:00:02,800 --> 00:00:03,100\nketdi,\n\n" +
    "4\n00:00:03,200 --> 00:00:04,200\nma'no O'ZBEKISTON\n\n";
const SRT_UZ_NEW =
    "1\n00:00:00,000 --> 00:00:01,600\nÇoyxonada qóşiq eşitdik.\n\n" +
    "2\n00:00:01,700 --> 00:00:02,700\nIs'hoq aka toǵga\n\n" +
    "3\n00:00:02,800 --> 00:00:03,100\nketdi,\n\n" +
    "4\n00:00:03,200 --> 00:00:04,200\nma'no ÓZBEKISTON\n\n";
const UZ_TR_BLOCKS = [{ text: "Bugun o'zbek tilida gaplashamiz.", start: 0.0, end: 1.6 }, { text: "Choy ichamiz, Is'hoq aka!", start: 1.7, end: 4.2 }];
const UZ_TR_CURRENT = "1\n00:00:00,000 --> 00:00:01,600\nBugun o'zbek tilida gaplashamiz.\n\n2\n00:00:01,700 --> 00:00:04,200\nChoy ichamiz, Is'hoq aka!\n\n";
const UZ_TR_NEW = "1\n00:00:00,000 --> 00:00:01,600\nBugun ózbek tilida gaplaşamiz.\n\n2\n00:00:01,700 --> 00:00:04,200\nÇoy içamiz, Is'hoq aka!\n\n";
const ALPHABET_KEY = "ogoCaption.alphabet";

function run(o) {
    const { mac, home, docs, projFolder, pythonExists = true, projWritable = true, model = true,
            target = '', lang = 'uz', detected = 'uz', trMode = 'ok', click = 'generate', pickSrt = null,
            words = WORDS, storage = {}, pick = null, alphabetEl = true } = o;
    return new Promise((resolve) => {
        const P = mac ? path.posix : path.win32;
        const base = mac ? P.join(home, 'Library', 'Application Support', 'OgoCaption') : P.join(docs, 'OgoCaption');
        const py = mac ? P.join(base, 'runtime', 'bin', 'python3') : P.join(base, 'runtime', 'python.exe');
        fs.rmSync(base, { recursive: true, force: true });
        if (pythonExists) { fs.mkdirSync(P.dirname(py), { recursive: true }); fs.writeFileSync(py, ''); }
        if (model) {
            const md = P.join(base, 'Engine', 'translate_model');
            fs.mkdirSync(md, { recursive: true }); fs.writeFileSync(P.join(md, 'model.bin'), '');
        }
        if (projFolder) {
            if (projWritable) fs.mkdirSync(projFolder, { recursive: true });
            else { fs.mkdirSync(P.dirname(projFolder), { recursive: true }); fs.writeFileSync(projFolder, 'fayl, papka emas'); }
        }
        const log = { eval: [], spawn: [], status: [], imported: [], cfg: [] };
        let done = false;
        // localStorage: {kalit: qiymat} yoki 'throw' (CEP'da saqlash taqiqlangan holat)
        const store = Object.assign({}, storage === 'throw' ? {} : storage);
        const localStorage = storage === 'throw'
            ? { getItem() { throw new Error('SecurityError'); }, setItem() { throw new Error('SecurityError'); } }
            : { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
        let alphabetOnLoad = null;
        const finish = () => { if (!done) { done = true; resolve({ log, base, py, P, store, alphabetOnLoad }); } };

        const mkEl = (extra = {}) => Object.assign({
            classList: { add() {}, remove() {} }, style: {}, textContent: '', innerHTML: '', disabled: false,
            _h: {}, addEventListener(ev, fn) { this._h[ev] = fn; }, querySelector() { return null; },
        }, extra);
        // resetBtn() tugma matnini qaytaradi - shu payt oqim tugagan bo'ladi
        const btnText = new Proxy(mkEl(), { set(t, k, v) { t[k] = v; if (k === 'textContent' && v.indexOf('Caption Yaratish') > -1) setImmediate(finish); return true; } });
        const loader = mkEl();
        const statusText = mkEl();
        const statusProxy = new Proxy(statusText, { set(t, k, v) { if (k === 'textContent') log.status.push(v); t[k] = v; return true; } });
        const statusEl = mkEl({ querySelector: sel => sel === '.status-text' ? statusProxy : mkEl() });
        const els = {
            wordsPerLine: mkEl({ value: '3' }), wordsPerLineVal: mkEl(), languageSelect: mkEl({ value: lang }),
            translateSelect: mkEl({ value: target }), translateSrtBtn: mkEl({ textContent: '📄 Tayyor SRT faylni tarjima qilish' }),
            generateBtn: mkEl({ querySelector(sel) { return sel === '.btn-text' ? btnText : loader; } }),
            statusMessage: statusEl,
        };
        // eski index.html (alifbo tanlovisiz) bilan ham ishlashi kerak: alphabetEl: false
        if (alphabetEl) els.alphabetSelect = mkEl({ value: 'current' });
        const document = { getElementById: id => els[id], querySelectorAll: () => [], body: { style: {} } };

        class CSInterface {
            constructor() { this.hostEnvironment = { appSkinInfo: { panelBackgroundColor: { color: { red: 30, green: 30, blue: 30 } } } }; }
            addEventListener() {}
            getOSInformation() { return mac ? 'Mac OS X 14.6.1' : 'Windows 10 64-bit'; }
            getSystemPath() { return docs; }
            evalScript(script, cb) {
                log.eval.push(script);
                setImmediate(() => {
                    let m;
                    if ((m = /^exportAudioToTemp\((.*)\)$/.exec(script))) {
                        // Windows paketi argumentsiz chaqiradi - hostscript o'zi Documents/OgoCaption/temp ga yozadi
                        const dir = m[1] ? JSON.parse(m[1]) : P.join(base, 'temp');
                        fs.mkdirSync(dir, { recursive: true });   // hostscript ham temp papkani yaratadi
                        cb(dir + (mac ? '/' : '\\') + 'temp_audio.wav|Reels #1 (final)');
                    } else if (script === 'getProjectFolder()') {
                        cb(projFolder || '');
                    } else if ((m = /^importCaptions\((.*)\)$/.exec(script))) {
                        const p = JSON.parse(m[1]);  // ExtendScript ham xuddi shunday parse qiladi
                        log.imported.push(p);
                        cb(fs.existsSync(p) ? 'SUCCESS' : 'ERROR: SRT fayli topilmadi.');
                    } else cb('EvalScript error.');
                });
            }
        }
        const spawn = (cmd, args, opts) => {
            log.spawn.push({ cmd, args, opts });
            const child = new EventEmitter();
            child.stdout = new EventEmitter(); child.stderr = new EventEmitter();
            const script = P.basename(args[0]);
            setImmediate(() => {
                if (script === 'transcribe.py') {
                    child.stdout.emit('data', Buffer.from('PROGRESS:40\nPROGRESS:100\n'));
                    child.stdout.emit('data', Buffer.from(JSON.stringify({ success: true, words: words, language: detected }) + '\n'));
                    child.emit('close', 0, null);
                    return;
                }
                // translate.py <cfg.json>
                const cfg = JSON.parse(fs.readFileSync(args[1], 'utf8'));
                log.cfg.push(cfg);
                if (trMode === 'sigkill') { child.emit('close', null, 'SIGKILL'); return; }
                if (trMode === 'nomodel') {
                    child.stdout.emit('data', Buffer.from(JSON.stringify({ error: "Tarjima modeli topilmadi: X" }) + '\n'));
                    child.emit('close', 1, null);
                    return;
                }
                child.stdout.emit('data', Buffer.from('PROGRESS:2\nPROGRESS:10\nPROGRESS:100\n'));
                child.stdout.emit('data', Buffer.from(JSON.stringify({ success: true, blocks: cfg.target === 'uz' ? UZ_TR_BLOCKS : TR_BLOCKS, sentences: 2 }) + '\n'));
                child.emit('close', 0, null);
            });
            return child;
        };

        const fakeOs = { homedir: () => home };
        const ctx = {
            window: { cep: { fs: { showOpenDialogEx: () => (pickSrt ? { err: 0, data: [pickSrt] } : { err: 0, data: [] }) } }, localStorage },
            document, CSInterface, SystemPath: { MY_DOCUMENTS: 'myDocuments' }, console,
            process: { platform: mac ? 'darwin' : 'win32', env: { PATH: '/usr/bin', LOCALAPPDATA: '', ProgramFiles: '' } },
            require: m => ({ fs: fs, path: P, os: fakeOs, child_process: { spawn, exec() {} } })[m],
            alert: msg => log.status.push('ALERT ' + msg), setTimeout, setImmediate,
        };
        vm.createContext(ctx);
        vm.runInContext(SRC, ctx);
        ctx.window.onload();
        if (els.alphabetSelect) alphabetOnLoad = els.alphabetSelect.value;
        // foydalanuvchi alifboni tanlaydi (change hodisasi)
        if (pick && els.alphabetSelect) { els.alphabetSelect.value = pick; els.alphabetSelect._h.change.call(els.alphabetSelect); }
        (click === 'srt' ? els.translateSrtBtn : els.generateBtn)._h.click();
        // darhol qaytadigan xato stsenariylarida resetBtn chaqirilmaydi - kafolat
        setTimeout(finish, 400);
    });
}

const last = log => log.status[log.status.length - 1] || '';
const read = p => fs.readFileSync(p, 'utf8');

async function macSuite() {
    const home = TMP + '/home/editor';
    // 1) Mac, loyiha papkasida apostrof, tarjimasiz - eski natija baytma-bayt
    {
        const proj = TMP + "/home/editor/Projects/Lochin's O'zbek proj";
        const { log, base, py } = await run({ mac: true, home, projFolder: proj });
        assert.strictEqual(log.eval[0], 'exportAudioToTemp(' + JSON.stringify(base + '/temp') + ')');
        const sp = log.spawn[0];
        assert.strictEqual(sp.cmd, py);
        assert.deepStrictEqual(Array.from(sp.args), [base + '/Engine/transcribe.py', base + '/temp/temp_audio.wav', 'uz']);
        assert.strictEqual(sp.opts.cwd, base + '/Engine');
        assert.strictEqual(sp.opts.env.PYTHONIOENCODING, 'utf-8');
        assert.strictEqual(sp.opts.env.PATH, '/usr/bin');
        assert.deepStrictEqual(log.imported, [proj + '/Reels__1__final__captions.srt']);
        assert.strictEqual(read(log.imported[0]), SRT_BODY);
        assert.strictEqual(log.spawn.length, 1);
        assert(log.status.some(s => s.indexOf('AI tahlil qilmoqda (100%)') === 0));
        assert(/kiritildi!$/.test(last(log)), last(log));
        console.log("OK  Mac: runtime/bin/python3, Application Support, apostrofli loyiha papkasi, tarjimasiz SRT o'zgarmagan");
    }
    // 2) Mac, uz -> ru tarjima
    {
        const proj = TMP + "/home/editor/Projects/O'zbek tarjima";
        const { log, base, py } = await run({ mac: true, home, projFolder: proj, target: 'ru' });
        assert.strictEqual(log.spawn.length, 2);
        const t = log.spawn[1];
        assert.strictEqual(t.cmd, py);
        assert.deepStrictEqual(Array.from(t.args), [base + '/Engine/translate.py', base + '/temp/translate_input.json']);
        assert.strictEqual(t.opts.env.PYTHONIOENCODING, 'utf-8');
        const cfg = log.cfg[0];
        assert.strictEqual(cfg.mode, 'words'); assert.strictEqual(cfg.source, 'uz'); assert.strictEqual(cfg.target, 'ru');
        assert.strictEqual(cfg.words_per_line, 3);
        assert.deepStrictEqual(cfg.words.map(w => w.word), ['Salom,', 'bugun', 'yigirma', '5', "o'zbek", 'tilida.']);
        assert.deepStrictEqual(log.imported, [proj + '/Reels__1__final__captions.srt', proj + '/Reels__1__final__captions_ru.srt']);
        assert.strictEqual(read(log.imported[0]), SRT_BODY);
        assert.strictEqual(read(log.imported[1]), TR_BODY);
        assert(log.status.some(s => s.indexOf('Tarjima qilinmoqda (100%)') === 0));
        assert(/rus tiliga tarjima \(2 ta SRT\) kiritildi!$/.test(last(log)), last(log));
        console.log("OK  Mac: uz->ru tarjima - translate.py cfg, 2 ta SRT loyiha papkasida");
    }
    // 3) Mac, loyiha papkasiga yozib bo'lmaydi -> ikkala SRT temp ga
    {
        const { log, base } = await run({ mac: true, home, projFolder: TMP + '/ro/proj', projWritable: false, target: 'en' });
        assert.deepStrictEqual(log.imported, [base + '/temp/Reels__1__final__captions.srt', base + '/temp/Reels__1__final__captions_en.srt']);
        console.log("OK  Mac: loyiha papkasiga yozib bo'lmasa -> asl va tarjima SRT temp ga");
    }
    // 4) Mac, model o'rnatilmagan -> darhol tushunarli xato, hech narsa ishga tushmaydi
    {
        const { log } = await run({ mac: true, home, projFolder: '', target: 'ru', model: false });
        assert.strictEqual(log.eval.length, 0); assert.strictEqual(log.spawn.length, 0);
        assert(/Tarjima modeli o'rnatilmagan.*tools\/INSTALL-TRANSLATE-MODEL\.command/.test(last(log)), last(log));
        console.log("OK  Mac: model yo'q -> INSTALL-TRANSLATE-MODEL.command haqida xabar, audio eksport qilinmaydi");
    }
    // 5) Mac, auto til = tarjima tili -> tarjima o'tkazib yuboriladi
    {
        const { log } = await run({ mac: true, home, projFolder: '', target: 'ru', lang: 'auto', detected: 'ru' });
        assert.strictEqual(log.spawn.length, 1); assert.strictEqual(log.imported.length, 1);
        assert(/Tarjima qilinmadi: asl til ham rus\.$/.test(last(log)), last(log));
        console.log("OK  Mac: auto til = tarjima tili -> faqat asl SRT");
    }
    // 6) Mac, tarjima paytida SIGKILL (xotira) -> maslahat, asl SRT baribir kiritilgan
    {
        const { log } = await run({ mac: true, home, projFolder: '', target: 'ru', trMode: 'sigkill' });
        assert.strictEqual(log.imported.length, 1);
        assert(last(log).indexOf('SIGKILL') > -1 && last(log).indexOf('TEST-ENGINE.command') > -1, last(log));
        console.log("OK  Mac: tarjimada SIGKILL -> tushunarli maslahat (asl SRT kiritilgan)");
    }
    // 7) Mac, tayyor SRT ni tarjima qilish; SRT papkasi yozib bo'lmaydigan -> temp ga
    {
        const srtDir = TMP + "/home/editor/Shared O'zbek";
        fs.mkdirSync(srtDir, { recursive: true });
        const src = srtDir + '/fixed.srt';
        fs.writeFileSync(src, SRT_BODY);
        let r = await run({ mac: true, home, projFolder: '', target: 'en', click: 'srt', pickSrt: src });
        assert.deepStrictEqual(r.log.eval, [importOf(srtDir + '/fixed_en.srt')]);
        assert.strictEqual(r.log.cfg[0].mode, 'srt'); assert.strictEqual(r.log.cfg[0].srt_path, src);
        assert.strictEqual(r.log.cfg[0].target, 'en');
        assert.strictEqual(read(srtDir + '/fixed_en.srt'), TR_BODY);
        assert(/2 ta gap ingliz tiliga tarjima qilindi: fixed_en\.srt$/.test(last(r.log)), last(r.log));
        // SRT turgan "papka" aslida fayl (yozib bo'lmaydi) -> temp
        const roDir = TMP + '/ro2/srtdir';
        fs.mkdirSync(path.dirname(roDir), { recursive: true }); fs.writeFileSync(roDir, 'fayl');
        r = await run({ mac: true, home, projFolder: '', target: 'uz', click: 'srt', pickSrt: roDir + '/a.srt' });
        assert.deepStrictEqual(r.log.imported, [r.base + '/temp/a_uz.srt']);
        console.log("OK  Mac: tayyor SRT tarjimasi -> <nom>_<til>.srt yonida, yozib bo'lmasa temp ga");
    }
    // 8) Mac, SRT tugmasi: til tanlanmagan / dialog bekor qilingan
    {
        let r = await run({ mac: true, home, projFolder: '', target: '', click: 'srt' });
        assert(/Avval yuqorida tarjima tilini tanlang/.test(last(r.log))); assert.strictEqual(r.log.spawn.length, 0);
        r = await run({ mac: true, home, projFolder: '', target: 'ru', click: 'srt', pickSrt: null });
        assert.strictEqual(r.log.spawn.length, 0); assert.strictEqual(r.log.status.length, 0);
        console.log("OK  Mac: SRT tugmasi - til tanlanmagan / dialog bekor -> hech narsa ishga tushmaydi");
    }
    // 9) Mac, Python yo'q
    {
        const { log } = await run({ mac: true, home, projFolder: '', pythonExists: false });
        assert.strictEqual(log.spawn.length, 0);
        assert(last(log).indexOf('INSTALL.command') > -1, last(log));
        console.log('OK  Mac: Python topilmasa INSTALL.command haqida xabar');
    }
    // 10) Universal panel Windows rejimida
    {
        const docs = TMP.replace(/\//g, '\\') + '\\Documents';
        const proj = TMP.replace(/\//g, '\\') + "\\Proj O'zbek";
        let r = await run({ mac: false, docs, projFolder: proj, target: 'ru' });
        assert.strictEqual(r.base, docs + '\\OgoCaption');
        assert.strictEqual(r.log.spawn[0].cmd, r.py); assert.strictEqual(r.log.spawn[1].cmd, r.py);
        assert.strictEqual(r.log.spawn[1].opts.windowsHide, true); assert.strictEqual(r.log.spawn[1].opts.env, undefined);
        assert.deepStrictEqual(r.log.imported, [proj + '\\Reels__1__final__captions.srt', proj + '\\Reels__1__final__captions_ru.srt']);
        r = await run({ mac: false, docs, projFolder: '', target: 'ru', model: false });
        assert(/tools\\INSTALL-TRANSLATE-MODEL\.bat/.test(last(r.log)), last(r.log));
        console.log("OK  Universal panel Windows rejimida: Documents\\OgoCaption, runtime\\python.exe, 2 ta SRT; model yo'q -> .bat");
    }
}

function importOf(p) { return 'importCaptions(' + JSON.stringify(p) + ')'; }

async function winSuite() {
    const docs = TMP.replace(/\//g, '\\') + '\\Documents';
    // 1) tarjimasiz - eski natija baytma-bayt; apostrofli papka endi import bo'ladi (JSON.stringify)
    {
        const proj = TMP.replace(/\//g, '\\') + "\\Proj O'zbek";
        const { log, base, py } = await run({ mac: false, docs, projFolder: proj });
        assert.strictEqual(log.eval[0], 'exportAudioToTemp()');
        assert.strictEqual(log.spawn[0].cmd, py);
        assert.deepStrictEqual(Array.from(log.spawn[0].args), [base + '\\Engine\\transcribe.py', base + '\\temp\\temp_audio.wav', 'uz']);
        assert.strictEqual(log.spawn[0].opts.windowsHide, true);
        assert.strictEqual(log.spawn[0].opts.cwd, base + '\\Engine');
        assert.deepStrictEqual(log.imported, [proj + '\\Reels__1__final__captions.srt']);
        assert.strictEqual(log.eval[2], importOf(proj + '\\Reels__1__final__captions.srt'));
        assert.strictEqual(read(log.imported[0]), SRT_BODY);
        assert(/kiritildi!$/.test(last(log)), last(log));
        console.log("OK  Win: runtime\\python.exe, tarjimasiz SRT o'zgarmagan, apostrofli loyiha papkasiga import");
    }
    // 2) uz -> ru tarjima
    {
        const proj = TMP.replace(/\//g, '\\') + '\\Proj2';
        const { log, base, py } = await run({ mac: false, docs, projFolder: proj, target: 'ru' });
        assert.strictEqual(log.spawn.length, 2);
        assert.strictEqual(log.spawn[1].cmd, py);
        assert.deepStrictEqual(Array.from(log.spawn[1].args), [base + '\\Engine\\translate.py', base + '\\temp\\translate_input.json']);
        assert.strictEqual(log.spawn[1].opts.windowsHide, true);
        assert.deepStrictEqual(log.cfg[0].words.map(w => w.word), ['Salom,', 'bugun', 'yigirma', '5', "o'zbek", 'tilida.']);
        assert.strictEqual(log.cfg[0].source, 'uz'); assert.strictEqual(log.cfg[0].target, 'ru');
        assert.deepStrictEqual(log.imported, [proj + '\\Reels__1__final__captions.srt', proj + '\\Reels__1__final__captions_ru.srt']);
        assert.strictEqual(read(log.imported[1]), TR_BODY);
        assert(/rus tiliga tarjima \(2 ta SRT\) kiritildi!$/.test(last(log)), last(log));
        console.log("OK  Win: uz->ru tarjima - translate.py cfg, 2 ta SRT");
    }
    // 3) loyiha saqlanmagan -> temp
    {
        const { log, base } = await run({ mac: false, docs, projFolder: '', target: 'en' });
        assert.deepStrictEqual(log.imported, [base + '\\temp\\Reels__1__final__captions.srt', base + '\\temp\\Reels__1__final__captions_en.srt']);
        console.log('OK  Win: loyiha saqlanmagan -> ikkala SRT OgoCaption\\temp ga');
    }
    // 4) model yo'q
    {
        const { log } = await run({ mac: false, docs, projFolder: '', target: 'ru', model: false });
        assert.strictEqual(log.eval.length, 0); assert.strictEqual(log.spawn.length, 0);
        assert(/Tarjima modeli o'rnatilmagan.*tools\\INSTALL-TRANSLATE-MODEL\.bat/.test(last(log)), last(log));
        console.log("OK  Win: model yo'q -> INSTALL-TRANSLATE-MODEL.bat haqida xabar, audio eksport qilinmaydi");
    }
    // 5) translate.py JSON xato bilan chiqsa (exit 1) -> "AI xatosi: ..."
    {
        const { log } = await run({ mac: false, docs, projFolder: '', target: 'ru', trMode: 'nomodel' });
        assert.strictEqual(log.imported.length, 1);
        assert.strictEqual(last(log), 'AI xatosi: Tarjima modeli topilmadi: X');
        console.log('OK  Win: translate.py xatosi -> "AI xatosi: ..." (asl SRT kiritilgan)');
    }
    // 6) auto til = tarjima tili
    {
        const { log } = await run({ mac: false, docs, projFolder: '', target: 'en', lang: 'auto', detected: 'en' });
        assert.strictEqual(log.spawn.length, 1);
        assert(/Tarjima qilinmadi: asl til ham ingliz\.$/.test(last(log)), last(log));
        console.log("OK  Win: auto til = tarjima tili -> faqat asl SRT");
    }
    // 7) tayyor SRT tarjimasi
    {
        const srtDir = TMP.replace(/\//g, '\\') + "\\Subs O'zbek";
        fs.mkdirSync(srtDir, { recursive: true });
        const src = srtDir + '\\fixed.SRT';
        fs.writeFileSync(src, SRT_BODY);
        const { log } = await run({ mac: false, docs, projFolder: '', target: 'ru', click: 'srt', pickSrt: src });
        assert.deepStrictEqual(log.eval, [importOf(srtDir + '\\fixed_ru.srt')]);
        assert.strictEqual(log.cfg[0].mode, 'srt'); assert.strictEqual(log.cfg[0].srt_path, src);
        assert.strictEqual(read(srtDir + '\\fixed_ru.srt'), TR_BODY);
        console.log("OK  Win: tayyor SRT tarjimasi -> fixed_ru.srt yonida, import");
    }
    // 8) Python yo'q
    {
        const { log } = await run({ mac: false, docs, projFolder: '', pythonExists: false });
        assert.strictEqual(log.spawn.length, 0);
        assert(last(log).indexOf('INSTALL.bat') > -1, last(log));
        console.log('OK  Win: Python topilmasa INSTALL.bat haqida xabar');
    }
}

// Alifbo: joriy / yangi (oʻ->ó, gʻ->ǵ, sh->ş, ch->ç). mac=false - Windows yo'llari bilan.
async function alphabetSuite(mac) {
    const tag = mac ? 'Mac' : 'Win';
    const W = s => (mac ? s : s.replace(/\//g, '\\'));
    const env = mac ? { mac: true, home: TMP + '/home/editor' } : { mac: false, docs: W(TMP) + '\\Documents' };
    const proj = W(TMP + '/alifbo/Loyiha');
    const uz = o => run(Object.assign({}, env, { projFolder: proj, words: WORDS_UZ }, o));
    const srtOf = (r, i = 0) => read(r.log.imported[i]);
    // 1) Default (hech narsa saqlanmagan) - joriy alifbo, natija o'zgarmagan, localStorage'ga yozilmaydi
    {
        const r = await uz({});
        assert.strictEqual(r.alphabetOnLoad, 'current');
        assert.strictEqual(srtOf(r), SRT_UZ_CURRENT);
        assert.deepStrictEqual(r.store, {});
        console.log(`OK  ${tag} alifbo: default - joriy, SRT o'zgarmagan, localStorage'ga yozilmaydi`);
    }
    // 2) Foydalanuvchi "yangi" ni tanladi -> eslab qolinadi, SRT yangi alifboda (mergeWords dan keyin)
    {
        const r = await uz({ pick: 'new' });
        assert.strictEqual(r.store[ALPHABET_KEY], 'new');
        assert.strictEqual(srtOf(r), SRT_UZ_NEW);
        assert(/kiritildi!$/.test(last(r.log)), last(r.log));
        console.log(`OK  ${tag} alifbo: "yangi" tanlandi -> localStorage, Çoyxonada qóşiq / Is'hoq / toǵga / ÓZBEKISTON`);
    }
    // 3) Qayta ochilganda saqlangan "yangi" tiklanadi; uz->ru tarjimaga joriy yozuvdagi so'zlar ketadi
    {
        const r = await uz({ storage: { [ALPHABET_KEY]: 'new' }, target: 'ru' });
        assert.strictEqual(r.alphabetOnLoad, 'new');
        assert.strictEqual(srtOf(r, 0), SRT_UZ_NEW);
        assert.deepStrictEqual(r.log.cfg[0].words.map(w => w.word),
            ['Choyxonada', "qo'shiq", 'eshitdik.', "Is'hoq", 'aka', 'tog‘ga', 'ketdi,', "ma'no", "O'ZBEKISTON"]);
        assert.strictEqual(srtOf(r, 1), TR_BODY);
        console.log(`OK  ${tag} alifbo: saqlangan "yangi" tiklandi; tarjimaga joriy yozuv, ru SRT o'zgarmagan`);
    }
    // 4) "yangi" saqlangan, foydalanuvchi "joriy" ga qaytardi
    {
        const r = await uz({ storage: { [ALPHABET_KEY]: 'new' }, pick: 'current' });
        assert.strictEqual(r.store[ALPHABET_KEY], 'current');
        assert.strictEqual(srtOf(r), SRT_UZ_CURRENT);
        console.log(`OK  ${tag} alifbo: "joriy" ga qaytarildi -> eslab qolindi, SRT joriy`);
    }
    // 5) Asl til o'zbek emas -> asl SRT o'zgarmaydi; ->uz tarjima yangi alifboda
    {
        const r = await uz({ storage: { [ALPHABET_KEY]: 'new' }, lang: 'ru', detected: 'ru', target: 'uz' });
        assert.strictEqual(srtOf(r, 0), SRT_UZ_CURRENT);
        assert.strictEqual(r.log.cfg[0].source, 'ru'); assert.strictEqual(r.log.cfg[0].target, 'uz');
        assert.strictEqual(srtOf(r, 1), UZ_TR_NEW);
        assert(/o'zbek tiliga tarjima \(2 ta SRT\) kiritildi!$/.test(last(r.log)), last(r.log));
        console.log(`OK  ${tag} alifbo: ru asl SRT o'zgarmaydi, ru->uz tarjima yangi alifboda`);
    }
    // 6) Auto: o'zbek aniqlansa - yangi alifbo, ingliz aniqlansa - o'zgarmaydi
    {
        let r = await uz({ storage: { [ALPHABET_KEY]: 'new' }, lang: 'auto', detected: 'uz' });
        assert.strictEqual(srtOf(r), SRT_UZ_NEW);
        r = await uz({ storage: { [ALPHABET_KEY]: 'new' }, lang: 'auto', detected: 'en' });
        assert.strictEqual(srtOf(r), SRT_UZ_CURRENT);
        console.log(`OK  ${tag} alifbo: auto -> uz aniqlansa yangi, en aniqlansa o'zgarmaydi`);
    }
    // 7) Tayyor SRT tarjimasi: ->uz yangi alifboda; ->ru o'zgarmaydi; joriy alifboda ->uz o'zgarmagan
    {
        const srtDir = W(TMP + '/alifbo/Subs');
        fs.mkdirSync(srtDir, { recursive: true });
        const src = srtDir + (mac ? '/' : '\\') + 'tayyor.srt';
        fs.writeFileSync(src, SRT_BODY);
        const out = srtDir + (mac ? '/' : '\\') + 'tayyor_uz.srt';
        let r = await run(Object.assign({}, env, { projFolder: '', storage: { [ALPHABET_KEY]: 'new' }, target: 'uz', click: 'srt', pickSrt: src }));
        assert.deepStrictEqual(r.log.imported, [out]);
        assert.strictEqual(read(out), UZ_TR_NEW);
        r = await run(Object.assign({}, env, { projFolder: '', storage: { [ALPHABET_KEY]: 'new' }, target: 'ru', click: 'srt', pickSrt: src }));
        assert.strictEqual(read(r.log.imported[0]), TR_BODY);
        r = await run(Object.assign({}, env, { projFolder: '', target: 'uz', click: 'srt', pickSrt: src }));
        assert.strictEqual(read(out), UZ_TR_CURRENT);
        console.log(`OK  ${tag} alifbo: tayyor SRT ->uz yangi alifboda, ->ru o'zgarmaydi, joriyda ->uz o'zgarmagan`);
    }
    // 8) localStorage ishlamasa (taqiqlangan) - default joriy, tanlov baribir ishlaydi, xato yo'q
    {
        let r = await uz({ storage: 'throw' });
        assert.strictEqual(r.alphabetOnLoad, 'current');
        assert.strictEqual(srtOf(r), SRT_UZ_CURRENT);
        r = await uz({ storage: 'throw', pick: 'new' });
        assert.strictEqual(srtOf(r), SRT_UZ_NEW);
        // noto'g'ri saqlangan qiymat -> joriy
        r = await uz({ storage: { [ALPHABET_KEY]: 'lotin2021' } });
        assert.strictEqual(r.alphabetOnLoad, 'current');
        assert.strictEqual(srtOf(r), SRT_UZ_CURRENT);
        console.log(`OK  ${tag} alifbo: localStorage taqiqlangan / noto'g'ri qiymat -> joriy, xatosiz`);
    }
    // 9) Eski index.html (alifbo tanlovi yo'q) - joriy, saqlangan qiymat e'tiborsiz
    {
        const r = await uz({ alphabetEl: false, storage: { [ALPHABET_KEY]: 'new' }, target: 'uz', lang: 'ru', detected: 'ru' });
        assert.strictEqual(srtOf(r, 0), SRT_UZ_CURRENT);
        assert.strictEqual(srtOf(r, 1), UZ_TR_CURRENT);
        console.log(`OK  ${tag} alifbo: alifbo tanlovisiz eski index.html -> joriy`);
    }
}

(async () => {
    if (KIND === 'win') await winSuite(); else await macSuite();
    await alphabetSuite(KIND !== 'win');
    if (KIND !== 'win') await alphabetSuite(false);   // universal panel Windows rejimida
    fs.rmSync(TMP, { recursive: true, force: true });
    console.log("\nHAMMASI O'TDI (main.js, " + KIND + ")");
})().catch(e => { console.error(e); process.exit(1); });
