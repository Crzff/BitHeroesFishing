@echo off
rem Suite de pruebas segura: un archivo por proceso, con tope de RAM (no congela el equipo).
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\comprobar_tests.ps1" %*
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
