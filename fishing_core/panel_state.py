"""Modelo puro del panel. INPUT_SENT no se presenta como captura confirmada."""

import json
from dataclasses import dataclass, field


@dataclass
class PanelState:
    run_id: str
    activity: str = "Preparando motores · espera inicial de 5 s"
    outcome: str = "Sin resultados en esta sesión"
    bait_total: int | None = None
    bait_initial: int | None = None
    bait_remaining_estimate: int | None = None
    bait_details: str = "Se comprobarán al llegar a START"
    bait_checking: bool = False
    completed: int = 0
    terminal: bool = False
    checked_perf_ns: int | None = None
    catch_successes: int = 0
    direct_rewards: int = 0
    failed: int = 0
    cast_maximum: int | None = None
    cast_value: int | None = None
    cast_attempt: str | None = None
    cast_observations: int = 0
    cast_maximum_hits: int = 0
    cast_unconfirmed: bool = False
    _closed_attempts: set = field(default_factory=set, repr=False)
    _cast_observed_attempts: set = field(default_factory=set, repr=False)

    def apply(self, event):
        if event.get("run_id") != self.run_id or event.get("role") != "CONTROL":
            return
        kind = event.get("event")
        if self.terminal:
            return
        if kind == "BAIT_CHECK_STARTED":
            self.activity = "Comprobando inventario de cebos"
            self.bait_checking = True
        elif kind == "BAIT_INVENTORY" and self.bait_initial is None and event.get("reliable") is True and type(event.get("total")) is int:
            self.bait_total = event["total"]
            self.checked_perf_ns = event.get("checked_perf_ns")
            if self.bait_initial is None:
                self.bait_initial = self.bait_total
            self.bait_remaining_estimate = self.bait_initial
            self.bait_details = (" · ".join(f"{s['name']}: {s['quantity']}" for s in event.get("stacks", [])) or "Inventario vacío") + " (cantidades iniciales)"
            self.bait_checking = False
            self.activity = "Cebos comprobados · cerrando inventario"
        elif kind in ("BAIT_BUDGET_INITIALIZED", "BAIT_BUDGET_UPDATED", "BAIT_BUDGET_REACHED"):
            initial=event.get("initial_total")
            remaining=event.get("estimated_remaining")
            debited=event.get("attempts_debited")
            if (type(initial) is not int or initial!=self.bait_initial or type(remaining) is not int
                    or type(debited) is not int or not 0<=remaining<=initial or remaining!=max(0,initial-debited)):
                return
            if self.bait_remaining_estimate is not None and remaining>self.bait_remaining_estimate:
                return
            self.bait_remaining_estimate=remaining
            if kind=="BAIT_BUDGET_REACHED":
                self.activity="Detenido: presupuesto inicial de cebos agotado"
                self.terminal=True
        elif kind == "BAIT_READ_FAILED":
            self.bait_total = None
            self.bait_remaining_estimate = None
            self.bait_checking = False
            self.bait_details = "Lectura no fiable; no se inicia otra pesca"
            self.activity = "Detenido: no se pudo contar todo el inventario"
            self.terminal = True
        elif kind == "BAIT_EXHAUSTED":
            self.bait_total = 0
            self.bait_remaining_estimate = 0
            self.activity = "Detenido: no quedan cebos"
            self.terminal = True
        elif kind == "CYCLE_COMPLETE":
            attempt = event.get("attempt_id")
            outcome, path = event.get("outcome"), event.get("outcome_path")
            if (not isinstance(attempt, str) or not attempt or attempt in self._closed_attempts
                    or outcome not in ("SUCCESS", "FAILED") or path not in ("CATCH", "DIRECT_REWARD")):
                return
            self._closed_attempts.add(attempt)
            self.completed += 1
            if outcome == "FAILED":
                self.failed += 1
            elif path == "CATCH":
                self.catch_successes += 1
            else:
                self.direct_rewards += 1
            self._outcome(event)
        elif kind == "CAST_LOCK_OBSERVED":
            attempt = event.get("attempt_id")
            if attempt != self.cast_attempt or attempt is None or attempt in self._cast_observed_attempts:
                return
            if event.get("status") == "FROZEN_VALUE_NOT_CONFIRMED":
                self.cast_unconfirmed = True
                return
            minimum, maximum, value = (event.get(name) for name in ("minimum", "maximum", "value"))
            if (event.get("status") != "FROZEN_VALUE_OBSERVED"
                    or any(type(number) is not int for number in (minimum, maximum, value))
                    or not 0 < minimum < maximum <= 999 or not minimum <= value <= maximum
                    or maximum != self.cast_maximum):
                return
            self._cast_observed_attempts.add(attempt)
            self.cast_value = value
            self.cast_observations += 1
            self.cast_maximum_hits += int(value == maximum)
            self.cast_unconfirmed = False
        elif kind == "RUN_LIMIT_REACHED":
            self.activity = f"Prueba terminada · {event['completed']} ciclos completos"
            self.terminal = True
        elif kind in ("SAFETY_STOP", "PROCESS_ERROR"):
            self.activity = "Detenido: " + str(event.get("reason", "error"))
            self.terminal = True
        elif kind == "CONTROL_INPUT_SENT":
            purpose = event.get("purpose")
            if purpose == "CAST":
                scores = event.get("fresh_scores", {})
                maximum = scores.get("CAST_MAX")
                self.cast_attempt = event.get("attempt_id")
                self.cast_maximum = maximum if type(maximum) is int and 0 < maximum <= 999 else None
                self.cast_value = None
                self.cast_unconfirmed = False
            self._outcome(event)
            activities = {"START": "START enviado · preparando CAST", "CAST": "CAST enviado · esperando pez u objeto",
                          "TRADE": "Recogiendo ITEMS", "ITEMS": "ITEMS cerrados · volviendo a START",
                          "CLOSE": "FAILED · cerrando resultado"}
            self.activity = activities.get(purpose, self.activity)
            if purpose == "START" and event.get("retry", 0):
                self.activity = f"Reintentando START ({event['retry']}/2) · esperando CAST"
        elif kind == "STATE_TRANSITION":
            self._outcome(event)
            state = event.get("new")
            self.activity = {"WAIT_CAST": "Preparando CAST", "WAIT_CAST_RESULT": "Esperando pez u objeto",
                             "CATCH_GAME": "CATCH · siguiendo al pez",
                             "WAIT_RESULT": "CATCH enviado · esperando resultado",
                             "WAIT_ITEMS": "Recogiendo ITEMS", "WAIT_START": "Cerrando resultado · volviendo a START"}.get(state, self.activity)

    def _outcome(self, event):
        if event.get("outcome") == "SUCCESS":
            if event.get("outcome_path") == "RECOVERY":
                self.outcome = "Resultado previo SUCCESS · recuperando sesión"
            else:
                self.outcome = "Recompensa directa · sin CATCH" if event.get("outcome_path") == "DIRECT_REWARD" else "Captura confirmada (SUCCESS)"
        elif event.get("outcome") == "FAILED":
            self.outcome = "Captura fallida (FAILED)"

    @property
    def result_summary(self):
        return (f"CATCH: {self.catch_successes} · directas: {self.direct_rewards} · "
                f"FAILED: {self.failed} · cierres: {self.completed}")

    @property
    def cast_label(self):
        if self.cast_value is not None:
            return (f"CAST retenido: {self.cast_value}/{self.cast_maximum} · "
                    f"máximos: {self.cast_maximum_hits}/{self.cast_observations}")
        if self.cast_unconfirmed:
            return "CAST: valor retenido no confirmado"
        if self.cast_attempt is not None:
            target = f" · objetivo {self.cast_maximum}" if self.cast_maximum is not None else ""
            return f"CAST enviado{target} · pendiente de observación"
        return "CAST: sin lanzamiento en esta sesión"

    @property
    def bait_label(self):
        if self.bait_checking:
            return "Cebos: comprobando…"
        if self.bait_total is None:
            return "Cebos: sin lectura confirmada"
        remaining=self.bait_remaining_estimate
        warning = " · pocos cebos" if remaining is not None and 0 < remaining <= 10 else ""
        return f"Cebos iniciales: {self.bait_initial} · restantes estimados: {remaining}{warning}"


class SessionFeed:
    """Lee lineas completas de CONTROL; no relee el historico ni CATCH_FRAME."""
    def __init__(self, directory, run_id):
        self.path = directory / "control_events.jsonl"
        self.run_id = run_id
        self.offset = 0

    def read(self):
        if not self.path.exists():
            return []
        events = []
        with self.path.open("rb") as stream:
            stream.seek(self.offset)
            while True:
                start = stream.tell()
                line = stream.readline()
                if not line.endswith(b"\n"):
                    self.offset = start
                    break
                event = json.loads(line.decode("utf-8"))
                self.offset = stream.tell()
                if event.get("run_id") == self.run_id:
                    events.append(event)
        return events
