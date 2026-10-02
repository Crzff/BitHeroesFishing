"""Seguir geometria no autoriza CATCH: el input exige 100% de la captura."""


def can_track(status):
    if not status.ready or status.xy is None:
        return False
    return (status.kind=="CATCH_ACTIVE" or status.kind=="UNKNOWN"
            and status.percentage is None and status.scores.get("CATCH",0)>=.92)


def input_block(status,capture_start_ns,now_ns):
    if status.kind!="CATCH_ACTIVE" or not status.ready or status.xy is None or status.percentage!=100:
        return "DISPLAY_NOT_100"
    if not 0<=now_ns-capture_start_ns<=60_000_000:
        return "CAPTURE_TOO_OLD"
    return None
