"""Zona segura del panel para la interfaz comprobada 1920x1080.

No captura, no envia input y no modifica los motores. El inventario esta a
la derecha de x=555; las barras de pesca empiezan por debajo de y=710.
Se reservan margenes para evitar incluso bordes/sombras sobre esas zonas.
"""

ACTIVE_GEOMETRY="520x650+10+10"
ACTIVE_SIZE=(520,650)
SAFE_RIGHT=550
SAFE_BOTTOM=690


def panel_bounds_safe(rect):
    if len(rect)!=4:
        return False
    left,top,right,bottom=rect
    return 0<=left<right<=SAFE_RIGHT and 0<=top<bottom<=SAFE_BOTTOM


def stop_button_visible(app,rect):
    """El boton de parada tambien debe caber completo en la vista compacta."""
    button=app.btn_detener
    if not button.winfo_ismapped():
        return False
    left,top=button.winfo_rootx(),button.winfo_rooty()
    width,height=button.winfo_width(),button.winfo_height()
    return (width>0 and height>0 and rect[0]<=left and rect[1]<=top
            and left+width<=rect[2] and top+height<=rect[3])


def window_bounds(app):
    import ctypes
    from ctypes import wintypes
    user=ctypes.windll.user32
    user.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT]
    user.GetAncestor.restype=wintypes.HWND
    user.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
    hwnd=user.GetAncestor(app.winfo_id(),2)
    rect=wintypes.RECT()
    if not hwnd or not user.GetWindowRect(hwnd,ctypes.byref(rect)):
        raise RuntimeError("No se puede verificar el rectangulo del panel")
    return rect.left,rect.top,rect.right,rect.bottom


def focus_game():
    """Activa solo el Chrome del juego identificado; no hace clics para dar foco."""
    import ctypes
    from ctypes import wintypes
    user=ctypes.windll.user32
    kernel=ctypes.windll.kernel32
    user.GetForegroundWindow.restype=wintypes.HWND
    user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowThreadProcessId.restype=wintypes.DWORD
    user.SetForegroundWindow.argtypes=[wintypes.HWND]
    user.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
    windows=[]
    @ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    def visit(hwnd,param):
        if user.IsWindowVisible(hwnd):
            title=ctypes.create_unicode_buffer(2048)
            user.GetWindowTextW(hwnd,title,len(title))
            if title.value=="Play Bit Heroes Online | Kongregate - Google Chrome":
                windows.append(hwnd)
        return True
    user.EnumWindows(visit,0)
    if len(windows)!=1:
        raise RuntimeError("No se identifica una ventana unica de Bit Heroes en Chrome")
    if user.GetAsyncKeyState(0x77)&0x8000:
        raise KeyboardInterrupt("F8")
    game=windows[0]
    if user.IsIconic(game):
        user.ShowWindow(game,9)
    user.SetForegroundWindow(game)
    if user.GetForegroundWindow()!=game:
        # Windows puede rechazar una activacion de otro hilo. Adjuntar solo
        # durante el cambio de foco y deshacerlo siempre, sin input de raton.
        current=kernel.GetCurrentThreadId()
        foreground=user.GetWindowThreadProcessId(user.GetForegroundWindow(),None)
        attached=False
        try:
            if foreground and foreground!=current:
                attached=bool(user.AttachThreadInput(current,foreground,True))
            user.SetForegroundWindow(game)
        finally:
            if attached:
                user.AttachThreadInput(current,foreground,False)
    if user.GetForegroundWindow()!=game:
        raise RuntimeError("Windows no confirma el foco del juego; no se inician motores")
    return game
