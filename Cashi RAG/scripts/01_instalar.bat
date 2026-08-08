@echo off
chcp 65001 > NUL
echo ============================================================
echo   INSTALACIÓN DE DEPENDENCIAS Y ENTORNOS — VISTA TERRITORIO
echo ============================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

echo [1/3] Verificando instalación de Python...
python --version
if %errorlevel% neq 0 (
    echo [ERROR] Python no está instalado o no se encuentra en el PATH.
    pause
    exit /b 1
)

echo.
echo [2/3] Instalando dependencias de Python desde requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo [3/3] Instalación completada con éxito.
echo ============================================================
pause
