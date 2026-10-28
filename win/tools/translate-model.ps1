# OgoCaption - oflayn tarjima modelini o'rnatish (ixtiyoriy, 2.95 GB)
# Lokal nusxa (translate_model papkasi) bo'lsa - ko'chiradi, bo'lmasa internetdan yuklaydi.
param(
    [switch]$NoPause,
    [ValidateSet("ask", "yes", "no")][string]$Download = "ask",
    [string]$TestRoot = ""  # ichki: sinov uchun boshqa papkaga o'rnatadi
)
$ErrorActionPreference = "Continue"
function Ok($m)   { Write-Host "  [OK]   $m" -ForegroundColor Green }
function Bad($m)  { Write-Host "  [XATO] $m" -ForegroundColor Red }
function Warn($m) { Write-Host "  [!]    $m" -ForegroundColor Yellow }
function Done($code) {
    Write-Host ""
    if (-not $NoPause) { Read-Host "Yopish uchun Enter bosing" }
    exit $code
}

Write-Host ""
Write-Host "  === OgoCaption: oflayn tarjima modeli (MADLAD-400-3B, 2.95 GB) ===" -ForegroundColor Cyan
Write-Host ""

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$docs = [Environment]::GetFolderPath("MyDocuments")
$dest = Join-Path $docs "OgoCaption"
if ($TestRoot -ne "") {
    $dest = Join-Path $TestRoot "Documents/OgoCaption"
    Write-Host "  (SINOV REJIMI: $TestRoot)" -ForegroundColor Magenta
}
$engine = Join-Path $dest "Engine"

if (-not (Test-Path (Join-Path $engine "translate.py"))) {
    Bad "Tarjimali OgoCaption o'rnatilmagan ($engine\translate.py yo'q)."
    Write-Host "         Avval paketdagi INSTALL.bat ni ishga tushiring." -ForegroundColor DarkGray
    Done 1
}

# main.js dagi bilan bir xil tartib: python-path.txt -> portativ runtime
$py = $null
$cfg = Join-Path $dest "python-path.txt"
if (Test-Path $cfg) {
    $c = (Get-Content $cfg -Raw).Trim().Trim('"')
    if ($c -and (Test-Path $c)) { $py = $c }
}
if (-not $py) {
    $p1 = Join-Path $dest "runtime\python.exe"
    if (Test-Path $p1) { $py = $p1 }
}
if (-not $py) { Bad "Python topilmadi. INSTALL.bat ni qayta ishga tushiring."; Done 1 }

$getter = Join-Path $engine "get_translate_model.py"
if (-not (Test-Path $getter)) { $getter = Join-Path $root "payload\Engine\get_translate_model.py" }

Write-Host "  Qayerga : $engine\translate_model"
Write-Host "  Manba   : paket yonidagi translate_model papkasi, bo'lmasa internet (HuggingFace)"
Write-Host ""
& $py $getter --dest (Join-Path $engine "translate_model") `
    --source (Join-Path $root "translate_model") `
    --source (Join-Path $root "payload\Engine\translate_model") `
    --source (Join-Path (Split-Path -Parent $root) "translate_model") `
    --download $Download
$code = $LASTEXITCODE

Write-Host ""
if ($code -eq 0) {
    Ok "Tayyor. Premiere'da panelni qayta oching -> 'Tarjima (internetsiz)' kartasida tilni tanlang."
} elseif ($code -eq 3) {
    Warn "Model o'rnatilmadi. Caption tarjimasiz ishlayveradi."
} else {
    Bad "Model o'rnatilmadi (yuqoridagi xatoga qarang). Qayta ishga tushirsangiz - yuklash davom etadi."
}
Done $code
