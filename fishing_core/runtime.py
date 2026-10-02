"""Runtime en vivo. Solo estas funciones abren MSS y envian input.

El replay y las pruebas importan motores puros, nunca ejecutan este runtime.
"""

from __future__ import annotations

import copy
import json
import os
import time
import traceback
from dataclasses import asdict

import cv2
import numpy as np

from . import VERSION
from .control_flow import ControlFlow, SafetyStop
from .catch_policy import CatchPolicy
from .detector import Detector
from .processes import Mutex, minimize_console
from .protocol import Channel, AttemptLock, atomic_json, valid_request, valid_signal, io_diagnostics
from .telemetry import ROOT, Telemetry
from .vision import FrameView, UIClassifier
from .bait_runtime import audit_baits, close_selection
from .bait_budget import BaitBudget
from .cast_sampling import CAST_MONITOR, CastSampler
from .catch_context import can_track, input_block
from .result_closure import ResultClosure
from .cast_audit import CastAudit
from .cast_peak import CastPeakPolicy,DEFAULT_GAME_DELAY_MS
from .cast_test import pending_budget

FAST_MONITOR={"left":430,"top":710,"width":1310,"height":320}
FULL_MONITOR={"left":0,"top":0,"width":1920,"height":1080}


class WindowsIO:
    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.user32=ctypes.windll.user32
        self.user32.SetProcessDPIAware()
        self.user32.GetForegroundWindow.restype=wintypes.HWND
        self.expected_hwnd=int(os.environ.get("FISHING_TEST_GAME_HWND","0"))
        if (self.user32.GetSystemMetrics(0),self.user32.GetSystemMetrics(1)) != (1920,1080):
            raise SafetyStop("Se requiere pantalla principal 1920x1080; no se envian clics")

    def emergency(self):
        if self.user32.GetAsyncKeyState(0x77)&0x8000:
            raise KeyboardInterrupt("F8")

    def click(self,xy):
        self.emergency()
        if self.expected_hwnd and self.user32.GetForegroundWindow()!=self.expected_hwnd:
            raise SafetyStop("Prueba CAST: el juego perdio el primer plano; no se envia input")
        if not self.user32.SetCursorPos(int(xy[0]),int(xy[1])):
            raise SafetyStop("Windows rechazo SetCursorPos")
        # Solo CONTROL, nunca CATCH: permitir que el juego procese el cambio
        # de cursor y DOWN en botones de interfaz. CAST usa su ruta inmediata.
        if getattr(self,"control_mode",False):
            time.sleep(.01)
            self.emergency()
            if self.expected_hwnd and self.user32.GetForegroundWindow()!=self.expected_hwnd:
                raise SafetyStop("CONTROL: foco perdido antes de DOWN; no se envia input")
        self.user32.mouse_event(0x0002,0,0,0,0)
        try:
            if getattr(self,"control_mode",False):
                time.sleep(.025)
        finally:
            self.user32.mouse_event(0x0004,0,0,0,0)

    def cast_click(self,xy):
        """DOWN/UP en una llamada. CATCH conserva su metodo de input original."""
        import ctypes
        from ctypes import wintypes
        self.emergency()
        if self.expected_hwnd and self.user32.GetForegroundWindow()!=self.expected_hwnd:
            raise SafetyStop("Prueba CAST: juego fuera de primer plano; no se envia input")
        point=wintypes.POINT()
        if not self.user32.GetCursorPos(ctypes.byref(point)):
            raise SafetyStop("CAST: Windows no devuelve posicion del cursor")
        if (point.x,point.y)!=(int(xy[0]),int(xy[1])) and not self.user32.SetCursorPos(int(xy[0]),int(xy[1])):
            raise SafetyStop("CAST: Windows rechazo SetCursorPos")
        class Mouse(ctypes.Structure):
            _fields_=[("dx",wintypes.LONG),("dy",wintypes.LONG),("data",wintypes.DWORD),
                      ("flags",wintypes.DWORD),("time",wintypes.DWORD),("extra",ctypes.c_size_t)]
        class Payload(ctypes.Union):
            _fields_=[("mouse",Mouse)]
        class Input(ctypes.Structure):
            _fields_=[("kind",wintypes.DWORD),("payload",Payload)]
        packet=(Input*2)()
        packet[0].payload.mouse.flags=0x0002
        packet[1].payload.mouse.flags=0x0004
        self.user32.SendInput.argtypes=[wintypes.UINT,ctypes.POINTER(Input),ctypes.c_int]
        sent=self.user32.SendInput(2,packet,ctypes.sizeof(Input))
        if sent!=2:
            if sent==1:
                self.user32.SendInput(1,ctypes.byref(packet[1]),ctypes.sizeof(Input))
            raise SafetyStop(f"CAST: SendInput incompleto ({sent}/2); recepcion del juego desconocida")


