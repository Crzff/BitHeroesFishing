"""Predice el pico usando lecturas reales recientes; nunca envia input.

La demora extra es una estimacion a calibrar, no latencia medida del juego.
"""

from collections import deque

import numpy as np

DEFAULT_GAME_DELAY_MS=32


class CastPeakPolicy:
    # Chrome conserva los limites historicos. Steam necesita anticipar tambien
    # la captura de verificacion, que puede tardar un frame completo a ~30 Hz.
    PROFILES={
        "Chrome":{"min_samples":6,"min_progress":.65,"max_capture_ms":15,
                  "source_wait_min_ms":5,"source_wait_max_ms":22,"verification_wait_max_ms":16},
        "Steam":{"min_samples":4,"min_progress":.45,"max_capture_ms":45,
                 "source_wait_min_ms":30,"source_wait_max_ms":85,"verification_wait_max_ms":60},
    }

    def __init__(self,game_delay_ms=DEFAULT_GAME_DELAY_MS,*,client="Chrome"):
        if not 0<=game_delay_ms<=80:
            raise ValueError("Demora CAST fuera de 0..80 ms")
        if client not in self.PROFILES:
            raise ValueError("Cliente CAST debe ser Chrome o Steam")
        self.delay_ms=game_delay_ms
        self.client=client
        self.profile=self.PROFILES[client]
        self.history=deque(maxlen=12)
        self.key=None

    def configuration(self):
        return {"client":self.client,**self.profile,"history_max_ms":160,
                "verification_freshness_max_ms":80,"game_delay_estimate_ms":self.delay_ms,
                "fresh_displayed_maximum_fallback":self.client=="Steam"}

    def sample(self,status,start_ns,end_ns,now_ns,cycle_id,verification=False):
        s=status.scores
        minimum,maximum,value=s.get("CAST_MIN"),s.get("CAST_MAX"),s.get("CAST_VALUE")
        result={"ready":False,"reason":"CAST_NO_MEASUREMENT","game_delay_estimate_ms":self.delay_ms,
                "sampling_client":self.client}
        if (status.kind!="CAST" or status.xy is None or not s.get("CAST_RANGE_VALID")
                or any(type(v) is not int for v in (minimum,maximum,value))
                or not 0<minimum<maximum<=999 or not minimum<=value<=maximum):
            self.history.clear()
            return result
        key=(cycle_id,minimum,maximum)
        mid=(start_ns+end_ns)//2
        if (key!=self.key or self.history and (not 0<mid-self.history[-1][0]<=100_000_000
                                             or value<self.history[-1][1])):
            self.history.clear()
        self.key=key
        self.history.append((mid,value,end_ns-start_ns))
        while self.history and mid-self.history[0][0]>160_000_000:
            self.history.popleft()
        result.update(value=value,minimum=minimum,maximum=maximum,samples=len(self.history))
        if len(self.history)<self.profile["min_samples"] or mid-self.history[0][0]<40_000_000:
            return dict(result,reason="CAST_NEEDS_RISING_HISTORY")
        amplitude=maximum-minimum
        if (amplitude<=0 or value-minimum<self.profile["min_progress"]*amplitude
                or value-self.history[0][1]<.12*amplitude):
            return dict(result,reason="CAST_NOT_APPROACHING_PEAK")
        if (not 0<=now_ns-end_ns<=30_000_000
                or not 0<end_ns-start_ns<=self.profile["max_capture_ms"]*1_000_000):
            return dict(result,reason="CAST_SAMPLE_TIMING_UNCERTAIN")
        fallback=None
        if self.client=="Steam" and value-minimum>=.85*amplitude:
            if not verification:
                # Solo propone otra captura si la prediccion normal no sirve.
                # Nunca autoriza input sin verificacion del maximo exacto.
                fallback=dict(result,ready=True,reason="STEAM_FRESH_MAXIMUM_CANDIDATE")
            elif value==maximum:
                return dict(result,ready=True,reason="STEAM_FRESH_DISPLAYED_MAXIMUM",
                            scheduled_input_ns=now_ns+1_000_000,wait_ms=1,
                            displayed_maximum_is_not_guaranteed_retained_maximum=True)
        x=np.array([(p[0]-mid)/1e9 for p in self.history])
        y=np.array([(p[1]-minimum)/amplitude for p in self.history])
        weights=np.array([1/(p[2]/1e6+4) for p in self.history])
        coeff=np.polyfit(x,y,2,w=weights)
        if coeff[0]<0:
            linear=np.polyfit(x,y,1,w=weights)
            coeff=np.array([0,linear[0],linear[1]])
        residual=float(np.sqrt(np.average((np.polyval(coeff,x)-y)**2,weights=weights**2)))*amplitude
        if residual>max(.4,.03*amplitude) or coeff[1]<=0:
            return fallback if fallback is not None else dict(result,reason="CAST_FIT_UNCERTAIN",residual=residual)
        roots=np.roots([coeff[0],coeff[1],coeff[2]-1])
        future=[float(r.real) for r in roots if abs(r.imag)<1e-7 and 0<r.real<=.15]
        if not future:
            return fallback if fallback is not None else dict(result,reason="CAST_NO_FUTURE_PEAK",residual=residual)
        peak_ns=mid+round(min(future)*1e9)
        # SendInput CAST se envia en bloque; no se usa esta ruta en CATCH.
        scheduled=peak_ns-round((self.delay_ms+1)*1e6)
        wait_ms=(scheduled-now_ns)/1e6
        if verification:
            # El tiempo de espera nunca convierte la captura fresca en una
            # verificacion de mas de 80 ms. Runtime vuelve a comprobarlo antes
            # de enviar el paquete, ademas del contexto completo de 200 ms.
            wait_max=min(self.profile["verification_wait_max_ms"],80-(now_ns-start_ns)/1e6)
            ready=-2<=wait_ms<=wait_max
        else:
            ready=self.profile["source_wait_min_ms"]<=wait_ms<=self.profile["source_wait_max_ms"]
        if not ready and fallback is not None:
            return fallback
        return dict(result,ready=ready,reason="CAST_PREDICTED_PEAK" if ready else "CAST_WAIT_PEAK_WINDOW",
                    predicted_peak_ns=peak_ns,scheduled_input_ns=scheduled,wait_ms=wait_ms,
                    residual=residual,velocity_units_per_second=float(coeff[1]*amplitude))
