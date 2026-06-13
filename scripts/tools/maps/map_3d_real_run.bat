@echo off
echo 🚀 Starting 3D Mind Map with Real Directory Walking...
echo.

REM Check if path argument provided
if "%1"=="" (
    echo 📁 No directory specified, using client-workspace
    set "TARGET_PATH=../client-workspace"
) else (
    set "TARGET_PATH=%1"
)

echo 🎯 Target directory: %TARGET_PATH%
echo.

REM Start the directory walker server
python directory_walker.py "%TARGET_PATH%" -p 8000

echo.
echo ✅ 3D Mind Map server stopped
pause
