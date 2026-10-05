"""Backend gamescope: el juego corre en una pantalla virtual y el usuario puede usar otras ventanas.

- Imagen: el nodo PipeWire "gamescope" (1920x1080) mediante un gst-launch persistente que
  escribe fotogramas BGR crudos; siempre se devuelve el más reciente, nunca uno viejo.
- Input: XTest sobre el servidor X propio de gamescope (no mueve el cursor del usuario).
- Guarda: la ventana "Bit Heroes" debe seguir en ese servidor; F8 sigue mirándose en el
  escritorio del usuario (niri) mediante LinuxAPI.emergency.

Uso: lanzar el juego con `gamescope --backend headless -w 1920 -h 1080 -W 1920 -H 1080 --
steam ...` y exportar FARM_BACKEND=gamescope.
"""

from __future__ import annotations

import os
import select
import subprocess
import threading
import time

import numpy as np

from .control_flow import SafetyStop

W,H=1920,1080
FRAME=W*H*3
GAME_TITLE='Bit Heroes'


def pipewire_serial(name='gamescope'):
    """object.serial del nodo de vídeo de gamescope en PipeWire."""
    out=subprocess.run(['pw-cli','ls','Node'],capture_output=True,text=True,timeout=10).stdout
    block={}
    for line in out.splitlines()+['id end']:
        line=line.strip()
        if line.startswith('id '):
            if block.get('node.name')==f'"{name}"' and block.get('media.class')=='"Video/Source"':return block['object.serial'].strip('"')
            block={}
        elif ' = ' in line:
            k,v=line.split(' = ',1);block[k]=v
    raise RuntimeError('No hay nodo de vídeo de gamescope en PipeWire; ¿se lanzó el juego con gamescope?')


def find_display(title=GAME_TITLE):
    """Servidor X de gamescope que contiene la ventana del juego."""
    from Xlib import display
    for entry in sorted(os.listdir('/tmp/.X11-unix')):
        name=':'+entry.lstrip('X')
        try:
            d=display.Display(name)
        except Exception:
            continue
        if window_of(d,title) is not None:return d
        d.close()
    raise RuntimeError('No se encontró la ventana de Bit Heroes en ningún servidor X de gamescope')


def window_of(d,title=GAME_TITLE):
    def walk(w):
        for c in w.query_tree().children:
            try:
                if c.get_wm_name()==title and c.get_geometry().width==W:return c
            except Exception:
                pass
            found=walk(c)
            if found is not None:return found
        return None
    return walk(d.screen().root)


class PipeWireFrames:
    """Lee el flujo crudo en un hilo y conserva solo el último fotograma completo."""
    def __init__(self,serial):
        self.proc=subprocess.Popen(['gst-launch-1.0','-q','pipewiresrc',f'target-object={serial}','always-copy=true','!',
                                    'videoconvert','!','video/x-raw,format=BGR,width=1920,height=1080','!','fdsink','fd=1'],
                                   stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0)
        self.lock=threading.Lock();self.latest=None;self.stamp=0.0;self.error=None
        self.thread=threading.Thread(target=self.pump,daemon=True);self.thread.start()

    def pump(self):
        buf=bytearray()
        try:
            while True:
                chunk=self.proc.stdout.read(FRAME-len(buf))
                if not chunk:break
                buf+=chunk
                if len(buf)==FRAME:
                    with self.lock:self.latest=bytes(buf);self.stamp=time.monotonic()
                    buf=bytearray()
        except Exception as exc:
            self.error=exc

    def frame(self,newer_than,timeout=2.0):
        """Fotograma recibido después de newer_than; nunca reutiliza uno anterior."""
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            with self.lock:
                if self.latest is not None and self.stamp>newer_than:
                    return np.frombuffer(self.latest,np.uint8).reshape(H,W,3)
            if self.proc.poll() is not None:raise RuntimeError('El flujo de gamescope se cerró')
            time.sleep(.01)
        raise RuntimeError('gamescope no entregó un fotograma nuevo')

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:self.proc.wait(2)
            except subprocess.TimeoutExpired:self.proc.kill()


