"""Comprobacion opt-in de captura real; enfoca Steam, nunca envia inputs al juego."""

import ctypes
import json
from pathlib import Path
import statistics
import sys
import time

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from fishing_core.game_window import focus_window,WindowGuard
from fishing_core.linux import LinuxAPI,LinuxCapture,Niri
from fishing_core.processes import Mutex
from fishing_core.runtime import FULL_MONITOR,LINUX_FAST_MONITOR
from fishing_core.vision import FrameView,UIClassifier
from fishing_core.detector import Detector


def main():
    ipc=Niri();old=ipc.request("FocusedWindow");api=LinuxAPI();mutex=None
    try:
        mutex=Mutex("LAUNCHER")
        game=focus_window("Steam",api);guard=WindowGuard(game,api)
        ui=UIClassifier();detector=Detector();times=[]
        before=len(list(Path("/proc/self/fd").iterdir()))
        with LinuxCapture(guard) as capture:
            full=capture.grab(FULL_MONITOR)
            assert (full.width,full.height,len(full.bgra))==(1920,1080,1920*1080*4)
            for _ in range(100):
                start=time.perf_counter_ns();api.emergency();guard.check()
                shot=capture.grab(LINUX_FAST_MONITOR)
                view=FrameView(np.frombuffer(shot.bgra,np.uint8).reshape(shot.height,shot.width,4),470,741)
                ui.catch_status(view);detector.detect(view,start/1e9)
                times.append((time.perf_counter_ns()-start)/1e6)
            # Capacidad menor de cuatro bytes: el C debe rechazarla sin copiar.
            sentinel=(ctypes.c_ubyte*4)(1,2,3,4)
            native=capture.native
            assert native.lib.fishing_capture_grab(native.handle,0,0,1,1,sentinel,3)<0
            assert bytes(sentinel)==bytes((1,2,3,4))
        after=len(list(Path("/proc/self/fd").iterdir()))
        assert after==before,"Fuga de descriptores en la captura Wayland"
        samples=sorted(times[5:]);median=statistics.median(samples)
        assert median<20,"CATCH no cumple el intervalo existente de 20 ms"
        print(json.dumps({"game_inputs":0,"samples":len(samples),"loop_median_ms":round(median,3),
                          "loop_p95_ms":round(samples[int(len(samples)*.95)],3),
                          "fd_before_after":[before,after],"undersized_buffer_rejected":True}))
    finally:
        api.close()
        if mutex:mutex.close()
        if old:ipc.request({"Action":{"FocusWindow":{"id":old["id"]}}})


if __name__=="__main__":
    main()
