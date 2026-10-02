"""Muestreo local de CONTROL; no envia input ni decide CATCH.

La vista completa mantiene prioridad de modales. Solo tras ver CAST en ella
se permiten lecturas locales durante 200 ms, con texto en la misma posicion.
"""

from .vision import Evidence

CAST_MONITOR={"left":830,"top":775,"width":260,"height":245}


class CastSampler:
    CONTEXT_MAX_NS=200_000_000
    LOCAL_START_MAX_NS=140_000_000
    POLL_SLEEP=.003

    def __init__(self):
        self.context_ns=None
        self.context_xy=None
        self.context_range=None

    def reset(self):
        self.context_ns=None
        self.context_xy=None
        self.context_range=None

    def observe_full(self,e,capture_start_ns):
        self.reset()
        if e.kind=="CAST" and e.xy is not None:
            self.context_ns=capture_start_ns
            self.context_xy=e.xy
            self.context_range=(e.scores.get("CAST_MIN"),e.scores.get("CAST_MAX"))

    def current(self,now_ns):
        return (self.context_ns is not None and
                0<=now_ns-self.context_ns<self.CONTEXT_MAX_NS)

    def use_local(self,state,now_ns):
        if state!="WAIT_CAST":
            self.reset()
            return False
        return (self.current(now_ns) and
                now_ns-self.context_ns<self.LOCAL_START_MAX_NS)

    def same_position(self,e):
        return (e.kind=="CAST" and e.xy is not None and self.context_xy is not None
                and max(abs(e.xy[i]-self.context_xy[i]) for i in (0,1))<=3)

    def local_evidence(self,e):
        if (self.same_position(e) and self.context_range==
                (e.scores.get("CAST_MIN"),e.scores.get("CAST_MAX"))):
            return e
        self.reset()
        return Evidence(scores={**e.scores,"CAST_CONTEXT":"LOCAL_TEXT_LOST_OR_MOVED"})
