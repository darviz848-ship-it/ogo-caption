# OgoCaption - o'chirish
$ErrorActionPreference = "Continue"
Write-Host ""
Write-Host "  === OgoCaption o'chirish ===" -ForegroundColor Cyan
Write-Host ""

$docs = [Environment]::GetFolderPath("MyDocuments")
$dest = Join-Path $docs "OgoCaption"
$cep  = Join-Path $env:APPDATA "Adobe\CEP\extensions\OgoCaption"

Write-Host "  Quyidagilar o'chiriladi:" -ForegroundColor Yellow
Write-Host "    $cep"
Write-Host "    $dest   (AI modellar bilan birga: ~1.9 GB, tarjima modeli bo'lsa +2.95 GB)"
Write-Host ""
$a = Read-Host "  Davom etamizmi? (ha/yo'q)"
if ($a -ne "ha" -and $a -ne "h" -and $a -ne "y") { Write-Host "  Bekor qilindi."; Read-Host "Enter"; exit }

$ppro = Get-Process -Name "Adobe Premiere Pro" -ErrorAction SilentlyContinue
if ($ppro) { Write-Host "  [!] Premiere Pro ochiq - avval yoping." -ForegroundColor Yellow; Read-Host "Yopgach Enter bosing" }

foreach ($p in @($cep, $dest)) {
    if (Test-Path $p) {
        try {
            Remove-Item -Path $p -Recurse -Force
            Write-Host "  [OK]  o'chirildi: $p" -ForegroundColor Green
        } catch {
            Write-Host "  [XATO] o'chmadi: $p" -ForegroundColor Red
            Write-Host "         $($_.Exception.Message)" -ForegroundColor DarkGray
        }
    } else {
        Write-Host "  [ - ] yo'q edi: $p" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "  Eslatma: HKCU\Software\Adobe\CSXS.* dagi PlayerDebugMode tegilmadi" -ForegroundColor DarkGray
Write-Host "  (boshqa CEP panellar uchun kerak bo'lishi mumkin)." -ForegroundColor DarkGray
Write-Host ""
Read-Host "Yopish uchun Enter bosing"
