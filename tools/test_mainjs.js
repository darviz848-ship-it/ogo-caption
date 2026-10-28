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

function run(o) {
    const { mac, home, docs, projFolder, pythonExists = true, projWritable = true, model = true,
            target = '', lang = 'uz', detected = 'uz', trMode = 'ok', click = 'generate', pickSrt = null } = o;
    return new Promise((resolve) => {
        const P = mac ? path.posix : path.win32;
        const base = mac ? P.join(home, 'Library', 'Application Support', 'OgoCaption') : P.join(docs, 'OgoCaption');
        const py = mac ? P.join(base, 'runtime', 'bin', 'python3') : P.join(base, 'runtime', 'python.exe');
        realFs.rmSync(base, { recursive: true, force: true });
        if (pythonExists) { realFs.mkdirSync(P.dirname(py), { recursive: true }); realFs.writeFileSync(py, ''); }
        if (model) {
            const md = P.join(base, 'Engine', 'translate_model');
            realFs.mkdirSync(md, { recursive: true }); realFs.writeFileSync(P.join(md, 'model.bin'), '');
        }
        if (projFolder) {
            if (projWritable) realFs.mkdirSync(projFolder, { recursive: true });
            else { realFs.mkdirSync(P.dirname(projFolder), { recursive: true }); realFs.writeFileSync(projFolder, 'fayl, papka emas'); }
        }
        const log = { eval: [], spawn: [], status: [], imported: [], cfg: [] };
        let done = false;
        const finish = () => { if (!done) { done = true; resolve({ log, base, py, P }); } };

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
                        realFs.mkdirSync(dir, { recursive: true });   // hostscript ham temp papkani yaratadi
                        cb(dir + (mac ? '/' : '\\') + 'temp_audio.wav|Reels #1 (final)');
                    } else if (script === 'getProjectFolder()') {
                        cb(projFolder || '');
                    } else if ((m = /^importCaptions\((.*)\)$/.exec(script))) {
                        const p = JSON.parse(m[1]);  // ExtendScript ham xuddi shunday parse qiladi
                        log.imported.push(p);
                        cb(realFs.existsSync(p) ? 'SUCCESS' : 'ERROR: SRT fayli topilmadi.');
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
                    child.stdout.emit('data', Buffer.from(JSON.stringify({ success: true, words: WORDS, language: detected }) + '\n'));
                    child.emit('close', 0, null);
                    return;
                }
                // translate.py <cfg.json>
                log.cfg.push(JSON.parse(realFs.readFileSync(args[1], 'utf8')));
                if (trMode === 'sigkill') { child.emit('close', null, 'SIGKILL'); return; }
                if (trMode === 'nomodel') {
                    child.stdout.emit('data', Buffer.from(JSON.stringify({ error: "Tarjima modeli topilmadi: X" }) + '\n'));
                    child.emit('close', 1, null);
                    return;
                }
                child.stdout.emit('data', Buffer.from('PROGRESS:2\nPROGRESS:10\nPROGRESS:100\n'));
                child.stdout.emit('data', Buffer.from(JSON.stringify({ success: true, blocks: TR_BLOCKS, sentences: 2 }) + '\n'));
                child.emit('close', 0, null);
            });
            return child;
        };

        const fakeOs = { homedir: () => home };
        const ctx = {
            window: { cep: { fs: { showOpenDialogEx: () => (pickSrt ? { err: 0, data: [pickSrt] } : { err: 0, data: [] }) } } },
            document, CSInterface, SystemPath: { MY_DOCUMENTS: 'myDocuments' }, console,
            process: { platform: mac ? 'darwin' : 'win32', env: { PATH: '/usr/bin', LOCALAPPDATA: '', ProgramFiles: '' } },
            require: m => ({ fs: realFs, path: P, os: fakeOs, child_process: { spawn, exec() {} } })[m],
            alert: msg => log.status.push('ALERT ' + msg), setTimeout, setImmediate,
        };
        vm.createContext(ctx);
        vm.runInContext(SRC, ctx);
        ctx.window.onload();
        (click === 'srt' ? els.translateSrtBtn : els.generateBtn)._h.click();
        // darhol qaytadigan xato stsenariylarida resetBtn chaqirilmaydi - kafolat
        setTimeout(finish, 400);
    });
}

const last = log => log.status[log.status.length - 1] || '';
const read = p => realFs.readFileSync(p, 'utf8');

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
        realFs.mkdirSync(srtDir, { recursive: true });
        const src = srtDir + '/fixed.srt';
        realFs.writeFileSync(src, SRT_BODY);
        let r = await run({ mac: true, home, projFolder: '', target: 'en', click: 'srt', pickSrt: src });
        assert.deepStrictEqual(r.log.eval, [importOf(srtDir + '/fixed_en.srt')]);
        assert.strictEqual(r.log.cfg[0].mode, 'srt'); assert.strictEqual(r.log.cfg[0].srt_path, src);
        assert.strictEqual(r.log.cfg[0].target, 'en');
        assert.strictEqual(read(srtDir + '/fixed_en.srt'), TR_BODY);
        assert(/2 ta gap ingliz tiliga tarjima qilindi: fixed_en\.srt$/.test(last(r.log)), last(r.log));
        // SRT turgan "papka" aslida fayl (yozib bo'lmaydi) -> temp
        const roDir = TMP + '/ro2/srtdir';
        realFs.mkdirSync(path.dirname(roDir), { recursive: true }); realFs.writeFileSync(roDir, 'fayl');
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
        realFs.mkdirSync(srtDir, { recursive: true });
        const src = srtDir + '\\fixed.SRT';
        realFs.writeFileSync(src, SRT_BODY);
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

(async () => {
    if (KIND === 'win') await winSuite(); else await macSuite();
    realFs.rmSync(TMP, { recursive: true, force: true });
    console.log("\nHAMMASI O'TDI (main.js, " + KIND + ")");
})().catch(e => { console.error(e); process.exit(1); });
