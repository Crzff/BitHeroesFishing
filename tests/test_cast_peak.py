import unittest

from fishing_core.cast_peak import CastPeakPolicy
from fishing_core.vision import Evidence


class CastPeakTests(unittest.TestCase):
    def evidence(self,value,minimum=20,maximum=40):
        return Evidence("CAST",(960,970),value==maximum,scores={"CAST_MIN":minimum,"CAST_MAX":maximum,
                         "CAST_VALUE":value,"CAST_RANGE_VALID":True})

    def feed(self,policy,values=None,maximum=40):
        decision=None
        for index,value in enumerate(values or range(26,39)):
            mid=1_000_000_000+index*10_000_000
            decision=policy.sample(self.evidence(value,maximum=maximum),mid-2_000_000,mid+2_000_000,
                                   mid+3_000_000,1)
        return decision

    def test_rising_trace_predicts_peak_before_displayed_maximum(self):
        p=CastPeakPolicy(20)
        d=self.feed(p,range(26,38))
        self.assertTrue(d["ready"],d)
        self.assertEqual(d["value"],37)
        self.assertAlmostEqual(d["predicted_peak_ns"],1_140_000_000,delta=1)
        self.assertAlmostEqual(d["wait_ms"],6,delta=.001)

    def test_delay_changes_scheduled_input_not_measured_limits(self):
        early=self.feed(CastPeakPolicy(10),range(26,38))
        late=self.feed(CastPeakPolicy(30),range(26,38))
        self.assertEqual(early["maximum"],40)
        self.assertEqual(early["predicted_peak_ns"],late["predicted_peak_ns"])
        self.assertEqual(early["scheduled_input_ns"]-late["scheduled_input_ns"],20_000_000)

    def test_descending_or_static_history_never_claims_future_peak(self):
        for values in (list(range(40,27,-1)),[40]*12,[20]*12):
            self.assertFalse(self.feed(CastPeakPolicy(),values)["ready"])

    def test_missing_reading_new_cycle_and_changed_range_reset_history(self):
        for e,cycle in ((Evidence(),1),(self.evidence(37),2),(self.evidence(37,maximum=48),1)):
            p=CastPeakPolicy()
            self.feed(p,range(26,38))
            d=p.sample(e,1_119_000_000,1_121_000_000,1_122_000_000,cycle)
            self.assertFalse(d["ready"])
            self.assertLessEqual(len(p.history),1)

    def test_old_or_slow_capture_and_time_gap_do_not_authorize(self):
        for start,end,now in ((1_110_000_000,1_130_000_000,1_131_000_000),
                              (1_119_000_000,1_121_000_000,1_160_000_000),
                              (1_299_000_000,1_301_000_000,1_302_000_000)):
            p=CastPeakPolicy()
            self.feed(p,range(26,38))
            self.assertFalse(p.sample(self.evidence(38),start,end,now,1)["ready"])

    def test_bounds_are_validated_not_only_trusted_from_flag(self):
        p=CastPeakPolicy()
        e=self.evidence(45,minimum=40,maximum=20)
        self.assertFalse(p.sample(e,0,1,2,1)["ready"])

    def test_invalid_delay_rejected(self):
        for delay in (-1,81,float("nan"),float("inf")):
            with self.assertRaises(ValueError):
                CastPeakPolicy(delay)
