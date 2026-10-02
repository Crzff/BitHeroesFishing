"""Entrada acotada HOME -> FISHING -> PLAY -> START, solo de CONTROL.

No reclama cebos gratis, no entra en Events/Shop y nunca envia START/CAST/CATCH.
Toda accion requiere identidad de pantalla estable y otra captura fresca.
"""

import time
from pathlib import Path

import numpy as np

from .control_flow import SafetyStop
from .vision import Evidence,FrameView,UIClassifier

NAV_ASSETS=Path(__file__).resolve().parent.parent/"assets/fishing_navigation.npz"
ROIS={
    "HOME_FISHING":(1750,880,1910,930),
    "HOME_SETTINGS":(1750,1025,1910,1080),
    "FISHING_TITLE":(780,230,1130,350),
    "FISHING_PLAY":(680,580,930,780),
    "FISHING_EVENTS":(960,555,1250,660),
}
ALREADY_FISHING={"START","CAST","CATCH_ACTIVE","CATCH_PENDING","SELECT_MENU","SUCCESS","FAILED","ITEMS"}


class NavigationClassifier:
    def __init__(self,asset_path=NAV_ASSETS):
        with np.load(asset_path,allow_pickle=False) as assets:
            if set(assets.files)!=set(ROIS):
                raise ValueError("Referencias de navegacion incompletas")
            self.templates={name:assets[name].astype(np.float32) for name in assets.files}

    def classify(self,view,existing=None):
        # Nunca reinterpretar un CAST/resultado/menu de cebos como HOME/PLAY.
        if existing is not None and existing.kind in ALREADY_FISHING:
            return existing
        found={name:UIClassifier.match(self,view,name,roi,threshold=.94) for name,roi in ROIS.items()}
        scores={name:score for name,(score,xy) in found.items()}
        if all(found[name][1] is not None for name in ("FISHING_TITLE","FISHING_PLAY","FISHING_EVENTS")):
            return Evidence("FISHING_MENU",found["FISHING_PLAY"][1],True,scores=scores)
        if all(found[name][1] is not None for name in ("HOME_FISHING","HOME_SETTINGS")):
            x,y=found["HOME_FISHING"][1]
            # Centro del icono inmediatamente encima de su etiqueta. Lejos
            # de Offers, Shop y otros modos; la disposicion es 1920x1080 fija.
            xy=(x,y-64)
            if 1760<=xy[0]<=1900 and 780<=xy[1]<=875:
                return Evidence("HOME",xy,True,scores=scores)
        return Evidence(scores=scores)


def enter_fishing(io,ui,grab,stop,log,*,navigator=None,timeout=60):
    """Puede entrar desde HOME o PLAY; si ya esta pescando no navega ni reinicia.

    El motor normal es el unico que lee inventario y envia START. Una pantalla
    desconocida, una carga lenta o un cambio de foco no autorizan otro modo.
    """
    navigator=navigator or NavigationClassifier()
    deadline=time.perf_counter()+timeout
    stable_key=None
    stable_since=None
    samples=0
    sent=set()
    waiting_for_travel=False
    last_kind="UNKNOWN"
    log.emit("NAVIGATION_BEGIN",human=True,allowed_actions=["OPEN_FISHING","PLAY_FISHING"],
             shop_allowed=False,free_bait_claim_allowed=False)
    while time.perf_counter()<deadline:
        stop()
        image=grab()
        existing=ui.classify(FrameView(image))
        evidence=navigator.classify(FrameView(image),existing)
        last_kind=evidence.kind
        if evidence.kind in ALREADY_FISHING:
            log.emit("NAVIGATION_READY",human=True,screen=evidence.kind,
                     entered_from_home="OPEN_FISHING" in sent,play_sent="PLAY_FISHING" in sent)
            return image,evidence
        if waiting_for_travel:
            # Tras PLAY no volver a clicar HOME, PLAY, Shop ni un modal
            # desconocido mientras se desplaza el personaje.
            time.sleep(.1)
            continue
        purpose={"HOME":"OPEN_FISHING","FISHING_MENU":"PLAY_FISHING"}.get(evidence.kind)
        if not purpose or not evidence.ready or purpose in sent:
            stable_key=None
            stable_since=None
            samples=0
            time.sleep(.1)
            continue
        key=(evidence.kind,evidence.xy)
        now=time.perf_counter()
        if key!=stable_key:
            stable_key=key
            stable_since=now
            samples=0
        samples+=1
        if samples<3 or now-stable_since<.3:
            time.sleep(.1)
            continue
        # Una tercera captura aparte confirma que el boton no cambio durante
        # animacion/carga. WindowsIO protege foco, identidad y geometria.
        stop()
        verify_start=time.perf_counter_ns()
        fresh_image=grab()
        fresh=navigator.classify(FrameView(fresh_image),ui.classify(FrameView(fresh_image)))
        verify_end=time.perf_counter_ns()
        same=(fresh.kind==evidence.kind and fresh.ready and fresh.xy is not None
              and max(abs(fresh.xy[i]-evidence.xy[i]) for i in (0,1))<=3)
        if not same or verify_end-verify_start>150_000_000:
            stable_key=None
            samples=0
            log.emit("NAVIGATION_ACTION_CANCELLED",human=True,purpose=purpose,screen=fresh.kind,input_sent=False)
            time.sleep(.1)
            continue
        stop()
        io.click(fresh.xy)
        sent.add(purpose)
        log.emit("NAVIGATION_INPUT_SENT",human=True,purpose=purpose,xy=fresh.xy,
                 screen=fresh.kind,verification_ms=(verify_end-verify_start)/1e6)
        stable_key=None
        samples=0
        if purpose=="PLAY_FISHING":
            waiting_for_travel=True
            log.emit("NAVIGATION_TRAVEL_WAIT",human=True,timeout_seconds=timeout,
                     another_play_allowed=False)
        time.sleep(.15)
    raise SafetyStop(f"Entrada a Fishing no confirmada en {timeout:g} s; pantalla={last_kind}; sin clics a otros modos")
