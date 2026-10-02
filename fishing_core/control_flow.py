"""Maquina de estados pura. Ninguna accion puede ser un clic CATCH."""

from __future__ import annotations

from dataclasses import dataclass

from .vision import Evidence


class SafetyStop(RuntimeError):
    pass


@dataclass
class Action:
    purpose: str
    expected_screen: str
    xy: tuple
    cycle_id: int
    attempt_id: str
    retry: int = 0


class ControlFlow:
    START_RETRY_DELAY = 1.0
    MAX_START_RETRIES = 2
    TIMEOUTS = {"RESUME": 15, "WAIT_CAST": 15, "WAIT_CAST_RESULT": 45,
                "CATCH_GAME": 45, "WAIT_RESULT": 45, "WAIT_ITEMS": 10, "WAIT_START": 12}

    def __init__(self, run_id: str, now: float):
        self.run_id = run_id
        self.state = "RESUME"
        self.entered = now
        self.cycle_id = 0
        self.attempt_id = ""
        self.saw_catch = False
        self.input_confirmed = False
        self.outcome = None
        self.outcome_path = None
        self.last_kind = None
        self.last_xy = None
        self.stable_since = now
        self.stable_count = 0
        self.last_action = -float("inf")
        self.retries = 0
        self.wait_close_purpose = None
        self.transitions = []

    def transition(self, state: str, now: float, reason: str):
        if state == self.state:
            return
        self.transitions.append((self.state, state, reason))
        self.state = state
        self.entered = now
        self.retries = 0

    @property
    def request_state(self):
        return self.state

    def _click(self, purpose, e, now, next_state, retry=0):
        if purpose not in ("START", "CAST", "TRADE", "ITEMS", "CLOSE") or not e.xy:
            raise SafetyStop("Accion CONTROL no permitida")
        self.last_action = now
        self.transition(next_state, now, purpose)
        return Action(purpose, e.kind, e.xy, self.cycle_id, self.attempt_id, retry)

    def _new_cycle(self):
        self.cycle_id += 1
        self.attempt_id = f"{self.run_id}:{self.cycle_id}"
        self.saw_catch = False
        self.input_confirmed = False
        self.outcome = None
        self.outcome_path = None

    def step(self, e: Evidence, now: float, valid_input: bool = False) -> Action | None:
        same_position = e.xy is None and self.last_xy is None or (
            e.xy is not None and self.last_xy is not None and
            max(abs(e.xy[i]-self.last_xy[i]) for i in (0, 1)) <= 3)
        if e.kind == self.last_kind and same_position:
            self.stable_count += 1
        else:
            self.stable_count = 1
            self.stable_since = now
        self.last_kind, self.last_xy = e.kind, e.xy
        stable = self.stable_count >= 2 and now-self.stable_since >= (.25 if e.kind == "START" else .06)

        if now-self.entered > self.TIMEOUTS[self.state]:
            raise SafetyStop(f"Timeout {self.state}; pantalla={e.kind}")

        if self.state in ("WAIT_CAST_RESULT", "CATCH_GAME", "WAIT_RESULT"):
            if e.kind in ("CATCH_ACTIVE", "CATCH_PENDING"):
                self.saw_catch = True
                self.transition("CATCH_GAME" if not self.input_confirmed else "WAIT_RESULT", now, e.kind)
            if valid_input:
                self.input_confirmed = True
                self.saw_catch = True
                self.transition("WAIT_RESULT", now, "INPUT_SENT_VALIDATED")
            if stable and e.ready and e.kind in ("SUCCESS", "FAILED"):
                if e.kind == "SUCCESS" and self.saw_catch and not self.input_confirmed:
                    raise SafetyStop("SUCCESS de CATCH sin input confirmado del intento actual")
                self.outcome = e.kind
                self.outcome_path = "CATCH" if self.saw_catch else "DIRECT_REWARD"
                if e.kind == "SUCCESS":
                    return self._click("TRADE", e, now, "WAIT_ITEMS")
                self.wait_close_purpose = "CLOSE"
                return self._click("CLOSE", e, now, "WAIT_START")
            return None

        if self.state == "RESUME":
            if e.kind in ("CATCH_ACTIVE", "CATCH_PENDING"):
                raise SafetyStop("Minijuego ya activo al iniciar: no pertenece a un CAST autorizado")
            if stable and e.ready:
                if e.kind == "START":
                    self._new_cycle()
                    return self._click("START", e, now, "WAIT_CAST")
                if e.kind == "CAST":
                    self._new_cycle()
                    return self._click("CAST", e, now, "WAIT_CAST_RESULT")
                if e.kind == "SUCCESS":
                    self.outcome, self.outcome_path = "SUCCESS", "RECOVERY"
                    return self._click("TRADE", e, now, "WAIT_ITEMS")
                if e.kind in ("ITEMS", "FAILED"):
                    self.outcome_path = "RECOVERY"
                    self.wait_close_purpose = "ITEMS" if e.kind == "ITEMS" else "CLOSE"
                    return self._click(self.wait_close_purpose, e, now, "WAIT_START")
            return None

        if self.state == "WAIT_CAST":
            if stable and e.kind == "CAST" and e.ready:
                return self._click("CAST", e, now, "WAIT_CAST_RESULT")
            if stable and e.kind == "START" and e.ready and now-self.last_action >= self.START_RETRY_DELAY:
                self.retries += 1
                if self.retries > self.MAX_START_RETRIES:
                    raise SafetyStop("START sigue visible tras el input inicial y dos reintentos; no se envia CAST")
                # Mismo ciclo/intento. Solo START confirmado; nunca reintentar CAST o CATCH.
                return self._click("START", e, now, "WAIT_CAST", retry=self.retries)
            return None

        if self.state == "WAIT_ITEMS":
            if stable and e.kind == "ITEMS" and e.ready:
                self.wait_close_purpose = "ITEMS"
                return self._click("ITEMS", e, now, "WAIT_START")
            if stable and e.kind == "SUCCESS" and e.ready and now-self.last_action >= .8:
                self.retries += 1
                if self.retries > 3:
                    raise SafetyStop("TRADE no desaparece")
                return self._click("TRADE", e, now, "WAIT_ITEMS")
            return None

        if self.state == "WAIT_START":
            if stable and e.kind == "START" and e.ready:
                self._new_cycle()
                return self._click("START", e, now, "WAIT_CAST")
            if stable and e.kind in ("ITEMS", "FAILED") and e.ready and now-self.last_action >= .8:
                purpose = "ITEMS" if e.kind == "ITEMS" else "CLOSE"
                if purpose != self.wait_close_purpose:
                    raise SafetyStop("Modal inesperado al esperar START")
                self.retries += 1
                if self.retries > 3:
                    raise SafetyStop("El modal no desaparece")
                return self._click(purpose, e, now, "WAIT_START")
        return None
