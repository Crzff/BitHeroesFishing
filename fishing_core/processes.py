"""Supervision de hijos y exclusividad. No inicia procesos al importar."""

from __future__ import annotations

import os
import subprocess
import sys
import time

from .protocol import Channel
from . import VERSION
from .telemetry import ROOT, run_environment


class Mutex:
    def __init__(self, role: str):
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
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle=None


def python_executable():
    # El acceso directo usa pythonw; los motores deben tener consola visible.
    exe=ROOT.__class__(sys.executable)
    console=exe.with_name("python.exe")
    return str(console if exe.name.lower()=="pythonw.exe" and console.exists() else exe)


def minimize_console():
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.windll.kernel32
    kernel.GetConsoleWindow.restype=wintypes.HWND
    hwnd=kernel.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
        ctypes.windll.user32.ShowWindow(hwnd,6)


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


def start_children():
    mutex=Mutex("LAUNCHER")
    env=run_environment()
    channel=Channel(env["FISHING_RUN_ID"])
    catch=control=None
    try:
        flags=subprocess.CREATE_NEW_CONSOLE | 0x00000200
        catch=subprocess.Popen([python_executable(),"-B","-u",str(ROOT/"CATCH_FAST_PROCESS_V6_FINAL.py")],
                               cwd=str(ROOT),env=env,creationflags=flags)
        deadline=time.monotonic()+5
        while channel.ready() is None:
            if catch.poll() is not None or time.monotonic()>deadline:
                raise RuntimeError("CATCH no termino de inicializar; CONTROL no se inicia")
            time.sleep(.025)
        control=subprocess.Popen([python_executable(),"-B","-u",str(ROOT/"FISHING_CONTROL_PROCESS.py")],
                                 cwd=str(ROOT),env=env,creationflags=flags)
        return catch,control,channel,mutex
    except Exception:
        try:
            close_children((catch,control),channel)
        finally:
            mutex.close()
        raise


def console_launcher():
    import ctypes
    catch=control=channel=mutex=None
    try:
        catch,control,channel,mutex=start_children()
        print(f"{VERSION} | sesion {channel.run_id} | F8 o Ctrl+C para detener ambos",flush=True)
        minimize_console()
        while catch.poll() is None and control.poll() is None:
            if ctypes.windll.user32.GetAsyncKeyState(0x77)&0x8000:
                break
            time.sleep(.03)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            close_children((catch,control),channel)
        finally:
            if mutex:
                mutex.close()
