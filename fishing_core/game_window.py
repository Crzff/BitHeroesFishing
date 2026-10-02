"""Identificacion y guardia de ventana. No abre juegos ni envia input al importar."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import ntpath

CHROME_TITLE="Play Bit Heroes Online | Kongregate - Google Chrome"
CLIENTS=("Auto", "Steam", "Chrome")
ENV_WINDOW="FISHING_GAME_WINDOW"


@dataclass(frozen=True)
class GameWindow:
    hwnd: int
    pid: int
    client: str
    rect: tuple[int, int, int, int]

    def serialize(self):
        return json.dumps(asdict(self))

    @classmethod
    def deserialize(cls, text):
        value=json.loads(text)
        if (not isinstance(value,dict) or set(value)!={"hwnd","pid","client","rect"}
                or type(value["hwnd"]) is not int or value["hwnd"]<=0
                or type(value["pid"]) is not int or value["pid"]<=0
                or value["client"] not in CLIENTS[1:]
                or not isinstance(value["rect"],list) or len(value["rect"])!=4
                or any(type(n) is not int for n in value["rect"])):
            raise RuntimeError("Identidad de ventana invalida; no se envia input")
        return cls(value["hwnd"],value["pid"],value["client"],tuple(value["rect"]))


def window_client(title, class_name, executable):
    """El titulo solo no basta: comprobar tambien clase y ejecutable."""
    name=ntpath.basename(executable).casefold()
    if title=="Bit Heroes" and class_name=="UnityWndClass" and name=="bit heroes.exe":
        return "Steam"
    if title==CHROME_TITLE and class_name=="Chrome_WidgetWin_1" and name=="chrome.exe":
        return "Chrome"
    return None


def select_window(windows, client="Auto"):
    if client not in CLIENTS:
        raise RuntimeError("Selecciona Auto, Steam o Chrome")
    matches=[window for window in windows if client=="Auto" or window.client==client]
    if len(matches)!=1:
        if matches:
            raise RuntimeError("Hay varias ventanas del juego; selecciona Steam/Chrome o cierra duplicadas")
        raise RuntimeError(f"No se identifica Bit Heroes ({client}); abre el juego y deja FISHING / START visible")
    return matches[0]


def validate_geometry(window, screen):
    if tuple(screen)!=(1920,1080):
        raise RuntimeError("Se requiere pantalla principal 1920x1080; no se envian clics")
    left,top,right,bottom=window.rect
    if window.client=="Steam":
        if window.rect!=(0,0,1920,1080):
            raise RuntimeError("Steam requiere area de juego 1920x1080 en (0,0); usa pantalla completa sin bordes")
    elif not (left==0 and right==1920 and 0<=top<200 and 1070<=bottom<=1080):
        raise RuntimeError("Chrome debe ocupar la pantalla principal 1920x1080 con la disposicion compatible")


class WindowsAPI:
    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes=ctypes
        self.types=wintypes
        self.user=ctypes.WinDLL("user32",use_last_error=True)
        self.kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        user,kernel=self.user,self.kernel
        user.SetProcessDPIAware()
        user.GetForegroundWindow.restype=wintypes.HWND
        for name in ("IsWindow","IsWindowVisible","IsIconic","SetForegroundWindow","BringWindowToTop"):
            getattr(user,name).argtypes=[wintypes.HWND]
        user.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
        user.GetClassNameW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
        user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
        user.GetWindowThreadProcessId.restype=wintypes.DWORD
        user.GetClientRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
        user.ClientToScreen.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.POINT)]
        user.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
        user.AttachThreadInput.argtypes=[wintypes.DWORD,wintypes.DWORD,wintypes.BOOL]
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]

    def screen(self):
        return self.user.GetSystemMetrics(0),self.user.GetSystemMetrics(1)

    def foreground(self):
        return self.user.GetForegroundWindow()

    def emergency(self):
        if self.user.GetAsyncKeyState(0x77)&0x8000:
            raise KeyboardInterrupt("F8")

    def pid(self, hwnd):
        pid=self.types.DWORD()
        self.user.GetWindowThreadProcessId(hwnd,self.ctypes.byref(pid))
        return pid.value

    def title(self, hwnd):
        text=self.ctypes.create_unicode_buffer(2048)
        self.user.GetWindowTextW(hwnd,text,len(text))
        return text.value

    def class_name(self, hwnd):
        text=self.ctypes.create_unicode_buffer(256)
        self.user.GetClassNameW(hwnd,text,len(text))
        return text.value

    def executable(self, pid):
        handle=self.kernel.OpenProcess(0x1000,False,pid)
        if not handle:
            return ""
        try:
            text=self.ctypes.create_unicode_buffer(32768)
            size=self.types.DWORD(len(text))
            if not self.kernel.QueryFullProcessImageNameW(handle,0,text,self.ctypes.byref(size)):
                return ""
            return text.value
        finally:
            self.kernel.CloseHandle(handle)

    def rect(self, hwnd):
        rect=self.types.RECT()
        origin=self.types.POINT(0,0)
        if not (self.user.GetClientRect(hwnd,self.ctypes.byref(rect))
                and self.user.ClientToScreen(hwnd,self.ctypes.byref(origin))):
            raise RuntimeError("No se puede comprobar el area de juego")
        return origin.x,origin.y,origin.x+rect.right,origin.y+rect.bottom

    def inspect(self, hwnd):
        if not self.user.IsWindow(hwnd) or not self.user.IsWindowVisible(hwnd):
            raise RuntimeError("La ventana del juego ya no existe o esta oculta")
        pid=self.pid(hwnd)
        client=window_client(self.title(hwnd),self.class_name(hwnd),self.executable(pid))
        if client is None:
            raise RuntimeError("La ventana no es Bit Heroes de Steam ni el Chrome compatible")
        return GameWindow(hwnd,pid,client,self.rect(hwnd))

    def windows(self):
        candidates=[]
        @self.ctypes.WINFUNCTYPE(self.types.BOOL,self.types.HWND,self.types.LPARAM)
        def visit(hwnd,param):
            if self.user.IsWindowVisible(hwnd) and self.title(hwnd) in ("Bit Heroes",CHROME_TITLE):
                try:
                    candidates.append(self.inspect(hwnd))
                except RuntimeError:
                    pass
            return True
        if not self.user.EnumWindows(visit,0):
            raise RuntimeError("Windows no permite enumerar las ventanas del juego")
        return candidates

    def activate(self, hwnd):
        self.emergency()
        if self.user.IsIconic(hwnd):
            self.user.ShowWindow(hwnd,9)
        self.user.SetForegroundWindow(hwnd)
        if self.foreground()!=hwnd:
            current=self.kernel.GetCurrentThreadId()
            foreground=self.user.GetWindowThreadProcessId(self.foreground(),None)
            attached=False
            try:
                if foreground and foreground!=current:
                    attached=bool(self.user.AttachThreadInput(current,foreground,True))
                self.user.BringWindowToTop(hwnd)
                self.user.SetForegroundWindow(hwnd)
            finally:
                if attached:
                    self.user.AttachThreadInput(current,foreground,False)
        if self.foreground()!=hwnd:
            raise RuntimeError("Windows no confirma el foco del juego; no se inician motores")


def focus_window(client="Auto", api=None):
    api=api or WindowsAPI()
    api.emergency()
    game=select_window(api.windows(),client)
    api.activate(game.hwnd)
    # Restaurar una ventana minimizada cambia su rectangulo; leerlo de nuevo.
    current=api.inspect(game.hwnd)
    if (current.hwnd,current.pid,current.client)!=(game.hwnd,game.pid,game.client):
        raise RuntimeError("Cambio la identidad del juego al enfocarlo")
    validate_geometry(current,api.screen())
    WindowGuard(current,api).check()
    return current


class WindowGuard:
    def __init__(self, game, api=None):
        self.game=game
        self.api=api or WindowsAPI()
        validate_geometry(game,self.api.screen())
        if self.api.inspect(game.hwnd)!=game:
            raise RuntimeError("La ventana seleccionada cambio antes de iniciar")

    def check(self):
        api,game=self.api,self.game
        if (not api.user.IsWindow(game.hwnd) or not api.user.IsWindowVisible(game.hwnd)
                or api.user.IsIconic(game.hwnd) or api.foreground()!=game.hwnd):
            raise RuntimeError("El juego perdio el primer plano o fue minimizado; no se envia input")
        title="Bit Heroes" if game.client=="Steam" else CHROME_TITLE
        if api.pid(game.hwnd)!=game.pid or api.title(game.hwnd)!=title:
            raise RuntimeError("Cambio la ventana o la pestaña del juego; no se envia input")
        if api.rect(game.hwnd)!=game.rect:
            raise RuntimeError("El juego se movio o cambio de tamaño; no se envia input")
        validate_geometry(game,api.screen())
