@echo off
echo.
set /p folderPath=Enter full folder path to unblock: 

if not exist "%folderPath%" (
    echo.
    echo Folder does not exist.
    pause
    exit /b
)

echo.
echo Unblocking all files in:
echo %folderPath%
echo.

powershell -Command "Get-ChildItem -Path '%folderPath%' -Recurse -Force | Unblock-File"

echo.
echo Done.
pause