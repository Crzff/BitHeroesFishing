import unittest

from fishing_core.farm_budget import FarmBudget


class FarmBudgetTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.budget = FarmBudget(max_runs=2, max_energy=20, max_seconds=60,
                                 energy_reserve=5, clock=lambda: self.now)

    def enter(self, attempt="run:1", **fields):
        return self.budget.reserve_entry(attempt, **{
            "resource": "ENERGY", "balance": 25, "cost": 10, **fields})

    def finish(self, attempt="run:1", outcome="VICTORY", **fields):
        return self.budget.finish_run(attempt, outcome, **{
            "closure_confirmed": True, **fields})

    def test_entry_reserved_once_and_uncertain_input_blocks_another_intent(self):
        self.assertTrue(self.enter())
        self.assertFalse(self.enter())
        before = self.budget.payload()
        with self.assertRaises(ValueError):
            self.enter("run:2")
        self.assertEqual(self.budget.payload(), before)
        self.assertEqual(before["entries_reserved"], 1)
        self.assertEqual(before["energy_reserved"], 10)
        self.now += 61
        with self.assertRaises(ValueError):
            self.enter("run:2")
        self.assertEqual(self.budget.payload(), before)

    def test_only_confirmed_unique_result_releases_the_next_entry(self):
        with self.assertRaises(ValueError):
            self.finish()
        self.enter()
        for proof in (False, None, 1, "yes"):
            with self.subTest(proof=proof), self.assertRaises(ValueError):
                self.finish(closure_confirmed=proof)
        for outcome in (None, "UNKNOWN", "SUCCESS"):
            with self.subTest(outcome=outcome), self.assertRaises(ValueError):
                self.finish(outcome=outcome)
        self.assertTrue(self.finish())
        self.assertFalse(self.finish())
        with self.assertRaises(ValueError):
            self.finish(outcome="DEFEAT")
        self.assertFalse(self.enter())
        self.assertTrue(self.enter("run:2", balance=15))
        self.assertEqual(self.budget.payload()["completed_runs"], 1)

    def test_run_limit_and_energy_limit_are_independent_of_live_balance(self):
        for limits, costs in (({"max_runs": 1}, (10, 1)),
                              ({"max_energy": 11}, (10, 2))):
            with self.subTest(limits=limits):
                self.budget = FarmBudget(**{"max_runs": 2, "max_energy": 20,
                                             "max_seconds": 60, **limits})
                self.enter(cost=costs[0])
                self.finish()
                before = self.budget.payload()
                with self.assertRaises(ValueError):
                    self.enter("run:2", balance=9999, cost=costs[1])
                self.assertEqual(self.budget.payload(), before)

    def test_cost_is_reread_and_reserve_is_never_spent(self):
        with self.assertRaises(ValueError):
            self.enter(balance=14)
        self.assertTrue(self.enter(balance=15))
        self.finish()
        self.assertTrue(self.enter("run:2", balance=8, cost=3))
        self.assertEqual(self.budget.payload()["energy_reserved"], 13)

    def test_elapsed_deadline_and_clock_errors_block_entry_but_not_recording(self):
        self.enter()
        self.now += 60
        self.assertTrue(self.finish())
        before = self.budget.payload()
        for now in (160, 161, 99, None, True, float("nan"), float("inf")):
            with self.subTest(now=now):
                self.now = now
                with self.assertRaises(ValueError):
                    self.enter("run:2")
                self.assertEqual(self.budget.payload(), before)

    def test_defeat_is_recorded_and_stops_further_entries(self):
        self.enter()
        self.assertTrue(self.finish(outcome="DEFEAT"))
        with self.assertRaises(ValueError):
            self.enter("run:2")
        self.assertEqual(self.budget.payload()["stop_reason"], "DEFEAT")
        self.assertEqual(self.budget.payload()["completed_runs"], 1)

    def test_clock_rollback_within_session_window_is_not_a_new_allowance(self):
        self.now += 10
        self.enter()
        self.finish()
        before = self.budget.payload()
        self.now -= 1
        with self.assertRaises(ValueError):
            self.enter("run:2")
        self.assertEqual(self.budget.payload(), before)

    def test_unrepresentable_integer_times_have_the_same_safe_error(self):
        defaults = {"max_runs": 1, "max_energy": 10, "max_seconds": 60}
        with self.assertRaises(ValueError):
            FarmBudget(**{**defaults, "max_seconds": 10**1000})
        with self.assertRaises(ValueError):
            FarmBudget(**defaults, clock=lambda: 10**1000)
        with self.assertRaises(ValueError):
            FarmBudget(**{**defaults, "max_seconds": 5e-324}, clock=lambda: 100)
        self.now = 10**1000
        before = self.budget.payload()
        with self.assertRaises(ValueError):
            self.enter()
        self.assertEqual(self.budget.payload(), before)

    def test_invalid_readings_ids_and_other_resources_do_not_change_budget(self):
        before = self.budget.payload()
        for name in ("balance", "cost"):
            for value in (None, "10", True, -1, 1.5, float("nan"), float("inf")):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    self.enter(**{name: value})
                self.assertEqual(self.budget.payload(), before)
        for resource in (None, "SHARDS", "XEALS", "GEMS", "GOLD"):
            with self.subTest(resource=resource), self.assertRaises(ValueError):
                self.enter(resource=resource)
        for attempt in (None, "", " ", True, " run:1"):
            with self.subTest(attempt=attempt), self.assertRaises(ValueError):
                self.enter(attempt)
        with self.assertRaises(ValueError):
            self.enter(cost=0)
        self.assertEqual(self.budget.payload(), before)
        self.enter()
        for fields in ({"cost": 9}, {"resource": "SHARDS"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.enter(**fields)
        self.assertEqual(self.budget.payload()["energy_reserved"], 10)

    def test_invalid_limits_and_nonfinite_deadline_are_rejected(self):
        defaults = {"max_runs": 2, "max_energy": 20, "max_seconds": 60}
        for name in ("max_runs", "max_energy", "energy_reserve"):
            for value in (None, True, "1", -1, 1.5, float("inf")):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    FarmBudget(**{**defaults, name: value})
        for name in ("max_runs", "max_energy", "max_seconds"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                FarmBudget(**{**defaults, name: 0})
        for seconds in (None, True, "60", -1, float("nan"), float("inf")):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                FarmBudget(**{**defaults, "max_seconds": seconds})
        for now in (None, True, float("nan"), float("inf")):
            with self.subTest(now=now), self.assertRaises(ValueError):
                FarmBudget(**defaults, clock=lambda: now)
        with self.assertRaises(ValueError):
            FarmBudget(**{**defaults, "max_seconds": 1e308}, clock=lambda: 1e308)

    def enable_gold_budget(self, **limits):
        self.budget = FarmBudget(**{"max_runs": 2, "max_energy": 20, "max_seconds": 60,
                                    "max_gold": 100, "gold_reserve": 50,
                                    "clock": lambda: self.now, **limits})

    def gold(self, action="restock:1", **fields):
        return self.budget.reserve_gold(action, **{
            "currency": "GOLD", "purpose": "RESTOCK_COMMON", "target": "approved-common",
            "balance": 150, "cost": 30, **fields})

    def test_gold_disabled_by_default_and_premium_currency_never_admitted(self):
        before = self.budget.payload()
        with self.assertRaises(ValueError):
            self.gold()
        self.assertEqual(self.budget.payload(), before)
        self.enable_gold_budget()
        before = self.budget.payload()
        for currency in (None, "GEMS", "ENERGY", "SHARDS", "XEALS"):
            with self.subTest(currency=currency), self.assertRaises(ValueError):
                self.gold(currency=currency)
        for purpose in (None, "BRIBE", "CRAFT", "RESTOCK_SCARCE", "REVIVE", "RECHARGE"):
            with self.subTest(purpose=purpose), self.assertRaises(ValueError):
                self.gold(purpose=purpose)
        self.assertEqual(self.budget.payload(), before)

    def test_persuade_and_restock_share_one_gold_ceiling_and_preserve_balance(self):
        self.enable_gold_budget()
        self.assertTrue(self.gold(cost=40))
        self.assertTrue(self.budget.finish_gold("restock:1", effect_confirmed=True))
        self.enter()
        self.assertTrue(self.gold("offer:1", purpose="PERSUADE", target="Bob", cost=60, balance=110))
        self.budget.finish_gold("offer:1", effect_confirmed=True)
        self.finish()
        before = self.budget.payload()
        with self.assertRaises(ValueError):
            self.gold("restock:2", balance=9999, cost=1)
        self.assertEqual(self.budget.payload(), before)
        self.assertEqual(before["gold_reserved"], 100)
        self.enable_gold_budget()
        with self.assertRaises(ValueError):
            self.gold(balance=79)
        self.assertTrue(self.gold(balance=80))

    def test_uncertain_gold_action_blocks_spend_entry_and_result_until_resolved(self):
        self.enable_gold_budget()
        self.assertTrue(self.gold())
        self.assertFalse(self.gold())
        with self.assertRaises(ValueError):
            self.gold("restock:2")
        with self.assertRaises(ValueError):
            self.enter()
        with self.assertRaises(ValueError):
            self.budget.finish_gold("unknown", effect_confirmed=True)
        for proof in (False, None, 1, "yes"):
            with self.subTest(proof=proof), self.assertRaises(ValueError):
                self.budget.finish_gold("restock:1", effect_confirmed=proof)
        self.assertTrue(self.budget.finish_gold("restock:1", effect_confirmed=True))
        self.assertFalse(self.budget.finish_gold("restock:1", effect_confirmed=True))
        self.assertFalse(self.gold())
        self.assertTrue(self.enter())
        self.gold("offer:1", purpose="PERSUADE", target="Bob")
        with self.assertRaises(ValueError):
            self.finish()
        self.budget.finish_gold("offer:1", effect_confirmed=True)
        self.assertTrue(self.finish())

    def test_gold_phase_deadline_and_defeat_are_enforced(self):
        self.enable_gold_budget()
        with self.assertRaises(ValueError):
            self.gold("offer:1", purpose="PERSUADE", target="Bob")
        self.enter()
        with self.assertRaises(ValueError):
            self.gold()
        self.finish(outcome="DEFEAT")
        with self.assertRaises(ValueError):
            self.gold()
        self.enable_gold_budget()
        self.gold()
        self.now += 60
        self.budget.finish_gold("restock:1", effect_confirmed=True)
        with self.assertRaises(ValueError):
            self.gold("restock:2")

    def test_gold_invalid_values_and_conflicting_ids_do_not_change_totals(self):
        self.enable_gold_budget()
        before = self.budget.payload()
        for name in ("balance", "cost"):
            for value in (None, True, "30", -1, 1.5, float("nan"), float("inf")):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    self.gold(**{name: value})
        for field in ("target", "action"):
            for value in (None, "", " ", True):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.gold(**{field: value})
        with self.assertRaises(ValueError):
            self.gold(cost=0)
        self.assertEqual(self.budget.payload(), before)
        self.gold()
        before = self.budget.payload()
        for fields in ({"cost": 31}, {"target": "other-item"}, {"purpose": "PERSUADE"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.gold(**fields)
        self.assertEqual(self.budget.payload(), before)
        for name in ("max_gold", "gold_reserve"):
            for value in (None, True, "1", -1, 1.5):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    self.enable_gold_budget(**{name: value})


if __name__ == "__main__":
    unittest.main()
