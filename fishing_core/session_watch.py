"""Vigilancia de registros; no captura ni decide/envia CAST o CATCH."""

from collections import Counter
from math import isfinite


def valid_age(value,maximum):
    return type(value) in (int,float) and isfinite(value) and 0<=value<=maximum


class SessionWatch:
    def __init__(self,run_id):
        self.run_id=run_id
        self.initial=None
        self.remaining=None
        self.inventory_reads=0
        self.casts=set()
        self.debits=set()
        self.catches=set()
        self.closed=set()
        self.closed_paths={}
        self.observed_casts=set()
        self.outcomes=Counter()
        self.locked_values=Counter()
        self.maximum_hits=0
        self.last_perf={}
        self.stopped=set()
        self.budget_reached=False
        self.initially_empty=False
        self.issues=[]
        self.max_catch_age_ms=0
        self.max_cast_age_ms=0

    def fail(self,reason):
        if reason not in self.issues:
            self.issues.append(reason)

    def apply(self,e):
        if e.get("run_id")!=self.run_id or e.get("role") not in ("CONTROL","CATCH"):
            return
        role=e["role"]
        kind=e.get("event")
        if type(e.get("perf_ns")) is int:
            self.last_perf[role]=max(self.last_perf.get(role,0),e["perf_ns"])
        attempt=e.get("attempt_id")
        if kind in ("SAFETY_STOP","PROCESS_ERROR","STOP_NOTIFICATION_ERROR"):
            self.fail(f"{role}: {e.get('reason',kind)}")
        elif kind=="PROCESS_STOP":
            self.stopped.add(role)
            if e.get("dropped",0):
                self.fail("Registro con eventos perdidos")
        elif role=="CONTROL" and kind=="BAIT_INVENTORY":
            self.inventory_reads+=1
            if self.inventory_reads!=1 or e.get("reliable") is not True or type(e.get("total")) is not int or e["total"]<0:
                self.fail("Inventario no fiable o contado mas de una vez")
            else:
                self.initial=self.remaining=e["total"]
        elif role=="CONTROL" and kind=="RUN_LIMIT":
            if type(e.get("max_cycles")) is not int or e["max_cycles"]!=0:
                self.fail("La sesion solicitada debe ser continua sin limite de ciclos")
        elif role=="CONTROL" and kind=="CONTROL_INPUT_SENT":
            if e.get("purpose")=="CATCH":
                self.fail("CONTROL no puede enviar CATCH")
            if e.get("purpose")=="START" and self.remaining==0:
                self.fail("START enviado despues de agotar el presupuesto")
            if e.get("purpose")=="CAST":
                if not isinstance(attempt,str) or not attempt or attempt in self.casts:
                    self.fail("CAST duplicado o sin intento")
                    return
                self.casts.add(attempt)
                age=e.get("fresh_age_ms",float("inf"))
                if valid_age(age,80):
                    self.max_cast_age_ms=max(self.max_cast_age_ms,age)
                if not valid_age(age,80) or not valid_age(e.get("full_cast_context_age_ms"),200):
                    self.fail("CAST sin evidencia fresca")
        elif role=="CONTROL" and kind=="BAIT_BUDGET_UPDATED":
            if not isinstance(attempt,str) or not attempt:
                self.fail("Descuento de cebo sin intento valido")
                return
            if attempt in self.debits:
                self.fail("Descuento de cebo duplicado")
                return
            debited=e.get("attempts_debited")
            remaining=e.get("estimated_remaining")
            if (type(self.initial) is not int or attempt not in self.casts
                    or type(e.get("initial_total")) is not int or e["initial_total"]!=self.initial
                    or type(debited) is not int or type(remaining) is not int
                    or debited!=len(self.debits)+1 or remaining!=self.initial-debited
                    or not 0<=remaining<=self.initial):
                self.fail("Descuento de cebo no coincide con CAST y presupuesto inicial")
                return
            self.debits.add(attempt)
            self.remaining=remaining
        elif role=="CATCH" and kind=="INPUT_SENT":
            if not isinstance(attempt,str) or not attempt or attempt in self.catches:
                self.fail("CATCH duplicado o sin intento")
                return
            self.catches.add(attempt)
            sent,captured=e.get("input_start_ns"),e.get("capture_start_ns")
            age=(sent-captured)/1e6 if type(sent) is int and type(captured) is int else None
            if valid_age(age,60):
                self.max_catch_age_ms=max(self.max_catch_age_ms,age)
            if type(e.get("percentage")) is not int or e["percentage"]!=100 or not valid_age(age,60):
                self.fail("CATCH sin 100% o sin captura fresca")
        elif role=="CONTROL" and kind=="CAST_LOCK_OBSERVED" and e.get("status")=="FROZEN_VALUE_OBSERVED":
            minimum,maximum,value=(e.get(name) for name in ("minimum","maximum","value"))
            if (not isinstance(attempt,str) or not attempt or attempt in self.observed_casts
                    or any(type(v) is not int for v in (minimum,maximum,value))
                    or not 0<minimum<maximum<=999 or not minimum<=value<=maximum):
                self.fail("CAST retenido duplicado o lectura invalida")
                return
            self.observed_casts.add(attempt)
            self.locked_values[value]+=1
            if value==maximum:
                self.maximum_hits+=1
        elif role=="CONTROL" and kind=="CYCLE_COMPLETE":
            if not isinstance(attempt,str) or not attempt or attempt in self.closed or attempt not in self.casts:
                self.fail("Cierre duplicado o sin CAST")
                return
            outcome,path=e.get("outcome"),e.get("outcome_path")
            if outcome not in ("SUCCESS","FAILED") or path not in ("CATCH","DIRECT_REWARD"):
                self.fail("Resultado o ruta no reconocidos")
                return
            self.closed.add(attempt)
            self.closed_paths[attempt]=path
            proof=e.get("closure_evidence",{})
            if (not isinstance(proof,dict) or not valid_age(proof.get("stable_ms"),float("inf"))
                    or proof["stable_ms"]<600 or not valid_age(proof.get("capture_age_ms"),200)):
                self.fail("Cierre sin estabilidad o captura fresca")
            self.outcomes[(outcome,path)]+=1
            if outcome!="SUCCESS":
                self.fail("Ciclo FAILED cerrado; revisar antes de seguir")
        elif role=="CONTROL" and kind=="BAIT_BUDGET_REACHED":
            if (type(self.initial) is not int or self.remaining!=0
                    or len(self.closed)!=self.initial or self.closed!=self.casts or self.debits!=self.casts):
                self.fail("Agotamiento sin cerrar el ultimo ciclo")
                return
            self.budget_reached=True
        elif role=="CONTROL" and kind=="BAIT_EXHAUSTED":
            if self.initial!=0 or self.casts:
                self.fail("Cero inicial sin inventario fiable vacio")
                return
            self.initially_empty=True

    def finalize(self):
        """Solo al detener motores, despues de drenar ambos registros.

        Los archivos CONTROL/CATCH se vacian por separado. No exigir el
        input CATCH al leer un cierre CONTROL antes de vaciar el otro archivo.
        """
        if self.stopped!={"CONTROL","CATCH"}:
            self.fail("No se acredita el cierre de registros de ambos motores")
        if not self.catches<=self.casts:
            self.fail("CATCH sin CAST de la misma sesion")
        if self.debits!=self.casts:
            self.fail("CAST con descuento ausente o distinto al intento")
        if not self.observed_casts<=self.casts:
            self.fail("CAST retenido sin envio registrado del intento")
        for attempt,path in self.closed_paths.items():
            if path=="CATCH" and attempt not in self.catches:
                self.fail("Cierre CATCH sin input registrado del intento")
            elif path=="DIRECT_REWARD" and attempt in self.catches:
                self.fail("Recompensa directa presentada pese a un input CATCH")
        if self.issues:
            return "STOPPED_FOR_REVIEW"
        if self.budget_reached:
            return "BAIT_ZERO_FINAL_CLOSURE_CONFIRMED"
        if self.initially_empty:
            return "INITIAL_INVENTORY_EMPTY"
        return "USER_STOP_OR_UNEXPECTED_EXIT_REVIEW_REQUIRED"

    def snapshot(self):
        return {"run_id":self.run_id,"initial_baits":self.initial,"estimated_remaining":self.remaining,
                "inventory_reads":self.inventory_reads,"casts":len(self.casts),"unique_debits":len(self.debits),
                "catch_inputs":len(self.catches),"confirmed_closures":len(self.closed),
                "outcomes":[{"outcome":key[0],"path":key[1],"count":value} for key,value in self.outcomes.items()],
                "cast_frozen_values":dict(sorted(self.locked_values.items())),"cast_maximum_hits":self.maximum_hits,
                "maximum_not_guaranteed":True,"max_catch_capture_age_before_input_ms":self.max_catch_age_ms,
                "max_cast_verification_age_ms":self.max_cast_age_ms,"budget_reached":self.budget_reached,
                "initially_empty":self.initially_empty,"stopped_roles":sorted(self.stopped),"issues":self.issues}
