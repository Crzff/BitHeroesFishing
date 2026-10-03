"""Steam en niri/XWayland. Importar este modulo no captura ni envia input."""

from __future__ import annotations

import os
import ctypes
import json
from pathlib import Path
import socket
import sys
import time

from .control_flow import SafetyStop
from .game_window import ENV_WINDOW, GameWindow, WindowGuard

# Escape enviado ~0,6 s tras pedir foco se perdio; con 1,5 s estable funciono.
# ponytail: umbral fijo observado, medir mas sesiones si vuelve a perderse.
FOCUS_SETTLE=1.0


class Niri:
    def request(self,request):
        # Protocolo oficial: una peticion JSON y una respuesta por linea.
        # https://github.com/YaLTeR/niri/blob/main/niri-ipc/src/lib.rs
        path=os.environ.get("NIRI_SOCKET")
        if not path:
            raise RuntimeError("Esta adaptacion Linux requiere una sesion niri")
        try:
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
                connection.settimeout(.5)
                connection.connect(path)
                connection.sendall(json.dumps(request).encode()+b"\n")
                with connection.makefile("rb") as stream:
                    reply=json.loads(stream.readline(1_048_576))
            if "Err" in reply:
                raise RuntimeError("niri rechazo la peticion: "+str(reply["Err"]))
            result=reply["Ok"]
            return result[request] if isinstance(request,str) else result
        except (OSError,ValueError,KeyError,TypeError) as exc:
            raise RuntimeError("No se puede confirmar el estado de niri; no se envia input") from exc


class WaylandPointer:
    def __init__(self):
        library=Path(sys.prefix)/"lib"/"bitheroes-pointer.so"
        if not library.is_file():
            raise RuntimeError("Falta el adaptador Wayland; ejecuta INSTALAR.sh")
        self.lib=ctypes.CDLL(str(library),use_errno=True)
        self.lib.fishing_pointer_open.restype=ctypes.c_void_p
        self.lib.fishing_pointer_move.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint]
        self.lib.fishing_pointer_button.argtypes=[ctypes.c_void_p,ctypes.c_int]
        self.lib.fishing_pointer_close.argtypes=[ctypes.c_void_p]
        self.handle=self.lib.fishing_pointer_open()
        if not self.handle:
            raise RuntimeError("niri no permite abrir el puntero virtual Wayland")

    def move(self,x,y):
        if self.lib.fishing_pointer_move(self.handle,x,y)<0:
            raise SafetyStop("Wayland rechazo el movimiento del puntero")

    def button(self,pressed):
        if self.lib.fishing_pointer_button(self.handle,int(pressed))<0:
            raise SafetyStop("Wayland rechazo el evento de boton")

    def close(self):
        if self.handle:
            self.lib.fishing_pointer_close(self.handle)
            self.handle=None


