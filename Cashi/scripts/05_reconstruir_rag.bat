@echo off
chcp 65001 > NUL
echo ============================================================
echo   RECONSTRUCCIÓN DE ÍNDICE RAG LOCAL Y CONOCIMIENTO
echo ============================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

python rag/indexer.py

if %errorlevel% neq 0 (
    echo [ERROR] Ocurrió una falla durante la reconstrucción del RAG.
    pause
    exit /b 1
)

echo [OK] Índice RAG reconstruido exitosamente.
pause
