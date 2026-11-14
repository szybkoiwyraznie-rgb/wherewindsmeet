@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
title Where Winds Meet - instalacja latki
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
echo ===============================================
echo WHERE WINDS MEET - INSTALACJA LATKI
echo ===============================================
echo.
if not exist "%PS%" goto no_powershell
"%PS%" -NoLogo -NoProfile -Command "Get-ChildItem -LiteralPath '%~dp0' -Filter *.ps1 -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue" 2>nul
"%PS%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0instaluj_latke.ps1" -Akcja instaluj %*
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" goto done
echo BLAD. Przeczytaj komunikat powyzej. Zadna czesciowa zmiana nie zostala pozostawiona.
goto finish
:done
echo GOTOWE. Latka zainstalowana, kopia oryginalow zapisana.
goto finish
:no_powershell
set "RESULT=1"
echo BLAD: nie znaleziono Windows PowerShell.
:finish
echo.
pause
exit /b %RESULT%
