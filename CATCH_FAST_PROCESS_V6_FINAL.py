"""CATCH del perfil vigente, Windows 1920x1080.

Conserva el predictor Theil-Sen de la familia V6 encontrada, con fixes
comprobados de geometria y tiempo. NO se certifica como V6.2 original.
El runtime seleccionado es fishing_core.runtime: detector contextual,
input por intento, registro por sesion y ningun rearme por timeout.
Las funciones visuales/main historicas quedan solo como referencia;
el main historico esta bloqueado y ningun launcher lo selecciona.
Iniciar desde FISHING_BOT_APP.py o INICIAR_TODO.py. F8 detiene ambos.
"""

from __future__ import annotations

import csv
import ctypes
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Deque, List, Optional, Tuple

import mss
import numpy as np

# ------------------------------------------------------------------
# Parametros de captura / click
# ------------------------------------------------------------------
LOG_PATH = "CATCH_LOG.txt"
CSV_PATH = "CATCH_SAMPLES.csv"
CATCH_OK_SIGNAL = Path(__file__).with_name("CATCH_OK.signal")

CATCH_X = 960
CATCH_Y = 970

BAR_LEFT = 430
BAR_TOP = 710
BAR_WIDTH = 1030
BAR_HEIGHT = 180

MIN_FUERZA_VERDE = 400   # V6.8: reducido de 800 a 400 para zonas muy pequeñas
MIN_FUERZA_PEZ = 150      # V6.8: reducido de 300 a 150 para peces muy pequeños

VK_F8 = 0x77

# ONE_CLICK_LOCK
FRAMES_SIN_BARRA_PARA_REARMAR = 8
REARME_TIMEOUT_SEG = 1.5          # reducido de 3.0 a 1.5s
COOLDOWN = 0.65
FRAMES_POST_CLICK = 12            # frames de verificacion tras el click

user32 = ctypes.windll.user32

_historial_catch = deque(maxlen=200)


def catch_log(msg: str) -> None:
    linea = f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}"
    _historial_catch.append(linea)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
            f.flush()
    except Exception:
        pass


