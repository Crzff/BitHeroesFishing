import json
import csv
import tempfile
import unittest
from pathlib import Path

from fishing_core.telemetry import Telemetry, new_run_id


class TelemetryTests(unittest.TestCase):
    def test_complete_per_run_records(self):
        with tempfile.TemporaryDirectory() as temp:
            t = Telemetry("CATCH", new_run_id(), Path(temp))
            t.emit("INPUT_SENT", human=True, cycle_id=3, attempt_id="abc", input_ms=1.2)
            t.close()
            events = [json.loads(s) for s in t.path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([e["event"] for e in events], ["PROCESS_START", "INPUT_SENT", "PROCESS_STOP"])
            self.assertTrue(all(e["run_id"] == t.run_id and e["perf_ns"] > 0 for e in events))
            self.assertEqual(events[1]["cycle_id"], 3)

    def test_run_ids_unique(self):
        self.assertNotEqual(new_run_id(), new_run_id())

    def test_uniform_samples_and_nonfinite_diagnostics(self):
        with tempfile.TemporaryDirectory() as temp:
            t=Telemetry("CATCH",new_run_id(),Path(temp))
            t.emit("CATCH_FRAME",phase="pre",detected=False,reason="SIN_ZONA",delta=float("inf"))
            t.emit("CATCH_FRAME",phase="locked",detected=True,cp=500,cv=500)
            t.close()
            with (t.directory/"catch_samples_R1.csv").open(encoding="utf-8") as samples:
                rows=list(csv.DictReader(samples))
            self.assertEqual(len(rows),2)
            self.assertEqual(rows[0]["delta"],"")
            self.assertEqual(rows[1]["phase"],"locked")
            events=[json.loads(s) for s in t.path.read_text().splitlines()]
            self.assertIsNone(events[1]["delta"])


if __name__ == "__main__":
    unittest.main()
