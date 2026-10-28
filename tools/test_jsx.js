// hostscript.jsx ni Node'da soxta ExtendScript muhitida sinash (Mac + Windows)
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const SRC = fs.readFileSync(process.argv[2], 'utf8');

// --- ES3 tekshiruvi: ExtendScript tushunmaydigan narsalar yo'qligi
const es3Bad = [/\blet\s/, /\bconst\s/, /=>/, /`/, /\.forEach\(/, /\.trim\(/, /\bJSON\./, /\.map\(/, /\.filter\(/, /Array\.isArray/, /\.includes\(/, /\.startsWith\(/, /\.endsWith\(/];
const codeOnly = SRC.split('\n').map(l => l.replace(/\/\/.*$/, '')).join('\n');
for (const re of es3Bad) assert(!re.test(codeOnly), 'ES3 da yo\'q konstruksiya: ' + re);
console.log('OK  ES3: taqiqlangan konstruksiya yo\'q');

function makeEnv({ os, startup, userData, myDocuments, files, dirs, env }) {
    const fsSet = new Set(files);
    const dirSet = new Set(dirs || []);
    const calls = { export: [], import: [] };
    const isWin = os.indexOf('Windows') > -1;
    const sep = isWin ? '\\' : '/';
    const parentOf = p => { const i = p.lastIndexOf(sep); return i > 0 ? p.slice(0, i) : null; };
    function Folder(p) { this.fsName = p; }
    Object.defineProperty(Folder.prototype, 'exists', { get() { return dirSet.has(this.fsName); } });
    Object.defineProperty(Folder.prototype, 'parent', { get() { const q = parentOf(this.fsName); return q ? new Folder(q) : null; } });
    Folder.prototype.create = function () { dirSet.add(this.fsName); return true; };
    Folder.prototype.getFiles = function (mask) {
        const re = new RegExp('^' + mask.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.') + '$');
        const out = [];
        for (const d of dirSet) {
            if (parentOf(d) === this.fsName && re.test(d.slice(this.fsName.length + 1))) out.push(new Folder(d));
        }
        return out;
    };
    function File(p) { this.fsName = p; }
    Object.defineProperty(File.prototype, 'exists', { get() { return fsSet.has(this.fsName); } });
    Object.defineProperty(File.prototype, 'parent', { get() { const q = parentOf(this.fsName); return q ? new Folder(q) : null; } });
    File.prototype.remove = function () { fsSet.delete(this.fsName); return true; };
    Folder.startup = startup ? new Folder(startup) : undefined;
    Folder.userData = new Folder(userData);
    Folder.myDocuments = new Folder(myDocuments);
    const seq = {
        name: 'Reels 01',
        exportAsMediaDirect(out, preset, mode) { calls.export.push({ out, preset, mode }); fsSet.add(out); return ''; },
    };
    const app = {
        encoder: { ENCODE_ENTIRE: 0 },
        project: { activeSequence: seq, path: '', rootItem: {}, importFiles(list) { calls.import.push(list); return true; } },
    };
    const ctx = { $: { os, getenv: k => (env || {})[k] || null }, Folder, File, app };
    vm.createContext(ctx);
    vm.runInContext(SRC, ctx);
    return { ctx, calls, fsSet };
}

const PRESET = 'Waveform Audio 48kHz 16-bit.epr';
const MAC_UD = '/Users/editor/Library/Application Support';
const macRel = '/MediaIO/systempresets/3F3F3F3F_57415645/' + PRESET;

// 1) Mac: Folder.startup = .app/Contents/MacOS -> Contents/MediaIO dan topadi
{
    const app26 = '/Applications/Adobe Premiere Pro 2026/Adobe Premiere Pro 2026.app';
    const { ctx, calls } = makeEnv({
        os: 'Macintosh OS 14.6.1/64', startup: app26 + '/Contents/MacOS', userData: MAC_UD, myDocuments: '/Users/editor/Documents',
        files: [app26 + '/Contents' + macRel], dirs: [MAC_UD + '/OgoCaption/temp'],
    });
    const r = ctx.exportAudioToTemp(MAC_UD + '/OgoCaption/temp');
    assert.strictEqual(r, MAC_UD + '/OgoCaption/temp/temp_audio.wav|Reels 01');
    assert.strictEqual(calls.export[0].preset, app26 + '/Contents' + macRel);
    console.log('OK  Mac: preset ishlab turgan Premiere .app ichidan topildi');
}
// 2) Mac: startup yo'q, odatiy 2025 yo'li
{
    const app25 = '/Applications/Adobe Premiere Pro 2025/Adobe Premiere Pro 2025.app';
    const { ctx, calls } = makeEnv({
        os: 'Macintosh OS 13.4.0/64', startup: null, userData: MAC_UD, myDocuments: '/Users/editor/Documents',
        files: [app25 + '/Contents' + macRel], dirs: [],
    });
    const r = ctx.exportAudioToTemp('');   // bo'sh -> Application Support/OgoCaption/temp
    assert.strictEqual(r, MAC_UD + '/OgoCaption/temp/temp_audio.wav|Reels 01');
    assert.strictEqual(calls.export[0].preset, app25 + '/Contents' + macRel);
    console.log('OK  Mac: tempDir berilmasa ~/Library/Application Support/OgoCaption/temp; 2025 odatiy yo\'li');
}
// 3) Mac: Beta nomli papka -> /Applications skaneri topadi
{
    const beta = '/Applications/Adobe Premiere Pro (Beta)/Adobe Premiere Pro (Beta).app';
    const { ctx, calls } = makeEnv({
        os: 'Macintosh OS 15.0/64', startup: '/nowhere/MacOS', userData: MAC_UD, myDocuments: '/Users/editor/Documents',
        files: [beta + '/Contents' + macRel],
        dirs: ['/Applications', '/Applications/Adobe Premiere Pro (Beta)', beta, '/Applications/Safari.app'],
    });
    ctx.exportAudioToTemp(MAC_UD + '/OgoCaption/temp');
    assert.strictEqual(calls.export[0].preset, beta + '/Contents' + macRel);
    console.log('OK  Mac: nostandart nom (Beta) /Applications skanerida topildi');
}
// 4) Mac: tizim preseti yo'q -> paket bilan kelgan nusxa
{
    const bundled = MAC_UD + '/OgoCaption/presets/' + PRESET;
    const { ctx, calls } = makeEnv({
        os: 'Macintosh OS 14.0/64', startup: '/x/y/MacOS', userData: MAC_UD, myDocuments: '/Users/editor/Documents',
        files: [bundled], dirs: ['/Applications'],
    });
    ctx.exportAudioToTemp(MAC_UD + '/OgoCaption/temp');
    assert.strictEqual(calls.export[0].preset, bundled);
    console.log('OK  Mac: zaxira preset (OgoCaption/presets) ishlatildi');
}
// 5) Mac: hech qayerda yo'q -> tushunarli xato
{
    const { ctx, calls } = makeEnv({
        os: 'Macintosh OS 14.0/64', startup: null, userData: MAC_UD, myDocuments: '/Users/editor/Documents', files: [], dirs: [],
    });
    const r = ctx.exportAudioToTemp(MAC_UD + '/OgoCaption/temp');
    assert(r.indexOf('ERROR:') === 0 && calls.export.length === 0);
    console.log('OK  Mac: preset topilmasa ERROR qaytadi');
}
// 6) Windows: eski xatti-harakat saqlangan (Folder.startup + Documents)
{
    const pp = 'C:\\Program Files\\Adobe\\Adobe Premiere Pro 2026';
    const winPreset = pp + '\\MediaIO\\systempresets\\3F3F3F3F_57415645\\' + PRESET;
    const { ctx, calls } = makeEnv({
        os: 'Windows/64 10.0', startup: pp, userData: 'C:\\Users\\l\\AppData\\Roaming', myDocuments: 'C:\\Users\\l\\Documents',
        files: [winPreset], dirs: [], env: { ProgramFiles: 'C:\\Program Files' },
    });
    const r = ctx.exportAudioToTemp('');
    assert.strictEqual(r, 'C:\\Users\\l\\Documents\\OgoCaption\\temp\\temp_audio.wav|Reels 01');
    assert.strictEqual(calls.export[0].preset, winPreset);
    console.log('OK  Windows: Documents\\OgoCaption\\temp + Premiere 2026 preseti (o\'zgarmagan)');
}
// 7) importCaptions + getProjectFolder
{
    const { ctx, calls, fsSet } = makeEnv({
        os: 'Macintosh OS 14.0/64', startup: null, userData: MAC_UD, myDocuments: '/Users/editor/Documents', files: [], dirs: [],
    });
    const srt = "/Users/editor/Projects/Lochin's proj/Reels_01_captions.srt";
    fsSet.add(srt);
    assert.strictEqual(ctx.importCaptions(srt), 'SUCCESS');
    assert.deepStrictEqual(Array.from(calls.import[0]), [srt]);
    ctx.app.project.path = "/Users/editor/Projects/Lochin's proj/edit.prproj";
    assert.strictEqual(ctx.getProjectFolder(), "/Users/editor/Projects/Lochin's proj");
    console.log('OK  importCaptions va getProjectFolder (apostrofli yo\'l)');
}
console.log('\nHAMMASI O\'TDI (hostscript.jsx)');
