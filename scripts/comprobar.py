"""Diagnostico sin abrir MSS, motores, navegador ni enviar clics."""

import importlib
import json
from importlib import metadata
import os
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = {"mss": "mss", "numpy": "numpy", "opencv-python": "cv2",
            "customtkinter": "customtkinter", "Pillow": "PIL"}


def main():
    failed = False
    python_ok = os.name == "nt" and sys.version_info[:2] == (3, 13) and struct.calcsize("P") == 8
    print(f"{'OK' if python_ok else 'ERROR'} Python {sys.version.split()[0]} / {struct.calcsize('P') * 8} bits / {sys.platform}")
    failed |= not python_ok
    for package, module in PACKAGES.items():
        try:
            importlib.import_module(module)
            print(f"OK {package} {metadata.version(package)}")
        except Exception as exc:
            print(f"ERROR {package}: {exc}")
            failed = True
    try:
        import tkinter
        print(f"OK Tcl/Tk {tkinter.TkVersion}")
    except ImportError:
        print("ERROR falta Tcl/Tk")
        failed = True
    try:
        import numpy as np
        for name in ("bait_templates.npz", "cast_digits.npz", "ui_templates.npz"):
            with np.load(ROOT / "assets" / name, allow_pickle=False) as data:
                if not data.files:
                    raise ValueError(f"Plantillas vacias: {name}")
                for key in data.files:
                    if data[key].dtype != np.uint8 or data[key].size == 0:
                        raise ValueError(f"Plantilla invalida: {name}/{key}")
            print(f"OK plantillas {name}")
    except Exception as exc:
        print(f"ERROR plantillas: {exc}")
        failed = True
    if os.name == "nt":
        import ctypes
        user = ctypes.windll.user32
        user.SetProcessDPIAware()
        resolution = (user.GetSystemMetrics(0), user.GetSystemMetrics(1))
        ok = resolution == (1920, 1080)
        print(f"{'OK' if ok else 'ERROR'} pantalla principal {resolution[0]}x{resolution[1]}; se requiere 1920x1080")
        failed |= not ok
        try:
            sys.path.insert(0,str(ROOT))
            from fishing_core.game_window import WindowsAPI
            windows=WindowsAPI().windows()
            print('INFO clientes detectados (sin enfocar): '+(', '.join(w.client for w in windows) or 'ninguno'))
        except Exception as exc:
            print(f'AVISO no se pudo enumerar el juego: {exc}')
    for name in ("FISHING_BOT_APP.py", "CATCH_FAST_PROCESS_V6_FINAL.py", "FISHING_CONTROL_PROCESS.py"):
        ok = (ROOT / name).is_file()
        print(f"{'OK' if ok else 'ERROR'} archivo {name}")
        failed |= not ok
    try:
        settings=json.loads((ROOT/'fishing_runtime_config.json').read_text(encoding='utf-8'))
        limit=settings.get('max_ciclos_por_sesion') if isinstance(settings,dict) else None
        if type(limit) is not int or not 0<=limit<=10000:
            raise ValueError('max_ciclos_por_sesion debe ser entero entre 0 y 10000')
        print(f'OK configuracion de ciclos: {limit} (0 significa sin limite)')
    except (OSError, ValueError) as exc:
        print(f'ERROR configuracion de ciclos: {exc}')
        failed=True
    print("Sin captura de pantalla, sin motores y sin inputs.")
    print("La comprobacion no valida zoom, escala, posicion del juego ni garantiza capturas.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
