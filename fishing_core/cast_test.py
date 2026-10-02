"""Continuacion opt-in de un CAST de prueba que expiro sin input.

Nunca consume señales CATCH historicas ni presenta una estimacion como lectura.
"""

import json
import re

from .bait_budget import BaitBudget


def pending_budget(root,run_id):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}",run_id):
        raise ValueError("Sesion de origen invalida")
    directory=root/"runs"/run_id
    if (directory/"cast_pending_resumed.json").exists():
        raise ValueError("El CAST pendiente ya fue retomado")
    events=[json.loads(line) for line in (directory/"control_events.jsonl").read_text(encoding="utf-8").splitlines()]
    if not any(e["event"]=="AUTHORIZED_CAST_TEST" for e in events):
        raise ValueError("No es una prueba CAST autorizada")
    if not any(e["event"]=="SAFETY_STOP" and e.get("reason")=="Timeout WAIT_CAST; pantalla=CAST" for e in events):
        raise ValueError("La prueba no termino con CAST pendiente por timeout")
    request=json.loads((directory/"cycle.json").read_text(encoding="utf-8"))
    inputs=[e for e in events if e["event"]=="CONTROL_INPUT_SENT"]
    last=inputs[-1]
    if request["state"]!="WAIT_CAST" or last["purpose"]!="START" or last["cycle_id"]!=request["cycle_id"]:
        raise ValueError("No se acredita un START pendiente sin CAST")
    if any(e["purpose"]=="CAST" and e["cycle_id"]==last["cycle_id"] for e in inputs):
        raise ValueError("No se repite un CAST ya enviado")
    inventories=[e for e in events if e["event"]=="BAIT_INVENTORY"]
    if len(inventories)!=1 or inventories[0].get("reliable") is not True:
        raise ValueError("No hay un inventario inicial fiable unico")
    budget=BaitBudget(inventories[0]["total"])
    for event in inputs:
        if event["purpose"]=="CAST":
            if not budget.charge(event["attempt_id"]):
                raise ValueError("CAST duplicado en origen")
    if budget.remaining<=0:
        raise ValueError("No queda presupuesto estimado para la continuacion")
    return budget,{"origin_run":run_id,"origin_pending_attempt":last["attempt_id"],
                   "origin_initial_total_observed":inventories[0]["total"],
                   "remaining_is_estimate":True,"inventory_reopened":False},directory/"cast_pending_resumed.json"
