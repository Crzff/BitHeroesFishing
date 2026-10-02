import unittest

from fishing_core.session_watch import SessionWatch


class SessionWatchTests(unittest.TestCase):
    def event(self,watch,kind,role="CONTROL",**fields):
        watch.apply({"run_id":"run","role":role,"event":kind,"attempt_id":"run:1",**fields})

    def inventory(self,watch,total=1):
        self.event(watch,"BAIT_INVENTORY",reliable=True,total=total)

    def cast(self,watch):
        self.event(watch,"CONTROL_INPUT_SENT",purpose="CAST",fresh_age_ms=12,full_cast_context_age_ms=100)
        self.event(watch,"BAIT_BUDGET_UPDATED",initial_total=1,attempts_debited=1,estimated_remaining=0)

    def close(self,watch,outcome="SUCCESS"):
        self.event(watch,"CYCLE_COMPLETE",outcome=outcome,outcome_path="CATCH",
                   closure_evidence={"stable_ms":650,"capture_age_ms":30})

    def test_zero_requires_last_confirmed_closure(self):
        watch=SessionWatch("run")
        self.inventory(watch)
        self.cast(watch)
        self.event(watch,"BAIT_BUDGET_REACHED")
        self.assertIn("Agotamiento sin cerrar el ultimo ciclo",watch.issues)
        good=SessionWatch("run")
        self.inventory(good)
        self.cast(good)
        self.close(good)
        self.event(good,"BAIT_BUDGET_REACHED")
        self.assertTrue(good.budget_reached)
        self.assertFalse(good.issues)

    def test_failed_is_review_not_empty(self):
        watch=SessionWatch("run")
        self.inventory(watch)
        self.cast(watch)
        self.close(watch,"FAILED")
        self.assertTrue(watch.issues)
        self.assertFalse(watch.budget_reached)

    def test_initial_zero_is_supported_but_ambiguity_not_zero(self):
        watch=SessionWatch("run")
        self.inventory(watch,0)
        self.event(watch,"BAIT_EXHAUSTED")
        self.assertTrue(watch.initially_empty)
        self.assertFalse(watch.issues)
        bad=SessionWatch("run")
        self.event(bad,"BAIT_EXHAUSTED")
        self.assertTrue(bad.issues)

    def test_duplicate_cast_and_catch_are_reported(self):
        watch=SessionWatch("run")
        self.inventory(watch)
        self.cast(watch)
        self.event(watch,"CONTROL_INPUT_SENT",purpose="CAST",fresh_age_ms=10,full_cast_context_age_ms=90)
        self.assertTrue(watch.issues)
        watch=SessionWatch("run")
        for _ in range(2):
            self.event(watch,"INPUT_SENT",role="CATCH",percentage=100,capture_start_ns=0,input_start_ns=5_000_000)
        self.assertTrue(watch.issues)

    def test_old_capture_non_100_and_unstable_closure_are_reported(self):
        for percent,age in ((99,5),(100,61),(100,-1)):
            watch=SessionWatch("run")
            self.event(watch,"INPUT_SENT",role="CATCH",percentage=percent,capture_start_ns=0,input_start_ns=age*1_000_000)
            self.assertTrue(watch.issues)
        watch=SessionWatch("run")
        self.inventory(watch)
        self.cast(watch)
        self.event(watch,"CYCLE_COMPLETE",outcome="SUCCESS",closure_evidence={"stable_ms":550,"capture_age_ms":20})
        self.assertTrue(watch.issues)

    def test_foreign_run_ignored_and_inventory_counted_once(self):
        watch=SessionWatch("run")
        watch.apply({"run_id":"old","role":"CONTROL","event":"SAFETY_STOP","reason":"old"})
        self.assertFalse(watch.issues)
        self.inventory(watch)
        self.inventory(watch)
        self.assertTrue(watch.issues)

    def test_start_after_zero_and_wrong_debit_are_reported(self):
        watch=SessionWatch("run")
        self.inventory(watch)
        self.cast(watch)
        self.event(watch,"CONTROL_INPUT_SENT",purpose="START")
        self.assertTrue(watch.issues)
        watch=SessionWatch("run")
        self.inventory(watch)
        self.event(watch,"BAIT_BUDGET_UPDATED",initial_total=1,attempts_debited=1,estimated_remaining=0)
        self.assertTrue(watch.issues)

    def test_real_maxima_are_counted_not_guaranteed(self):
        watch=SessionWatch("run")
        for cycle,value in enumerate((39,40,40),1):
            self.event(watch,"CAST_LOCK_OBSERVED",attempt_id=f"run:{cycle}",status="FROZEN_VALUE_OBSERVED",value=value,minimum=20,maximum=40)
        snapshot=watch.snapshot()
        self.assertEqual(snapshot["cast_frozen_values"],{39:1,40:2})
        self.assertEqual(snapshot["cast_maximum_hits"],2)
        self.assertTrue(snapshot["maximum_not_guaranteed"])

    def stopped(self,watch):
        self.event(watch,"PROCESS_STOP",dropped=0)
        self.event(watch,"PROCESS_STOP",role="CATCH",dropped=0)

    def test_final_zero_requires_catch_input_from_same_attempt_after_both_logs_drained(self):
        watch=SessionWatch("run")
        self.inventory(watch)
        self.cast(watch)
        self.close(watch)
        self.event(watch,"BAIT_BUDGET_REACHED")
        self.assertFalse(watch.issues)  # CONTROL puede vaciar su archivo antes que CATCH.
        self.event(watch,"INPUT_SENT",role="CATCH",percentage=100,capture_start_ns=0,input_start_ns=5_000_000)
        self.stopped(watch)
        self.assertEqual(watch.finalize(),"BAIT_ZERO_FINAL_CLOSURE_CONFIRMED")
        missing=SessionWatch("run")
        self.inventory(missing)
        self.cast(missing)
        self.close(missing)
        self.event(missing,"BAIT_BUDGET_REACHED")
        self.stopped(missing)
        self.assertEqual(missing.finalize(),"STOPPED_FOR_REVIEW")

    def test_missing_process_stop_cannot_be_presented_as_verified_empty(self):
        watch=SessionWatch("run")
        self.inventory(watch,0)
        self.event(watch,"BAIT_EXHAUSTED")
        self.assertEqual(watch.finalize(),"STOPPED_FOR_REVIEW")

    def test_invalid_budgets_do_not_mutate_remaining_or_confirm_zero(self):
        watch=SessionWatch("run")
        self.event(watch,"BAIT_BUDGET_UPDATED",initial_total=None,attempts_debited=1,estimated_remaining=0)
        self.assertIsNone(watch.remaining)
        self.event(watch,"BAIT_BUDGET_REACHED")
        self.assertFalse(watch.budget_reached)
        good=SessionWatch("run")
        self.inventory(good)
        self.event(good,"CONTROL_INPUT_SENT",purpose="CAST",fresh_age_ms=10,full_cast_context_age_ms=100)
        self.event(good,"BAIT_BUDGET_UPDATED",initial_total=1,attempts_debited=True,estimated_remaining=False)
        self.assertEqual(good.remaining,1)
        self.assertFalse(good.debits)

    def test_invalid_capture_age_has_explicit_issue_instead_of_type_error(self):
        for age in (None,"12",True,float("nan"),float("inf")):
            watch=SessionWatch("run")
            self.event(watch,"CONTROL_INPUT_SENT",purpose="CAST",fresh_age_ms=age,full_cast_context_age_ms=100)
            self.assertIn("CAST sin evidencia fresca",watch.issues)
        watch=SessionWatch("run")
        self.event(watch,"INPUT_SENT",role="CATCH",percentage=100,input_start_ns=None,capture_start_ns=0)
        self.assertTrue(watch.issues)

    def test_direct_reward_cannot_hide_a_catch_input_and_orphan_input_is_rejected(self):
        watch=SessionWatch("run")
        self.inventory(watch)
        self.cast(watch)
        self.event(watch,"CYCLE_COMPLETE",outcome="SUCCESS",outcome_path="DIRECT_REWARD",
                   closure_evidence={"stable_ms":650,"capture_age_ms":30})
        self.event(watch,"INPUT_SENT",role="CATCH",percentage=100,capture_start_ns=0,input_start_ns=5_000_000)
        self.stopped(watch)
        self.assertEqual(watch.finalize(),"STOPPED_FOR_REVIEW")
        orphan=SessionWatch("run")
        self.event(orphan,"INPUT_SENT",role="CATCH",percentage=100,capture_start_ns=0,input_start_ns=5_000_000)
        self.stopped(orphan)
        self.assertEqual(orphan.finalize(),"STOPPED_FOR_REVIEW")

    def test_duplicate_retained_values_are_not_counted_as_multiple_maxima(self):
        watch=SessionWatch("run")
        for _ in range(2):
            self.event(watch,"CAST_LOCK_OBSERVED",status="FROZEN_VALUE_OBSERVED",value=40,minimum=20,maximum=40)
        self.assertEqual(watch.maximum_hits,1)
        self.assertTrue(watch.issues)
