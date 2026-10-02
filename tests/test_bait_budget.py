import unittest

from fishing_core.bait_budget import BaitBudget


class BaitBudgetTests(unittest.TestCase):
    def test_each_identified_attempt_is_debited_at_most_once(self):
        budget=BaitBudget(2)
        self.assertTrue(budget.charge("run:1"))
        self.assertEqual(budget.remaining,1)
        self.assertFalse(budget.charge("run:1"))
        self.assertEqual(budget.remaining,1)
        budget.charge("run:2")
        self.assertEqual(budget.remaining,0)
        with self.assertRaises(ValueError):
            budget.charge("run:3")
        self.assertEqual(budget.payload()["attempts_debited"],2)
        self.assertTrue(budget.payload()["remaining_is_estimate"])

    def test_new_session_does_not_reuse_prior_budget(self):
        first=BaitBudget(1)
        first.charge("run:1")
        second=BaitBudget(1)
        self.assertEqual(second.remaining,1)
        self.assertNotEqual(first.charged_attempts,second.charged_attempts)

    def test_unknown_or_invalid_quantities_and_unidentified_attempts_are_rejected(self):
        for value in (None,-1,True,2.5,"103"):
            with self.assertRaises(ValueError):
                BaitBudget(value)
        for attempt in (None,"",1):
            with self.assertRaises(ValueError):
                BaitBudget(2).charge(attempt)
        with self.assertRaises(ValueError):
            BaitBudget(0).charge("run:1")
