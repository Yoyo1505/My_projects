@echo off
chcp 65001 > NUL
echo ============================================================
echo   ACTUALIZACIÓN Y REBUILD DE AGREGADOS DE DATOS
echo ============================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

echo Ejecutando pipeline ETL de datos...
python build_data.py --resume --aggs-only

if %errorlevel% neq 0 (
    echo [ERROR] Ocurrió una falla durante la generación de agregados.
    pause
    exit /b 1
)

echo [OK] Agregados actualizados correctamente.
pause
