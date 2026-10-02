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


def focus_game(client="Auto"):
    """Compatibilidad para herramientas previas que esperan solo el HWND."""
    from .game_window import focus_window
    return focus_window(client).hwnd
