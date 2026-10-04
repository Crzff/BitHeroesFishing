"""Cuotas conservadoras de una sesion de dungeon; no captura ni envia input."""

from math import isfinite
import time


def _quantity(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name}: entero conocido >= {minimum} requerido")
    return value


def _identifier(value):
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError("Intencion sin identificador valido")


def _seconds(value):
    if type(value) not in (int, float):
        raise ValueError("Tiempo desconocido o no finito")
    try:
        seconds = float(value)
    except OverflowError as exc:
        raise ValueError("Tiempo no representable") from exc
    if not isfinite(seconds):
        raise ValueError("Tiempo desconocido o no finito")
    return seconds


ENTRY_RESOURCES = ("ENERGY", "XEALS", "TOKENS", "SHARDS", "TICKETS", "BADGES")


class FarmBudget:
    # ponytail: un controlador y estado en memoria; diario transaccional para reanudar.
    def __init__(self, *, max_runs, max_energy, max_seconds, energy_reserve=0,
                 max_gold=0, gold_reserve=0, clock=None, stop_on_defeat=True):
        self.max_runs = _quantity(max_runs, "Limite de runs", 1)
        self.max_energy = _quantity(max_energy, "Limite de energia", 1)
        self.energy_reserve = _quantity(energy_reserve, "Reserva de energia")
        self.max_gold = _quantity(max_gold, "Limite de oro")
        self.gold_reserve = _quantity(gold_reserve, "Reserva de oro")
        duration = _seconds(max_seconds)
        if duration <= 0:
            raise ValueError("Duracion positiva requerida")
        self.clock = time.monotonic if clock is None else clock
        self._last_now = _seconds(self.clock())
        self.deadline = _seconds(self._last_now + duration)
        if self.deadline <= self._last_now:
            raise ValueError("Duracion no representable por el reloj")
        self._entries = {}
        self._results = {}
        self._gold_actions = {}
        self._gold_resolved = set()
        self.energy_reserved = 0  # unidades del recurso de entrada de la sesion
        self.resource = None
        self.gold_reserved = 0
        self.active_attempt = None
        self.pending_gold = None
        self.stop_reason = None
        # PvP, Expedition y Trials pueden perder con normalidad; Raid y World Boss no.
        self.stop_on_defeat = stop_on_defeat

    def _check_open(self):
        if self.stop_reason:
            raise ValueError(f"Sesion detenida: {self.stop_reason}")
        now = _seconds(self.clock())
        if now < self._last_now:
            raise ValueError("El reloj retrocedio; revisar antes de actuar")
        self._last_now = now
        if now >= self.deadline:
            raise ValueError("Tiempo de sesion agotado")

    def reserve_entry(self, attempt_id, *, resource, balance, cost):
        """True solo para una nueva intencion; efecto incierto nunca se libera."""
        _identifier(attempt_id)
        # Una sesion gasta un unico recurso regenerable; nunca oro ni gemas.
        if resource not in ENTRY_RESOURCES:
            raise ValueError("Recurso de entrada no permitido")
        if self.resource is None:
            self.resource = resource
        elif resource != self.resource:
            raise ValueError("Una sesion no mezcla recursos de entrada")
        _quantity(balance, "Saldo de energia")
        _quantity(cost, "Coste de entrada", 1)
        if attempt_id in self._entries:
            if self._entries[attempt_id] != cost:
                raise ValueError("ID de entrada reutilizado con otro coste")
            return False
        self._check_open()
        if self.pending_gold is not None:
            raise ValueError("Gasto de oro previo sin resolver")
        if self.active_attempt is not None:
            raise ValueError("Entrada previa sin cierre confirmado")
        if len(self._entries) >= self.max_runs:
            raise ValueError("Limite de runs alcanzado")
        if self.energy_reserved + cost > self.max_energy:
            raise ValueError("Cuota de energia agotada")
        if balance - cost < self.energy_reserve:
            raise ValueError("Saldo insuficiente o reserva de energia protegida")
        self._entries[attempt_id] = cost
        self.energy_reserved += cost
        self.active_attempt = attempt_id
        return True

    def finish_run(self, attempt_id, outcome, *, closure_confirmed):
        """Registra un resultado, no autoriza input ni acredita lectura de botin."""
        _identifier(attempt_id)
        if closure_confirmed is not True or outcome not in ("VICTORY", "DEFEAT"):
            raise ValueError("Resultado sin cierre confirmado")
        if attempt_id in self._results:
            if self._results[attempt_id] != outcome:
                raise ValueError("Resultado contradictorio para la misma entrada")
            return False
        if self.active_attempt != attempt_id:
            raise ValueError("Resultado sin entrada activa de esta sesion")
        if self.pending_gold is not None:
            raise ValueError("Gasto de oro previo sin resolver")
        self._results[attempt_id] = outcome
        self.active_attempt = None
        if outcome == "DEFEAT" and self.stop_on_defeat:
            self.stop_reason = "DEFEAT"
        return True

    def reserve_gold(self, action_id, *, currency, purpose, target, balance, cost):
        """Solo cuota; el llamante debe validar objetivo y rareza autorizados."""
        _identifier(action_id)
        _identifier(target)
        if currency != "GOLD" or purpose not in ("PERSUADE", "RESTOCK_COMMON"):
            raise ValueError("Moneda o proposito de gasto no permitidos")
        _quantity(balance, "Saldo de oro")
        _quantity(cost, "Coste en oro", 1)
        intent = (purpose, target, cost)
        if action_id in self._gold_actions:
            if self._gold_actions[action_id] != intent:
                raise ValueError("ID de gasto reutilizado con otro proposito, objetivo o coste")
            return False
        self._check_open()
        if self.pending_gold is not None:
            raise ValueError("Gasto de oro previo sin resolver")
        if (purpose == "PERSUADE") != (self.active_attempt is not None):
            raise ValueError("Persuade solo durante una run; reposicion solo entre runs")
        if self.gold_reserved + cost > self.max_gold:
            raise ValueError("Cuota compartida de oro agotada o deshabilitada")
        if balance - cost < self.gold_reserve:
            raise ValueError("Saldo insuficiente o reserva de oro protegida")
        self._gold_actions[action_id] = intent
        self.gold_reserved += cost
        self.pending_gold = action_id
        return True

    def finish_gold(self, action_id, *, effect_confirmed):
        """Confirmar efecto/cierre, no exito de reclutamiento ni reembolso."""
        _identifier(action_id)
        if effect_confirmed is not True:
            raise ValueError("Efecto del gasto de oro sin confirmar")
        if action_id in self._gold_resolved:
            return False
        if self.pending_gold != action_id:
            raise ValueError("Confirmacion sin gasto de oro pendiente")
        self._gold_resolved.add(action_id)
        self.pending_gold = None
        return True

    def payload(self):
        return {"entries_reserved": len(self._entries), "energy_reserved": self.energy_reserved,
                "completed_runs": len(self._results), "active_attempt": self.active_attempt,
                "gold_reserved": self.gold_reserved, "pending_gold": self.pending_gold,
                "stop_reason": self.stop_reason, "reserved_is_actual_spend": False}