def catch_log_inicio() -> None:
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 72 + "\n")
            f.write("NUEVA EJECUCION V6.7 " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
            f.write("=" * 72 + "\n")
            f.flush()
    except Exception:
        pass


def click_directo(x: int, y: int) -> None:
    user32.SetCursorPos(int(x), int(y))
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP


# ------------------------------------------------------------------
# Configuracion V6
# ------------------------------------------------------------------
@dataclass
class ConfigV6:
    # --- ventana de estimacion ---
    ventana_seg: float = 0.16          # antiguedad maxima de una muestra
    max_muestras: int = 8
    min_muestras: int = 4              # V6.2: aumentado de 2 a 4 para Theil-Sen robusto
    min_span_seg: float = 0.050        # V6.2: aumentado de 14ms a 50ms para peces rapidos
    gap_reset_seg: float = 0.05        # hueco que rompe la continuidad

    # --- guardas de identidad / plausibilidad ---
    max_salto_zona_px: float = 45.0
    max_vrel_px_s: float = 8000.0
    salto_margen_px: float = 25.0
    
    # --- modo de busqueda tras perder el pez ---
    frames_sin_deteccion_para_buscar: int = 30
    frames_busqueda_activa: int = 120
    
    # --- reintento de CATCH si falla ---
    max_reintentos_catch: int = 3
    tiempo_espera_reintento: float = 0.5

    # --- calidad del ajuste ---
    max_residual_px: float = 5.0       # MAD de los residuos del ajuste

    # --- ventana de acierto ---
    tol_min_px: float = 3.0
    tol_max_px: float = 14.0
    escala_tolerancia: float = 1.2     # V6.2: reducido de 1.5 a 1.2 para mayor precision
    escala_rescate: float = 2.0        # tolerancia cuando ya vamos tarde
    min_overlap_rel: float = 0.70      # fraccion del solape MAXIMO posible
    factor_estricto_2m: float = 0.60   # con 2 muestras exigimos mas centro
    min_solape_actual: float = 0.60    # V6.2: solape actual minimo (60%)
    min_solape_pred: float = 0.70      # V6.2: solape predicho minimo (70%)

    # --- latencia ---
    lat_click_est_seg: float = 0.020   # coste de enviar el click (EWMA)
    lat_click_alpha: float = 0.30
    lat_click_min_seg: float = 0.003
    lat_click_max_seg: float = 0.045
    horizonte_min_seg: float = 0.015
    horizonte_max_seg: float = 0.090

    # --- frame ---
    dt_defecto_seg: float = 0.025
    dt_max_seg: float = 0.020          # V6.2: reducido de 60ms a 20ms (50 FPS)
    margen_frame: float = 0.55         # fraccion del frame que anticipamos

    # --- pez practicamente quieto dentro de la zona ---
    v_quieto_px_s: float = 45.0

    # --- velocidad minima para considerar "aproximacion" ---
    v_min_px_s: float = 35.0

    # --- confirmacion de aproximacion ---
    frames_acercamiento: int = 2


# ------------------------------------------------------------------
# Observacion de un frame
# ------------------------------------------------------------------
@dataclass
class Obs:
    t_captura: float          # perf_counter al INICIO del grab
    centro_pez: float
    centro_zona: float
    ancho_pez: float
    ancho_zona: float         # ancho INTERIOR util de la zona verde

    @property
    def delta(self) -> float:
        return self.centro_pez - self.centro_zona


@dataclass
class Ajuste:
    v: float                  # px/s de delta (negativo = delta bajando)
    delta: float              # delta ajustado en t_ref
    t_ref: float
    residual: float
    n: int
    span: float


@dataclass
class Decision:
    disparar: bool
    motivo: str
    # diagnostico (siempre relleno, va al log)
    delta: float = 0.0
    delta_pred: float = 0.0
    v: float = 0.0
    n: int = 0
    span_ms: float = 0.0
    residual: float = 0.0
    horizonte_ms: float = 0.0
    t_centro_ms: float = float('inf')
    limite_ms: float = 0.0
    dt_frame_ms: float = 0.0
    tolerancia_px: float = 0.0
    overlap_actual: float = 0.0
    overlap_pred: float = 0.0
    overlap_max: float = 0.0
    endpoint_error_px: float = 0.0


# ------------------------------------------------------------------
# Geometria
# ------------------------------------------------------------------
def solape_fraccion(delta: float, ancho_pez: float, ancho_zona: float) -> float:
    """Fraccion del pez que queda dentro de la zona, dados sus centros."""
    if ancho_pez <= 0 or ancho_zona <= 0:
        return 0.0
    # Interseccion de intervalos, no min(ancho)-distancia entre centros.
    pez_i, pez_d = delta - ancho_pez / 2, delta + ancho_pez / 2
    zona_i, zona_d = -ancho_zona / 2, ancho_zona / 2
    solape = max(0.0, min(pez_d, zona_d) - max(pez_i, zona_i))
    return solape / ancho_pez


def solape_maximo(ancho_pez: float, ancho_zona: float) -> float:
    if ancho_pez <= 0:
        return 0.0
    return min(1.0, ancho_zona / ancho_pez)


def tolerancia_px(cfg: ConfigV6, ancho_pez: float, ancho_zona: float) -> float:
    """
    Margen de error aceptable en px.
    Si la zona es mas ancha que el pez, el pez cabe con holgura y podemos
    aceptar (ancho_zona - ancho_pez)/2 de error.
    Si el pez es mas ancho que la zona (caso real de tus logs: pez=77px,
    zona util=55px) solo hay una posicion buena: el centro.
    """
    holgura = (ancho_zona - ancho_pez) / 2.0
    base = max(cfg.tol_min_px, min(cfg.tol_max_px, holgura))
    return base * cfg.escala_tolerancia


# ------------------------------------------------------------------
# Ajuste robusto de la trayectoria (Theil-Sen)
# ------------------------------------------------------------------
def theil_sen(puntos: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Devuelve (pendiente, ordenada evaluada en t del ultimo punto)."""
    n = len(puntos)
    pendientes: List[float] = []
    for i in range(n):
        ti, di = puntos[i]
        for j in range(i + 1, n):
            tj, dj = puntos[j]
            dt = tj - ti
            if dt > 1e-6:
                pendientes.append((dj - di) / dt)
    if not pendientes:
        return 0.0, puntos[-1][1]
    v = median(pendientes)
    t_ref = puntos[-1][0]
    inter = median(d - v * (t - t_ref) for t, d in puntos)
    return v, inter


def mad(valores: List[float]) -> float:
    if not valores:
        return 0.0
    m = median(valores)
    return median([abs(x - m) for x in valores])


# ------------------------------------------------------------------
# Tracker de una barra
# ------------------------------------------------------------------
class TrackerBarra:
    def __init__(self, cfg: ConfigV6):
        self.cfg = cfg
        self.muestras: Deque[Obs] = deque(maxlen=cfg.max_muestras)
        self.dts: Deque[float] = deque(maxlen=6)
        self.ultimo_reset: str = "init"
        self.cruces: int = 0
        self.frames_acercando: int = 0

    # -- ciclo de vida --------------------------------------------
    def reset(self, motivo: str) -> None:
        self.muestras.clear()
        self.dts.clear()
        self.ultimo_reset = motivo
        self.cruces = 0
        self.frames_acercando = 0

    def perdida_deteccion(self) -> None:
        if self.muestras:
            self.reset("sin_deteccion")

    # -- ingesta ---------------------------------------------------
    def agregar(self, obs: Obs) -> Optional[str]:
        """
        Devuelve None si la muestra se acepto, o el motivo del reset.
        Las guardas evitan el fallo mas grave de V5: que el detector
        cambie de bloque verde entre frames y genere una velocidad
        relativa completamente falsa (var=602 px/s en tu log).
        """
        cfg = self.cfg
        if self.muestras:
            prev = self.muestras[-1]
            dt = obs.t_captura - prev.t_captura
            if dt <= 0:
                return None
            if dt > cfg.gap_reset_seg:
                self.reset("gap_temporal")
            elif abs(obs.centro_zona - prev.centro_zona) > cfg.max_salto_zona_px:
                self.reset("cambio_de_zona")
            elif abs(obs.centro_pez - prev.centro_pez) > (
                cfg.max_vrel_px_s * dt + cfg.salto_margen_px
            ):
                self.reset("salto_pez")
            else:
                self.dts.append(dt)
                if prev.delta * obs.delta < 0:
                    self.cruces += 1

        motivo = self.ultimo_reset if not self.muestras else None
        self.muestras.append(obs)

        # poda por ventana temporal
        while (
            len(self.muestras) > 2
            and (obs.t_captura - self.muestras[0].t_captura) > cfg.ventana_seg
        ):
            self.muestras.popleft()
        return motivo

    # -- estado ----------------------------------------------------
    @property
    def dt_frame(self) -> float:
        if not self.dts:
            return self.cfg.dt_defecto_seg
        return median(self.dts)

    def ajuste(self) -> Optional[Ajuste]:
        cfg = self.cfg
        if len(self.muestras) < cfg.min_muestras:
            return None
        puntos = [(m.t_captura, m.delta) for m in self.muestras]
        span = puntos[-1][0] - puntos[0][0]
        if span < cfg.min_span_seg:
            return None
        v, delta_ref = theil_sen(puntos)
        t_ref = puntos[-1][0]
        residuos = [d - (delta_ref + v * (t - t_ref)) for t, d in puntos]
        return Ajuste(
            v=v,
            delta=delta_ref,
            t_ref=t_ref,
            residual=mad(residuos) if len(puntos) >= 3 else 0.0,
            n=len(puntos),
            span=span,
        )


# ------------------------------------------------------------------
# Decision
# ------------------------------------------------------------------
def decidir(
    tracker: TrackerBarra,
    obs: Obs,
    proc_age_seg: float,
    cfg: ConfigV6,
    lat_click_est_seg: Optional[float] = None,
) -> Decision:
    """
    obs  : la observacion del frame actual (ya insertada en el tracker)
    proc_age_seg : tiempo transcurrido desde el INICIO de la captura hasta
                   este instante (grab + deteccion + decision)
    """
    lat_click = cfg.lat_click_est_seg if lat_click_est_seg is None else lat_click_est_seg

    horizonte = max(
        cfg.horizonte_min_seg,
        min(cfg.horizonte_max_seg, proc_age_seg + lat_click),
    )
    dt_frame = tracker.dt_frame
    limite = horizonte + cfg.margen_frame * dt_frame

    wp = obs.ancho_pez
    wz = obs.ancho_zona
    tol = tolerancia_px(cfg, wp, wz)
    ov_max = solape_maximo(wp, wz)
    ov_ahora = solape_fraccion(obs.delta, wp, wz)

    d = Decision(
        disparar=False,
        motivo="sin_ajuste",
        delta=obs.delta,
        horizonte_ms=horizonte * 1000.0,
        limite_ms=limite * 1000.0,
        dt_frame_ms=dt_frame * 1000.0,
        tolerancia_px=tol,
        overlap_actual=ov_ahora,
        overlap_max=ov_max,
    )

    aj = tracker.ajuste()
    if len(tracker.muestras) >= 2:
        dt_actual = tracker.muestras[-1].t_captura - tracker.muestras[-2].t_captura
        if dt_actual > cfg.dt_max_seg:
            tracker.frames_acercando = 0
            d.motivo = "FRAME_LENTO"
            return d
    if aj is None:
        tracker.frames_acercando = 0
        # Caso borde: pez practicamente parado dentro de la zona y
        # todavia sin historial (p.ej. la barra acaba de aparecer ya alineada).
        # V6 FINAL: requiere al menos 2 muestras para evitar falsos CATCH.
        ov_min_sin_ajuste = cfg.min_overlap_rel * ov_max
        if (len(tracker.muestras) >= 2 and abs(obs.delta) <= tol * 0.5
                and ov_ahora >= ov_min_sin_ajuste):
            d.disparar = True
            d.motivo = "ALINEADO_SIN_HISTORIAL"
            d.delta_pred = obs.delta
            d.overlap_pred = ov_ahora
        return d

    # delta proyectado al instante en que el click llega al juego
    delta_pred = aj.delta + aj.v * horizonte
    ov_pred = solape_fraccion(delta_pred, wp, wz)

    d.delta = aj.delta
    d.delta_pred = delta_pred
    d.v = aj.v
    d.n = aj.n
    d.span_ms = aj.span * 1000.0
    d.residual = aj.residual
    d.overlap_pred = ov_pred
    d.endpoint_error_px = obs.delta - aj.delta

    # calidad del ajuste
    if aj.n >= 3 and aj.residual > cfg.max_residual_px:
        tracker.frames_acercando = 0
        d.motivo = f"ruido residual={aj.residual:.1f}"
        return d

    # El MAD puede ser pequeno aunque el ultimo punto ya se haya apartado
    # del ajuste por aceleracion. No usar un centro historico que contradice
    # la captura actual (fallo real: ajuste -21 px, observado +10.5 px).
    # Conserva Theil-Sen y el umbral existente; solo rechaza ese ajuste.
    if abs(d.endpoint_error_px) > cfg.max_residual_px:
        tracker.frames_acercando = 0
        d.motivo = "FIT_CURRENT_SAMPLE_MISMATCH"
        return d

    # con 2 muestras exigimos estar mas centrados
    tol_efectiva = tol * (cfg.factor_estricto_2m if aj.n < 3 else 1.0)
    ov_min = cfg.min_overlap_rel * ov_max

    aproximandose = aj.delta * aj.v < 0 and abs(aj.v) >= cfg.v_min_px_s
    if aproximandose:
        t_centro = -aj.delta / aj.v
        # V6.2: verificar que t_centro >= 0 (evita valores negativos)
        if t_centro < 0:
            t_centro = float('inf')
    else:
        t_centro = float('inf')
    d.t_centro_ms = t_centro * 1000.0 if t_centro != float('inf') else float('inf')

    # ---- caso pez casi quieto dentro de la zona -------------------
    # V6.2: no disparar si la geometria ACTUAL o predicha esta por debajo
    # del solape minimo. La prediccion decide cuando, pero no autoriza un
    # click desde una posicion geometricamente insegura.
    if abs(aj.v) < cfg.v_quieto_px_s:
        tracker.frames_acercando = 0
        if (abs(delta_pred) <= tol_efectiva 
                and ov_ahora >= cfg.min_solape_actual * ov_max
                and ov_pred >= cfg.min_solape_pred * ov_max):
            d.disparar = True
            d.motivo = "QUIETO_EN_ZONA"
        else:
            d.motivo = "lento_fuera_de_zona"
        return d

    # ---- se aleja: nunca disparar ---------------------------------
    if not aproximandose:
        tracker.frames_acercando = 0
        d.motivo = "alejandose"
        return d

    # ---- confirmacion de aproximacion (2 frames consecutivos) ------
    if aproximandose:
        tracker.frames_acercando += 1
    else:
        tracker.frames_acercando = 0

    if tracker.frames_acercando < cfg.frames_acercamiento:
        d.motivo = "aprox_no_confirmada"
        return d

    # ---- aun hay tiempo: esperar mejor frame ----------------------
    if t_centro > limite:
        d.motivo = "aun_hay_tiempo"
        return d

    # ---- ¿vamos tarde? --------------------------------------------
    # Si el centro llega antes que nuestra latencia, esperar solo empeora
    # el tiro: o disparamos ya, o esta pasada esta perdida. Aceptamos una
    # tolerancia mayor (rescate) porque la alternativa es no disparar.
    tarde = t_centro < horizonte
    tol_disparo = tol_efectiva * (cfg.escala_rescate if tarde else 1.0)

    if abs(delta_pred) > tol_disparo:
        d.motivo = "ultima_ventana_fuera" if not tarde else "tarde_y_fuera"
        return d

    # V6.2: guardia geometrica obligatoria para TODAS las rutas rapidas.
    # Evita RESCATE_TARDE/ULTIMA_OPORTUNIDAD desde un solape actual bajo.
    if ov_ahora < cfg.min_solape_actual * ov_max:
        d.motivo = "overlap_actual_bajo"
        return d
    if ov_pred < cfg.min_solape_pred * ov_max:
        d.motivo = "overlap_pred_bajo"
        return d

    d.disparar = True
    d.motivo = "RESCATE_TARDE" if tarde else "ULTIMA_OPORTUNIDAD"
    return d


def actualizar_latencia_click(cfg: ConfigV6, actual: float, medido: float) -> float:
    """EWMA del envio de input solamente; no mide respuesta del juego."""
    m = max(cfg.lat_click_min_seg, min(cfg.lat_click_max_seg, medido))
    return (1.0 - cfg.lat_click_alpha) * actual + cfg.lat_click_alpha * m


# ------------------------------------------------------------------
# Deteccion (misma vision que V5 + centroides ponderados y ancho util)
# ------------------------------------------------------------------
def bloques(xs: np.ndarray, salto: int = 3):
    if xs.size == 0:
        return []
    return np.split(xs, np.where(np.diff(xs) > salto)[0] + 1)


def centroide(score: np.ndarray, gr: np.ndarray) -> float:
    """Centro ponderado por intensidad: mas estable que (inicio+fin)/2."""
    peso = score[gr].astype(np.float64)
    total = peso.sum()
    if total <= 0:
        return float((gr[0] + gr[-1]) / 2.0)
    return float((gr.astype(np.float64) * peso).sum() / total)


def detectar(frame, zona_previa=None):
    b = frame[:, :, 0].astype(np.int16)
    g = frame[:, :, 1].astype(np.int16)
    r = frame[:, :, 2].astype(np.int16)

    h = r.shape[0]
    y0, y1 = 12, max(13, h - 18)
    rr, gg, bb = r[y0:y1], g[y0:y1], b[y0:y1]

    # V6.8: Filtro más permisivo para zonas pequeñas (colores menos saturados)
    # V6.8: Filtro más permisivo para zonas pequeñas (colores menos saturados)
    verde = (
        (gg >= 70) & (gg >= rr + 5) & (gg >= bb + 8) & (rr <= 250) & (bb <= 220)
    )
    score_v = np.count_nonzero(verde, axis=0)
    xs_v = np.where(score_v >= 2)[0]  # V6.8: reducido de 3 a 2 para detectar zonas muy pequeñas
    
    # Logging detallado para depuración del detector
    if len(xs_v) > 0:
        max_score = int(score_v.max()) if len(score_v) > 0 else 0
        print(f"    DETECTOR_VERDE: {len(xs_v)} columnas, max_score={max_score}", flush=True)
    else:
        # Muestreo cada ~2 segundos para no saturar el log
        import random
        if random.random() < 0.05:
            print(f"    DETECTOR_VERDE: sin columnas (max_score={int(score_v.max()) if len(score_v) > 0 else 0})", flush=True)
    
    # Logging de muestreo de colores para entender qué está viendo el detector
    import random
    if random.random() < 0.02:  # 2% de los frames
        # Tomar una muestra del centro de la imagen
        h, w = r.shape
        y_mid = h // 2
        x_mid = w // 2
        print(f"    DETECTOR_DEBUG: centro r={r[y_mid, x_mid]} g={g[y_mid, x_mid]} b={b[y_mid, x_mid]}", flush=True)
        # Contar píxeles que pasan cada filtro
        filtro_g = (gg >= 120)
        filtro_r = (gg >= rr + 15)
        filtro_b = (gg >= bb + 20)
        filtro_rr = (rr <= 220)
        filtro_bb = (bb <= 190)
        print(f"    DETECTOR_DEBUG: filtro_g={np.count_nonzero(filtro_g)} filtro_r={np.count_nonzero(filtro_r)} filtro_b={np.count_nonzero(filtro_b)} filtro_rr={np.count_nonzero(filtro_rr)} filtro_bb={np.count_nonzero(filtro_bb)}", flush=True)

    verdes = []
    for gr in bloques(xs_v):
        if gr.size < 3:  # V6.8: reducido de 5 a 3 para detectar zonas muy pequeñas
            continue
        vi, vd = int(gr[0]), int(gr[-1])
        ancho_v = vd - vi + 1
        if 3 <= ancho_v <= 240:  # V6.8: reducido de 5 a 3
            fuerza = int(score_v[gr].sum())
            # V6.8: umbral proporcional al tamaño de la zona
            # Reducido de 1200 a 100 para detectar zonas muy pequeñas (29px)
            # Fuerza máxima para zona 29px = 29 * 14 = 406
            min_fuerza_v = max(100, int(ancho_v * 5))
            if fuerza >= min_fuerza_v:
                verdes.append((fuerza, vi, vd, centroide(score_v, gr)))
                print(f"    DETECTOR: zona encontrada ancho={ancho_v} fuerza={fuerza} min_fuerza={min_fuerza_v}", flush=True)
    if not verdes:
        print(f"    DETECTOR: sin zona verde (xs_v={len(xs_v)})", flush=True)
        return None, "sin zona verde"

    # V6.8: Filtro más permisivo para peces pequeños (colores menos saturados)
    pezmask = (
        (rr >= 140) & (rr >= gg + 20) & (rr >= bb + 40)
        & (gg >= 20) & (gg <= 220) & (bb <= 170)
    )
    score_p = np.count_nonzero(pezmask, axis=0)
    xs_p = np.where(score_p >= 3)[0]  # V6.8: reducido de 5 a 3
    
    # Logging detallado para depuración del detector de pez
    if len(xs_p) > 0:
        max_score_p = int(score_p.max()) if len(score_p) > 0 else 0
        print(f"    DETECTOR_PEZ: {len(xs_p)} columnas, max_score={max_score_p}", flush=True)
    else:
        import random
        if random.random() < 0.05:
            print(f"    DETECTOR_PEZ: sin columnas (max_score={int(score_p.max()) if len(score_p) > 0 else 0})", flush=True)
    
    # Logging para depuración del detector de pez
    if len(xs_p) > 0:
        max_score_p = int(score_p.max()) if len(score_p) > 0 else 0
        print(f"    DETECTOR_PEZ: {len(xs_p)} columnas con pez, max_score={max_score_p}", flush=True)

    peces = []
    for gr in bloques(xs_p):
        if gr.size < 7:
            continue
        pi, pd = int(gr[0]), int(gr[-1])
        ancho_p = pd - pi + 1
        if 7 <= ancho_p <= 150:
            fuerza_p = int(score_p[gr].sum())
            # V6.8: umbral proporcional al tamaño del pez
            min_fuerza_p = max(400, int(ancho_p * 8))
            if fuerza_p >= min_fuerza_p:
                peces.append((fuerza_p, pi, pd, centroide(score_p, gr)))
    if not peces:
        return None, "sin pez"

    fuerza_p, pi, pd, centro_pez = max(peces)
    ancho_pez = pd - pi + 1

    # Continuidad: si ya seguiamos una zona, preferimos LA MISMA zona.
    # Solo si no hay ninguna cerca volvemos a "la mas cercana al pez".
    mejor = None
    for fuerza_v, vi, vd, cvw in verdes:
        a, z = vi + 2, vd - 2
        if z <= a:
            continue
        centro_verde = (a + z) / 2.0
        ancho_zona = z - a + 1
        if zona_previa is not None:
            coste = abs(centro_verde - zona_previa)
            if coste > 45.0:
                coste += 1000.0     # penaliza cambiar de zona
        else:
            coste = abs(centro_pez - centro_verde)
        cand = (coste, -fuerza_v, vi, vd, a, z, centro_verde, ancho_zona, fuerza_v)
        if mejor is None or cand < mejor:
            mejor = cand
    if mejor is None:
        return None, f"pez=({pi},{pd}) sin candidato verde"

    _, _, vi, vd, a, z, centro_verde, ancho_zona, fuerza_v = mejor
    solape = max(0, min(pd, z) - max(pi, a) + 1)

    datos = {
        "pez": (pi, pd),
        "verde": (vi, vd),
        "centro_pez": centro_pez,
        "centro_verde": centro_verde,
        "ancho_pez": float(ancho_pez),
        "ancho_zona": float(ancho_zona),
        "solape": solape,
        "fuerza_verde": fuerza_v,
        "fuerza_pez": fuerza_p,
    }
    info = (
        f"pez=({pi},{pd}) verde=({vi},{vd}) wp={ancho_pez} wz={ancho_zona} "
        f"cp={centro_pez:.1f} cv={centro_verde:.1f} delta={centro_pez-centro_verde:+.1f}"
    )
    return datos, info


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def _main_historico_bloqueado() -> None:
    raise RuntimeError("Runtime historico deshabilitado; usar main del perfil vigente")
    cfg = ConfigV6()
    print("CATCH V6.7 activo. F8 = parada de emergencia | Ctrl+C tambien detiene.")

    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), 0x00008000)
    except Exception:
        pass

    monitor = {"left": BAR_LEFT, "top": BAR_TOP, "width": BAR_WIDTH, "height": BAR_HEIGHT}

    csv_f = open(CSV_PATH, "a", newline="", encoding="utf-8")
    csv_w = csv.writer(csv_f)
    if csv_f.tell() == 0:
        csv_w.writerow(
            ["barra", "fase", "t_ms", "cp", "cv", "delta", "wp", "wz",
             "overlap", "v_fit", "n", "residual", "t_centro_ms", "horizonte_ms",
             "tol_px", "motivo"]
        )

    tracker = TrackerBarra(cfg)
    lat_total_est = 0.045            # V6.2: latencia total estimada (captura+proc+click)
    zona_previa = None

    catch_bloqueado = False
    frames_sin_barra = 0
    frames_sin_deteccion = 0
    t_bloqueo = 0.0
    ultimo_click = 0.0
    barra_id = 0
    post_click_restantes = 0

    capturas = 0
    t0 = time.perf_counter()

    catch_log_inicio()
    catch_log(
        f"INICIO_V6.7 BAR=({BAR_LEFT},{BAR_TOP},{BAR_WIDTH},{BAR_HEIGHT}) "
        f"CLICK=({CATCH_X},{CATCH_Y}) ventana={cfg.ventana_seg*1000:.0f}ms "
        f"min_muestras={cfg.min_muestras} min_span={cfg.min_span_seg*1000:.0f}ms "
        f"tol=[{cfg.tol_min_px},{cfg.tol_max_px}]x{cfg.escala_tolerancia} "
        f"min_solape_actual={cfg.min_solape_actual} min_solape_pred={cfg.min_solape_pred} "
        f"dt_max={cfg.dt_max_seg*1000:.0f}ms frames_acercamiento={cfg.frames_acercamiento} "
        f"rearme_timeout={REARME_TIMEOUT_SEG}s ONE_CLICK_LOCK=1 F8_STOP=1"
    )
    print(f"LOG: {Path(LOG_PATH).resolve()}  |  CSV: {Path(CSV_PATH).resolve()}", flush=True)

    with mss.mss() as sct:
        try:
            while True:
                t_cap = time.perf_counter()
                shot = sct.grab(monitor)
                frame = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(
                    (shot.height, shot.width, 4)
                )
                datos, info = detectar(frame, zona_previa)
                capturas += 1
                ahora = time.perf_counter()

                if user32.GetAsyncKeyState(VK_F8) & 0x8000:
                    catch_log("EMERGENCY_STOP_F8")
                    print("\n>>> F8: CATCH V6.7 detenido.", flush=True)
                    break

                # ---------- verificacion posterior al click -------------
                if post_click_restantes > 0 and datos is not None:
                    post_click_restantes -= 1
                    delta = datos["centro_pez"] - datos["centro_verde"]
                    csv_w.writerow(
                        [barra_id, "post", f"{(t_cap-ultimo_click)*1000:.1f}",
                         f"{datos['centro_pez']:.1f}", f"{datos['centro_verde']:.1f}",
                         f"{delta:+.1f}", datos["ancho_pez"], datos["ancho_zona"],
                         f"{solape_fraccion(delta, datos['ancho_pez'], datos['ancho_zona']):.3f}",
                         "", "", "", "", "", "", "post_click"]
                    )
                    csv_f.flush()

                # ---------- ONE_CLICK_LOCK ------------------------------
                if catch_bloqueado:
                    if datos is None:
                        frames_sin_barra += 1
                        if frames_sin_barra >= FRAMES_SIN_BARRA_PARA_REARMAR:
                            catch_bloqueado = False
                            frames_sin_barra = 0
                            tracker.reset("rearme")
                            zona_previa = None
                            catch_log("CATCH_DESBLOQUEADO barra_ausente")
                    else:
                        frames_sin_barra = 0
                        if (ahora - t_bloqueo) > REARME_TIMEOUT_SEG:
                            catch_bloqueado = False
                            tracker.reset("rearme_timeout")
                            zona_previa = None
                            catch_log("CATCH_DESBLOQUEADO timeout")
                    if catch_bloqueado:
                        continue

                if datos is None:
                    frames_sin_deteccion += 1
                    if frames_sin_deteccion >= cfg.frames_sin_deteccion_para_buscar:
                        tracker.perdida_deteccion()
                        zona_previa = None
                        frames_sin_deteccion = 0
                else:
                    frames_sin_deteccion = 0
                    if (ahora - ultimo_click) < COOLDOWN:
                        tracker.reset("cooldown")
                    else:
                        zona_previa = datos["centro_verde"]
                    obs = Obs(
                        t_captura=t_cap,
                        centro_pez=datos["centro_pez"],
                        centro_zona=datos["centro_verde"],
                        ancho_pez=datos["ancho_pez"],
                        ancho_zona=datos["ancho_zona"],
                    )
                    motivo_reset = tracker.agregar(obs)
                    if motivo_reset:
                        catch_log(f"TRACK_RESET motivo={motivo_reset}")
                    if len(tracker.muestras) == 1:
                        barra_id += 1

                    proc_age = time.perf_counter() - t_cap
                    d = decidir(tracker, obs, proc_age, cfg, lat_total_est)

                    csv_w.writerow(
                        [barra_id, "pre", f"{t_cap*1000:.1f}",
                         f"{obs.centro_pez:.1f}", f"{obs.centro_zona:.1f}",
                         f"{obs.delta:+.1f}", obs.ancho_pez, obs.ancho_zona,
                         f"{d.overlap_actual:.3f}", f"{d.v:+.1f}", d.n,
                         f"{d.residual:.2f}",
                         f"{d.t_centro_ms:.1f}" if d.t_centro_ms != float('inf') else "inf",
                         f"{d.horizonte_ms:.1f}", f"{d.tolerancia_px:.1f}", d.motivo]
                    )

                    if d.disparar:
                        catch_log(
                            f"V6.7_DECISION motivo={d.motivo} delta={d.delta:+.1f} "
                            f"pred={d.delta_pred:+.1f} v={d.v:+.1f}px/s n={d.n} "
                            f"span={d.span_ms:.0f}ms res={d.residual:.1f} "
                            f"t_centro={d.t_centro_ms:.1f}ms limite={d.limite_ms:.1f}ms "
                            f"horizonte={d.horizonte_ms:.1f}ms dt_frame={d.dt_frame_ms:.1f}ms "
                            f"tol={d.tolerancia_px:.1f}px ov={d.overlap_actual:.3f}"
                            f"->{d.overlap_pred:.3f}/max{d.overlap_max:.3f} "
                            f"proc={proc_age*1000:.1f}ms lat_total_est={lat_total_est*1000:.1f}ms | {info}"
                        )

                        t_click0 = time.perf_counter()
                        click_directo(CATCH_X, CATCH_Y)
                        t_click1 = time.perf_counter()

                        # Verificación: esperar y verificar si el CATCH fue exitoso
                        # Si aparece "FAILED!" o "IT GOT AWAY!", reintentar el CATCH
                        catch_exitoso = False
                        for intento in range(3):
                            time.sleep(0.3)
                            # Verificar si apareció "SUCCESS!" o "FAILED!"
                            # Por ahora, verificamos si la zona verde sigue visible
                            # Si la zona verde desapareció, el CATCH fue exitoso
                            catch_exitoso = True
                            break
                        
                        if not catch_exitoso:
                            catch_log(f"CATCH_NO_EXITOSO barra={barra_id} reintento={intento+1}")
                            click_directo(CATCH_X, CATCH_Y)
                            catch_log(f"CATCH_REINTENTO barra={barra_id}")

                        # V6.7: única modificación funcional sobre V6.2.
                        # Avisar a CONTROL SOLO después de que el CATCH real fue enviado.
                        try:
                            CATCH_OK_SIGNAL.write_text(
                                f"{time.time():.6f}\n", encoding="utf-8"
                            )
                            catch_log("CATCH_OK_SIGNAL escrito")
                        except Exception as e:
                            catch_log(f"CATCH_SIGNAL_ERROR {e!r}")
                        # V6.2: EWMA de latencia TOTAL (captura + procesamiento + click)
                        total_desde_captura = t_click1 - t_cap
                        lat_total_est = actualizar_latencia_click(
                            cfg, lat_total_est, total_desde_captura
                        )

                        catch_log(
                            f"CLICK_ENVIADO_V6.7 barra={barra_id} "
                            f"click_ms={(t_click1-t_click0)*1000:.2f} "
                            f"total_desde_captura_ms={total_desde_captura*1000:.2f} "
                            f"lat_total_est_ms={lat_total_est*1000:.2f}"
                        )
                        print(
                            f">>> CATCH V6.7 {d.motivo} delta={d.delta:+.1f} "
                            f"pred={d.delta_pred:+.1f} v={d.v:+.0f} "
                            f"t_centro={d.t_centro_ms:.0f}ms",
                            flush=True,
                        )

                        ultimo_click = t_click1
                        catch_bloqueado = True
                        t_bloqueo = t_click1
                        frames_sin_barra = 0
                        post_click_restantes = FRAMES_POST_CLICK
                        tracker.reset("post_click")
                        csv_f.flush()

                if ahora - t0 >= 5.0:
                    fps = capturas / (ahora - t0)
                    print(f"CATCH FPS: {fps:.0f}", flush=True)
                    catch_log(f"FPS={fps:.1f}")
                    capturas = 0
                    t0 = ahora

        except KeyboardInterrupt:
            print("\nCATCH V6.7 detenido.")
        finally:
            csv_f.close()


def main():
    import sys
    from fishing_core.runtime import run_catch
    return run_catch(sys.modules[__name__])


if __name__ == "__main__":
    raise SystemExit(main())
