import json
import tempfile
import unittest
from pathlib import Path

from fishing_core.cast_test import pending_budget


class PendingCastTests(unittest.TestCase):
    def source(self,root):
        d=root/"runs"/"test_origin"
        d.mkdir(parents=True)
        events=[{"event":"AUTHORIZED_CAST_TEST"},
                {"event":"BAIT_INVENTORY","reliable":True,"total":13},
                {"event":"CONTROL_INPUT_SENT","purpose":"START","cycle_id":1,"attempt_id":"origin:1"},
                {"event":"CONTROL_INPUT_SENT","purpose":"CAST","cycle_id":1,"attempt_id":"origin:1"},
                {"event":"CYCLE_COMPLETE","cycle_id":1},
                {"event":"CONTROL_INPUT_SENT","purpose":"START","cycle_id":2,"attempt_id":"origin:2"},
                {"event":"SAFETY_STOP","reason":"Timeout WAIT_CAST; pantalla=CAST"}]
        (d/"control_events.jsonl").write_text("\n".join(json.dumps(e) for e in events),encoding="utf-8")
        (d/"cycle.json").write_text(json.dumps({"state":"WAIT_CAST","cycle_id":2}))
        return d,events

    def test_pending_cast_reuses_observation_and_only_previous_cast_debits(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            d,events=self.source(root)
            budget,info,marker=pending_budget(root,"test_origin")
            self.assertEqual((budget.initial_total,budget.remaining),(13,12))
            self.assertFalse(info["inventory_reopened"])
            self.assertTrue(info["remaining_is_estimate"])
            self.assertEqual(info["origin_pending_attempt"],"origin:2")
            self.assertEqual(marker,d/"cast_pending_resumed.json")
            self.assertFalse(marker.exists())

    def test_used_origin_and_any_sent_cast_in_pending_cycle_reject(self):
        for used in (False,True):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp)
                d,events=self.source(root)
                if used:
                    (d/"cast_pending_resumed.json").write_text("{}")
                else:
                    events.insert(-1,{"event":"CONTROL_INPUT_SENT","purpose":"CAST","cycle_id":2,"attempt_id":"origin:2"})
                    (d/"control_events.jsonl").write_text("\n".join(json.dumps(e) for e in events))
                with self.assertRaises(ValueError):
                    pending_budget(root,"test_origin")

    def test_path_traversal_and_non_test_session_are_not_resume_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            d,events=self.source(root)
            with self.assertRaises(ValueError):
                pending_budget(root,"../test_origin")
            (d/"control_events.jsonl").write_text("\n".join(json.dumps(e) for e in events[1:]))
            with self.assertRaises(ValueError):
                pending_budget(root,"test_origin")
