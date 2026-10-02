import json
import tempfile
import unittest
from pathlib import Path

from fishing_core.panel_state import PanelState, SessionFeed


class PanelStateTests(unittest.TestCase):
    def event(self, kind, **fields):
        return {"run_id": "test", "role": "CONTROL", "event": kind, **fields}

    def test_input_is_not_success_and_direct_reward_is_distinct(self):
        state = PanelState("test")
        state.apply(self.event("STATE_TRANSITION", new="CATCH_GAME"))
        self.assertIn("CATCH", state.activity)
        state.apply(self.event("STATE_TRANSITION", new="WAIT_RESULT"))
        self.assertIn("esperando resultado", state.activity)
        self.assertNotIn("confirmada", state.outcome)
        state.apply(self.event("CONTROL_INPUT_SENT", purpose="TRADE", outcome="SUCCESS", outcome_path="CATCH"))
        self.assertIn("confirmada", state.outcome)
        self.assertEqual(state.activity, "Recogiendo ITEMS")
        state.apply(self.event("CONTROL_INPUT_SENT", purpose="TRADE", outcome="SUCCESS", outcome_path="DIRECT_REWARD"))
        self.assertIn("sin CATCH", state.outcome)

    def test_navigation_progress_does_not_claim_inventory_or_completed_fishing(self):
        state=PanelState("test")
        for kind,fields,text in (
            ("NAVIGATION_BEGIN",{},"Fishing"),
            ("NAVIGATION_INPUT_SENT",{"purpose":"OPEN_FISHING"},"Abriendo"),
            ("NAVIGATION_INPUT_SENT",{"purpose":"PLAY_FISHING"},"PLAY"),
            ("NAVIGATION_TRAVEL_WAIT",{},"Esperando al personaje"),
            ("NAVIGATION_READY",{"screen":"START"},"inventario inicial"),
        ):
            state.apply(self.event(kind,**fields))
            self.assertIn(text,state.activity)
            self.assertIsNone(state.bait_initial)
            self.assertEqual(state.completed,0)
            self.assertIsNone(state.cast_attempt)

    def test_initial_total_is_preserved_and_remaining_is_explicitly_estimated(self):
        state = PanelState("test")
        state.apply(self.event("BAIT_INVENTORY", reliable=True, total=103, stacks=[]))
        state.apply(self.event("CONTROL_INPUT_SENT", purpose="START"))
        self.assertEqual(state.bait_total, 103)
        state.apply(self.event("BAIT_BUDGET_UPDATED",initial_total=103,attempts_debited=1,estimated_remaining=102))
        state.apply(self.event("BAIT_INVENTORY", reliable=True, total=102, stacks=[]))
        self.assertEqual(state.bait_total, 103)
        self.assertEqual(state.bait_initial, 103)
        self.assertEqual(state.bait_remaining_estimate,102)
        self.assertIn("restantes estimados: 102", state.bait_label)
        self.assertIn("Cebos iniciales: 103",state.bait_label)

    def test_stale_session_and_final_events_cannot_overwrite_stop(self):
        state = PanelState("test")
        state.apply({"run_id": "old", "role": "CONTROL", "event": "BAIT_INVENTORY", "reliable": True, "total": 999})
        self.assertIsNone(state.bait_total)
        state.apply(self.event("BAIT_EXHAUSTED"))
        state.apply(self.event("HEARTBEAT", state="WAIT_CAST"))
        state.apply(self.event("RUN_LIMIT_REACHED", completed=3))
        self.assertIn("no quedan cebos", state.activity)

    def test_failed_read_does_not_misrepresent_remaining_baits(self):
        state = PanelState("test")
        state.apply(self.event("BAIT_INVENTORY", reliable=True, total=103, stacks=[]))
        state.apply(self.event("BAIT_READ_FAILED", reason="scroll"))
        self.assertIsNone(state.bait_total)
        self.assertTrue(state.terminal)

    def test_partial_jsonl_lines_and_old_sessions_are_not_consumed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"control_events.jsonl"
            feed = SessionFeed(Path(temp), "test")
            self.assertEqual(feed.read(), [])
            line = json.dumps(self.event("BAIT_INVENTORY", total=103))
            path.write_text(line[:20], encoding="utf-8")
            self.assertEqual(feed.read(), [])
            with path.open("a", encoding="utf-8") as f:
                f.write(line[20:]+"\n")
                f.write('{"run_id":"old"}\n')
            self.assertEqual(feed.read(), [json.loads(line)])
            self.assertEqual(feed.read(), [])

    def test_start_retry_is_reported_without_claiming_a_new_fishing_attempt(self):
        state=PanelState("test")
        state.apply(self.event("BAIT_INVENTORY",reliable=True,total=103,stacks=[]))
        state.apply(self.event("CONTROL_INPUT_SENT",purpose="START",retry=0))
        details=state.bait_details
        state.apply(self.event("CONTROL_INPUT_SENT",purpose="START",retry=1))
        self.assertIn("Reintentando START (1/2)",state.activity)
        self.assertEqual(state.bait_details,details)
        self.assertEqual(state.bait_total,103)
        self.assertEqual(state.completed,0)

    def test_budget_limit_does_not_claim_a_fresh_zero_inventory_read(self):
        state=PanelState("test")
        state.apply(self.event("BAIT_INVENTORY",reliable=True,total=1,stacks=[]))
        state.apply(self.event("BAIT_BUDGET_UPDATED",initial_total=1,attempts_debited=1,estimated_remaining=0))
        self.assertFalse(state.terminal)
        state.apply(self.event("BAIT_BUDGET_REACHED",initial_total=1,attempts_debited=1,estimated_remaining=0))
        self.assertTrue(state.terminal)
        self.assertIn("presupuesto inicial",state.activity)
        self.assertEqual(state.bait_total,1)

    def test_invalid_or_out_of_order_budget_updates_cannot_restore_baits(self):
        state=PanelState("test")
        state.apply(self.event("BAIT_INVENTORY",reliable=True,total=103,stacks=[]))
        state.apply(self.event("BAIT_BUDGET_UPDATED",initial_total=103,attempts_debited=2,estimated_remaining=101))
        for initial,debited,remaining in [(103,1,102),(104,2,102),(103,2,110)]:
            state.apply(self.event("BAIT_BUDGET_UPDATED",initial_total=initial,attempts_debited=debited,estimated_remaining=remaining))
        self.assertEqual(state.bait_remaining_estimate,101)

    def test_result_counters_require_unique_confirmed_closures_not_sent_inputs(self):
        state=PanelState("test")
        state.apply(self.event("CONTROL_INPUT_SENT",purpose="TRADE",outcome="SUCCESS",outcome_path="CATCH"))
        self.assertEqual(state.catch_successes,0)
        events=[self.event("CYCLE_COMPLETE",attempt_id="test:1",outcome="SUCCESS",outcome_path="CATCH"),
                self.event("CYCLE_COMPLETE",attempt_id="test:2",outcome="SUCCESS",outcome_path="DIRECT_REWARD"),
                self.event("CYCLE_COMPLETE",attempt_id="test:3",outcome="FAILED",outcome_path="CATCH")]
        for e in events+events:
            state.apply(e)
        self.assertEqual((state.completed,state.catch_successes,state.direct_rewards,state.failed),(3,1,1,1))
        self.assertIn("cierres: 3",state.result_summary)

    def test_cast_sent_value_is_never_shown_as_frozen_maximum(self):
        state=PanelState("test")
        state.apply(self.event("CONTROL_INPUT_SENT",purpose="CAST",attempt_id="test:1",
                               fresh_scores={"CAST_MAX":40,"CAST_VALUE":40}))
        self.assertIsNone(state.cast_value)
        self.assertIn("pendiente",state.cast_label)
        state.apply(self.event("CAST_LOCK_OBSERVED",attempt_id="test:1",status="FROZEN_VALUE_OBSERVED",
                               minimum=20,maximum=40,value=39))
        self.assertIn("39/40",state.cast_label)
        self.assertIn("máximos: 0/1",state.cast_label)

    def test_old_duplicate_or_unconfirmed_cast_does_not_inflate_maxima(self):
        state=PanelState("test")
        def sent(attempt):
            return self.event("CONTROL_INPUT_SENT",purpose="CAST",attempt_id=attempt,fresh_scores={"CAST_MAX":40})
        locked=self.event("CAST_LOCK_OBSERVED",attempt_id="test:1",status="FROZEN_VALUE_OBSERVED",
                          minimum=20,maximum=40,value=40)
        state.apply(sent("test:1"))
        state.apply(locked)
        state.apply(locked)
        self.assertEqual(state.cast_maximum_hits,1)
        state.apply(sent("test:2"))
        state.apply(locked)
        self.assertIsNone(state.cast_value)
        state.apply(self.event("CAST_LOCK_OBSERVED",attempt_id="test:2",status="FROZEN_VALUE_NOT_CONFIRMED"))
        self.assertIn("no confirmado",state.cast_label)
        self.assertEqual(state.cast_observations,1)
