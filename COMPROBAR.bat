@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Primero ejecuta INSTALAR.bat.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -B scripts\comprobar.py
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