def capture(sct,monitor):
    shot=sct.grab(monitor)
    return np.frombuffer(shot.bgra,np.uint8).reshape(shot.height,shot.width,4)


def check_stop(io,channel,log):
    io.emergency()
    log.check()
    if channel.stop_path.exists():
        raise KeyboardInterrupt("Parada compartida")


def _managed(role,loop,model=None):
    run_id=os.environ.get("FISHING_RUN_ID")
    if not run_id:
        print("Inicia desde el panel o INICIAR_TODO.py: se requiere una sesion compartida.",flush=True)
        return 2
    mutex=channel=log=None
    code=0
    reason="NORMAL"
    try:
        mutex=Mutex(role)
        channel=Channel(run_id)
        log=Telemetry(role,run_id)
        io=WindowsIO()
        minimize_console()
        ui=UIClassifier()
        loop(io,ui,channel,log,model)
    except KeyboardInterrupt:
        reason="STOP_REQUESTED"
    except SafetyStop as exc:
        reason=str(exc)
        code=2
        if log:
            log.emit("SAFETY_STOP",human=True,reason=reason)
        print(f"{role} detenido por seguridad: {reason}",flush=True)
    except Exception as exc:
        reason=repr(exc)
        code=1
        if log:
            log.emit("PROCESS_ERROR",human=True,reason=reason,traceback=traceback.format_exc())
        traceback.print_exc()
    finally:
        if channel:
            try:
                channel.stop(role,reason)
            except Exception as exc:
                code=1
                if log:
                    log.emit("STOP_NOTIFICATION_ERROR",human=True,reason=repr(exc))
                print(f"No se pudo publicar la parada compartida: {exc}",flush=True)
        if log:
            try:
                log.emit("IPC_DIAGNOSTICS",human=True,counts=io_diagnostics())
                log.close()
            except Exception as exc:
                print(f"Error cerrando registros: {exc}",flush=True)
                code=1
        if mutex:
            mutex.close()
    return code


def run_control():
    return _managed("CONTROL",_control_loop)


def run_catch(model):
    return _managed("CATCH",_catch_loop,model)


