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

    def steam_trace(self,policy,verification=False):
        decisions=[]
        for index in range(26):
            mid=1_000_000_000+index*33_333_333
            phase=min(index/24,1)
            value=20+int(28*phase**3)
            decision=policy.sample(self.evidence(value,maximum=48),mid-13_000_000,
                                   mid+13_000_000,mid+16_000_000,1,verification=verification)
            decisions.append(decision)
        return decisions

    def test_steam_30_hz_trace_reproduces_old_starvation_but_new_profile_predicts(self):
        old=self.steam_trace(CastPeakPolicy())
        self.assertFalse(any(d["ready"] for d in old))
        self.assertTrue(all(d["reason"]=="CAST_NEEDS_RISING_HISTORY" for d in old))
        steam=self.steam_trace(CastPeakPolicy(client="Steam"))
        ready=[d for d in steam if d["ready"]]
        self.assertTrue(ready,steam)
        self.assertTrue(all(d["sampling_client"]=="Steam" and d["value"]<=48 for d in ready))
        self.assertTrue(any(d["value"]<48 for d in ready))
        self.assertTrue(all(d["samples"]>=4 and d.get("residual",0)<=.84 for d in ready))

    def test_steam_verification_wait_does_not_exceed_80_ms_total_freshness(self):
        decisions=self.steam_trace(CastPeakPolicy(client="Steam"),verification=True)
        ready=[d for d in decisions if d["ready"]]
        self.assertTrue(ready)
        self.assertTrue(all(d["wait_ms"]<=51 for d in ready))  # 29 ms from start to classification.

    def test_steam_slow_or_stale_verification_is_not_authorized(self):
        for duration,age in ((46_000_000,3_000_000),(26_000_000,31_000_000)):
            policy=CastPeakPolicy(client="Steam")
            self.steam_trace(policy)
            # Nueva historia ascendente: comprobar la guardia temporal y no
            # confundirla con la historia descendente del final de la curva.
            policy.history.clear()
            result=None
            for index,value in enumerate(range(25,45,2)):
                mid=3_000_000_000+index*33_333_333
                result=policy.sample(self.evidence(value,maximum=48),mid-duration//2,
                                     mid+duration//2,mid+duration//2+age,1,verification=True)
            self.assertFalse(result["ready"])
            self.assertEqual(result["reason"],"CAST_SAMPLE_TIMING_UNCERTAIN")

    def test_steam_descending_static_or_bad_measurement_still_cannot_click(self):
        for values in ([40]*12,list(range(48,24,-2)),[20]*12):
            policy=CastPeakPolicy(client="Steam")
            decisions=[]
            for index,value in enumerate(values):
                mid=1_000_000_000+index*33_333_333
                decisions.append(policy.sample(self.evidence(value,maximum=48),mid-13_000_000,
                                               mid+13_000_000,mid+16_000_000,1))
            self.assertFalse(any(d["ready"] for d in decisions))
        policy=CastPeakPolicy(client="Steam")
        self.steam_trace(policy)
        decision=policy.sample(Evidence(),3_000_000_000,3_001_000_000,3_002_000_000,1)
        self.assertFalse(decision["ready"])
        self.assertFalse(policy.history)

    def test_chrome_profile_limits_and_32_ms_delay_are_unchanged(self):
        config=CastPeakPolicy().configuration()
        self.assertEqual(config["client"],"Chrome")
        self.assertEqual(config["min_samples"],6)
        self.assertEqual(config["max_capture_ms"],15)
        self.assertEqual(config["game_delay_estimate_ms"],32)
        self.assertEqual(CastPeakPolicy(client="Steam").configuration()["game_delay_estimate_ms"],32)

    def test_invalid_sampling_client_is_rejected(self):
        for client in ("Auto","Brave",None):
            with self.assertRaises(ValueError):
                CastPeakPolicy(client=client)

    def test_steam_candidate_requires_fresh_exact_maximum_and_never_static_history(self):
        policy=CastPeakPolicy(client="Steam")
        last=None
        for index,value in enumerate((32,36,40,44)):
            mid=1_000_000_000+index*33_333_333
            last=policy.sample(self.evidence(value,maximum=48),mid-13_000_000,
                               mid+13_000_000,mid+16_000_000,1)
        self.assertTrue(last["ready"])
        self.assertEqual(last["reason"],"STEAM_FRESH_MAXIMUM_CANDIDATE")
        mid=1_133_333_332
        fresh=policy.sample(self.evidence(48,maximum=48),mid-13_000_000,
                            mid+13_000_000,mid+16_000_000,1,verification=True)
        self.assertTrue(fresh["ready"])
        self.assertEqual(fresh["reason"],"STEAM_FRESH_DISPLAYED_MAXIMUM")
        self.assertNotIn("predicted_peak_ns",fresh)
        self.assertTrue(fresh["displayed_maximum_is_not_guaranteed_retained_maximum"])
        self.assertFalse(any(d["ready"] for d in self.steam_trace(CastPeakPolicy())))

    def test_steam_fresh_maximum_still_rejects_slow_or_old_capture(self):
        for duration,age in ((46_000_000,3_000_000),(26_000_000,31_000_000)):
            policy=CastPeakPolicy(client="Steam")
            for index,value in enumerate((32,36,40,44)):
                mid=1_000_000_000+index*33_333_333
                policy.sample(self.evidence(value,maximum=48),mid-13_000_000,mid+13_000_000,mid+16_000_000,1)
            mid=1_133_333_332
            fresh=policy.sample(self.evidence(48,maximum=48),mid-duration//2,mid+duration//2,
                                mid+duration//2+age,1,verification=True)
            self.assertFalse(fresh["ready"])
            self.assertEqual(fresh["reason"],"CAST_SAMPLE_TIMING_UNCERTAIN")
