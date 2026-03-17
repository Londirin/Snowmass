@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON_EXE=%ROOT%backend\.python\python.exe"

if not exist "%PYTHON_EXE%" (
  echo Snowmass cannot start because %PYTHON_EXE% is missing.
  echo Please ask Codex to rebuild the local Python runtime, or install Python 3.11 and update the start script.
  pause
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo Snowmass cannot start because Node.js is not installed or not on PATH.
  echo Install Node.js, then run this file again.
  pause
  exit /b 1
)

echo Starting Snowmass backend...
start "Snowmass Backend" cmd /k "cd /d "%ROOT%backend" && "%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Starting Snowmass frontend...
start "Snowmass Frontend" cmd /k "cd /d "%ROOT%frontend" && node server.js"

echo Waiting a moment for the app to start...
powershell -NoProfile -Command "Start-Sleep -Seconds 3"

start "" http://127.0.0.1:3000

echo.
echo Snowmass should now be opening in your browser.
echo If the page does not appear yet, wait a few seconds and refresh.
endlocal
