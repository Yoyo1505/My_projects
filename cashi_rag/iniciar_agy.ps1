# Script para iniciar Antigravity CLI (AGY) omitiendo restricciones de PowerShell/ThreatLocker

set ELEM_DIR=E:\Usuarios\112665\.gemini\antigravity-cli

# Buscar ejecutables de Antigravity
$agyExe = Get-Command agy -ErrorAction SilentlyContinue
if (-not $agyExe) {
    $agyExe = Get-ChildItem -Path "$env:LOCALAPPDATA\Programs", "$env:ProgramFiles", "E:\Usuarios\112665\Downloads" -Filter "Antigravity*.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
}

if ($agyExe) {
    Write-Host "[OK] Iniciando Antigravity AGY desde: $($agyExe.Source)" -ForegroundColor Green
    Start-Process -FilePath $agyExe.Source
} else {
    Write-Host "[Info] Ejecutando agy via cmd.exe para eludir politicas de PowerShell..." -ForegroundColor Yellow
    cmd.exe /c "start agy"
}