def _control_loop(io,ui,channel,log,model):
    import mss
    io.control_mode=True
    deadline=time.perf_counter()+5
    print(f"CONTROL {VERSION}: inicio en 5 segundos. F8 detiene ambos procesos.",flush=True)
    while time.perf_counter()<deadline:
        check_stop(io,channel,log)
        time.sleep(.05)
    ready=channel.ready()
    if not ready or ready.get("run_id") != channel.run_id or not isinstance(ready.get("catch_pid"),int):
        raise SafetyStop("CATCH no esta listo para la misma sesion")
    catch_pid=ready["catch_pid"]
    flow=ControlFlow(channel.run_id,time.perf_counter())
    settings=json.loads((ROOT/"fishing_runtime_config.json").read_text(encoding="utf-8"))
    max_cycles=settings.get("max_ciclos_por_sesion")
    supervised_session=os.environ.get("FISHING_SUPERVISED_SESSION")=="1"
    cast_delay_ms=float(os.environ.get("FISHING_CAST_DELAY_MS",str(DEFAULT_GAME_DELAY_MS)))
    observe_first_cast=float(os.environ.get("FISHING_CAST_OBSERVE_SECONDS","0"))
    if not 0<=observe_first_cast<=8:
        raise SafetyStop("Observacion CAST de prueba fuera de 0..8 segundos")
    if "FISHING_TEST_MAX_CYCLES" in os.environ:
        test_limit=int(os.environ["FISHING_TEST_MAX_CYCLES"])
        if not 1<=test_limit<=20:
            raise SafetyStop("Limite de prueba fuera de 1..20 ciclos")
        max_cycles=test_limit
        log.emit("AUTHORIZED_CAST_TEST",human=True,max_cycles=max_cycles,observe_first_cast_seconds=observe_first_cast,
                 persistent_runtime_config_unchanged=True)
    if type(max_cycles) is not int or not 0 <= max_cycles <= 10000:
        raise SafetyStop("max_ciclos_por_sesion debe ser entero de 0 a 10000")
    completed=0
    bait_budget=None
    resume_info=resume_marker=None
    resume_run=os.environ.get("FISHING_CAST_RESUME_RUN")
    if resume_run:
        if max_cycles!=1 or not os.environ.get("FISHING_TEST_GAME_HWND"):
            raise SafetyStop("Retomar CAST requiere prueba opt-in de un solo ciclo y foco protegido")
        bait_budget,resume_info,resume_marker=pending_budget(ROOT,resume_run)
    log.emit("RUN_LIMIT",human=True,max_cycles=max_cycles,zero_means_continuous=True,
             supervised_stop_after_failed_closure=supervised_session)
    request=None
    last_publish=last_heartbeat=0
    current_attempt=None
    issued_ns=0
    image=None
    full_image=None
    cast_sampler=CastSampler()
    cast_candidate=cast_verification=None
    result_closure=ResultClosure()
    cast_audit=CastAudit()
    cast_peak=CastPeakPolicy(cast_delay_ms)
    log.emit("CAST_CONFIGURATION",human=True,target="PREDICTED_CURRENT_BAR_MAXIMUM",game_delay_estimate_ms=cast_delay_ms,
             estimate_is_not_measured_game_latency=True,full_context_max_ms=200,verification_max_ms=80,
             scheduled_input_lateness_max_ms=3,noncritical_control_move_settle_ms=10,noncritical_control_hold_ms=25,
             catch_click_timing_unchanged=True)
    with mss.mss() as sct:
        try:
            while True:
                check_stop(io,channel,log)
                start=time.perf_counter_ns()
                local_cast=cast_sampler.use_local(flow.state,start)
                source_roi=CAST_MONITOR if local_cast else FULL_MONITOR
                image=capture(sct,source_roi)
                cap_done=time.perf_counter_ns()
                if local_cast:
                    e=cast_sampler.local_evidence(ui.cast_status(FrameView(image,830,775)))
                else:
                    full_image=image
                    e=ui.classify(FrameView(image))
                    cast_sampler.observe_full(e,start)
                class_done=time.perf_counter_ns()
                now=time.perf_counter()
                peak_decision=None
                if flow.state=="WAIT_CAST":
                    peak_decision=cast_peak.sample(e,start,cap_done,class_done,flow.cycle_id)
                if flow.state=="WAIT_CAST":
                    log.emit("CAST_FRAME",cycle_id=flow.cycle_id,attempt_id=flow.attempt_id,
                             capture_start_ns=start,capture_end_ns=cap_done,local_cast=local_cast,
                             ready=e.ready,scores=e.scores,prediction=peak_decision,full_context_age_ms=(class_done-cast_sampler.context_ns)/1e6
                             if cast_sampler.context_ns is not None else None)
                if cast_audit.pending is not None and not local_cast:
                    measured=ui.cast_reader.measure(FrameView(image))
                    _,cast_xy=ui.match(FrameView(image),"CAST",(830,910,1090,1020))
                    locked=cast_audit.observe(measured,cast_xy is not None,start)
                    if locked:
                        log.emit("CAST_LOCK_OBSERVED",human=True,**locked)
                        if locked["status"]=="FROZEN_VALUE_OBSERVED":
                            cv2.imwrite(str(channel.directory/f"cast_locked_{locked['cycle_id']:04d}.png"),image)
                if flow.state=="WAIT_START" and result_closure.pending is not None:
                    proof=result_closure.observe(FrameView(image),e,start,class_done)
                    if proof:
                        # Confirmar de nuevo en otra captura completa. Ningun
                        # input, recuento o nuevo intento para comprobar el cierre.
                        close_start=time.perf_counter_ns()
                        close_image=capture(sct,FULL_MONITOR)
                        close_status=ui.classify(FrameView(close_image))
                        proof=result_closure.observe(FrameView(close_image),close_status,
                                                     close_start,time.perf_counter_ns())
                        check_stop(io,channel,log)
                        if proof:
                            finished=result_closure.finish()
                            completed+=1
                            log.emit("CYCLE_COMPLETE",human=True,**finished)
                            if bait_budget is not None and bait_budget.remaining==0:
                                cv2.imwrite(str(channel.directory/"result_closure_confirmed.png"),close_image)
                                atomic_json(channel.directory/"result_closure.json",
                                            {"schema":1,"run_id":channel.run_id,**finished,
                                             "verification_capture_start_ns":close_start,**bait_budget.payload()})
                                log.emit("BAIT_BUDGET_REACHED",human=True,completed=completed,**bait_budget.payload())
                                print("Presupuesto inicial agotado y ultimo resultado cerrado; ambos motores se detienen.",flush=True)
                                return
                            if max_cycles and completed>=max_cycles:
                                log.emit("RUN_LIMIT_REACHED",human=True,completed=completed)
                                print(f"Prueba finalizada: {completed} ciclos. Revisar registros antes de continuar.",flush=True)
                                return
                            if supervised_session and finished["outcome"]=="FAILED":
                                # La vigilancia externa puede leer el cierre
                                # despues de otro START. Parar aqui mantiene
                                # START como punto seguro para la revision.
                                raise SafetyStop("Ciclo FAILED cerrado; supervision detiene antes de otro START")
                            continue
                if e.kind=="SELECT_MENU" and flow.state=="RESUME":
                    close_selection(io,ui,lambda:capture(sct,FULL_MONITOR),
                                    lambda:check_stop(io,channel,log),log)
                    flow.entered=time.perf_counter()
                    continue
                if e.kind=="CAST" and flow.state=="RESUME":
                    if resume_info is None or not e.scores.get("CAST_RANGE_VALID"):
                        raise SafetyStop("Iniciar en START: se requiere comprobar los cebos antes de pescar")
                    flow._new_cycle()
                    flow.transition("WAIT_CAST",now,"AUTHORIZED_PENDING_CAST_RESUME")
                    atomic_json(resume_marker,{"reserved_by_run":channel.run_id,"input_sent":False,**resume_info})
                    log.emit("BAIT_BUDGET_RESUMED",human=True,**{**resume_info,**bait_budget.payload()})
                    continue
                signal=channel.signal()
                ack=valid_signal(signal,request,channel.run_id,catch_pid,time.perf_counter_ns())
                previous=(flow.state,flow.cycle_id,flow.outcome,flow.outcome_path)
                snapshot=copy.deepcopy(flow.__dict__)
                flow_e=e
                if flow.state=="WAIT_CAST" and e.kind=="CAST" and peak_decision is not None:
                    flow_e=copy.copy(e)
                    flow_e.ready=peak_decision["ready"]
                if flow.state=="WAIT_CAST" and flow.cycle_id==1 and now-flow.entered<observe_first_cast:
                    flow_e=copy.copy(e)
                    flow_e.ready=False
                if flow.state=="WAIT_START" and result_closure.pending is not None and e.kind=="START":
                    # Mantener estabilidad/timeouts, pero no proponer otro
                    # START hasta registrar una sola vez el cierre anterior.
                    flow_e=copy.copy(e)
                    flow_e.ready=False
                action=flow.step(flow_e,now,ack)
                if action:
                    # Revalidacion fresca: CONTROL nunca pulsa un boton por una captura vieja.
                    fresh_start_ns=time.perf_counter_ns()
                    if action.purpose=="CAST":
                        verification_roi=CAST_MONITOR
                        fresh_image=capture(sct,verification_roi)
                        fresh_capture_end_ns=time.perf_counter_ns()
                        fresh=cast_sampler.local_evidence(ui.cast_status(FrameView(fresh_image,830,775)))
                        fresh_peak=cast_peak.sample(fresh,fresh_start_ns,fresh_capture_end_ns,
                                                   time.perf_counter_ns(),flow.cycle_id,verification=True)
                        if (peak_decision and fresh_peak.get("predicted_peak_ns") is not None
                                and abs(fresh_peak["predicted_peak_ns"]-peak_decision.get("predicted_peak_ns",0))>12_000_000):
                            fresh_peak["ready"]=False
                            fresh_peak["reason"]="CAST_PEAK_CHANGED_DURING_VERIFICATION"
                        fresh.ready=fresh_peak["ready"]
                        fresh.scores["CAST_PREDICTION"]=fresh_peak
                    else:
                        verification_roi=FULL_MONITOR
                        fresh_image=capture(sct,verification_roi)
                        fresh_capture_end_ns=time.perf_counter_ns()
                        fresh=ui.classify(FrameView(fresh_image))
                    fresh_end_ns=time.perf_counter_ns()
                    if (fresh.kind != action.expected_screen or not fresh.ready or not fresh.xy
                            or action.purpose=="CAST" and (not cast_sampler.same_position(fresh)
                                                          or not cast_sampler.current(fresh_end_ns))):
                        flow.__dict__.clear()
                        flow.__dict__.update(snapshot)
                        log.emit("ACTION_CANCELLED",human=True,purpose=action.purpose,screen=fresh.kind,
                                 source_ready=e.ready,fresh_ready=fresh.ready,
                                 source_scores=e.scores,fresh_scores=fresh.scores,
                                  source_age_ms=(fresh_end_ns-start)/1e6,
                                  verification_ms=(fresh_end_ns-fresh_start_ns)/1e6,
                                  source_roi=source_roi,local_cast=local_cast,
                                  full_cast_context_valid=cast_sampler.current(fresh_end_ns) if action.purpose=="CAST" else None,
                                  verification_roi=verification_roi)
                        if action.purpose=="CAST":
                            cast_candidate=FrameView(image,source_roi["left"],source_roi["top"]).crop(
                                (830,775,1090,1020)).copy()
                            cast_verification=fresh_image[:,:,:3].copy()
                        time.sleep(cast_sampler.POLL_SLEEP if flow.state=="WAIT_CAST" else .02)
                        continue
                    action.xy=fresh.xy
                    if action.purpose=="START" and bait_budget is not None and bait_budget.remaining==0:
                        log.emit("BAIT_BUDGET_REACHED",human=True,completed=completed,**bait_budget.payload())
                        print("Presupuesto inicial de cebos agotado: no se inicia otra pesca.",flush=True)
                        return
                    if action.purpose=="START" and bait_budget is None:
                        inventory=audit_baits(io,ui,channel,log,lambda:capture(sct,FULL_MONITOR),
                                              lambda:check_stop(io,channel,log))
                        bait_budget=BaitBudget(inventory.total)
                        log.emit("BAIT_BUDGET_INITIALIZED",human=True,**bait_budget.payload())
                        if inventory.total==0:
                            log.emit("BAIT_EXHAUSTED",human=True,total=0,completed=completed)
                            print("Sin cebos: ambos motores se detienen antes de START.",flush=True)
                            return
                        if inventory.total<=10:
                            log.emit("BAIT_LOW",human=True,total=inventory.total)
                        # El inventario no extiende una captura vieja del boton START.
                        fresh_start_ns=time.perf_counter_ns()
                        fresh_image=capture(sct,FULL_MONITOR)
                        fresh_capture_end_ns=time.perf_counter_ns()
                        fresh=ui.classify(FrameView(fresh_image))
                        fresh_end_ns=time.perf_counter_ns()
                        if fresh.kind!="START" or not fresh.ready or not fresh.xy:
                            raise SafetyStop("START no confirmado despues de cerrar inventario; no se pesca")
                        action.xy=fresh.xy
                        flow.entered=time.perf_counter()
                        result_closure.remember_start(FrameView(fresh_image),fresh)
                    if action.purpose=="CAST" and (bait_budget is None or bait_budget.remaining==0
                                                   or action.attempt_id in bait_budget.charged_attempts):
                        raise SafetyStop("CAST sin presupuesto disponible o ya enviado para este intento")
                if flow.attempt_id != current_attempt:
                    current_attempt=flow.attempt_id
                    issued_ns=time.perf_counter_ns()
                if action or flow.state != previous[0] or now-last_publish >= .5:
                    request={"schema":1,"run_id":channel.run_id,"cycle_id":flow.cycle_id,
                             "attempt_id":flow.attempt_id,"state":flow.request_state,
                             "issued_perf_ns":issued_ns,"updated_perf_ns":time.perf_counter_ns(),
                             "control_pid":os.getpid()}
                    if action is None or action.purpose!="CAST":
                        atomic_json(channel.request_path,request)
                        last_publish=now
                for old,new,reason in ([] if action is not None and action.purpose=="CAST" else flow.transitions):
                    log.emit("STATE_TRANSITION",human=True,cycle_id=flow.cycle_id,
                             attempt_id=flow.attempt_id,old=old,new=new,reason=reason,
                             screen=e.kind,input_confirmed=flow.input_confirmed,
                             outcome=flow.outcome,outcome_path=flow.outcome_path)
                if action is None or action.purpose!="CAST":
                    flow.transitions.clear()
                if action:
                    check_stop(io,channel,log)
                    if action.purpose=="CAST":
                        scheduled=fresh_peak.get("scheduled_input_ns",time.perf_counter_ns())
                        while time.perf_counter_ns()<scheduled:
                            check_stop(io,channel,log)
                            if scheduled-time.perf_counter_ns()>2_000_000:
                                time.sleep(.001)
                    fresh_age_ms=(time.perf_counter_ns()-fresh_start_ns)/1e6
                    schedule_late_ms=(time.perf_counter_ns()-scheduled)/1e6 if action.purpose=="CAST" else None
                    if action.purpose=="CAST" and (fresh_age_ms>80 or not cast_sampler.current(time.perf_counter_ns())
                                                   or schedule_late_ms>3):
                        reason=("CAST_VERIFICATION_EXPIRED" if fresh_age_ms>80 else
                                "FULL_CAST_CONTEXT_EXPIRED" if not cast_sampler.current(time.perf_counter_ns()) else
                                "CAST_SCHEDULE_MISSED")
                        flow.__dict__.clear()
                        flow.__dict__.update(snapshot)
                        cast_sampler.reset()
                        log.emit("ACTION_CANCELLED",human=True,purpose="CAST",reason=reason,
                                 fresh_age_ms=fresh_age_ms,input_sent=False,budget_debited=False,attempt_armed=False)
                        time.sleep(cast_sampler.POLL_SLEEP)
                        continue
                    t0=time.perf_counter_ns()
                    if action.purpose=="CAST":
                        io.cast_click(action.xy)
                    else:
                        io.click(action.xy)
                    t1=time.perf_counter_ns()
                    # El intervalo de reintento empieza en el input real, no en
                    # la propuesta anterior al conteo/cierre del inventario.
                    flow.last_action=t1/1e9
                    if action.purpose=="START" and action.retry:
                        log.emit("START_RETRY",human=True,cycle_id=action.cycle_id,attempt_id=action.attempt_id,
                                 retry=action.retry,max_retries=flow.MAX_START_RETRIES,reason="START_STILL_VISIBLE")
                    log.emit("CONTROL_INPUT_SENT",human=True,cycle_id=action.cycle_id,
                              attempt_id=action.attempt_id,purpose=action.purpose,xy=action.xy,
                              retry=action.retry,
                              input_start_ns=t0,input_end_ns=t1,input_ms=(t1-t0)/1e6,
                              evidence=fresh.kind,outcome=flow.outcome,outcome_path=flow.outcome_path,
                               source_scores=e.scores,fresh_scores=fresh.scores,fresh_age_ms=fresh_age_ms,
                               source_roi=source_roi,local_cast=local_cast,
                               full_cast_context_age_ms=(t0-cast_sampler.context_ns)/1e6 if action.purpose=="CAST" else None,
                              verification_capture_ms=(fresh_capture_end_ns-fresh_start_ns)/1e6,
                              verification_classification_ms=(fresh_end_ns-fresh_capture_end_ns)/1e6,
                                verification_roi=verification_roi)
                    if action.purpose=="CAST":
                        cast_candidate=cast_verification=None
                        bait_budget.charge(action.attempt_id)
                        log.emit("BAIT_BUDGET_UPDATED",human=True,cycle_id=action.cycle_id,
                                 attempt_id=action.attempt_id,**bait_budget.payload())
                        if bait_budget.remaining==10:
                            log.emit("BAIT_LOW",human=True,total=10,remaining_is_estimate=True)
                        cast_audit.sent(action.cycle_id,action.attempt_id,fresh.scores.get("CAST_MIN"),
                                        fresh.scores.get("CAST_MAX"),t1)
                        if resume_marker is not None:
                            atomic_json(resume_marker,{"resumed_by_run":channel.run_id,"cast_input_end_ns":t1,**resume_info})
                            resume_marker=None
                        request["updated_perf_ns"]=time.perf_counter_ns()
                        atomic_json(channel.request_path,request)
                        last_publish=now
                        for old,new,reason in flow.transitions:
                            log.emit("STATE_TRANSITION",human=True,cycle_id=flow.cycle_id,attempt_id=flow.attempt_id,
                                     old=old,new=new,reason=reason,screen=e.kind,input_confirmed=flow.input_confirmed,
                                     outcome=flow.outcome,outcome_path=flow.outcome_path)
                        flow.transitions.clear()
                    if (action.purpose in ("ITEMS","CLOSE") and bait_budget is not None
                            and action.attempt_id in bait_budget.charged_attempts):
                        result_closure.arm(action.cycle_id,action.attempt_id,flow.outcome,
                                           flow.outcome_path,action.purpose,t1)
                if now-last_heartbeat >= 1:
                    log.emit("HEARTBEAT",human=True,cycle_id=flow.cycle_id,attempt_id=flow.attempt_id,
                               state=flow.state,screen=e.kind,ready=e.ready,scores=e.scores,
                               source_roi=source_roi,local_cast=local_cast,
                              capture_ms=(cap_done-start)/1e6,classification_ms=(class_done-cap_done)/1e6,
                              ipc_io=io_diagnostics())
                    last_heartbeat=now
                time.sleep(cast_sampler.POLL_SLEEP if flow.state=="WAIT_CAST" else .025)
        except SafetyStop:
            if full_image is not None:
                cv2.imwrite(str(channel.directory/"control_stop.png"),full_image)
            for name,evidence_image in (("cast_last_candidate.png",cast_candidate),
                                        ("cast_last_verification.png",cast_verification)):
                if evidence_image is not None and evidence_image.size:
                    cv2.imwrite(str(channel.directory/name),evidence_image)
            raise


