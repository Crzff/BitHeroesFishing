"""Instalador local: no importa motores, no captura pantalla y no envia input."""

import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    if os.name != "nt" or sys.version_info[:2] != (3, 13) or struct.calcsize("P") != 8:
        print("Se necesita Windows y Python 3.13 de 64 bits, con Tcl/Tk y pip.")
        return 1
    try:
        import tkinter  # Solo verifica disponibilidad; no abre una ventana.
    except ImportError:
        print("Falta Tcl/Tk. Modifica la instalacion de Python para incluirlo.")
        return 1
    environment = ROOT / ".venv"
    python = environment / "Scripts/python.exe"
    try:
        if not python.exists():
            if environment.exists():
                print(".venv existe pero esta incompleto. No se sobrescribe; revisalo o usa una carpeta nueva.")
                return 1
            subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")],
                       cwd=ROOT, check=True)
        subprocess.run([str(python), "-m", "pip", "check"], cwd=ROOT, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"No se completo la instalacion: {exc}")
        return 1
    print("Instalacion completada. Ejecuta COMPROBAR.bat y despues ABRIR_BOT.bat.")
    print("Abrir el panel no inicia pesca: INICIAR BOT es una accion separada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
