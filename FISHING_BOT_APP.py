"""
FISHING_BOT_APP.py - Panel de control para el bot de pesca de Bit Heroes

Interfaz de juego con marcos en relieve usando Tk y CustomTkinter.
Controla los procesos CATCH y CONTROL directamente.

Uso:
    python FISHING_BOT_APP.py
"""

import os
import sys
import json
import time
import threading
import tkinter as tk
from pathlib import Path
from datetime import datetime

import customtkinter as ctk
from fishing_core.processes import start_children, close_children
from fishing_core import VERSION
from fishing_core.panel_state import PanelState, SessionFeed
from fishing_core.panel_safety import ACTIVE_GEOMETRY, ACTIVE_SIZE, panel_bounds_safe, stop_button_visible, window_bounds
from fishing_core.game_window import CLIENTS, focus_window
from fishing_core.protocol import atomic_json
from fishing_core.project_links import support_url
from fishing_core.panel_theme import (
    COLOR_BG, COLOR_CARD, COLOR_ACCENT, COLOR_HOVER, COLOR_FRAME, COLOR_INSET, COLOR_GOLD,
    COLOR_SUCCESS, COLOR_DANGER, COLOR_TEXT, COLOR_TEXT_DIM,
    WINDOW_STYLE, PANEL_STYLE, TITLE_STYLE, START_STYLE, STOP_STYLE, BUTTON_STYLE,
    MENU_STYLE,
)

# ============================================================
# Configuración
# ============================================================

HERE = Path(__file__).resolve().parent
CATCH_SCRIPT = HERE / "CATCH_FAST_PROCESS_V6_FINAL.py"
CONTROL_SCRIPT = HERE / "FISHING_CONTROL_PROCESS.py"

LOG_CATCH = HERE / "CATCH_LOG.txt"
LOG_CONTROL = HERE / "CONTROL_LOG.txt"
LOG_SAMPLES = HERE / "CATCH_SAMPLES.csv"

# Archivo de configuración
CONFIG_FILE = HERE / "fishing_bot_config.json"

# ============================================================
# Clase principal de la aplicación
# ============================================================

