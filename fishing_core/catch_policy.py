"""Caso inicial separado del predictor historico, comprobable en replay.

Solo la aparicion ya en 100%, confirmada en dos capturas, puede usar esta
ruta. Exige continuidad y proyeccion dentro de la franja central. El resto
conserva Theil-Sen y sus rutas; no se relajan sus umbrales.
"""

from dataclasses import replace


class CatchPolicy:
    def __init__(self):
        self.reset()

    def reset(self):
        self.first_seen=None
        self.previous=None
        self.previous_pct=None

    def seen(self,when):
        if self.first_seen is None:
            self.first_seen=when

    def miss(self):
        self.previous=None
        self.previous_pct=None

    def evaluate(self,obs,pct,decision,cfg):
        previous,previous_pct=self.previous,self.previous_pct
        self.previous,self.previous_pct=obs,pct
        if decision.disparar or previous is None or self.first_seen is None:
            return decision
        if decision.motivo == "FIT_CURRENT_SAMPLE_MISMATCH":
            return decision
        if decision.n>=cfg.min_muestras and decision.residual>cfg.max_residual_px:
            return decision
        dt=obs.t_captura-previous.t_captura
        horizon=decision.horizonte_ms/1000
        if (pct != 100 or previous_pct != 100 or not .003 <= dt <= cfg.dt_max_seg
                or not 0 <= obs.t_captura-self.first_seen <= .25 or horizon > .06):
            return decision
        if abs(obs.ancho_zona-previous.ancho_zona)>max(5,previous.ancho_zona*.15):
            return decision
        velocity=(obs.delta-previous.delta)/dt
        projected=obs.delta+velocity*horizon
        corridor=obs.ancho_zona/2-4
        if corridor<=0 or abs(velocity)>1200 or abs(obs.delta)>corridor or abs(projected)>corridor:
            return decision
        intersection=max(0,min(projected+obs.ancho_pez/2,obs.ancho_zona/2)
                         -max(projected-obs.ancho_pez/2,-obs.ancho_zona/2))
        return replace(decision,disparar=True,motivo="APARICION_100_CONFIRMADA",
                       delta_pred=projected,v=velocity,n=2,span_ms=dt*1000,
                       dt_frame_ms=dt*1000,overlap_pred=intersection/obs.ancho_pez)
