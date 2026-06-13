@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo        QiOne Desktop Tools Builder
echo ========================================
echo.

python build_QiOne_Tools.py

echo.
echo Builder closed.
pause
