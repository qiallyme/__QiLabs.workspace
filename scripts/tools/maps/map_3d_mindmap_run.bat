@echo off
echo 🚀 Generating 3D Mind Map for Directory Structure...
echo.

REM Generate directory structure data from client-workspace folder
python generate_3d_data.py ../client-workspace -o directory_structure.json

if %ERRORLEVEL% NEQ 0 (
    echo ❌ Error generating directory data
    pause
    exit /b 1
)

echo.
echo 🎯 Opening 3D Mind Map in browser...
start 3d_mindmap_dynamic.html

echo.
echo ✅ 3D Mind Map launched!
echo    - Use mouse to rotate, zoom, and pan
echo    - Click nodes to select them
echo    - Use controls panel to change layout and settings
echo    - Search for specific files/folders
echo.
pause