def _catch_loop(io,ui,channel,log,model):
    import mss
    cfg=model.ConfigV6()
    tracker=model.TrackerBarra(cfg)
    detector=Detector()
    policy=CatchPolicy()
    lock=AttemptLock()
    attempt_id=None
    track_id=0
    input_est=cfg.lat_click_est_seg
    last_heartbeat=0
    previous_tracking=False
    log.emit("CONFIG",human=True,config=asdict(cfg),capture_roi=FAST_MONITOR,
             click=(960,970),input_estimate_is_game_latency=False)
    atomic_json(channel.ready_path,{"schema":1,"run_id":channel.run_id,"catch_pid":os.getpid()})
    print(f"CATCH {VERSION} listo. Un clic por intento; sin rearme por timeout. F8 detiene ambos.",flush=True)
    with mss.mss() as sct:
        while True:
            check_stop(io,channel,log)
            cap_start=time.perf_counter_ns()
            image=capture(sct,FAST_MONITOR)
            cap_done=time.perf_counter_ns()
            view=FrameView(image,430,710)
            status=ui.catch_status(view)
            trackable=can_track(status)
            context_done=time.perf_counter_ns()
            request=channel.request()
            request_done=time.perf_counter_ns()
            armed=valid_request(request,channel.run_id,time.perf_counter_ns())
            if armed and request["attempt_id"] != attempt_id:
                attempt_id=request["attempt_id"]
                tracker.reset("new_attempt")
                detector.reset()
                policy.reset()
                track_id+=1
                log.emit("ATTEMPT_ARMED",human=True,cycle_id=request["cycle_id"],attempt_id=attempt_id)
            decision=detection=None
            detector_ms=tracking_ms=decision_ms=0.0
            estimate_used=input_est
            diagnostic={}
            phase="locked" if attempt_id and not lock.available(attempt_id) else "pre"
            reason="NOT_ARMED" if not armed else status.kind
            if armed and trackable and lock.available(attempt_id):
                policy.seen(cap_start/1e9)
                detect_start=time.perf_counter_ns()
                detection,diagnostic=detector.detect(view,cap_start/1e9)
                detect_done=time.perf_counter_ns()
                detector_ms=(detect_done-detect_start)/1e6
                if detection:
                    obs=model.Obs(cap_start/1e9,detection.centro_pez,detection.centro_zona,
                                  detection.ancho_pez,detection.ancho_zona)
                    reset=tracker.agregar(obs)
                    if reset:
                        track_id+=1
                        log.emit("TRACK_RESET",cycle_id=request["cycle_id"],attempt_id=attempt_id,reason=reset)
                    vision_done=time.perf_counter_ns()
                    tracking_ms=(vision_done-detect_done)/1e6
                    decision=model.decidir(tracker,obs,(vision_done-cap_start)/1e9,cfg,input_est)
                    decision=policy.evaluate(obs,status.percentage,decision,cfg)
                    decision_ms=(time.perf_counter_ns()-vision_done)/1e6
                    reason=decision.motivo
                else:
                    tracker.perdida_deteccion()
                    policy.miss()
                    reason=diagnostic["reason"]
            else:
                if previous_tracking:
                    tracker.reset("not_active")
                    detector.reset()
                    policy.miss()
            previous_tracking=trackable
            decision_done=time.perf_counter_ns()
            sent_ms=None
            if decision and decision.disparar:
                block=input_block(status,cap_start,decision_done)
                if block:
                    reason=block
                else:
                    # Ultima comprobacion del intento; no registrar/flush antes del input.
                    fresh_request=channel.request()
                    if not valid_request(fresh_request,channel.run_id,time.perf_counter_ns()) or fresh_request["attempt_id"] != attempt_id:
                        reason="ATTEMPT_CHANGED"
                    else:
                        check_stop(io,channel,log)
                        # IPC/parada pueden tardar: no basta comprobar la edad
                        # antes de ellos. No reclamar el clic si ya se vencio.
                        final_block=input_block(status,cap_start,time.perf_counter_ns())
                        if final_block:
                            reason=final_block
                        else:
                            lock.claim(attempt_id)
                            t0=time.perf_counter_ns()
                            io.click((960,970))
                            t1=time.perf_counter_ns()
                            sent_ms=(t1-t0)/1e6
                            input_est=model.actualizar_latencia_click(cfg,input_est,(t1-t0)/1e9)
                            signal={"schema":1,"event":"INPUT_SENT","run_id":channel.run_id,
                                    "cycle_id":request["cycle_id"],"attempt_id":attempt_id,
                                    "catch_pid":os.getpid(),"sent_perf_ns":t1,"input_start_ns":t0,
                                    "input_end_ns":t1,"input_ms":sent_ms}
                            log.emit("INPUT_SENT",human=True,**{k:v for k,v in signal.items() if k not in ("schema","event","run_id")},
                                     decision=asdict(decision),percentage=status.percentage,
                                     capture_start_ns=cap_start,capture_end_ns=cap_done,
                                      decision_end_ns=decision_done,pre_input_gap_ms=(t0-decision_done)/1e6,
                                      input_est_used_ms=estimate_used*1000)
                            atomic_json(channel.signal_path,signal)
                            log.emit("SIGNAL_PUBLISHED",cycle_id=request["cycle_id"],attempt_id=attempt_id,
                                     sent_perf_ns=t1,published_perf_ns=time.perf_counter_ns())
                            phase="input_sent"
                            tracker.reset("post_click")
            log.emit("CATCH_FRAME",cycle_id=request.get("cycle_id") if request else None,
                     attempt_id=attempt_id,track_id=track_id,phase=phase,screen=status.kind,
                     percentage=status.percentage,detected=detection is not None,
                     cp=detection.centro_pez if detection else None,cv=detection.centro_zona if detection else None,
                     wp=detection.ancho_pez if detection else None,wz=detection.ancho_zona if detection else None,
                     delta=detection.centro_pez-detection.centro_zona if detection else None,
                     v=decision.v if decision else None,residual=decision.residual if decision else None,
                      reason=reason,candidates=diagnostic,scores=status.scores,
                      trackable=trackable,
                      tracking_only=trackable and status.percentage is None and armed and phase!="locked",
                     capture_ms=(cap_done-cap_start)/1e6,
                     vision_ms=(context_done-cap_done)/1e6+detector_ms,
                     context_ms=(context_done-cap_done)/1e6,detector_ms=detector_ms,
                     ipc_ms=(request_done-context_done)/1e6,tracking_ms=tracking_ms,
                     decision_ms=decision_ms,input_ms=sent_ms,input_est_ms=input_est*1000,
                     input_est_used_ms=estimate_used*1000,capture_start_ns=cap_start,capture_end_ns=cap_done)
            now=time.perf_counter()
            if now-last_heartbeat>=1:
                log.emit("HEARTBEAT",human=True,attempt_id=attempt_id,screen=status.kind,phase=phase,armed=armed,
                         ipc_io=io_diagnostics())
                last_heartbeat=now
            # Ceder CPU cuando no hay oportunidad. No dormir dentro de la ventana activa.
            if not armed or phase=="locked" or not trackable:
                time.sleep(.015)
