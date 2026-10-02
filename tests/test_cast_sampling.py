import unittest

from fishing_core.cast_sampling import CAST_MONITOR,CastSampler
from fishing_core.vision import Evidence


class CastSamplingTests(unittest.TestCase):
    def test_no_local_sampling_without_full_cast_or_outside_wait_cast(self):
        sampler=CastSampler()
        self.assertFalse(sampler.use_local("WAIT_CAST",0))
        for kind in ("START","SELECT_MENU","SUCCESS","FAILED","ITEMS","CATCH_ACTIVE","UNKNOWN"):
            sampler.observe_full(Evidence(kind,(960,970),True),0)
            self.assertFalse(sampler.use_local("WAIT_CAST",1))
        sampler.observe_full(Evidence("CAST",(960,970),False),0)
        self.assertTrue(sampler.use_local("WAIT_CAST",1))
        self.assertFalse(sampler.use_local("WAIT_CAST_RESULT",2))
        self.assertFalse(sampler.use_local("WAIT_CAST",3))

    def test_full_context_expires_at_200_ms_even_with_continuous_local_detections(self):
        sampler=CastSampler()
        e=Evidence("CAST",(960,970),True)
        sampler.observe_full(e,100)
        for delta in (1,50_000_000,139_999_999):
            self.assertTrue(sampler.use_local("WAIT_CAST",100+delta))
            self.assertIs(sampler.local_evidence(e),e)
        self.assertFalse(sampler.use_local("WAIT_CAST",140_000_100))
        self.assertTrue(sampler.current(199_999_999))
        self.assertFalse(sampler.use_local("WAIT_CAST",200_000_100))
        self.assertFalse(sampler.current(99))

    def test_lost_or_moved_text_requires_full_reclassification(self):
        for e in (Evidence("UNKNOWN"),Evidence("CATCH_ACTIVE",(960,970),True),
                  Evidence("CAST",(964,970),True),Evidence("CAST",None,True)):
            sampler=CastSampler()
            sampler.observe_full(Evidence("CAST",(960,970),True),0)
            self.assertFalse(sampler.local_evidence(e).ready)
            self.assertFalse(sampler.current(1))

    def test_missing_number_is_not_ready_but_can_continue_sampling_same_cast_text(self):
        sampler=CastSampler()
        sampler.observe_full(Evidence("CAST",(960,970),False),0)
        e=Evidence("CAST",(963,969),False)
        self.assertIs(sampler.local_evidence(e),e)
        self.assertFalse(e.ready)
        self.assertTrue(sampler.current(1))

    def test_monitor_contains_number_and_active_button_only(self):
        self.assertEqual(CAST_MONITOR,{"left":830,"top":775,"width":260,"height":245})
        self.assertLess(CAST_MONITOR["width"]*CAST_MONITOR["height"],1920*1080*.04)

    def test_changed_range_cannot_use_previous_full_context(self):
        sampler=CastSampler()
        sampler.observe_full(Evidence("CAST",(960,970),False,scores={"CAST_MIN":20,"CAST_MAX":40}),0)
        status=Evidence("CAST",(960,970),True,scores={"CAST_MIN":20,"CAST_MAX":48})
        self.assertFalse(sampler.local_evidence(status).ready)
        self.assertFalse(sampler.current(1))
