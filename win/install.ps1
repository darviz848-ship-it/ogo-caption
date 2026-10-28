# =============================================================
#  OgoCaption - Premiere Pro AI subtitr paneli
#  O'rnatuvchi skript (Windows, admin huquqi shart emas)
# =============================================================
param(
    [switch]$Force,     # savol bermasdan o'rnatadi
    [switch]$NoPause,   # oxirida "Enter bosing" so'ramaydi
    [string]$TestRoot = ""  # ichki: sinov uchun boshqa papkaga o'rnatadi
)

$ErrorActionPreference = "Stop"

function Say($msg, $color = "Gray") { Write-Host $msg -ForegroundColor $color }
function Head($msg) { Write-Host ""; Write-Host "  $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  [!]   $msg" -ForegroundColor Yellow }
function Die($msg) {
    Write-Host ""
    Write-Host "  [XATO] $msg" -ForegroundColor Red
    Write-Host ""
    if (-not $NoPause) { Read-Host "Yopish uchun Enter bosing" }
    exit 1
}

Clear-Host
Write-Host ""
Write-Host "  ===========================================================" -ForegroundColor Cyan
Write-Host "    OgoCaption  ::  Premiere Pro uchun offline AI subtitr" -ForegroundColor White
Write-Host "    O'rnatuvchi" -ForegroundColor DarkGray
Write-Host "  ===========================================================" -ForegroundColor Cyan

# ---------- 0. Paket joyi ----------
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$payload = Join-Path $root "payload"
if (-not (Test-Path $payload)) {
    Die "payload papkasi topilmadi. install.ps1 va payload bir papkada turishi kerak."
}
foreach ($part in @("panel", "Engine", "mogrts", "runtime.zip")) {
    if (-not (Test-Path (Join-Path $payload $part))) { Die "payload\$part topilmadi. Paket to'liq ko'chirilmagan." }
}

# ---------- 1. Maqsad papkalar ----------
$docs    = [Environment]::GetFolderPath("MyDocuments")
$dest    = Join-Path $docs "OgoCaption"
$cepRoot = Join-Path $env:APPDATA "Adobe\CEP\extensions"
$cep     = Join-Path $cepRoot "OgoCaption"
if ($TestRoot -ne "") {
    $dest = Join-Path $TestRoot "Documents/OgoCaption"
    $cep  = Join-Path $TestRoot "AppData/Adobe/CEP/extensions/OgoCaption"
    Write-Host "  (SINOV REJIMI: $TestRoot)" -ForegroundColor Magenta
}

Head "Qayerga o'rnatiladi"
Say  "    Panel   : $cep"
Say  "    Enjin   : $dest"

# ---------- 2. Bo'sh joy ----------
$needBytes = 0
Get-ChildItem $payload -Recurse -File | ForEach-Object { $needBytes += $_.Length }
$needGb = [math]::Round($needBytes / 1GB, 2)
$destDrive = (Split-Path -Qualifier $dest)
$free = (Get-PSDrive -Name $destDrive.TrimEnd(":")).Free
$freeGb = [math]::Round($free / 1GB, 2)
Head "Joy"
Say  "    Kerak   : $needGb GB"
Say  "    Bo'sh   : $freeGb GB ($destDrive)"
if ($free -lt ($needBytes * 1.05)) { Die "Diskda joy yetarli emas." }

# ---------- 3. Premiere ochiqmi ----------
$ppro = Get-Process -Name "Adobe Premiere Pro" -ErrorAction SilentlyContinue
if ($ppro) {
    Warn "Premiere Pro ochiq. O'rnatishdan oldin yopish tavsiya etiladi."
    if (-not $Force) {
        $a = Read-Host "  Premiere yopilgach davom etish uchun Enter bosing (bekor qilish uchun N)"
        if ($a -eq "N" -or $a -eq "n") { Die "Bekor qilindi." }
    }
}

# ---------- 4. Tasdiq ----------
if (-not $Force) {
    Write-Host ""
    $go = Read-Host "  O'rnatishni boshlaymizmi? (H/y)"
    if ($go -eq "N" -or $go -eq "n" -or $go -eq "yo'q") { Die "Bekor qilindi." }
}

# ---------- 5. Eski o'rnatmani zaxiralash ----------
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
Head "Eski o'rnatmani tekshirish"
if (Test-Path $cep) {
    # MUHIM: zaxira "extensions" papkasidan TASHQARIGA chiqariladi,
    # aks holda Premiere uni ikkinchi (dublikat) panel deb ko'radi.
    $bakRoot = Split-Path -Parent (Split-Path -Parent $cep)
    $bak = Join-Path $bakRoot "OgoCaption.backup-$stamp"
    Move-Item -Path $cep -Destination $bak -Force
    Ok "Eski panel zaxiraga olindi: $bak"
} else {
    Say "    Eski panel yo'q - toza o'rnatish."
}

# ---------- 6. Nusxalash ----------
function CopyTree($src, $dst, $label) {
    Say "    $label ..." 
    $null = robocopy $src $dst /E /NFL /NDL /NJH /NJS /NC /NS /NP /R:2 /W:2
    if ($LASTEXITCODE -ge 8) { Die "$label nusxalanmadi (robocopy kodi $LASTEXITCODE)" }
    Ok "$label"
}

Head "Fayllar ko'chirilmoqda (modellar ~1.9 GB, biroz vaqt oladi)"
CopyTree (Join-Path $payload "panel")   $cep                          "Panel (CEP kengaytma)"
CopyTree (Join-Path $payload "Engine")  (Join-Path $dest "Engine")    "Enjin + AI modellar"
CopyTree (Join-Path $payload "mogrts")  (Join-Path $dest "mogrts")    "MOGRT shablonlar"

