"""Selector local. Abrirlo/buscar un familiar no envía input al juego."""

import customtkinter as ctk
import tkinter as tk

from .dungeon_catalog import CATALOG,FAMILIARS,dungeon,routes_for,farm_plan
from .dungeon_runtime import validate_supported
from .panel_theme import (COLOR_CARD, COLOR_GOLD, COLOR_TEXT, COLOR_TEXT_DIM,
                          TITLE_STYLE, PANEL_STYLE, START_STYLE, STOP_STYLE,
                          BUTTON_STYLE, ENTRY_STYLE, MENU_STYLE)


class DungeonPanel(ctk.CTkFrame):
    def __init__(self,master,on_start,on_stop):
        super().__init__(master,fg_color=COLOR_CARD,corner_radius=0)
        self.pack(fill='both',expand=True,padx=8,pady=8)
        self.labels={f"{row['id']} · {row['name']}":row['id'] for row in CATALOG}
        tk.Label(self,text='BIT HEROES · DUNGEONS',**TITLE_STYLE).pack(fill='x',pady=(0,12))
        ctk.CTkLabel(self,text='Objetivo familiar (opcional)',anchor='w',text_color=COLOR_GOLD).pack(fill='x')
        self.familiar=ctk.CTkComboBox(self,values=sorted(FAMILIARS),command=lambda _:self.search(),width=400,
                                    border_color=COLOR_TEXT_DIM, **MENU_STYLE)
        self.familiar.set('');self.familiar.pack(fill='x',pady=8)
        self.familiar.bind('<Return>',lambda _:self.search())
        self.search_button=ctk.CTkButton(self,text='Buscar dungeon del familiar',command=self.search,
                                       **BUTTON_STYLE)
        self.search_button.pack(fill='x',pady=(0,12))
        ctk.CTkLabel(self,text='Dungeon · zona y nombre',anchor='w',text_color=COLOR_GOLD).pack(fill='x')
        self.route=ctk.CTkOptionMenu(self,values=list(self.labels),command=self.route_changed,**MENU_STYLE)
        self.route.pack(fill='x',pady=8)
        self.route.set(next(label for label,identifier in self.labels.items() if identifier=='Z5D2'))
        ctk.CTkLabel(self,text='Dificultad',anchor='w',text_color=COLOR_GOLD).pack(fill='x')
        self.difficulty=ctk.CTkOptionMenu(self,values=['Normal','Hard','Heroic'],command=lambda _:self.route_changed(self.route.get()),**MENU_STYLE)
        self.difficulty.set('Normal');self.difficulty.pack(fill='x',pady=8)
        limits=tk.Frame(self,**PANEL_STYLE);limits.pack(fill='x',pady=8)
        limits.columnconfigure((0,1),weight=1)
        ctk.CTkLabel(limits,text='Máximo runs',text_color=COLOR_GOLD).grid(row=0,column=0,sticky='w',padx=8)
        ctk.CTkLabel(limits,text='Máximo energía',text_color=COLOR_GOLD).grid(row=0,column=1,sticky='w',padx=8)
        self.runs=ctk.CTkEntry(limits,width=180,**ENTRY_STYLE);self.runs.insert(0,'1');self.runs.grid(row=1,column=0,sticky='ew',padx=8,pady=8)
        self.energy=ctk.CTkEntry(limits,width=180,**ENTRY_STYLE);self.energy.insert(0,'30');self.energy.grid(row=1,column=1,sticky='ew',padx=8,pady=8)
        self.details=ctk.CTkLabel(self,text='',justify='left',wraplength=450,text_color=COLOR_TEXT)
        self.details.pack(fill='x',pady=12)
        self.start=tk.Button(self,text='▶  START · DUNGEON',command=on_start,**START_STYLE)
        self.start.pack(fill='x',pady=8)
        self.stop=tk.Button(self,text='■  DETENER · F8',command=on_stop,state='disabled',**STOP_STYLE)
        self.stop.pack(fill='x',pady=8)
        self.status=ctk.CTkLabel(self,text='Detenido · Z5D2 Normal / Z5D3 Heroic\nTealk: solo 1 run por sesión',wraplength=450,justify='left',text_color=COLOR_TEXT)
        self.status.pack(fill='x',pady=12)
        ctk.CTkLabel(self,text='Gasto automático de oro: aún desactivado.\nSin gemas, compras o consumibles.\nOtro familiar reconocido: rechazar.\nObjetivo o nombre desconocido: pausa.\n77 dungeons / 220 familiares de la wiki (Z1–20).\nMáximo 15 min/sesión · abrir no inicia una run.\nF8 detiene el bot; Auto nativo puede seguir la dungeon.',
                      wraplength=450,justify='left',text_color=COLOR_TEXT_DIM).pack(fill='x',pady=12)
        self.route_changed(self.route.get())

    def route_changed(self,label):
        item=dungeon(self.labels[label])
        values=['Special'] if item['special'] else ['Normal','Hard','Heroic']
        self.difficulty.configure(values=values)
        if self.difficulty.get() not in values:self.difficulty.set(values[0])
        try:
            validate_supported(farm_plan(item['id'],self.difficulty.get(),1,30))
            message='Disponible en Steam/niri · elige Aramore con Zones.'
            if item['id']=='Z5D3':message+='\nSolo 1 run por sesión · coste 30 energía.'
        except ValueError:message='Catálogo público · ruta/dificultad pendiente de calibrar.'
        self.details.configure(text=f"Zona {item['zone']} · {item['zone_name']}\n{message}")

    def search(self):
        if not self.familiar.get().strip():
            self.route.configure(values=list(self.labels))
            self.status.configure(text='Catálogo completo · disponibles Z5D2 Normal y Z5D3 Heroic (1 run)')
            return
        candidates=routes_for(self.familiar.get())
        if not candidates:
            self.status.configure(text='Sin ruta de captura directa: revisa el nombre o la receta de fusión.')
            return
        labels=[label for label,identifier in self.labels.items() if identifier in {row['id'] for row in candidates}]
        self.route.configure(values=labels);self.route.set(labels[0]);self.route_changed(labels[0])
        self.status.configure(text=f"{self.familiar.get()}: {len(labels)} rutas. No se ha iniciado ninguna run.")

    def plan(self):
        return farm_plan(self.labels[self.route.get()],self.difficulty.get(),int(self.runs.get()),
                         int(self.energy.get()),self.familiar.get())

    def active(self,active):
        self.start.configure(state='disabled' if active else 'normal')
        self.stop.configure(state='normal' if active else 'disabled')
        for widget in (self.route,self.familiar,self.difficulty,self.runs,self.energy,self.search_button):
            widget.configure(state='disabled' if active else 'normal')
