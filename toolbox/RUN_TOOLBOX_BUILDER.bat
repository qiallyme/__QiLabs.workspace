@echo off
setlocal
cd /d "%~dp0"

if not exist "%~dp0_toolbox_maintenance\interactive_toolbox_maintenance.ps1" (
  echo.
  echo [ERROR] Missing _toolbox_maintenance\interactive_toolbox_maintenance.ps1
  echo Unzip the maintenance kit directly into C:\QiLabs\00_QiLabs.workspace\toolbox
  echo.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_toolbox_maintenance\interactive_toolbox_maintenance.ps1"

echo.
pause