# Portativ Python zip ichida keladi: fleshkada 4000+ mayda fayl
# 2 GB dan ortiq joy egallab, ko'chirishni sekinlashtiradi.
Say "    Portativ Python ochilmoqda ..."
$rtZip = Join-Path $payload "runtime.zip"
$rtDir = Join-Path $dest "runtime"
if (Test-Path $rtDir) { Remove-Item -Path $rtDir -Recurse -Force }
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($rtZip, $rtDir)
} catch {
    Expand-Archive -Path $rtZip -DestinationPath $rtDir -Force
}
if (-not (Test-Path (Join-Path $rtDir "python.exe"))) { Die "runtime.zip ochilmadi." }
Ok "Portativ Python"

$tempDir = Join-Path $dest "temp"
if (-not (Test-Path $tempDir)) { New-Item -ItemType Directory -Path $tempDir | Out-Null }
Ok "temp papka"

# ---------- 7. Reestr: imzosiz panelga ruxsat ----------
Head "Reestr sozlanmoqda (imzosiz CEP panelga ruxsat)"
$done = 0
for ($v = 9; $v -le 20; $v++) {
    $key = "HKCU:\Software\Adobe\CSXS.$v"
    try {
        if (-not (Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
        Set-ItemProperty -Path $key -Name "PlayerDebugMode" -Value "1" -Type String
        $done++
    } catch { }
}
Ok "CSXS.9 - CSXS.20 ($done ta kalit)"

# ---------- 8. Tekshiruv ----------
Head "Tekshiruv"
$py = Join-Path $dest "runtime\python.exe"
if (-not (Test-Path $py)) { Die "Portativ Python ko'chmadi: $py" }

$check = & $py -c "import faster_whisper, ctranslate2, numpy, tokenizers; print('ENGINE-OK', faster_whisper.__version__)" 2>&1
if ("$check" -notlike "*ENGINE-OK*") { Die "Python enjin ishlamadi:`n$check" }
Ok "Python enjin: $check"

foreach ($m in @("uzbek_model", "multi_model")) {
    $cfg = Join-Path $dest "Engine\$m\config.json"
    $bin = Join-Path $dest "Engine\$m\model.bin"
    if (-not (Test-Path $cfg)) { Die "$m\config.json yo'q" }
    if (-not (Test-Path $bin)) { Die "$m\model.bin yo'q" }
    $mb = [math]::Round((Get-Item $bin).Length / 1MB)
    Ok "$m ($mb MB)"
}
if (-not (Test-Path (Join-Path $dest "Engine\uzbek_model\tokenizer.json"))) {
    Warn "uzbek_model\tokenizer.json yo'q - internetsiz ishlamasligi mumkin."
}
foreach ($f in @("transcribe.py", "translate.py", "get_translate_model.py")) {
    if (-not (Test-Path (Join-Path $dest "Engine\$f"))) { Die "Enjin fayli yetishmayapti: Engine\$f" }
}
Ok "Enjin skriptlari joyida"
foreach ($f in @("index.html", "js\main.js", "jsx\hostscript.jsx", "CSXS\manifest.xml")) {
    if (-not (Test-Path (Join-Path $cep $f))) { Die "Panel fayli yetishmayapti: $f" }
}
Ok "Panel fayllari joyida"

# ---------- 9. Oflayn tarjima modeli (ixtiyoriy) ----------
# Model 2.95 GB - paketga sig'maydi. Lokal nusxa (translate_model papkasi) bo'lsa
# ko'chiriladi, bo'lmasa internetdan yuklash taklif qilinadi. Xato o'rnatishni to'xtatmaydi.
Head "Oflayn tarjima modeli (ixtiyoriy, 2.95 GB)"
$trDest = Join-Path $dest "Engine\translate_model"
$trMode = "ask"
if ($Force) { $trMode = "no" }
& $py (Join-Path $dest "Engine\get_translate_model.py") --dest $trDest `
    --source (Join-Path $root "translate_model") `
    --source (Join-Path (Split-Path -Parent $root) "translate_model") `
    --download $trMode
$trOk = ($LASTEXITCODE -eq 0)
if ($trOk) { Ok "Tarjima modeli joyida" }
else { Warn "Tarjima modeli o'rnatilmadi - caption ishlaydi, tarjima yo'q. Keyin: tools\INSTALL-TRANSLATE-MODEL.bat" }

# ---------- 10. Yakun ----------
Write-Host ""
Write-Host "  ===========================================================" -ForegroundColor Green
Write-Host "    TAYYOR! OgoCaption o'rnatildi." -ForegroundColor Green
Write-Host "  ===========================================================" -ForegroundColor Green
Write-Host ""
Say "    Endi nima qilish kerak:" "White"
Say "      1. Premiere Pro ni butunlay yopib, qaytadan oching"
Say "      2. Window  ->  Extensions  ->  ogo caption"
Say "      3. Timeline'da sequence ochib, 'Subtitr yasash' tugmasini bosing"
Write-Host ""
if (-not $trOk) { Say "    Tarjima kerak bo'lsa: tools\INSTALL-TRANSLATE-MODEL.bat" "DarkGray" }
Say "    Ishlamasa: tools\TEST-ENGINE.bat ni ishga tushiring." "DarkGray"
Say "    O'chirish uchun: tools\UNINSTALL.bat" "DarkGray"
Write-Host ""
if (-not $NoPause) { Read-Host "Yopish uchun Enter bosing" }
