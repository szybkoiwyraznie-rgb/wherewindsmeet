@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
title Where Winds Meet - zbieranie danych
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
echo ===============================================
echo WHERE WINDS MEET - ZBIERANIE DANYCH
echo ===============================================
echo.
echo Zamknij gre i poczekaj na koniec aktualizacji Steam.
echo Program nic nie zmienia w grze i nie wysyla nic sam.
echo.
if not exist "%PS%" goto no_powershell
"%PS%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0zbierz.ps1" %*
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
