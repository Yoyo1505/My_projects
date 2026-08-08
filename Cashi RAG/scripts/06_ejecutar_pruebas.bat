@echo off
chcp 65001 > NUL
echo ============================================================
echo   SUITE DE PRUEBAS DE CALIDAD E INTEGRIDAD
echo ============================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

echo [1/2] Ejecutando Smoke Test raíz...
python _test_smoke.py

echo.
echo [2/2] Ejecutando suite de pruebas en tests/ ...
python -m unittest discover -s tests -p "*.py"

echo ============================================================
echo Pruebas finalizadas.
pause
