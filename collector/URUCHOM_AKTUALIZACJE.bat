@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
title Where Winds Meet - zbieranie aktualizacji
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
echo ===============================================
echo WHERE WINDS MEET - ZBIERANIE AKTUALIZACJI
echo ===============================================
echo.
echo Zamknij gre i poczekaj na koniec aktualizacji Steam.
echo Program sprawdza stan juz wyslanych plikow po SHA-256 (LocalData\Patch
echo oraz Package: data*, index*, MANIFEST, zh_cn/en) z pominieciem blacklisty.
echo Pakuje tylko nowe lub zmienione pliki: jeden ZIP do 90 MiB albo
echo automatycznie kilka czesci po ok. 85 MiB przy duzej aktualizacji.
echo Nic nie zmienia w grze i nie wysyla nic sam.
echo.
if not exist "%PS%" goto no_powershell
"%PS%" -NoLogo -NoProfile -Command "Get-ChildItem -LiteralPath '%~dp0' -Filter *.ps1 -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue" 2>nul
"%PS%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0zbierz.ps1" -Tryb aktualizacja %*
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" goto done
if "%RESULT%"=="2" goto partial
echo BLAD. Przeczytaj komunikat powyzej i napisz mi, co sie pojawilo.
goto finish
:partial
echo UWAGA: ZIP powstal, ale zbieranie bylo niepelne. Wyslij go mimo to.
goto finish
:done
echo GOTOWE. Wgraj ZIP pokazany powyzej na Dysk Google.
goto finish
:no_powershell
set "RESULT=1"
echo BLAD: nie znaleziono Windows PowerShell. Napisz mi o tym.
:finish
echo.
pause
exit /b %RESULT%
