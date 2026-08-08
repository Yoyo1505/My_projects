@echo off
chcp 65001 > NUL
echo ============================================================
echo   VALIDACIÓN DE ENTORNOS Y DEPENDENCIAS
echo ============================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

python -c "import polars, duckdb, pyarrow, streamlit, plotly, pandas; print('[OK] Todas las bibliotecas clave importadas correctamente.')"
if %errorlevel% neq 0 (
    echo [ERROR] Faltan dependencias clave. Ejecute 01_instalar.bat primero.
    pause
    exit /b 1
)

echo [OK] El entorno está correctamente configurado.
pause
