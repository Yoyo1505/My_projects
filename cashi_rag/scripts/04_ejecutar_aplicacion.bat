@echo off
chcp 65001 > NUL
echo ============================================================
echo   INICIANDO DASHBOARD VISTA TERRITORIO (STREAMLIT)
echo ============================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

echo Lanzando Streamlit en puerto 8503...
python -m streamlit run app.py --server.port 8503

pause