class LinuxAPI:
    platform="linux"

    def __init__(self):
        from Xlib import X, display
        if not os.environ.get("NIRI_SOCKET") or not os.environ.get("DISPLAY"):
            raise RuntimeError("Steam Linux requiere niri y XWayland en esta adaptacion")
        self.X=X
        self.display=display.Display()
        self.niri=Niri()
        self.f8=self.display.keysym_to_keycode(0xffc5)
        if not self.f8:
            self.close()
            raise RuntimeError("XWayland no permite comprobar F8")

    def screen(self):
        outputs=[o for o in self.niri.request("Outputs").values() if o.get("logical")]
        if len(outputs)!=1:
            raise RuntimeError("Linux requiere un solo monitor activo para esta disposicion")
        output=outputs[0]
        logical=output["logical"]
        if tuple(logical.get(k) for k in ("x","y","width","height","scale","transform"))!=(0,0,1920,1080,1.0,"Normal"):
            raise RuntimeError("Linux requiere 1920x1080, escala 1 y orientacion normal")
        mode=output["modes"][output["current_mode"]]
        if (mode["width"],mode["height"])!=(1920,1080):
            raise RuntimeError("El modo fisico del monitor no es 1920x1080")
        return 1920,1080

    def emergency(self):
        keys=self.display.query_keymap()
        if keys[self.f8//8] & (1<<(self.f8%8)):
            raise KeyboardInterrupt("F8")

    def _window(self,xid):
        return self.display.create_resource_object("window",xid)

    def inspect(self,xid):
        try:
            window=self._window(xid)
            title=window.get_wm_name()
            classes=window.get_wm_class()
            prop=window.get_full_property(self.display.intern_atom("_NET_WM_PID"),self.X.AnyPropertyType)
            if (title!="Bit Heroes" or not classes or "steam_app_666860" not in classes
                    or prop is None or len(prop.value)!=1
                    or window.get_attributes().map_state!=self.X.IsViewable):
                raise RuntimeError("La ventana XWayland no es Bit Heroes de Steam visible")
            pid=int(prop.value[0])
            if pid<=0 or Path(f"/proc/{pid}/comm").read_text().strip()!="Bit Heroes.exe":
                raise RuntimeError("No se confirma el proceso de Bit Heroes")
            matches=[w for w in self.niri.request("Windows")
                     if w.get("app_id")=="steam_app_666860" and w.get("title")=="Bit Heroes"]
            if len(matches)!=1:
                raise RuntimeError("No se identifica una sola ventana Steam en niri; cierra duplicadas")
            geometry=window.get_geometry()
            return GameWindow(xid,pid,"Steam",(geometry.x,geometry.y,
                              geometry.x+geometry.width,geometry.y+geometry.height),matches[0]["id"])
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("No se puede confirmar la identidad de la ventana Steam") from exc

    def windows(self):
        result=[]
        for window in self.display.screen().root.query_tree().children:
            try:
                if window.get_wm_name()=="Bit Heroes":
                    result.append(self.inspect(window.id))
            except RuntimeError:
                continue
        return result

    def activate(self,xid):
        self.emergency()
        game=self.inspect(xid)
        self.niri.request({"Action":{"FocusWindow":{"id":game.compositor_id}}})
        deadline=time.monotonic()+3
        stable_since=None
        while True:
            self.emergency()
            try:
                self.check_window(game)
                # El foco llega antes que el final de la animacion y Wine/Unity
                # puede perder la primera tecla: contar foco continuo confirmado.
                now=time.monotonic()
                if stable_since is None:
                    stable_since=now
                if now-stable_since>=FOCUS_SETTLE:
                    return
            except RuntimeError:
                stable_since=None
                if time.monotonic()>=deadline:
                    raise
            if time.monotonic()>=deadline:
                raise RuntimeError("Steam no mantuvo el foco estable; no se envia input")
            time.sleep(.02)

    def check_window(self,game):
        if game.client!="Steam" or game.compositor_id is None or self.inspect(game.hwnd)!=game:
            raise RuntimeError("Cambio la identidad o geometria del juego en Linux")
        self.screen()
        if self.niri.request("OverviewState").get("is_open") is not False:
            raise RuntimeError("La vista general de niri esta abierta; no se envia input")
        validate_niri_window(self.niri.request("FocusedWindow"),game)
        focus=self.display.get_input_focus().focus
        if getattr(focus,"id",None)!=game.hwnd:
            raise RuntimeError("XWayland no confirma el foco de Steam; no se envia input")
        self.game=game

    def cursor(self):
        pointer=self.display.screen().root.query_pointer()
        if getattr(pointer.child,"id",None)!=self.game.hwnd:
            raise RuntimeError("El cursor no apunta a Steam; no se hace clic sobre otra ventana")
        return pointer.root_x,pointer.root_y

    def close(self):
        if self.display:
            self.display.close()
            self.display=None


class WaylandCapture:
    def __init__(self):
        self.handle=None
        if sys.byteorder!="little":
            raise RuntimeError("La captura Wayland requiere BGRA little endian")
        self.lib=ctypes.CDLL(str(Path(sys.prefix)/"lib"/"bitheroes-pointer.so"),use_errno=True)
        self.lib.fishing_capture_open.restype=ctypes.c_void_p
        self.lib.fishing_capture_grab.argtypes=[ctypes.c_void_p,*([ctypes.c_int]*4),
                                              ctypes.POINTER(ctypes.c_ubyte),ctypes.c_size_t]
        self.lib.fishing_capture_close.argtypes=[ctypes.c_void_p]
        self.lib.fishing_capture_close.restype=None
        self.handle=self.lib.fishing_capture_open()
        if not self.handle:
            raise RuntimeError("No se puede abrir wlr-screencopy; comprueba INSTALAR.sh y el monitor")

    def grab(self,x,y,w,h):
        if not self.handle:
            raise RuntimeError("La captura Wayland esta cerrada")
        pixels=(ctypes.c_ubyte*(w*h*4))()
        if self.lib.fishing_capture_grab(self.handle,x,y,w,h,pixels,len(pixels))<0:
            raise RuntimeError("Wayland no entrego un frame completo actual; no se reutiliza el anterior")
        return bytearray(pixels)

    def close(self):
        if self.handle:
            self.lib.fishing_capture_close(self.handle)
            self.handle=None


class LinuxCapture:
    """Frame del compositor: Unity puede conservar una superficie X11 antigua."""
    def __init__(self,guard):
        self.guard=guard
        self.native=None

    def __enter__(self):
        return self

    def __exit__(self,*args):
        self.close()
        return False

    def close(self):
        if self.native is not None:
            self.native.close()
            self.native=None

    def grab(self,monitor):
        from mss.screenshot import ScreenShot
        try:
            self.guard.check()
            x,y,w,h=(monitor[k] for k in ("left","top","width","height"))
            if (any(type(n) is not int for n in (x,y,w,h))
                    or x<0 or y<0 or w<=0 or h<=0 or x+w>1920 or y+h>1080):
                raise RuntimeError("Region de captura Linux fuera del juego")
            if self.native is None:
                self.native=WaylandCapture()
            pixels=self.native.grab(x,y,w,h)
            self.guard.check()  # Nunca devolver el escritorio si cambio el foco durante la copia.
            if len(pixels)!=w*h*4:
                raise RuntimeError("Pixeles de captura Wayland incompletos")
            return ScreenShot(pixels,monitor)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            raise SafetyStop("No se puede capturar la ventana Steam: "+str(exc)) from exc


def validate_niri_window(window, game):
    if (not isinstance(window,dict) or window.get("id")!=game.compositor_id
            or window.get("title")!="Bit Heroes"
            or window.get("app_id")!="steam_app_666860"
            or window.get("is_focused") is not True):
        raise RuntimeError("Steam perdio el foco o cambio su identidad en niri; no se envia input")
    layout=window.get("layout",{})
    if (layout.get("window_size")!=[1920,1080] or layout.get("tile_size")!=[1920,1080]
            or layout.get("window_offset_in_tile")!=[0,0]
            or layout.get("tile_pos_in_workspace_view") not in (None,[0,0])):
        raise RuntimeError("Steam debe estar a pantalla completa 1920x1080, sin bordes ni escala")


class LinuxIO:
    platform="linux"

    def __init__(self):
        self.game_guard=self.pointer=None
        try:
            game=GameWindow.deserialize(os.environ.get(ENV_WINDOW,""))
            self.game_guard=WindowGuard(game)
            self.check_game()
            self.pointer=WaylandPointer()
        except (Exception,KeyboardInterrupt) as exc:
            self.close()
            if isinstance(exc,KeyboardInterrupt):
                raise
            raise SafetyStop(str(exc)) from exc

    def emergency(self):
        self.game_guard.api.emergency()

    def check_game(self):
        try:
            self.game_guard.check()
        except RuntimeError as exc:
            raise SafetyStop(str(exc)) from exc

    def _move(self,xy,settle=True):
        if (len(xy)!=2 or any(type(n) is not int for n in xy)
                or not (0<=xy[0]<1920 and 0<=xy[1]<1080)):
            raise SafetyStop("Coordenadas Linux invalidas; no se envia input")
        self.emergency()
        self.check_game()
        self.pointer.move(*xy)
        if settle and getattr(self,"control_mode",False):
            # Wine/Unity procesa los botones de interfaz por frames: el cursor
            # confirmado en XWayland aun puede no haber llegado al juego.
            time.sleep(.08)
        self.emergency()
        self.check_game()
        try:
            cursor=self.game_guard.api.cursor()
            if cursor!=tuple(xy):
                raise RuntimeError(f"Wayland no confirma el cursor: esperada {tuple(xy)}, actual {cursor}; no se hace clic")
        except RuntimeError as exc:
            raise SafetyStop(str(exc)) from exc

    def click(self,xy):
        self._move(xy)
        try:
            self.pointer.button(True)
            if getattr(self,"control_mode",False):
                time.sleep(.06)
        finally:
            self.pointer.button(False)

    def cast_click(self,xy):
        self._move(xy,settle=False)
        try:
            self.pointer.button(True)
        finally:
            self.pointer.button(False)

    def escape(self):
        from Xlib import X
        from Xlib.ext import xtest
        self.emergency();self.check_game()
        display=self.game_guard.api.display;key=display.keysym_to_keycode(0xff1b)
        if not key:raise SafetyStop('Escape no disponible; no se envía otra tecla')
        try:
            xtest.fake_input(display,X.KeyPress,key);display.sync();time.sleep(.06)
            self.emergency();self.check_game()
        finally:
            xtest.fake_input(display,X.KeyRelease,key);display.sync()

    def close(self):
        try:
            if self.pointer is not None:
                self.pointer.close()
        finally:
            if self.game_guard is not None:
                self.game_guard.api.close()
