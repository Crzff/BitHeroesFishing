import tempfile
import json
import os
import threading
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fishing_core.protocol import AttemptLock, Channel, atomic_json, valid_request, valid_signal
from fishing_core import protocol


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.req = dict(schema=1, run_id="run", cycle_id=1, attempt_id="a", state="CATCH_GAME",
                        issued_perf_ns=10, updated_perf_ns=20)
        self.signal = dict(schema=1, run_id="run", cycle_id=1, attempt_id="a", event="INPUT_SENT",
                           catch_pid=123, sent_perf_ns=30)

    def test_exact_signal_identity(self):
        self.assertTrue(valid_signal(self.signal, self.req, "run", 123, 40))
        for key, value in [("cycle_id", 2), ("attempt_id", "old"), ("run_id", "old"),
                           ("catch_pid", 999), ("sent_perf_ns", 1), ("event", "SUCCESS")]:
            self.assertFalse(valid_signal({**self.signal, key:value}, self.req, "run", 123, 40))
        self.assertFalse(valid_signal(1790750634.604579, self.req, "run", 123, 40))

    def test_lease_and_noncatch_states(self):
        self.assertTrue(valid_request(self.req, "run", 40))
        self.assertFalse(valid_request(self.req, "run", 4_000_000_000))
        for state in ("WAIT_ITEMS", "WAIT_START", "WAIT_RESULT", "STOP"):
            self.assertFalse(valid_request({**self.req,"state":state}, "run", 40))

    def test_no_timeout_or_absence_rearm(self):
        lock = AttemptLock()
        lock.claim("a")
        self.assertFalse(lock.available("a"))
        with self.assertRaises(RuntimeError):
            lock.claim("a")
        self.assertTrue(lock.available("b"))

    def test_atomic_roundtrip_and_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            ch = Channel("run", Path(temp))
            atomic_json(ch.request_path, self.req)
            self.assertEqual(ch.request(), self.req)
            self.assertIsNone(ch.signal())
            self.assertEqual(list(ch.directory.glob("*.tmp")), [])
            with self.assertRaises(ValueError):
                Channel("../escape", Path(temp))

    @unittest.skipUnless(os.name == "nt", "Semantica de handles de Windows")
    def test_writer_waits_until_reader_closes_handle(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"cycle.json"
            atomic_json(path, {"generation": 1})
            done = threading.Event()
            errors = []
            def writer():
                try:
                    atomic_json(path, {"generation": 2})
                except Exception as exc:
                    errors.append(repr(exc))
                finally:
                    done.set()
            with protocol._ipc_guard(path, 0) as owned:
                self.assertTrue(owned)
                with path.open(encoding="utf-8") as reader:
                    worker = threading.Thread(target=writer)
                    worker.start()
                    self.assertFalse(done.wait(.015))
                    self.assertEqual(json.loads(reader.read()), {"generation": 1})
            worker.join(timeout=1)
            self.assertTrue(done.is_set())
            self.assertEqual(errors, [])
            self.assertEqual(protocol.read_json(path), {"generation": 2})

    @unittest.skipUnless(os.name == "nt", "Semantica de handles de Windows")
    def test_reader_skips_busy_writer_without_waiting(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"cycle.json"
            values = []
            with protocol._ipc_guard(path, 0) as owned:
                self.assertTrue(owned)
                worker = threading.Thread(target=lambda: values.append(protocol.read_json(path)))
                worker.start()
                worker.join(timeout=1)
                self.assertFalse(worker.is_alive())
            self.assertEqual(values, [None])

    @unittest.skipUnless(os.name == "nt", "Mutex compartido entre procesos de Windows")
    def test_child_process_observes_the_same_ipc_mutex(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"cycle.json"
            atomic_json(path, {"generation": 1})
            code = ("import json,sys; from pathlib import Path; "
                    "from fishing_core.protocol import read_json; "
                    "print(json.dumps(read_json(Path(sys.argv[1]))))")
            with protocol._ipc_guard(path, 0) as owned:
                self.assertTrue(owned)
                result = subprocess.run([sys.executable, "-B", "-c", code, str(path)],
                                        cwd=str(Path(protocol.__file__).resolve().parent.parent),
                                        capture_output=True, text=True, timeout=5, check=True)
            self.assertIsNone(json.loads(result.stdout))
            self.assertEqual(protocol.read_json(path), {"generation": 1})

    def test_concurrent_reader_writer_never_observe_partial_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"cycle.json"
            atomic_json(path, {"generation": 0, "payload": "x"*500})
            done = threading.Event()
            errors = []
            def reader():
                try:
                    while not done.is_set():
                        value = protocol.read_json(path)
                        if value is not None:
                            self.assertEqual(value["payload"], "x"*500)
                except Exception as exc:
                    errors.append(repr(exc))
            worker = threading.Thread(target=reader)
            worker.start()
            try:
                for generation in range(1, 101):
                    atomic_json(path, {"generation": generation, "payload": "x"*500})
            finally:
                done.set()
                worker.join(timeout=5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(protocol.read_json(path)["generation"], 100)

    def test_transient_replace_denied_retries_same_complete_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"cycle.json"
            replace = os.replace
            calls = 0
            def transient(source, target):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise PermissionError("Sharing violation")
                replace(source, target)
            with patch.object(protocol.os, "replace", side_effect=transient):
                atomic_json(path, self.req)
            self.assertEqual(calls, 2)
            self.assertEqual(protocol.read_json(path), self.req)
            self.assertEqual(list(Path(temp).glob("*.tmp")), [])

    def test_persistent_replace_denied_is_bounded_and_preserves_old_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"cycle.json"
            atomic_json(path, {"old": True})
            with patch.object(protocol.os, "replace", side_effect=PermissionError("Denied")) as replace, \
                 patch.object(protocol.time, "sleep"):
                with self.assertRaises(PermissionError):
                    atomic_json(path, self.req)
            self.assertEqual(replace.call_count, protocol.REPLACE_ATTEMPTS)
            self.assertEqual(protocol.read_json(path), {"old": True})
            self.assertEqual(list(Path(temp).glob("*.tmp")), [])

    def test_read_denied_skips_without_sleep_then_stops_if_persistent(self):
        with patch.dict(protocol._read_denied_since, {}, clear=True), \
             patch.object(Path, "read_text", side_effect=PermissionError("Denied")), \
             patch.object(protocol.time, "perf_counter", side_effect=[1, 1.1, 1.6]), \
             patch.object(protocol.time, "sleep") as sleep:
            self.assertIsNone(protocol.read_json(Path("test.json")))
            self.assertIsNone(protocol.read_json(Path("test.json")))
            with self.assertRaises(PermissionError):
                protocol.read_json(Path("test.json"))
            sleep.assert_not_called()

    def test_invalid_json_is_not_silenced(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"cycle.json"
            path.write_text('{"incomplete":')
            with self.assertRaises(json.JSONDecodeError):
                protocol.read_json(path)


if __name__ == "__main__":
    unittest.main()