class FishingBotApp(ctk.CTk):
    def __init__(self,farm_primary=False):
        super().__init__()
        self.farm_primary=farm_primary

        # Configuración de la ventana
        self.title(f"🎣 Bit Heroes Fishing Bot — {VERSION}")
        self.geometry("550x900+20+20")
        self.minsize(520, 850)
        self.configure(fg_color=COLOR_BG)

        # Estado
        self.p_catch = None
        self.p_control = None
        self.channel = None
        self.launch_mutex = None
        self._idle_pending = False
        self.bot_activo = False
        self.active_mode = 'Fishing'
        self.monitor_thread = None
        self.log_thread = None
        self.stop_event = threading.Event()
        self.siempre_visible = False
        self.panel_state = None
        self.session_feed = None
        self._fishing_view = False
        self._normal_view = None
        self._linux_panel = os.name!="nt"

        # Construir interfaz
        self._build_ui()
        if farm_primary:
            from fishing_core.dungeon_panel import DungeonPanel
            self.dungeon_panel=DungeonPanel(self.mode_tabs.tab('Dungeons'),self._iniciar_dungeon,self.detener_bot)
            self.title('Bit Heroes Farm Bot · Dungeons / Fishing')

        # Verificar scripts existen
        self._verificar_scripts()

        # Iniciar monitoreo
        self._iniciar_monitoreo()

        # Cargar configuración guardada
        self._cargar_config()
        # Aplicar preferencia de siempre visible
        if self.siempre_visible:
            self.attributes("-topmost", True)
        self._actualizar_ui()

        # Protocolo de cierre
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        """Construir la interfaz de usuario."""
        self.background = tk.Canvas(self, bg=COLOR_BG, highlightthickness=0)
        self.background.place(relwidth=1, relheight=1)
        self.background.bind('<Configure>', self._draw_background)
        self.window_frame = tk.Frame(self, **WINDOW_STYLE)
        self.window_frame.pack(fill='both', expand=True, padx=8, pady=8)
        # Frame principal
        parent=self.window_frame
        if self.farm_primary:
            # https://customtkinter.tomschimansky.com/documentation/widgets/tabview/
            self.mode_tabs=ctk.CTkTabview(parent, fg_color=COLOR_CARD, corner_radius=0,
                segmented_button_fg_color=COLOR_INSET,
                segmented_button_selected_color=COLOR_ACCENT,
                segmented_button_selected_hover_color=COLOR_HOVER,
                segmented_button_unselected_color=COLOR_INSET,
                segmented_button_unselected_hover_color=COLOR_CARD,
                segmented_button_font=ctk.CTkFont(family='Courier', size=14, weight='bold'),
                text_color=COLOR_GOLD, text_color_disabled=COLOR_TEXT_DIM)
            self.mode_tabs.pack(fill='both',expand=True)
            self.mode_tabs.add('Dungeons');self.mode_tabs.add('Fishing');self.mode_tabs.set('Dungeons')
            parent=self.mode_tabs.tab('Fishing')
        self.main_frame = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # Título
        self.title_label = tk.Label(
            self.main_frame,
            text="BIT HEROES · FISHING",
            **TITLE_STYLE,
        )
        self.title_label.pack(fill='x', pady=(0, 12))

        # Indicador de estado
        self.status_frame = tk.Frame(self.main_frame, **PANEL_STYLE)
        self.status_frame.pack(fill="x", pady=(0, 8))

        self.status_indicator = ctk.CTkLabel(
            self.status_frame,
            text="● DETENIDO",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLOR_DANGER,
            height=24,
        )
        self.status_indicator.pack(pady=8)

        # Frame de procesos
        self.procesos_frame = tk.Frame(self.main_frame, **PANEL_STYLE)
        self.procesos_frame.pack(fill="x", pady=(0, 8))

        self.procesos_title = ctk.CTkLabel(
            self.procesos_frame,
            text="Motores en ejecución",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_GOLD,
            height=20,
        )
        self.procesos_title.pack(anchor="w", padx=12, pady=(8, 4))

        # Estado CATCH
        self.estado_catch = ctk.CTkLabel(
            self.procesos_frame,
            text="  CATCH: —",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_DIM,
            height=20,
        )
        self.estado_catch.pack(anchor="w", padx=12, pady=2)

        # Estado CONTROL
        self.estado_control = ctk.CTkLabel(
            self.procesos_frame,
            text="  CONTROL: —",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_DIM,
            height=20,
        )
        self.estado_control.pack(anchor="w", padx=12, pady=(2, 12))

        self.activity_label = ctk.CTkLabel(self.procesos_frame, text="Actividad: esperando inicio",
                                         text_color=COLOR_TEXT, font=ctk.CTkFont(size=14, weight="bold"),
                                         wraplength=470, justify="left")
        self.activity_label.pack(anchor="w", padx=12, pady=(0, 4))
        self.outcome_label = ctk.CTkLabel(self.procesos_frame, text="Sin resultados en esta sesión",
                                        text_color=COLOR_TEXT_DIM, height=20, wraplength=470, justify="left")
        self.outcome_label.pack(anchor="w", padx=12, pady=(0, 4))
        self.cast_label = ctk.CTkLabel(self.procesos_frame, text="CAST: sin lanzamiento en esta sesión",
                                       text_color=COLOR_TEXT_DIM, height=20, wraplength=470, justify="left")
        self.cast_label.pack(anchor="w", padx=12, pady=(0, 12))

        self.bait_frame = tk.Frame(self.main_frame, **PANEL_STYLE)
        self.bait_frame.pack(fill="x", pady=(0, 8))
        self.bait_label = ctk.CTkLabel(self.bait_frame, text="Cebos: sin lectura confirmada",
                                     text_color=COLOR_TEXT, height=24, font=ctk.CTkFont(size=14, weight="bold"), wraplength=470)
        self.bait_label.pack(anchor="w", padx=12, pady=(10, 4))
        self.bait_details = ctk.CTkLabel(self.bait_frame, text="Lectura automática al llegar a START",
                                       text_color=COLOR_TEXT_DIM, height=20, wraplength=470, justify="left")
        self.bait_details.pack(anchor="w", padx=12, pady=(0, 4))
        self.bait_note = ctk.CTkLabel(self.bait_frame, text="Pescas ≈ restantes · 1 cebo por CAST · conteo inicial único\nSin límite de ciclos · parada con 0 estimados · F8 detiene",
                                    text_color=COLOR_TEXT_DIM, font=ctk.CTkFont(size=11), wraplength=470)
        self.bait_note.pack(anchor="w", padx=12, pady=(0, 10))

        # Botones
        self.botones_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_CARD, corner_radius=0)
        self.botones_frame.pack(fill="x", pady=(0, 8))

        self.btn_iniciar = tk.Button(
            self.botones_frame,
            text="▶  START · PESCA",
            **START_STYLE,
            command=self.iniciar_bot,
        )
        self.btn_iniciar.pack(fill="x", pady=(0, 8))

        self.btn_detener = tk.Button(
            self.botones_frame,
            text="■  DETENER · F8",
            **STOP_STYLE,
            command=self.detener_bot,
            state="disabled",
        )
        self.btn_detener.pack(fill="x", pady=(0, 8))

        self.btn_reiniciar = ctk.CTkButton(
            self.botones_frame,
            text="🔄  REINICIAR",
            font=ctk.CTkFont(size=13, weight="bold"),
            **BUTTON_STYLE,
            height=34,
            command=self.reiniciar_bot,
            state="disabled",
        )
        self.btn_reiniciar.pack(fill="x", pady=(0, 8))

        self.btn_siempre_visible = ctk.CTkButton(
            self.botones_frame,
            text="📌  SIEMPRE VISIBLE",
            font=ctk.CTkFont(size=13, weight="bold"),
            **BUTTON_STYLE,
            height=34,
            command=self.alternar_siempre_visible,
        )
        self.btn_siempre_visible.pack(fill="x")

        # Seleccion de esta sesion; no altera preferencias personales guardadas.
        self.game_frame = tk.Frame(self.main_frame, **PANEL_STYLE)
        self.game_frame.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(self.game_frame, text="Juego · visible y en primer plano", text_color=COLOR_TEXT).pack(side="left", padx=12)
        self.game_selector = ctk.CTkOptionMenu(self.game_frame,
            values=["Steam"] if self._linux_panel else list(CLIENTS), width=115, **MENU_STYLE)
        self.game_selector.set("Steam" if self._linux_panel else "Auto")
        self.game_selector.pack(side="right", padx=12, pady=6)

        # Frame de logs
        self.logs_frame = tk.Frame(self.main_frame, **PANEL_STYLE)
        self.logs_frame.pack(fill="both", expand=True)

        self.logs_title = ctk.CTkLabel(
            self.logs_frame,
            text="📋 Logs en tiempo real",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_DIM,
            height=20,
        )
        self.logs_title.pack(anchor="w", padx=12, pady=(8, 4))

        # Visible solo en el panel normal; el frame de logs se oculta al pescar.
        self.btn_apoyar = None
        url = support_url(HERE)
        if url:
            self.btn_apoyar = ctk.CTkButton(
                self.logs_frame, text="♡  Apoyar en Ko-fi (opcional)",
                **BUTTON_STYLE, height=26,
                command=self._abrir_apoyo,
            )
            self.btn_apoyar.pack(anchor="e", padx=12, pady=(0, 6))

        # Textbox de logs
        self.log_textbox = ctk.CTkTextbox(
            self.logs_frame,
            fg_color=COLOR_INSET,
            border_width=2,
            border_color=COLOR_FRAME,
            scrollbar_button_color=COLOR_ACCENT,
            scrollbar_button_hover_color=COLOR_FRAME,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=11, family="Consolas"),
            corner_radius=0,
            wrap="none",
        )
        self.log_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_textbox.configure(state="disabled")

    def _draw_background(self, event):
        """Mampostería pixelada original, sin imágenes ni descargas en ejecución."""
        self.background.delete('stone')
        colors = ('#1c3341', '#203847', '#1a303e')
        for row, y in enumerate(range(0, event.height, 32)):
            for column, x in enumerate(range(-32 if row % 2 else 0, event.width, 64)):
                self.background.create_rectangle(x+2, y+2, x+62, y+30,
                    fill=colors[(row+column) % len(colors)], outline=COLOR_BG, tags='stone')

    def _verificar_scripts(self):
        """Verificar que los scripts necesarios existen."""
        if not CATCH_SCRIPT.exists():
            self._log(f"❌ Error: No se encontró {CATCH_SCRIPT.name}")
            return False
        if not CONTROL_SCRIPT.exists():
            self._log(f"❌ Error: No se encontró {CONTROL_SCRIPT.name}")
            return False
        return True

    def _abrir_apoyo(self):
        """Solo un enlace externo por accion explicita y con pesca detenida."""
        if self.bot_activo:
            return
        url = support_url(HERE)
        if url:
            import webbrowser
            webbrowser.open(url)

    def _cargar_config(self):
        """Cargar preferencias guardadas."""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                if (not isinstance(config, dict) or set(config) != {"siempre_visible"}
                        or type(config["siempre_visible"]) is not bool):
                    raise ValueError("La preferencia siempre_visible debe ser un booleano; archivo no modificado")
                self.siempre_visible = config["siempre_visible"]
                self._log(f"📂 Configuración cargada: siempre_visible={self.siempre_visible}")
        except Exception as e:
            self._log(f"⚠️  Error cargando config: {e}")

    def _guardar_config(self):
        """Guardar preferencias."""
        try:
            config = {"siempre_visible": self.siempre_visible}
            if type(self.siempre_visible) is not bool:
                raise ValueError("La preferencia siempre_visible debe ser un booleano")
            atomic_json(CONFIG_FILE, config)
        except Exception as e:
            self._log(f"⚠️  Error guardando config: {e}")

    def alternar_siempre_visible(self):
        """Alternar siempre visible."""
        self.siempre_visible = not self.siempre_visible
        self.attributes("-topmost", self.siempre_visible)
        self._guardar_config()
        if self.siempre_visible:
            self._log("📌 Siempre visible ACTIVADO")
        else:
            self._log("📌 Siempre visible DESACTIVADO")
        self._actualizar_ui()

    def _preparar_vista_pesca(self):
        """Panel abierto, pero fuera de todas las zonas de lectura y clic."""
        if self._fishing_view:
            return
        if getattr(self,"_linux_panel",False):
            # ponytail: ocultar el panel en fullscreen niri; overlay nativo si se necesita.
            # No dependemos de coordenadas Tk falsas bajo XWayland ni tapamos el juego.
            self._fishing_view=True
            self.withdraw()
            self.update_idletasks()
            if self.state()!="withdrawn":
                raise RuntimeError("No se pudo ocultar el panel Linux; no se inicia pesca")
            self._log("Panel oculto durante la sesión · F8 detiene y vuelve a mostrarlo")
            return
        # CTk no admite minsize()/maxsize() sin argumentos como tkinter.
        # Guardar sus limites logicos, no consultar esos metodos setters.
        self._normal_view = (self.geometry(), (self._min_width, self._min_height),
                             (self._max_width, self._max_height),
                             self.resizable(), self.overrideredirect())
        self._fishing_view = True
        self.logs_frame.pack_forget()
        self.game_frame.pack_forget()
        self.btn_iniciar.pack_forget()
        self.btn_reiniciar.pack_forget()
        self.minsize(*ACTIVE_SIZE)
        self.maxsize(*ACTIVE_SIZE)
        self.resizable(False, False)
        # Sin barra de titulo durante la pesca: no se puede arrastrar ni
        # maximizar el panel accidentalmente encima de las barras.
        self.overrideredirect(True)
        self.geometry(ACTIVE_GEOMETRY)
        self.attributes("-topmost", self.siempre_visible)
        self.update_idletasks()
        bounds = window_bounds(self)
        if not panel_bounds_safe(bounds) or not stop_button_visible(self, bounds):
            raise RuntimeError(f"El panel no queda en la zona segura: {bounds}; no se inicia pesca")
        self._log("Panel compacto protegido · F8 o DETENER para parar; logs al detener")

    def _comprobar_vista_pesca(self):
        """Mantener la proteccion tambien al usar el panel sin supervisor."""
        if not self.bot_activo:
            return
        if getattr(self,"_linux_panel",False) and self._fishing_view and self.state()=="withdrawn":
            return
        try:
            bounds = window_bounds(self)
            if self._fishing_view and panel_bounds_safe(bounds) and stop_button_visible(self, bounds):
                return
            reason = "Panel fuera de la zona segura o DETENER oculto"
        except Exception as exc:
            reason = f"No se puede comprobar la zona segura del panel: {exc}"
        self._log(f"🛑 {reason}; deteniendo ambos motores")
        self._after_idle()
        if self.panel_state is not None and not self.panel_state.terminal:
            self.panel_state.activity = "Detenido: " + reason
            self.panel_state.terminal = True

    def _restaurar_vista_panel(self):
        """Restaurar solamente cuando ambos motores ya terminaron."""
        if not self._fishing_view:
            return
        if getattr(self,"_linux_panel",False):
            self._fishing_view=False
            self.deiconify()
            return
        geometry, minimum, maximum, resize, decorated = self._normal_view
        self._fishing_view = False
        self.maxsize(*maximum)
        self.minsize(*minimum)
        self.resizable(*resize)
        self.overrideredirect(decorated)
        self.geometry(geometry)
        self.btn_iniciar.pack(fill="x", pady=(0, 8), before=self.btn_detener)
        self.btn_reiniciar.pack(fill="x", pady=(0, 8), before=self.btn_siempre_visible)
        self.logs_frame.pack(fill="both", expand=True)
        self.game_frame.pack(fill="x", pady=(0, 8), before=self.logs_frame)
        self.attributes("-topmost", self.siempre_visible)
        self._normal_view = None

    def _iniciar_monitoreo(self):
        """Iniciar el hilo de monitoreo de procesos."""
        self.stop_event.clear()
        self.after(200, self._tick)

    def _consume_events(self):
        if self.session_feed is None:
            return
        try:
            for event in self.session_feed.read():
                if event.get('role')=='DUNGEON' and hasattr(self,'dungeon_panel'):
                    message=event.get('message')
                    if message:
                        self.dungeon_panel.status.configure(text=message)
                        self._log(message)
                    continue
                if self.panel_state is None:continue
                self.panel_state.apply(event)
                kind = event.get("event")
                if kind in ("BAIT_INVENTORY", "BAIT_LOW", "BAIT_EXHAUSTED", "BAIT_READ_FAILED",
                            "BAIT_BUDGET_UPDATED", "BAIT_BUDGET_REACHED",
                            "CYCLE_COMPLETE", "RUN_LIMIT_REACHED", "SAFETY_STOP", "PROCESS_ERROR"):
                    self._log(self.panel_state.bait_label if kind in ("BAIT_INVENTORY", "BAIT_BUDGET_UPDATED")
                              else self.panel_state.activity)
        except Exception as exc:
            self._log(f"No se pudo actualizar la actividad: {exc}")

    def _tick(self):
        """Procesos y actividad en el hilo Tk, sin threads que modifican widgets."""
        if self.stop_event.is_set():
            return
        self._consume_events()
        self._comprobar_vista_pesca()
        ended = any(p is not None and p.poll() is not None for p in (self.p_catch, self.p_control))
        if ended and not self._idle_pending:
            self._idle_pending = True
            self._after_idle()
            self._consume_events()
            if self.panel_state is not None and not self.panel_state.terminal:
                self.panel_state.activity = "Sesión detenida · revisar registros"
                self.panel_state.terminal = True
        self._actualizar_ui()
        self.after(200, self._tick)

    def _actualizar_ui(self):
        """Actualizar la interfaz según el estado de los procesos."""
        # Actualizar indicador de estado
        if self.bot_activo:
            self.status_indicator.configure(text="● ACTIVO", text_color=COLOR_SUCCESS)
        else:
            self.status_indicator.configure(text="● DETENIDO", text_color=COLOR_DANGER)
        if self.panel_state is not None:
            self.activity_label.configure(text="Actividad: " + self.panel_state.activity)
            self.outcome_label.configure(text=f"Último: {self.panel_state.outcome}\n{self.panel_state.result_summary}")
            self.cast_label.configure(text=self.panel_state.cast_label)
            self.bait_label.configure(text=self.panel_state.bait_label)
            self.bait_details.configure(text=self.panel_state.bait_details)

        # Actualizar estado de procesos
        if self.p_catch is not None and self.p_catch.poll() is None:
            self.estado_catch.configure(text="  CATCH: ✓ Ejecutándose", text_color=COLOR_SUCCESS)
        else:
            self.estado_catch.configure(text="  CATCH: —", text_color=COLOR_TEXT_DIM)

        if self.p_control is not None and self.p_control.poll() is None:
            self.estado_control.configure(text="  CONTROL: ✓ Ejecutándose", text_color=COLOR_SUCCESS)
        else:
            self.estado_control.configure(text="  CONTROL: —", text_color=COLOR_TEXT_DIM)

        # Actualizar botones
        self.btn_siempre_visible.configure(text="📌  SIEMPRE VISIBLE: " + ("SÍ" if self.siempre_visible else "NO"))
        if self.bot_activo:
            self.btn_iniciar.configure(state="disabled")
            self.btn_detener.configure(state="normal")
            self.btn_reiniciar.configure(state="disabled" if getattr(self,'active_mode','Fishing')=='Dungeons' else "normal")
        else:
            self.btn_iniciar.configure(state="normal")
            self.btn_detener.configure(state="disabled")
            self.btn_reiniciar.configure(state="disabled")
        if hasattr(self,'dungeon_panel'):
            self.dungeon_panel.active(self.bot_activo)
            self.mode_tabs.configure(state='disabled' if self.bot_activo else 'normal')

    def _log(self, mensaje):
        """Agregar un mensaje al log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        linea = f"[{timestamp}] {mensaje}\n"

        # Thread-safe update
        self.after(0, lambda: self._append_log(linea))

    def _append_log(self, linea):
        """Agregar línea al textbox (debe llamarse desde el hilo principal)."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", linea)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _after_idle(self):
        """Cerrar ambos hijos antes de perder sus referencias."""
        try:
            close_children((self.p_catch, self.p_control), self.channel)
        except Exception as exc:
            self._log(f"Error al detener motores: {exc}")
        if self.p_catch is not None and self.p_catch.poll() is not None:
            self.p_catch = None
        if self.p_control is not None and self.p_control.poll() is not None:
            self.p_control = None
        self.bot_activo = self.p_catch is not None or self.p_control is not None
        if not self.bot_activo:
            self.channel = None
            if self.launch_mutex:
                self.launch_mutex.close()
                self.launch_mutex = None
            self._restaurar_vista_panel()
        self._idle_pending = False
        self._actualizar_ui()

    # ============================================================
    # Acciones de los botones
    # ============================================================

    def iniciar_bot(self):
        """Iniciar todos los procesos del bot."""
        if self.bot_activo:
            self._log("⚠️  El bot ya está activo")
            return

        if not self._verificar_scripts():
            return

        self._log("🚀 Iniciando bot...")

        try:
            self._preparar_vista_pesca()
            game = focus_window(self.game_selector.get())
            self._log(f"Juego seleccionado: {game.client} · 1920x1080 · F8 detiene")
            self.p_catch, self.p_control, self.channel, self.launch_mutex = start_children(game)
            self.active_mode='Fishing'
            self.panel_state = PanelState(self.channel.run_id)
            self.session_feed = SessionFeed(self.channel.directory, self.channel.run_id)
            self._log(f"  CATCH iniciado (PID: {self.p_catch.pid})")
            self._log(f"  CONTROL iniciado (PID: {self.p_control.pid})")
            self._log(f"  {VERSION} | sesión: {self.channel.run_id}")

            self.bot_activo = True
            self._log("✅ Bot iniciado correctamente")

        except (Exception, KeyboardInterrupt) as e:
            self._log(f"❌ Error al iniciar: {e}")
            self._after_idle()

    def _iniciar_dungeon(self):
        if self.bot_activo:return
        try:
            plan=self.dungeon_panel.plan()
            from fishing_core.dungeon_runtime import start_dungeon,validate_supported
            validate_supported(plan)
            self._preparar_vista_pesca()
            game=focus_window('Steam')
            self.p_control,self.channel,self.launch_mutex=start_dungeon(game,plan)
            self.p_catch=None
            self.session_feed=SessionFeed(self.channel.directory,self.channel.run_id)
            self.session_feed.path=self.channel.directory/'dungeon_events.jsonl'
            self.panel_state=None
            self.active_mode='Dungeons'
            self.bot_activo=True
            self.dungeon_panel.status.configure(text='Dungeon iniciada · F8 detiene')
            self._actualizar_ui()
        except (Exception,KeyboardInterrupt) as exc:
            self._after_idle()
            self.dungeon_panel.status.configure(text='No iniciada: '+str(exc))

    def detener_bot(self):
        """Detener todos los procesos del bot."""
        if self.p_catch is None and self.p_control is None:
            self._log("⚠️  El bot no está activo")
            return

        self._log("🛑 Deteniendo bot...")

        self._after_idle()
        if not self.bot_activo:
            self._consume_events()
            if self.panel_state is not None and not self.panel_state.terminal:
                self.panel_state.activity = "Detenido por el usuario"
                self.panel_state.terminal = True
            self._log("✅ Ambos motores detenidos")

    def reiniciar_bot(self):
        """Reiniciar todos los procesos del bot."""
        if getattr(self,'active_mode','Fishing')=='Dungeons':return
        self._log("🔄 Reiniciando bot...")
        self.detener_bot()
        time.sleep(0.5)
        self.iniciar_bot()

    def _on_close(self):
        """Manejar el cierre de la ventana."""
        self._log("👋 Cerrando aplicación...")
        self.stop_event.set()
        self.detener_bot()
        if self.bot_activo:
            self.stop_event.clear()
            self._log("No se cierra el panel mientras quede un motor vivo.")
            return
        self.destroy()


# ============================================================
# Punto de entrada
# ============================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--iniciar", action="store_true", help="Iniciar pesca normal tras abrir el panel")
    args = parser.parse_args()
    # Configurar tema oscuro
    ctk.set_appearance_mode("dark")

    # Crear y ejecutar la aplicación
    app = FishingBotApp()
    if args.iniciar:
        app.after(700, app.iniciar_bot)
    app.mainloop()
