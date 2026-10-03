"""Acceso principal: dungeons primero; pesca existente en la segunda pestaña."""

import customtkinter as ctk
from FISHING_BOT_APP import FishingBotApp


if __name__=='__main__':
    ctk.set_appearance_mode('dark')
    app=FishingBotApp(farm_primary=True)
    app.mainloop()
