"""Muestra retenida por el juego tras CAST; no decide ni envia inputs."""


class CastAudit:
    def __init__(self):
        self.pending=None
        self.previous_value=None
        self.since=None
        self.samples=0

    def sent(self,cycle_id,attempt_id,minimum,maximum,sent_ns):
        self.pending={"cycle_id":cycle_id,"attempt_id":attempt_id,"minimum":minimum,
                      "maximum":maximum,"sent_ns":sent_ns}
        self.previous_value=self.since=None
        self.samples=0

    def observe(self,measurement,cast_active,capture_start_ns):
        if self.pending is None:
            return None
        p=self.pending
        elapsed=capture_start_ns-p["sent_ns"]
        if elapsed>2_000_000_000:
            self.pending=None
            return {**p,"status":"FROZEN_VALUE_NOT_CONFIRMED"}
        value=measurement.get("CAST_VALUE")
        valid=(elapsed>=100_000_000 and not cast_active and measurement.get("CAST_RANGE_VALID")
               and (measurement["CAST_MIN"],measurement["CAST_MAX"])==(p["minimum"],p["maximum"]))
        if not valid:
            self.previous_value=self.since=None
            self.samples=0
            return None
        if value!=self.previous_value:
            self.previous_value=value
            self.since=capture_start_ns
            self.samples=0
        self.samples+=1
        if self.samples>=3 and capture_start_ns-self.since>=80_000_000:
            self.pending=None
            return {**p,"status":"FROZEN_VALUE_OBSERVED","value":value,"at_displayed_maximum":value==p["maximum"],
                    "samples":self.samples,"stable_ms":(capture_start_ns-self.since)/1e6,
                    "capture_start_ns":capture_start_ns}
        return None
