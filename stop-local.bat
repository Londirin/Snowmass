@echo off
setlocal

echo Stopping Snowmass...
taskkill /FI "WINDOWTITLE eq Snowmass Backend" /T /F >nul 2>nul
taskkill /FI "WINDOWTITLE eq Snowmass Frontend" /T /F >nul 2>nul

echo.
echo Snowmass has been stopped.
echo You can also stop it by closing the two Snowmass command windows.
endlocal
