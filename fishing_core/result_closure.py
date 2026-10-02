"""Confirma el retorno visual tras ITEMS/CLOSE, sin exigir otro START.

UNKNOWN solo sirve si reaparece el escenario positivo de esta misma sesion.
No confundir pantalla negra/oculta o desaparicion del texto con modal cerrado.
"""

import numpy as np


class ResultClosure:
    REGIONS=((795,20,1115,95),(645,430,680,620),
             (1230,430,1270,620),(715,850,738,880))
    STABLE_NS=600_000_000
    MAX_GAP_NS=250_000_000
    MAX_AGE_NS=200_000_000

    def __init__(self):
        self.reference=None
        self.pending=None
        self.last_finished=0
        self._reset()

    def _reset(self):
        self.since=self.previous=None
        self.samples=0
        self.proof=None

    def remember_start(self,view,status):
        if self.reference is not None or status.kind!="START" or not status.ready:
            return
        patches=[view.crop(rect) for rect in self.REGIONS]
        if any(p.shape!=(rect[3]-rect[1],rect[2]-rect[0],3)
               for p,rect in zip(patches,self.REGIONS)):
            return
        # Una referencia vacia/uniforme no acredita que el juego sea visible.
        if patches[0].std()<25 or np.count_nonzero(patches[0].min(axis=2)>=210)<80:
            return
        self.reference=[p.astype(np.int16).copy() for p in patches]

    def arm(self,cycle_id,attempt_id,outcome,outcome_path,purpose,sent_ns):
        expected="ITEMS" if outcome=="SUCCESS" else "CLOSE" if outcome=="FAILED" else None
        if cycle_id<=self.last_finished or not attempt_id or purpose!=expected:
            return
        self.pending={"cycle_id":cycle_id,"attempt_id":attempt_id,"outcome":outcome,
                      "outcome_path":outcome_path,"close_purpose":purpose,"close_input_end_ns":sent_ns}
        self._reset()

    def observe(self,view,status,capture_start_ns,now_ns):
        self.proof=None
        if self.pending is None:
            return None
        if (capture_start_ns<self.pending["close_input_end_ns"]
                or not 0<=now_ns-capture_start_ns<=self.MAX_AGE_NS):
            self._reset()
            return None
        method=None
        scores=[]
        if status.kind=="START" and status.ready and status.xy is not None:
            method="START_CONFIRMED"
        elif (status.kind=="UNKNOWN" and self.reference is not None
              and not status.xy and not status.ready
              and all(status.scores.get(name,0)<.85 for name in ("SUCCESS","ITEMS","FAILED"))):
            for rect,ref in zip(self.REGIONS,self.reference):
                patch=view.crop(rect)
                if patch.shape!=ref.shape:
                    break
                scores.append(float(np.mean(np.max(np.abs(patch.astype(np.int16)-ref),axis=2)<=18)))
            if len(scores)==len(self.REGIONS) and min(scores)>=.90:
                method="FISHING_SCENE_RESTORED"
        if method is None:
            self._reset()
            return None
        if self.previous is None or not 0<capture_start_ns-self.previous<=self.MAX_GAP_NS:
            self.since=capture_start_ns
            self.samples=0
        self.previous=capture_start_ns
        self.samples+=1
        if self.samples>=2 and capture_start_ns-self.since>=self.STABLE_NS:
            self.proof={"method":method,"stable_ms":(capture_start_ns-self.since)/1e6,
                        "samples":self.samples,"scene_similarity":scores,
                        "capture_age_ms":(now_ns-capture_start_ns)/1e6}
        return self.proof

    def finish(self):
        if self.pending is None or self.proof is None:
            raise ValueError("No hay cierre visual confirmado")
        result=dict(self.pending,closure_evidence=self.proof)
        self.last_finished=result["cycle_id"]
        self.pending=None
        self._reset()
        return result
