@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
title Where Winds Meet - pakowanie duzych danych
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
echo ===============================================
echo WHERE WINDS MEET - DUZE DANE / DUZA AKTUALIZACJA
echo ===============================================
echo.
echo Zamknij gre i poczekaj na koniec aktualizacji Steam.
echo Program kopiuje pliki danych gry (data*, index*, MANIFEST, mapy)
echo i dzieli wynik na czesci po ok. 85 MiB na Pulpicie.
echo Nic nie zmienia w grze i nie wysyla nic sam.
echo.
if not exist "%PS%" goto no_powershell
"%PS%" -NoLogo -NoProfile -Command "Get-ChildItem -LiteralPath '%~dp0' -Filter *.ps1 -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue" 2>nul
"%PS%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0spakuj_dane.ps1" %*
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" goto done
echo BLAD. Przeczytaj komunikat powyzej i napisz mi, co sie pojawilo.
goto finish
:done
echo GOTOWE. Wgraj wygenerowane archiwa ZIP z Pulpitu na Dysk Google.
goto finish
:no_powershell
set "RESULT=1"
echo BLAD: nie znaleziono Windows PowerShell. Napisz mi o tym.
:finish
echo.
pause
exit /b %RESULT%
