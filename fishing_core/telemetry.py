"""Registros por sesion; nunca escribir/flush antes del clic critico."""

from __future__ import annotations

import hashlib
import csv
import json
import math
import os
import queue
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from importlib import metadata

from . import VERSION

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_FIELDS = ["schema","run_id","cycle_id","attempt_id","track_id","utc","perf_ns",
                 "capture_start_ns","capture_end_ns","phase",
                 "screen","percentage","detected","cp","cv","wp","wz","delta","v","residual",
                 "reason","capture_ms","vision_ms","context_ms","detector_ms","ipc_ms","tracking_ms",
                 "decision_ms","input_ms","input_est_ms","input_est_used_ms"]


def json_safe(value):
    if isinstance(value,float) and not math.isfinite(value):
        return None
    if isinstance(value,dict):
        return {k:json_safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [json_safe(v) for v in value]
    return value


def new_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid4().hex[:12]


def run_environment() -> dict:
    env = os.environ.copy()
    env["FISHING_RUN_ID"] = new_run_id()
    return env


def source_hashes(root: Path = ROOT) -> dict:
    paths = list(root.glob("*.py")) + list((root / "fishing_core").glob("*.py"))
    paths += list((root / "assets").glob("*"))
    if (root / "fishing_runtime_config.json").is_file():
        paths.append(root / "fishing_runtime_config.json")
    if (root / "requirements.txt").is_file():
        paths.append(root / "requirements.txt")
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths) if p.is_file()
    }


class Telemetry:
    def __init__(self, role: str, run_id: str, root: Path = ROOT):
        self.role = role
        self.run_id = run_id
        self.directory = root / "runs" / run_id
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / f"{role.lower()}_events.jsonl"
        self.legacy_log = root / ("CATCH_LOG.txt" if role == "CATCH" else "CONTROL_LOG.txt")
        self.pending = queue.Queue(maxsize=8192)
        self.error = None
        self.dropped = 0
        self.closed = False
        manifest_path=self.directory / f"{role.lower()}_manifest.json"
        if manifest_path.exists():
            raise FileExistsError("Esta sesion ya tiene registros de este motor; iniciar una sesion nueva")
        packages={}
        for name in ("mss","numpy","opencv-python","customtkinter","Pillow"):
            try:
                packages[name]=metadata.version(name)
            except metadata.PackageNotFoundError:
                packages[name]=None
        manifest = {
            "schema": 1, "version": VERSION, "role": role, "run_id": run_id,
            "pid": os.getpid(), "utc": datetime.now(timezone.utc).isoformat(),
            "source_sha256": source_hashes(root),
            "python":sys.version,"packages":packages,
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        self.worker = threading.Thread(target=self._write, name=f"log-{role}", daemon=True)
        self.worker.start()
        self.emit("PROCESS_START", human=True, version=VERSION)

    def emit(self, event: str, human: bool = False, **fields) -> None:
        record = {
            "schema": 1, "version": VERSION, "role": self.role,
            "run_id": self.run_id, "pid": os.getpid(),
            "utc": datetime.now(timezone.utc).isoformat(),
            "perf_ns": time.perf_counter_ns(), "event": event, **fields,
        }
        try:
            self.pending.put_nowait((json_safe(record), human))
        except queue.Full:
            self.dropped += 1

    def check(self) -> None:
        if self.error or self.dropped:
            raise RuntimeError(f"Registro incompleto: error={self.error!r}, perdidos={self.dropped}")

    def _write(self):
        try:
            with self.path.open("a", encoding="utf-8") as events, self.legacy_log.open(
                "a", encoding="utf-8"
            ) as legacy, (self.directory / f"{self.role.lower()}_samples_R1.csv").open(
                "w",newline="",encoding="utf-8"
            ) as samples:
                csv_writer=csv.DictWriter(samples,fieldnames=SAMPLE_FIELDS,extrasaction="ignore")
                csv_writer.writeheader()
                last_flush = time.perf_counter()
                while True:
                    try:
                        item = self.pending.get(timeout=0.25)
                    except queue.Empty:
                        events.flush()
                        legacy.flush()
                        samples.flush()
                        continue
                    if item is None:
                        self.pending.task_done()
                        break
                    record, human = item
                    events.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
                    if record["event"] == "CATCH_FRAME":
                        csv_writer.writerow(record)
                    if human:
                        legacy.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
                    self.pending.task_done()
                    if time.perf_counter() - last_flush >= 0.5:
                        events.flush()
                        legacy.flush()
                        samples.flush()
                        last_flush = time.perf_counter()
                events.flush()
                legacy.flush()
                samples.flush()
        except Exception as exc:
            self.error = repr(exc)

    def close(self):
        if self.closed:
            return
        self.emit("PROCESS_STOP", human=True, dropped=self.dropped)
        self.closed = True
        try:
            self.pending.put(None, timeout=2)
        except queue.Full:
            self.error = self.error or "No se pudo cerrar el registro"
        self.worker.join(timeout=5)
        if self.worker.is_alive():
            self.error = self.error or "El escritor no termino"
        self.check()
