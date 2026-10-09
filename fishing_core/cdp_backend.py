"""Imagen e input del navegador propio por CDP; importar no abre conexiones."""
import os
from pathlib import Path
import tempfile
import uuid
import time

from .accounts import brave_target, account_id
from .brave import Bridge, browser_identity
from .control_flow import SafetyStop
from .telemetry import ROOT


def emergency_source():
    """Punto de extensión para F8 en Windows; nunca habilitar sin una parada disponible."""
    if os.name=='nt':raise SafetyStop('F8 CDP en Windows pendiente de implementación')
    from .linux import LinuxAPI
    return LinuxAPI()


class CdpIO:
    platform='windows' if os.name=='nt' else 'linux'

    def __init__(self,read_only=False):
        self.bridge=None;self.desktop=None;self.frames=None;self.closed=False;self.failed=False
        self.game_guard=self;self.control_mode=False;self.read_only=read_only
        try:
            self.target=brave_target()
            if self.target is None:raise RuntimeError('CDP requiere una cuenta Brave explícita')
            self.account=account_id()
            self.identity=browser_identity(self.target[0],self.target[1],self.account)
            self.identity_checked=time.monotonic()
            self.desktop=emergency_source()
            self.frames=tempfile.TemporaryDirectory(prefix='cdp-',dir=ROOT/'runs')
            self.frames_dir=Path(self.frames.name)/'frames';self.frames_dir.mkdir(mode=0o700)
            self.bridge=Bridge(self.target[1],self.target[2],frames_dir=self.frames_dir)
            self.check()
        except BaseException:
            self.close();raise

    def emergency(self):
        self.desktop.emergency()

    def _call(self,op,**kwargs):
        if self.closed or self.failed:raise SafetyStop('CDP detenido; no se envía input')
        try:
            self.emergency()
            if brave_target()!=self.target:raise RuntimeError('Cambió el endpoint CDP propio')
            if account_id()!=self.account:raise RuntimeError('Cambió la cuenta CDP propia')
            now=time.monotonic()
            if now-self.identity_checked>=2:
                if browser_identity(self.target[0],self.target[1],self.account)!=self.identity:
                    raise RuntimeError('Cambió la identidad del proceso Brave propio')
                self.identity_checked=now
            self.bridge.call(op,**kwargs)
        except (RuntimeError,ValueError,OSError) as exc:
            self.failed=True
            raise SafetyStop(str(exc)) from exc
        except BaseException:
            self.failed=True;raise

    def check(self):self._call('check')
    def check_game(self):self.check()

    def _input(self,op,**kwargs):
        if self.read_only:raise SafetyStop('Modo observación: todo input está bloqueado')
        self._call(op,**kwargs)

    def _move(self,xy,settle=True):self._input('move',xy=xy)
    def click(self,xy):self._input('click',xy=xy)
    def cast_click(self,xy):self.click(xy)
    def check_point(self,xy):self._call('point',xy=xy)
    def wheel(self,steps,xy=(930,600)):self._input('wheel',xy=xy,steps=steps)

    def escape(self):
        self._input('escapeDown')
        self._input('escapeUp')

    def close(self):
        if self.closed:return
        self.closed=True
        try:
            if self.bridge is not None:self.bridge.close()
        finally:
            try:
                if self.desktop is not None:self.desktop.close()
            finally:
                if self.frames is not None:self.frames.cleanup()


class CdpCapture:
    def __init__(self,guard):self.guard=guard;self.closed=False
    def __enter__(self):return self
    def __exit__(self,*args):self.close();return False
    def close(self):self.closed=True

    def grab(self,monitor):
        from PIL import Image
        from mss.screenshot import ScreenShot
        destination=None
        try:
            if self.closed:raise RuntimeError('Captura CDP cerrada')
            x,y,w,h=(monitor[k] for k in ('left','top','width','height'))
            if any(type(n) is not int for n in (x,y,w,h)) or x<0 or y<0 or w<=0 or h<=0 or x+w>1920 or y+h>1080:
                raise RuntimeError('Región de captura fuera del juego')
            name=uuid.uuid4().hex+'.png';destination=self.guard.frames_dir/name
            self.guard._call('frame',path=name)
            with Image.open(destination) as image:
                if image.format!='PNG' or image.size!=(1920,1080):raise RuntimeError('Fotograma CDP incorrecto')
                raw=image.convert('RGBA').crop((x,y,x+w,y+h)).tobytes('raw','BGRA')
            self.guard.check()
            return ScreenShot(bytearray(raw),monitor)
        except KeyboardInterrupt:raise
        except Exception as exc:
            self.guard.failed=True
            raise SafetyStop('No se puede capturar CDP: '+str(exc)) from exc
        finally:
            if destination is not None:destination.unlink(missing_ok=True)
