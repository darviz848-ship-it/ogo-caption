// Yangi o'zbek alifbosi konvertori (main.js: toNewAlphabet / applyUzAlphabet) uchun unit-test.
// Ishlatish:
//   node test_alphabet.js [main.js ...]   - default: win va mac paketlaridagi ikkala main.js
// Holatlar tools/alphabet_cases.json da (translate.py testi ham shu faylni ishlatadi).
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const files = process.argv.length > 2 ? process.argv.slice(2) : [
    path.join(ROOT, 'win', 'payload', 'panel', 'js', 'main.js'),
    path.join(ROOT, 'mac', 'payload', 'panel', 'js', 'main.js'),
];
const CASES = JSON.parse(fs.readFileSync(path.join(__dirname, 'alphabet_cases.json'), 'utf8')).cases;
const hex = s => Array.from(s).map(c => 'U+' + c.codePointAt(0).toString(16).toUpperCase().padStart(4, '0')).join(' ');

// main.js ni Premiere'siz yuklaymiz: faqat funksiyalar kerak (window.onload chaqirilmaydi)
function load(file) {
    const ctx = { window: {}, console, require: () => ({}), process: { platform: 'win32', env: {} } };
    vm.createContext(ctx);
    vm.runInContext(fs.readFileSync(file, 'utf8'), ctx, { filename: file });
    assert.strictEqual(typeof ctx.toNewAlphabet, 'function', file + ': toNewAlphabet topilmadi');
    return ctx;
}

const results = [];
let failed = 0;
for (const file of files) {
    const m = load(file);
    const got = [];
    const failedBefore = failed;
    for (const [input, expected, note] of CASES) {
        const out = m.toNewAlphabet(input);
        got.push(out);
        if (out !== expected) {
            failed++;
            console.log(`XATO ${path.relative(ROOT, file)}: ${JSON.stringify(input)} -> ${JSON.stringify(out)}, kutilgan ${JSON.stringify(expected)} (${note})\n     ${hex(out)}\n     ${hex(expected)}`);
        }
        // Ikki marta qo'llash natijani o'zgartirmaydi
        assert.strictEqual(m.toNewAlphabet(out), out, 'ikki marta: ' + input);
    }

    // applyUzAlphabet: joriy alifboda aynan o'sha massiv (baytma-bayt), yangida - vaqtlar saqlanadi
    const blocks = [{ text: "Choy ichamiz, Is'hoq aka", start: 1.25, end: 2.5 }, { text: "o'zbekcha", start: 3, end: 4 }];
    assert.strictEqual(m.applyUzAlphabet(blocks, 'current'), blocks);
    assert.strictEqual(m.applyUzAlphabet(blocks, undefined), blocks);
    const nb = m.applyUzAlphabet(blocks, 'new');
    assert.deepStrictEqual(JSON.parse(JSON.stringify(nb)),
        [{ text: "Çoy içamiz, Is'hoq aka", start: 1.25, end: 2.5 }, { text: "ózbekça", start: 3, end: 4 }]);
    assert.strictEqual(blocks[0].text, "Choy ichamiz, Is'hoq aka", 'asl bloklar o\'zgarmasligi kerak');

    // localStorage: yo'q / xato beradi -> joriy
    assert.strictEqual(m.loadAlphabet(), 'current');
    m.window.localStorage = { getItem() { throw new Error('SecurityError'); }, setItem() { throw new Error('SecurityError'); } };
    assert.strictEqual(m.loadAlphabet(), 'current');
    m.saveAlphabet('new');   // xato tashqariga chiqmaydi
    const store = {};
    m.window.localStorage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
    m.saveAlphabet('new');
    assert.strictEqual(m.loadAlphabet(), 'new');
    m.saveAlphabet('boshqa');
    assert.strictEqual(store['ogoCaption.alphabet'], 'current');
    assert.strictEqual(m.loadAlphabet(), 'current');

    results.push(got);
    if (failed === failedBefore) {
        console.log(`OK  ${path.relative(ROOT, file)}: ${CASES.length} ta holat, ikki marta qo'llash, applyUzAlphabet, localStorage`);
    }
}

// Ikkala paketdagi konvertor bir xil natija beradi
for (let i = 1; i < results.length; i++) assert.deepStrictEqual(results[i], results[0], 'win va mac main.js konvertori farq qiladi');

if (failed) {
    console.log(`\n${failed} ta holat XATO`);
    process.exit(1);
}
console.log(`\nHAMMASI O'TDI (alifbo konvertori, ${CASES.length} ta holat x ${files.length} ta main.js)`);
