@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Primero ejecuta INSTALAR.bat. Necesitas Python 3.13 de 64 bits.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -B FISHING_BOT_APP.py
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
    echo El panel termino con un error. Revisa el mensaje anterior.
    pause
)
exit /b %RESULT%
