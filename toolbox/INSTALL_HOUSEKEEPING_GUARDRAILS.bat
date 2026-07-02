@echo off
setlocal
set "ROOT=C:\QiLabs\00_QiLabs.workspace\toolbox"
set "SCRIPT=%ROOT%\install_housekeeping_guardrails.ps1"

if not exist "%SCRIPT%" (
  echo Missing installer script:
  echo %SCRIPT%
  echo.
  echo Make sure you unzipped this package directly into:
  echo %ROOT%
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
echo.
pause
