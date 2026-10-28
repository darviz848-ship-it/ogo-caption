# OgoCaption - o'rnatilgan enjinni tekshirish
param(
    [switch]$NoPause,
    [string]$TestRoot = ""  # ichki: sinov o'rnatmasini tekshiradi
)
$ErrorActionPreference = "Continue"
function Ok($m)   { Write-Host "  [OK]   $m" -ForegroundColor Green }
function Bad($m)  { Write-Host "  [XATO] $m" -ForegroundColor Red }
function Warn($m) { Write-Host "  [!]    $m" -ForegroundColor Yellow }
function Head($m) { Write-Host ""; Write-Host "  $m" -ForegroundColor Cyan }

Write-Host ""
Write-Host "  === OgoCaption tekshiruvi ===" -ForegroundColor Cyan

$docs = [Environment]::GetFolderPath("MyDocuments")
$dest = Join-Path $docs "OgoCaption"
$cep  = Join-Path $env:APPDATA "Adobe\CEP\extensions\OgoCaption"
if ($TestRoot -ne "") {
    $dest = Join-Path $TestRoot "Documents/OgoCaption"
    $cep  = Join-Path $TestRoot "AppData/Adobe/CEP/extensions/OgoCaption"
}
$fail = 0

Head "1. Papkalar"
foreach ($p in @($dest, $cep, (Join-Path $dest "Engine"), (Join-Path $dest "mogrts"), (Join-Path $dest "runtime"))) {
    if (Test-Path $p) { Ok $p } else { Bad "topilmadi: $p"; $fail++ }
}

Head "2. Panel fayllari"
foreach ($f in @("index.html", "js\main.js", "js\CSInterface.js", "jsx\hostscript.jsx", "CSXS\manifest.xml", "css\style.css")) {
    if (Test-Path (Join-Path $cep $f)) { Ok $f } else { Bad "yo'q: $f"; $fail++ }
}

Head "3. AI modellar"
foreach ($m in @("uzbek_model", "multi_model")) {
    $bin = Join-Path $dest "Engine\$m\model.bin"
    if (Test-Path $bin) {
        $mb = [math]::Round((Get-Item $bin).Length / 1MB)
        Ok "$m - $mb MB"
    } else { Bad "$m\model.bin yo'q"; $fail++ }
    if (-not (Test-Path (Join-Path $dest "Engine\$m\tokenizer.json"))) {
        Warn "$m\tokenizer.json yo'q (internetsiz ishlamasligi mumkin)"
    }
}

Head "4. Reestr (PlayerDebugMode)"
$on = 0
for ($v = 9; $v -le 20; $v++) {
    $key = "HKCU:\Software\Adobe\CSXS.$v"
    if (Test-Path $key) {
        $val = (Get-ItemProperty -Path $key -Name "PlayerDebugMode" -ErrorAction SilentlyContinue).PlayerDebugMode
        if ($val -eq "1") { $on++ }
    }
}
if ($on -gt 0) { Ok "$on ta CSXS kalitida yoqilgan" } else { Bad "PlayerDebugMode yoqilmagan - panel Premiere'da ko'rinmaydi"; $fail++ }

Head "5. Python enjin"
# main.js dagi bilan bir xil tartib: python-path.txt -> portativ -> tizim
$py = $null
$cfg = Join-Path $dest "python-path.txt"
if (Test-Path $cfg) {
    $c = (Get-Content $cfg -Raw).Trim().Trim('"')
    if ($c -and (Test-Path $c)) { $py = $c; Ok "python-path.txt: $c" }
}
if (-not $py) {
    $p1 = Join-Path $dest "runtime\python.exe"
    if (Test-Path $p1) { $py = $p1; Ok "portativ Python: $p1" }
}
if (-not $py) {
    foreach ($v in @("Python314", "Python313", "Python312", "Python311", "Python310")) {
        $p2 = Join-Path $env:LOCALAPPDATA "Programs\Python\$v\python.exe"
        if (Test-Path $p2) { $py = $p2; Warn "tizim Python ishlatilmoqda: $p2"; break }
    }
}
if (-not $py) {
    Bad "Python topilmadi (portativ ham, tizimda ham)"; $fail++
} else {
    $imp = & $py -c "import faster_whisper, ctranslate2, numpy, av, onnxruntime, tokenizers; print('IMPORT-OK', faster_whisper.__version__)" 2>&1
    if ("$imp" -like "*IMPORT-OK*") { Ok "$imp" } else { Bad "import xatosi: $imp"; $fail++ }
}

