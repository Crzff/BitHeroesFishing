"""Supervision de hijos y exclusividad. No inicia procesos al importar."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time

from .protocol import Channel
from . import VERSION
from .telemetry import ROOT, run_environment
from .game_window import ENV_WINDOW, WindowGuard, focus_window, window_api


class Mutex:
    def __init__(self, role: str):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}",role):
            raise ValueError("Rol de proceso invalido")
        if os.name!="nt":
            import fcntl
            from pathlib import Path
            directory=Path(os.environ.get("XDG_RUNTIME_DIR",f"/tmp/opencode/bitheroes-{os.getuid()}"))
            directory.mkdir(mode=0o700,parents=True,exist_ok=True)
            if directory.stat().st_uid!=os.getuid():
                raise RuntimeError("El directorio de exclusividad no pertenece al usuario")
            self.handle=os.open(directory/f"bitheroes-{role}.lock",
                                os.O_CREAT|os.O_RDWR|os.O_CLOEXEC|os.O_NOFOLLOW,0o600)
            try:
                fcntl.flock(self.handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError as exc:
                os.close(self.handle)
                self.handle=None
                raise RuntimeError(f"Ya hay otro proceso {role}; no se inicia un duplicado") from exc
            return
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        kernel.CreateMutexW.argtypes=[wintypes.LPVOID,wintypes.BOOL,wintypes.LPCWSTR]
        kernel.CreateMutexW.restype=wintypes.HANDLE
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        self.kernel=kernel
        ctypes.set_last_error(0)
        self.handle=kernel.CreateMutexW(None,False,f"Local\\BitHeroesFishing_AUDIT_{role}")
        if not self.handle:
            raise OSError(ctypes.get_last_error(),"No se pudo crear la exclusion de procesos")
        if ctypes.get_last_error()==183:
            kernel.CloseHandle(self.handle)
            self.handle=None
            raise RuntimeError(f"Ya hay otro proceso {role}; no se inicia un duplicado")

    def close(self):
        if self.handle is not None:
            if os.name=="nt":
                self.kernel.CloseHandle(self.handle)
            else:
                os.close(self.handle)
            self.handle=None


def python_executable():
    # El acceso directo usa pythonw; los motores deben tener consola visible.
    exe=ROOT.__class__(sys.executable)
    console=exe.with_name("python.exe")
    return str(console if exe.name.lower()=="pythonw.exe" and console.exists() else exe)


def minimize_console():
    if os.name!="nt":
        return
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.windll.kernel32
    kernel.GetConsoleWindow.restype=wintypes.HWND
    hwnd=kernel.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
        ctypes.windll.user32.ShowWindow(hwnd,6)


def child_options():
    if os.name!="nt":
        return {"start_new_session":True}
    startup=subprocess.STARTUPINFO()
    startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow=7  # SW_SHOWMINNOACTIVE: no robar el foco del juego.
    return {"creationflags":subprocess.CREATE_NEW_CONSOLE|0x00000200,"startupinfo":startup}


def close_children(processes, channel=None):
    errors=[]
    if channel:
        try:
            channel.stop("LAUNCHER","STOP_REQUESTED")
        except Exception as exc:
            errors.append(repr(exc))
    deadline=time.monotonic()+2
    for p in processes:
        if p is None or p.poll() is not None:
            continue
        try:
            try:
                p.wait(timeout=max(.05,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:
                p.terminate()
                try:
                    p.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=1)
        except Exception as exc:
            errors.append(repr(exc))
    if errors:
        raise RuntimeError("Errores al detener procesos: "+"; ".join(errors))


def start_children(game=None):
    mutex=Mutex("LAUNCHER")
    catch=control=channel=guard=api=None
    try:
        if game is None:
            test_hwnd=os.environ.get("FISHING_TEST_GAME_HWND")
            if test_hwnd:
                api=window_api()
                game=api.inspect(int(test_hwnd))
            else:
                game=focus_window()
        guard=WindowGuard(game,api)
        guard.check()
        env=run_environment()
        env[ENV_WINDOW]=game.serialize()
        channel=Channel(env["FISHING_RUN_ID"])
        options=child_options()
        catch=subprocess.Popen([python_executable(),"-B","-u",str(ROOT/"CATCH_FAST_PROCESS_V6_FINAL.py")],
                               cwd=str(ROOT),env=env,**options)
        deadline=time.monotonic()+5
        while channel.ready() is None:
            if catch.poll() is not None or time.monotonic()>deadline:
                raise RuntimeError("CATCH no termino de inicializar; CONTROL no se inicia")
            time.sleep(.025)
        guard.check()
        control=subprocess.Popen([python_executable(),"-B","-u",str(ROOT/"FISHING_CONTROL_PROCESS.py")],
                                 cwd=str(ROOT),env=env,**options)
        return catch,control,channel,mutex
    except (Exception,KeyboardInterrupt):
        try:
            close_children((catch,control),channel)
        finally:
            mutex.close()
        raise
    finally:
        backend=guard.api if guard is not None else api
        if backend is not None and getattr(backend,"platform",None)=="linux":
            backend.close()


def console_launcher():
    catch=control=channel=mutex=api=None
    try:
        catch,control,channel,mutex=start_children()
        print(f"{VERSION} | sesion {channel.run_id} | F8 o Ctrl+C para detener ambos",flush=True)
        minimize_console()
        while catch.poll() is None and control.poll() is None:
            if api is None:
                api=window_api()
            api.emergency()
            time.sleep(.03)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            close_children((catch,control),channel)
        finally:
            if mutex:
                mutex.close()
            if api is not None and getattr(api,"platform",None)=="linux":
                api.close()
