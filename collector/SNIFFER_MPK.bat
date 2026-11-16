@echo off
setlocal
chcp 65001 >nul
echo.
echo Sniffer paczek .mpk (tylko odczyt gry, bez uruchamiania gry).
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sniffer_mpk.ps1" %*
set KOD=%ERRORLEVEL%
echo.
if not "%KOD%"=="0" echo BLAD: skrypt zakonczyl sie kodem %KOD%.
pause