Head "6. Haqiqiy transkripsiya (internetsiz, 2 soniyalik test audio)"
if (Test-Path $py) {
    $tempDir = Join-Path $dest "temp"
    if (-not (Test-Path $tempDir)) { New-Item -ItemType Directory -Path $tempDir | Out-Null }
    $wav = Join-Path $tempDir "selftest.wav"
    $mk = @"
import wave, struct, math
fr = 16000
w = wave.open(r'$wav', 'wb')
w.setnchannels(1); w.setsampwidth(2); w.setframerate(fr)
w.writeframes(b''.join(struct.pack('<h', int(3000 * math.sin(i / 18.0))) for i in range(fr * 2)))
w.close()
print('WAV-OK')
"@
    $mkFile = Join-Path $tempDir "_mkwav.py"
    Set-Content -Path $mkFile -Value $mk -Encoding UTF8
    $r = & $py $mkFile 2>&1
    if ("$r" -notlike "*WAV-OK*") { Bad "test audio yasalmadi: $r"; $fail++ }

    if (Test-Path $wav) {
        $env:HF_HUB_OFFLINE = "1"
        Push-Location (Join-Path $dest "Engine")
        $out = & $py "transcribe.py" $wav "uz" 2>&1
        Pop-Location
        Remove-Item Env:HF_HUB_OFFLINE -ErrorAction SilentlyContinue
        if ("$out" -like "*success*") {
            Ok "uzbek_model internetsiz yuklandi va ishladi"
        } else {
            Bad "transcribe.py xatosi:"
            Write-Host "$out" -ForegroundColor DarkGray
            $fail++
        }
        Remove-Item $wav, $mkFile -ErrorAction SilentlyContinue
    }
}

Head "7. Oflayn tarjima (ixtiyoriy)"
$trPy  = Join-Path $dest "Engine\translate.py"
$trBin = Join-Path $dest "Engine\translate_model\model.bin"
if (-not (Test-Path $trPy)) {
    Bad "Engine\translate.py yo'q - INSTALL.bat ni qayta ishga tushiring"; $fail++
} elseif (-not (Test-Path $trBin)) {
    Warn "Tarjima modeli o'rnatilmagan (ixtiyoriy). Kerak bo'lsa: tools\INSTALL-TRANSLATE-MODEL.bat"
} elseif ($py) {
    $mb = [math]::Round((Get-Item $trBin).Length / 1MB)
    Ok "translate_model - $mb MB"
    $tempDir = Join-Path $dest "temp"
    if (-not (Test-Path $tempDir)) { New-Item -ItemType Directory -Path $tempDir | Out-Null }
    $trCfg = Join-Path $tempDir "selftest_translate.json"
    $json = '{"mode": "words", "source": "uz", "target": "en", "words_per_line": 8, "words": [' +
        '{"word": "Salom,", "start": 0.0, "end": 0.5}, {"word": "bugun", "start": 0.6, "end": 1.0}, ' +
        '{"word": "havo", "start": 1.1, "end": 1.4}, {"word": "juda", "start": 1.5, "end": 1.8}, ' +
        '{"word": "yaxshi.", "start": 1.9, "end": 2.4}]}'
    Set-Content -Path $trCfg -Value $json -Encoding ASCII
    Write-Host "    'Salom, bugun havo juda yaxshi.' -> ingliz tiliga (model yuklanishi 10-30 soniya)..." -ForegroundColor DarkGray
    $out = & $py $trPy $trCfg 2>&1
    $last = ($out | Where-Object { "$_".Trim().StartsWith("{") } | Select-Object -Last 1)
    $res = $null
    try { $res = "$last" | ConvertFrom-Json } catch { }
    if ($res -and $res.success) {
        Ok ("tarjima ishladi: " + (($res.blocks | ForEach-Object { $_.text }) -join " "))
    } else {
        Bad "translate.py xatosi:"
        Write-Host "$out" -ForegroundColor DarkGray
        $fail++
    }
    Remove-Item $trCfg -ErrorAction SilentlyContinue
}

Write-Host ""
if ($fail -eq 0) {
    Write-Host "  ==> HAMMASI JOYIDA. Premiere'ni qayta ochib, Window > Extensions > ogo caption" -ForegroundColor Green
} else {
    Write-Host "  ==> $fail ta muammo topildi. INSTALL.bat ni qayta ishga tushirib ko'r." -ForegroundColor Red
}
Write-Host ""
if (-not $NoPause) { Read-Host "Yopish uchun Enter bosing" }
