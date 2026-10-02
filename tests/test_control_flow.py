import unittest

from fishing_core.control_flow import ControlFlow, SafetyStop
from fishing_core.vision import Evidence


class FlowTests(unittest.TestCase):
    def stable(self, f, kind, start, ack=False):
        e = Evidence(kind, (960, 970), True)
        f.step(e, start, ack)
        return f.step(e, start+.3, ack)

    def cast(self):
        f = ControlFlow("run", 0)
        self.assertEqual(self.stable(f, "START", 0).purpose, "START")
        self.assertEqual(self.stable(f, "CAST", .5).purpose, "CAST")
        return f

    def test_direct_reward_without_signal(self):
        f = self.cast()
        a = self.stable(f, "SUCCESS", 2)
        self.assertEqual(a.purpose, "TRADE")
        self.assertEqual(f.outcome_path, "DIRECT_REWARD")

    def test_no_trade_on_catch_even_with_signal(self):
        f = self.cast()
        self.assertIsNone(self.stable(f, "CATCH_ACTIVE", 2, True))
        self.assertEqual(f.state, "WAIT_RESULT")
        self.assertIsNone(self.stable(f, "CATCH_PENDING", 4, True))
        self.assertEqual(self.stable(f, "SUCCESS", 5, True).purpose, "TRADE")

    def test_failed_without_signal_is_closed(self):
        f = self.cast()
        f.step(Evidence("CATCH_ACTIVE"), 1)
        self.assertEqual(self.stable(f, "FAILED", 2).purpose, "CLOSE")
        self.assertEqual(f.outcome, "FAILED")

    def test_unconfirmed_catch_success_stops(self):
        f = self.cast()
        f.step(Evidence("CATCH_ACTIVE"), 1)
        with self.assertRaises(SafetyStop):
            self.stable(f, "SUCCESS", 2)

    def test_unknown_and_timeout_never_click(self):
        f = self.cast()
        self.assertIsNone(f.step(Evidence(), 5))
        with self.assertRaises(SafetyStop):
            f.step(Evidence(), 50)

    def test_start_behind_failed_is_not_a_new_cycle(self):
        f = self.cast()
        self.assertIsNone(self.stable(f, "START", 2))
        self.assertEqual(f.cycle_id, 1)

    def test_retries_bounded(self):
        f = self.cast()
        self.stable(f, "SUCCESS", 2)
        for t in (3.5, 5, 6.5):
            self.stable(f, "SUCCESS", t)
        with self.assertRaises(SafetyStop):
            self.stable(f, "SUCCESS", 8)

    def test_start_retry_keeps_same_cycle_and_is_bounded(self):
        f = ControlFlow("run", 0)
        first = self.stable(f, "START", 0)
        self.assertEqual(first.retry, 0)
        self.assertIsNone(f.step(Evidence("START", (960, 970), True), 1.1))
        retry = f.step(Evidence("START", (960, 970), True), 1.4)
        self.assertEqual((retry.purpose, retry.retry, retry.cycle_id, retry.attempt_id),
                         ("START", 1, first.cycle_id, first.attempt_id))
        retry = f.step(Evidence("START", (960, 970), True), 2.5)
        self.assertEqual(retry.retry, 2)
        with self.assertRaises(SafetyStop):
            f.step(Evidence("START", (960, 970), True), 3.6)
        self.assertEqual(f.cycle_id, 1)

    def test_start_retry_never_accepts_catch_or_unknown_or_menu(self):
        for kind in ("UNKNOWN", "SELECT_MENU", "CATCH_ACTIVE", "CATCH_PENDING"):
            f = ControlFlow("run", 0)
            self.stable(f, "START", 0)
            self.assertIsNone(self.stable(f, kind, 2), kind)
            self.assertEqual(f.retries, 0)

    def test_observed_cast_cancels_start_retries_and_does_not_retry_cast(self):
        f = ControlFlow("run", 0)
        self.stable(f, "START", 0)
        self.assertEqual(self.stable(f, "CAST", 1).purpose, "CAST")
        self.assertEqual(f.state, "WAIT_CAST_RESULT")
        self.assertIsNone(self.stable(f, "START", 3))
        self.assertIsNone(self.stable(f, "CAST", 5))
        self.assertEqual(f.cycle_id, 1)


if __name__ == "__main__":
    unittest.main()
