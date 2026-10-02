"""Inventario exclusivo de CONTROL, siempre antes de START; nunca pulsa CATCH."""

import time

import cv2

from .bait_inventory import BAIT_SLOT_XY, BaitReader
from .control_flow import SafetyStop
from .protocol import atomic_json
from .vision import FrameView


def wait_screen(kind, ui, grab, stop, timeout=3, stable_for=0):
    deadline = time.perf_counter()+timeout
    stable_since = None
    last_xy = None
    samples = 0
    while time.perf_counter() < deadline:
        stop()
        image = grab()
        evidence = ui.classify(FrameView(image))
        if evidence.kind == kind and evidence.ready:
            now = time.perf_counter()
            same_xy = evidence.xy is not None and last_xy is not None and max(
                abs(evidence.xy[i]-last_xy[i]) for i in (0, 1)) <= 3
            if stable_since is None or not same_xy:
                stable_since = now
                samples = 0
            samples += 1
            last_xy = evidence.xy
            if stable_for == 0 or samples >= 3 and now-stable_since >= stable_for:
                return image, evidence
        else:
            stable_since = None
            last_xy = None
            samples = 0
        time.sleep(.05)
    raise SafetyStop(f"Inventario: no se confirma pantalla {kind}")


def close_selection(io, ui, grab, stop, log):
    image, evidence = wait_screen("SELECT_MENU", ui, grab, stop)
    stop()
    io.click(evidence.xy)
    log.emit("INVENTORY_INPUT_SENT", human=True, purpose="CLOSE_BAIT_MENU", xy=evidence.xy)
    image, start = wait_screen("START", ui, grab, stop, stable_for=.6)
    log.emit("START_READY_AFTER_INVENTORY", human=True, stable_for_ms=600, xy=start.xy)
    return image, start


def audit_baits(io, ui, channel, log, grab, stop):
    """No confia en un SELECT preabierto: abre siempre desde el tercer cuadro."""
    reader = BaitReader()
    log.emit("BAIT_CHECK_STARTED", human=True)
    wait_screen("START", ui, grab, stop)
    stop()
    io.click(BAIT_SLOT_XY)
    log.emit("INVENTORY_INPUT_SENT", human=True, purpose="OPEN_BAIT_MENU", xy=BAIT_SLOT_XY)
    wait_screen("SELECT_MENU", ui, grab, stop)
    deadline = time.perf_counter()+3
    previous = None
    stable_since = None
    inventory = None
    last_image = None
    read_image = None
    reads_tried = 0
    while time.perf_counter() < deadline:
        stop()
        image = grab()
        last_image = image
        evidence = ui.menu_status(FrameView(image))
        if evidence.kind != "SELECT_MENU" or not evidence.ready:
            previous = None
            stable_since = None
            time.sleep(.05)
            continue
        inventory = reader.read(FrameView(image))
        read_image = image
        reads_tried += 1
        if inventory.reliable and inventory.signature == previous and time.perf_counter()-stable_since >= .1:
            # Solo se publica una lectura independiente confirmada; no estimacion acumulada.
            payload = {"schema": 1, "run_id": channel.run_id, "checked_perf_ns": time.perf_counter_ns(),
                       **inventory.payload()}
            atomic_json(channel.directory/"bait_inventory.json", payload)
            cv2.imwrite(str(channel.directory/"bait_inventory_last.png"), image[220:800, 555:1395])
            log.emit("BAIT_INVENTORY", human=True, **payload)
            close_selection(io, ui, grab, stop, log)
            return inventory
        if inventory.reliable:
            if previous != inventory.signature:
                stable_since = time.perf_counter()
            previous = inventory.signature
        else:
            previous = None
            stable_since = None
        time.sleep(.05)
    reason = inventory.reason if inventory is not None else "MENU_NOT_STABLE"
    # El runtime exterior tenia la captura START previa al conteo; conservar
    # aqui la captura de inventario que realmente fallo, sin reabrir el menu.
    failed_image = read_image if read_image is not None else last_image
    image_saved = False
    if failed_image is not None:
        try:
            image_saved = bool(cv2.imwrite(str(channel.directory/"bait_read_failure.png"),
                                          failed_image[220:800,555:1405]))
        except (cv2.error, OSError) as exc:
            log.emit("BAIT_DIAGNOSTIC_SAVE_FAILED", human=True, reason=repr(exc))
    log.emit("BAIT_READ_FAILED", human=True, reason=reason, reads_tried=reads_tried,
             diagnostic=inventory.diagnostic if inventory is not None else {},
             diagnostic_image="bait_read_failure.png" if image_saved else None,image_origin=[555,220])
    # No se declara 0 ni se inicia pesca ante fallo OCR.
    raise SafetyStop(f"No se puede contar todo el inventario de cebos: {reason}")