class GamescopeGuard:
    """Equivalente a WindowGuard: el juego sigue en su servidor X de gamescope. F8 en el escritorio."""
    def __init__(self):
        from .linux import LinuxAPI
        self.display=find_display();self.window=window_of(self.display)
        self.desktop=LinuxAPI()  # solo para F8 (estado del teclado del usuario)

    def check(self):
        try:
            if window_of(self.display) is None:raise RuntimeError('La ventana de Bit Heroes desapareció de gamescope')
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f'gamescope no responde: {exc}') from exc

    def close(self):
        try:self.display.close()
        finally:self.desktop.close()


class GamescopeIO:
    """Misma interfaz que LinuxIO (click, _move, escape, emergency, check_game) sobre gamescope."""
    platform='linux'

    def __init__(self):
        self.game_guard=GamescopeGuard();self.control_mode=False
        self.check_game()

    def emergency(self):
        self.game_guard.desktop.emergency()

    def check_game(self):
        try:self.game_guard.check()
        except RuntimeError as exc:raise SafetyStop(str(exc)) from exc

    def _move(self,xy,settle=True):
        from Xlib import X
        from Xlib.ext import xtest
        if len(xy)!=2 or any(type(n) is not int for n in xy) or not (0<=xy[0]<W and 0<=xy[1]<H):
            raise SafetyStop('Coordenadas fuera de la pantalla de gamescope')
        self.emergency();self.check_game()
        d=self.game_guard.display;xtest.fake_input(d,X.MotionNotify,x=xy[0],y=xy[1]);d.sync()
        if settle and self.control_mode:time.sleep(.08)
        self.emergency();self.check_game()

    def click(self,xy):
        from Xlib import X
        from Xlib.ext import xtest
        self._move(xy);d=self.game_guard.display
        try:
            xtest.fake_input(d,X.ButtonPress,1);d.sync()
            if self.control_mode:time.sleep(.06)
        finally:
            xtest.fake_input(d,X.ButtonRelease,1);d.sync()

    def cast_click(self,xy):
        self.click(xy)

    def escape(self):
        from Xlib import X
        from Xlib.ext import xtest
        self.emergency();self.check_game();d=self.game_guard.display;key=d.keysym_to_keycode(0xff1b)
        if not key:raise SafetyStop('Escape no disponible en gamescope')
        try:
            xtest.fake_input(d,X.KeyPress,key);d.sync();time.sleep(.06)
            self.emergency();self.check_game()
        finally:
            xtest.fake_input(d,X.KeyRelease,key);d.sync()

    def wheel(self,steps,xy=(930,600)):
        from Xlib import X
        from Xlib.ext import xtest
        self._move(xy);d=self.game_guard.display
        for _ in range(abs(steps)):
            self.emergency();self.check_game();button=5 if steps>0 else 4
            xtest.fake_input(d,X.ButtonPress,button);xtest.fake_input(d,X.ButtonRelease,button);d.sync();time.sleep(.05)

    def close(self):
        self.game_guard.close()


class GamescopeCapture:
    """Misma interfaz que LinuxCapture: grab(monitor) devuelve un ScreenShot BGRA del recorte pedido."""
    def __init__(self,guard):
        self.guard=guard;self.frames=PipeWireFrames(pipewire_serial())

    def __enter__(self):
        return self

    def __exit__(self,*args):
        self.close();return False

    def close(self):
        self.frames.close()

    def grab(self,monitor):
        from mss.screenshot import ScreenShot
        try:
            self.guard.check()
            x,y,w,h=(monitor[k] for k in ('left','top','width','height'))
            if any(type(n) is not int for n in (x,y,w,h)) or x<0 or y<0 or w<=0 or h<=0 or x+w>W or y+h>H:
                raise RuntimeError('Región de captura fuera del juego')
            frame=self.frames.frame(time.monotonic()-0.0)[y:y+h,x:x+w]
            bgra=np.dstack([frame,np.full(frame.shape[:2],255,np.uint8)])
            return ScreenShot(bytearray(bgra.tobytes()),monitor)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            raise SafetyStop('No se puede capturar gamescope: '+str(exc)) from exc


def backend():
    """(IO, Capture) según FARM_BACKEND: 'gamescope' o el escritorio niri por defecto."""
    if os.environ.get('FARM_BACKEND')=='gamescope':return GamescopeIO,GamescopeCapture
    from .linux import LinuxIO,LinuxCapture
    return LinuxIO,LinuxCapture
