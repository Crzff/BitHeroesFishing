@echo off
setlocal
cd /d "%~dp0"
echo Bit Heroes Fishing Bot - instalar dependencias
echo Necesita Python 3.13 de 64 bits. No inicia pesca.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -B scripts\instalar.py
) else (
    py -3.13 -B scripts\instalar.py
)
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Instalacion incompleta. Revisa el error anterior y docs\INSTALACION.md.
pause
exit /b %RESULT%
