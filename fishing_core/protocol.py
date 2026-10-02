"""IPC atomico, por sesion/intento. INPUT_SENT no significa SUCCESS."""

from __future__ import annotations

import json
import hashlib
import os
import re
import time
from collections import Counter
from functools import lru_cache
from contextlib import contextmanager
from pathlib import Path

from .telemetry import ROOT

ARMED_STATES = frozenset(("WAIT_CAST_RESULT", "CATCH_GAME"))
LEASE_NS = 3_000_000_000
READ_DENIED_LIMIT_SEG = .5
REPLACE_ATTEMPTS = 6
_io_counts = Counter()
_read_denied_since = {}


def io_diagnostics():
    return dict(_io_counts)


@lru_cache(maxsize=1)
def _windows_mutex_api():
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
    kernel.ReleaseMutex.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    return kernel


@contextmanager
def _ipc_guard(path: Path, wait_ms: int):
    """Coordina handles de lectores/escritores entre procesos de Windows.

    El lector CATCH nunca espera: si el escritor ocupa el archivo, descarta
    este frame. El escritor espera como maximo 100 ms. Crear/cerrar el
    handle por operacion evita acumular handles en el panel entre sesiones.
    """
    if os.name != "nt":
        yield True
        return
    import ctypes
    kernel = _windows_mutex_api()
    normalized = os.path.normcase(os.path.abspath(str(path)))
    name = "Local\\BitHeroesFishing_IPC_" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    handle = kernel.CreateMutexW(None, False, name)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    owned = False
    try:
        result = kernel.WaitForSingleObject(handle, wait_ms)
        if result not in (0, 0x80, 0x102):
            raise ctypes.WinError(ctypes.get_last_error())
        owned = result in (0, 0x80)
        if result == 0x80:
            _io_counts["abandoned_lock_recovered"] += 1
        yield owned
    finally:
        if owned:
            kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


def session_directory(run_id: str, root: Path = ROOT) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", run_id):
        raise ValueError("Identificador de sesion invalido")
    return root / "runs" / run_id


def read_json(path: Path):
    try:
        with _ipc_guard(path, 0) as owned:
            if not owned:
                _io_counts["read_lock_busy"] += 1
                return None
            text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _read_denied_since.pop(str(path), None)
        return None
    except PermissionError:
        _io_counts["read_denied"] += 1
        now = time.perf_counter()
        since = _read_denied_since.setdefault(str(path), now)
        if now - since >= READ_DENIED_LIMIT_SEG:
            _io_counts["persistent_read_denied"] += 1
            raise
        # Sin espera en el camino critico de CATCH: este frame no arma input.
        return None
    _read_denied_since.pop(str(path), None)
    _io_counts["reads_ok"] += 1
    return json.loads(text)


def atomic_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    text = json.dumps(data, allow_nan=False)
    with _ipc_guard(path, 100) as owned:
        if not owned:
            _io_counts["write_lock_timeout"] += 1
            raise TimeoutError(f"IPC ocupado durante 100 ms: {path}")
        try:
            temp.write_text(text, encoding="utf-8")
            for attempt in range(REPLACE_ATTEMPTS):
                try:
                    os.replace(temp, path)
                    _io_counts["writes_ok"] += 1
                    break
                except PermissionError:
                    _io_counts["replace_denied"] += 1
                    if attempt + 1 == REPLACE_ATTEMPTS:
                        _io_counts["persistent_replace_denied"] += 1
                        raise
                    time.sleep(.002 * 2 ** attempt)
        finally:
            temp.unlink(missing_ok=True)


def valid_request(request, run_id: str, now_ns: int) -> bool:
    if not isinstance(request, dict):
        return False
    return (
        request.get("schema") == 1 and request.get("run_id") == run_id
        and isinstance(request.get("cycle_id"), int) and request["cycle_id"] > 0
        and isinstance(request.get("attempt_id"), str) and bool(request["attempt_id"])
        and request.get("state") in ARMED_STATES
        and isinstance(request.get("issued_perf_ns"), int)
        and isinstance(request.get("updated_perf_ns"), int)
        and 0 <= now_ns-request["updated_perf_ns"] <= LEASE_NS
        and request["issued_perf_ns"] <= request["updated_perf_ns"]
    )


def valid_signal(signal, request, run_id: str, catch_pid: int, now_ns: int) -> bool:
    if not isinstance(signal, dict) or not isinstance(request, dict):
        return False
    return (
        signal.get("schema") == 1 and signal.get("event") == "INPUT_SENT"
        and signal.get("run_id") == run_id and signal.get("catch_pid") == catch_pid
        and signal.get("cycle_id") == request.get("cycle_id")
        and signal.get("attempt_id") == request.get("attempt_id")
        and isinstance(signal.get("sent_perf_ns"), int)
        and request.get("issued_perf_ns", now_ns+1) <= signal["sent_perf_ns"] <= now_ns
    )


class AttemptLock:
    """No se rearma por tiempo ni por perdida visual; solo por otro intento."""
    def __init__(self):
        self.sent = set()

    def available(self, attempt_id: str) -> bool:
        return bool(attempt_id) and attempt_id not in self.sent

    def claim(self, attempt_id: str):
        if not self.available(attempt_id):
            raise RuntimeError("Segundo input bloqueado para el mismo intento")
        self.sent.add(attempt_id)


class Channel:
    def __init__(self, run_id: str, root: Path = ROOT):
        self.run_id = run_id
        self.directory = session_directory(run_id, root)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.request_path = self.directory / "cycle.json"
        self.signal_path = self.directory / "CATCH_OK.signal"
        self.ready_path = self.directory / "catch_ready.json"
        self.stop_path = self.directory / "stop.json"

    def request(self):
        return read_json(self.request_path)

    def signal(self):
        return read_json(self.signal_path)

    def ready(self):
        return read_json(self.ready_path)

    def stop(self, role: str, reason: str):
        atomic_json(self.stop_path, {"schema": 1, "run_id": self.run_id,
                                    "role": role, "reason": reason, "perf_ns": time.perf_counter_ns()})
