"""Presupuesto de una sola lectura inicial; no representa inventario en vivo."""

from dataclasses import dataclass, field


@dataclass
class BaitBudget:
    initial_total: int
    charged_attempts: set = field(default_factory=set)

    def __post_init__(self):
        if type(self.initial_total) is not int or self.initial_total < 0:
            raise ValueError("Cantidad inicial de cebos invalida")

    @property
    def remaining(self):
        return max(0, self.initial_total-len(self.charged_attempts))

    def charge(self, attempt_id):
        if not isinstance(attempt_id, str) or not attempt_id:
            raise ValueError("El descuento requiere un intento identificado")
        if attempt_id in self.charged_attempts:
            return False
        if self.remaining == 0:
            raise ValueError("Presupuesto inicial de cebos agotado")
        self.charged_attempts.add(attempt_id)
        return True

    def payload(self):
        return {"initial_total": self.initial_total, "attempts_debited": len(self.charged_attempts),
                "estimated_remaining": self.remaining, "remaining_is_estimate": True,
                "consumption_assumption": "ONE_BAIT_PER_CAST_INPUT", "inventory_checks_per_session": 1}
