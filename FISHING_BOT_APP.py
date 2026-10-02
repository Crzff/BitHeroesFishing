"""
FISHING_BOT_APP.py - Panel de control para el bot de pesca de Bit Heroes

Interfaz gráfica moderna y oscura usando CustomTkinter.
Controla los procesos CATCH y CONTROL directamente.

Uso:
    python FISHING_BOT_APP.py
"""

import os
import sys
import json
import time
import threading
import subprocess
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

# ============================================================
# Configuración
# ============================================================

HERE = Path(__file__).resolve().parent
CATCH_SCRIPT = HERE / "CATCH_FAST_PROCESS_V6_FINAL.py"
CONTROL_SCRIPT = HERE / "FISHING_CONTROL_PROCESS.py"

LOG_CATCH = HERE / "CATCH_LOG.txt"
LOG_CONTROL = HERE / "CONTROL_LOG.txt"
LOG_SAMPLES = HERE / "CATCH_SAMPLES.csv"

# Flags para subprocess
FLAGS = subprocess.CREATE_NEW_CONSOLE | 0x00000200

# Archivo de configuración
CONFIG_FILE = HERE / "fishing_bot_config.json"

# Colores
COLOR_BG = "#101010"
COLOR_CARD = "#1d1d1d"
COLOR_ACCENT = "#333333"
COLOR_SUCCESS = "#dedede"
COLOR_DANGER = "#b3b3b3"
COLOR_TEXT = "#eeeeee"
COLOR_TEXT_DIM = "#a3a3a3"


# ============================================================
# Clase principal de la aplicación
# ============================================================

class FishingBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

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
        self.monitor_thread = None
        self.log_thread = None
        self.stop_event = threading.Event()
        self.siempre_visible = False
        self.panel_state = None
        self.session_feed = None
        self._fishing_view = False
        self._normal_view = None

        # Construir interfaz
        self._build_ui()

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
        # Frame principal
        self.main_frame = ctk.CTkFrame(self, fg_color=COLOR_BG)
        self.main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        # Título
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="🎣 Bit Heroes Fishing Bot",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLOR_TEXT,
        )
        self.title_label.pack(pady=(0, 12))

        # Indicador de estado
        self.status_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_CARD, corner_radius=12)
        self.status_frame.pack(fill="x", pady=(0, 12))

        self.status_indicator = ctk.CTkLabel(
            self.status_frame,
            text="● DETENIDO",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLOR_DANGER,
        )
        self.status_indicator.pack(pady=12)

        # Frame de procesos
        self.procesos_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_CARD, corner_radius=12)
        self.procesos_frame.pack(fill="x", pady=(0, 12))

        self.procesos_title = ctk.CTkLabel(
            self.procesos_frame,
            text="Motores en ejecución",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_DIM,
        )
        self.procesos_title.pack(anchor="w", padx=12, pady=(12, 4))

        # Estado CATCH
        self.estado_catch = ctk.CTkLabel(
            self.procesos_frame,
            text="  CATCH: —",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_DIM,
        )
        self.estado_catch.pack(anchor="w", padx=12, pady=2)

        # Estado CONTROL
        self.estado_control = ctk.CTkLabel(
            self.procesos_frame,
            text="  CONTROL: —",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_DIM,
        )
        self.estado_control.pack(anchor="w", padx=12, pady=(2, 12))

        self.activity_label = ctk.CTkLabel(self.procesos_frame, text="Actividad: esperando inicio",
                                         text_color=COLOR_TEXT, font=ctk.CTkFont(size=14, weight="bold"),
                                         wraplength=470, justify="left")
        self.activity_label.pack(anchor="w", padx=12, pady=(0, 4))
        self.outcome_label = ctk.CTkLabel(self.procesos_frame, text="Sin resultados en esta sesión",
                                        text_color=COLOR_TEXT_DIM, wraplength=470, justify="left")
        self.outcome_label.pack(anchor="w", padx=12, pady=(0, 4))
        self.cast_label = ctk.CTkLabel(self.procesos_frame, text="CAST: sin lanzamiento en esta sesión",
                                       text_color=COLOR_TEXT_DIM, wraplength=470, justify="left")
        self.cast_label.pack(anchor="w", padx=12, pady=(0, 12))

        self.bait_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_CARD, corner_radius=12)
        self.bait_frame.pack(fill="x", pady=(0, 12))
        self.bait_label = ctk.CTkLabel(self.bait_frame, text="Cebos: sin lectura confirmada",
                                     text_color=COLOR_TEXT, font=ctk.CTkFont(size=14, weight="bold"), wraplength=470)
        self.bait_label.pack(anchor="w", padx=12, pady=(10, 4))
        self.bait_details = ctk.CTkLabel(self.bait_frame, text="Lectura automática al llegar a START",
                                       text_color=COLOR_TEXT_DIM, wraplength=470, justify="left")
        self.bait_details.pack(anchor="w", padx=12, pady=(0, 4))
        self.bait_note = ctk.CTkLabel(self.bait_frame, text="Pescas ≈ restantes · 1 cebo por CAST · conteo inicial único\nSin límite de ciclos · parada con 0 estimados · F8 detiene",
                                    text_color=COLOR_TEXT_DIM, font=ctk.CTkFont(size=11), wraplength=470)
        self.bait_note.pack(anchor="w", padx=12, pady=(0, 10))

        # Botones
        self.botones_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_BG)
        self.botones_frame.pack(fill="x", pady=(0, 12))

        self.btn_iniciar = ctk.CTkButton(
            self.botones_frame,
            text="▶  INICIAR BOT",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLOR_SUCCESS,
            hover_color="#bdbdbd",
            text_color="#101010",
            text_color_disabled="#707070",
            height=44,
            corner_radius=10,
            command=self.iniciar_bot,
        )
        self.btn_iniciar.pack(fill="x", pady=(0, 8))

        self.btn_detener = ctk.CTkButton(
            self.botones_frame,
            text="⏹  DETENER BOT",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_ACCENT,
            hover_color="#484848",
            height=38,
            corner_radius=10,
            command=self.detener_bot,
            state="disabled",
        )
        self.btn_detener.pack(fill="x", pady=(0, 8))

        self.btn_reiniciar = ctk.CTkButton(
            self.botones_frame,
            text="🔄  REINICIAR",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_ACCENT,
            hover_color="#484848",
            height=38,
            corner_radius=10,
            command=self.reiniciar_bot,
            state="disabled",
        )
        self.btn_reiniciar.pack(fill="x", pady=(0, 8))

        self.btn_siempre_visible = ctk.CTkButton(
            self.botones_frame,
            text="📌  SIEMPRE VISIBLE",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_ACCENT,
            hover_color="#484848",
            height=38,
            corner_radius=10,
            command=self.alternar_siempre_visible,
        )
        self.btn_siempre_visible.pack(fill="x")

        # Seleccion de esta sesion; no altera preferencias personales guardadas.
        self.game_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_CARD)
        self.game_frame.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(self.game_frame, text="Juego · visible y en primer plano").pack(side="left", padx=12)
        self.game_selector = ctk.CTkOptionMenu(self.game_frame, values=list(CLIENTS), width=115)
        self.game_selector.set("Auto")
        self.game_selector.pack(side="right", padx=12, pady=6)

        # Frame de logs
        self.logs_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_CARD, corner_radius=12)
        self.logs_frame.pack(fill="both", expand=True)

        self.logs_title = ctk.CTkLabel(
            self.logs_frame,
            text="📋 Logs en tiempo real",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_DIM,
        )
        self.logs_title.pack(anchor="w", padx=12, pady=(12, 4))

        # Visible solo en el panel normal; el frame de logs se oculta al pescar.
        self.btn_apoyar = None
        url = support_url(HERE)
        if url:
            self.btn_apoyar = ctk.CTkButton(
                self.logs_frame, text="♡  Apoyar en Ko-fi (opcional)",
                fg_color=COLOR_ACCENT, hover_color="#484848", height=26,
                command=self._abrir_apoyo,
            )
            self.btn_apoyar.pack(anchor="e", padx=12, pady=(0, 6))

        # Textbox de logs
        self.log_textbox = ctk.CTkTextbox(
            self.logs_frame,
            fg_color="#141414",
            scrollbar_button_color="#424242",
            scrollbar_button_hover_color="#606060",
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=11, family="Consolas"),
            corner_radius=8,
            wrap="none",
        )
        self.log_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_textbox.configure(state="disabled")

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
            self.btn_reiniciar.configure(state="normal")
        else:
            self.btn_iniciar.configure(state="normal")
            self.btn_detener.configure(state="disabled")
            self.btn_reiniciar.configure(state="disabled")

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
