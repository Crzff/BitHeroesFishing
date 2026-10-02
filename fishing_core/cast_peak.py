"""Predice el pico usando lecturas reales recientes; nunca envia input.

La demora extra es una estimacion a calibrar, no latencia medida del juego.
"""

from collections import deque

import numpy as np

DEFAULT_GAME_DELAY_MS=32


class CastPeakPolicy:
    def __init__(self,game_delay_ms=DEFAULT_GAME_DELAY_MS):
        if not 0<=game_delay_ms<=80:
            raise ValueError("Demora CAST fuera de 0..80 ms")
        self.delay_ms=game_delay_ms
        self.history=deque(maxlen=12)
        self.key=None

    def sample(self,status,start_ns,end_ns,now_ns,cycle_id,verification=False):
        s=status.scores
        minimum,maximum,value=s.get("CAST_MIN"),s.get("CAST_MAX"),s.get("CAST_VALUE")
        result={"ready":False,"reason":"CAST_NO_MEASUREMENT","game_delay_estimate_ms":self.delay_ms}
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
        if len(self.history)<6 or mid-self.history[0][0]<40_000_000:
            return dict(result,reason="CAST_NEEDS_RISING_HISTORY")
        amplitude=maximum-minimum
        if amplitude<=0 or value-minimum<.65*amplitude or value-self.history[0][1]<.12*amplitude:
            return dict(result,reason="CAST_NOT_APPROACHING_PEAK")
        if not 0<=now_ns-end_ns<=30_000_000 or not 0<end_ns-start_ns<=15_000_000:
            return dict(result,reason="CAST_SAMPLE_TIMING_UNCERTAIN")
        x=np.array([(p[0]-mid)/1e9 for p in self.history])
        y=np.array([(p[1]-minimum)/amplitude for p in self.history])
        weights=np.array([1/(p[2]/1e6+4) for p in self.history])
        coeff=np.polyfit(x,y,2,w=weights)
        if coeff[0]<0:
            linear=np.polyfit(x,y,1,w=weights)
            coeff=np.array([0,linear[0],linear[1]])
        residual=float(np.sqrt(np.average((np.polyval(coeff,x)-y)**2,weights=weights**2)))*amplitude
        if residual>max(.4,.03*amplitude) or coeff[1]<=0:
            return dict(result,reason="CAST_FIT_UNCERTAIN",residual=residual)
        roots=np.roots([coeff[0],coeff[1],coeff[2]-1])
        future=[float(r.real) for r in roots if abs(r.imag)<1e-7 and 0<r.real<=.15]
        if not future:
            return dict(result,reason="CAST_NO_FUTURE_PEAK",residual=residual)
        peak_ns=mid+round(min(future)*1e9)
        # SendInput CAST se envia en bloque; no se usa esta ruta en CATCH.
        scheduled=peak_ns-round((self.delay_ms+1)*1e6)
        wait_ms=(scheduled-now_ns)/1e6
        ready=(-2<=wait_ms<=16) if verification else (5<=wait_ms<=22)
        return dict(result,ready=ready,reason="CAST_PREDICTED_PEAK" if ready else "CAST_WAIT_PEAK_WINDOW",
                    predicted_peak_ns=peak_ns,scheduled_input_ns=scheduled,wait_ms=wait_ms,
                    residual=residual,velocity_units_per_second=float(coeff[1]*amplitude))
