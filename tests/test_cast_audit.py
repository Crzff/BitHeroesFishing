import unittest

from fishing_core.cast_audit import CastAudit


class CastAuditTests(unittest.TestCase):
    def audit(self):
        audit=CastAudit()
        audit.sent(1,"run:1",20,40,0)
        return audit

    def measured(self,value=40,minimum=20,maximum=40):
        return {"CAST_MIN":minimum,"CAST_MAX":maximum,"CAST_VALUE":value,"CAST_RANGE_VALID":True}

    def test_inactive_button_stable_value_after_input_can_confirm_peak(self):
        a=self.audit()
        for ns in (100_000_000,150_000_000):
            self.assertIsNone(a.observe(self.measured(),False,ns))
        result=a.observe(self.measured(),False,200_000_000)
        self.assertTrue(result["at_displayed_maximum"])
        self.assertEqual(result["value"],40)
        self.assertIsNone(a.pending)

    def test_post_input_lower_value_is_reported_honestly_not_as_peak(self):
        a=self.audit()
        for ns in (100_000_000,150_000_000,200_000_000):
            result=a.observe(self.measured(39),False,ns)
        self.assertFalse(result["at_displayed_maximum"])
        self.assertEqual(result["value"],39)

    def test_active_cast_or_wrong_range_does_not_credit_locked_value(self):
        for active,measurement in ((True,self.measured()),(False,self.measured(maximum=48))):
            a=self.audit()
            for ns in (100_000_000,150_000_000,200_000_000):
                self.assertIsNone(a.observe(measurement,active,ns))

    def test_single_or_too_early_frame_cannot_prove_game_received_peak(self):
        a=self.audit()
        for ns in (1,40_000_000,80_000_000,100_000_000):
            self.assertIsNone(a.observe(self.measured(),False,ns))

    def test_missing_measurement_expires_as_unconfirmed_not_success(self):
        a=self.audit()
        result=a.observe({},False,2_000_000_001)
        self.assertEqual(result["status"],"FROZEN_VALUE_NOT_CONFIRMED")
        self.assertNotIn("at_displayed_maximum",result)
